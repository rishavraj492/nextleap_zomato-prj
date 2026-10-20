# Evaluation

Acceptance checks for the restaurant recommender, phase by phase, from [implementation-plan.md](implementation-plan.md).

A phase passes only when every check in that phase passes. Later phases must keep earlier checks passing. The default suite uses `backend/data/fixtures/zomato_sample.csv`, a fake model client, and no network.

Corner inputs and the required outcomes are listed in [edge-case.md](edge-case.md). This document says how to judge the build, not how each input is parsed.

## Rules

- Run backend tests from `backend/` with `pytest`. The run must exit 0.
- `pytest` must not download Hugging Face and must not call a live model. It must not need `LLM_API_KEY`.
- Phases 0–4 are judged by tests and API responses. Phases 5–7 add a browser pass.
- Catalog facts on a card (name, cuisine, rating, cost, location) come from the catalog. A model-written number that disagrees with the card fails the check.
- Accounts, booking, live Zomato search, embeddings, maps, cities outside Bengaluru, and fine-tuning are out of scope. Missing those features is a pass.

## Commands

```text
cd backend
pytest

uvicorn app.main:app --reload

cd frontend
npm run dev
```

Prepare the fixture catalog before Phase 1 checks that read parquet:

```text
cd backend
python scripts/prepare_dataset.py --source fixture
```

## Phase 0 — Scaffold

| Check | Pass when |
| --- | --- |
| Dependencies | `backend/requirements.txt` includes FastAPI, Uvicorn, Pydantic, pandas, pyarrow, datasets, httpx, and pytest. |
| Config | `backend/app/config.py` defines low as under 500, medium as 500–1000 inclusive, high as above 1000, `CANDIDATE_CAP = 20`, `RESULT_CAP = 5`, and a default model timeout of 20 seconds. Environment variables can override the catalog path, model name, base URL, and timeout. |
| Health | `GET /api/health` returns process status. `catalogLoaded: false` is acceptable until Phase 2. |
| CORS | The Vite dev origin is allowed. |
| Env template | `backend/.env.example` documents `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `CATALOG_PATH`, and `LLM_TIMEOUT_SECONDS`. |
| Frontend | `npm run dev` shows a page with the project title. |
| Gitignore | `.env`, `__pycache__`, `node_modules`, `backend/data/restaurants.parquet`, and frontend build output are ignored. `backend/data/fixtures/` is not ignored. |
| Tests | `pytest` exits 0. |

## Phase 1 — Catalog preparation

| Check | Pass when |
| --- | --- |
| Fixture columns | `zomato_sample.csv` has `url`, `address`, `name`, `online_order`, `book_table`, `rate`, `votes`, `phone`, `location`, `rest_type`, `dish_liked`, `cuisines`, `approx_cost(for two people)`, `reviews_list`, `menu_item`, `listed_in(type)`, and `listed_in(city)`. |
| Fixture coverage | The file includes a restaurant listed twice under different `listed_in(type)` values, rates `4.1/5`, `NEW`, `-`, and blank, costs `300`, `1,200`, and blank, one multi-cuisine row, and one null cuisine. |
| Offline prepare | `python scripts/prepare_dataset.py --source fixture` finishes with no network and writes parquet plus `facets.json`. |
| Hugging Face flag | `--source huggingface` is a separate flag and is not the default. |
| Rating parse | `4.1/5` becomes `4.1`. `NEW`, `-`, and blank become null. |
| Cost parse | `1,200` becomes `1200`. Blank and non-numeric costs become null. |
| Cuisines | Display string keeps original casing. Tokens are trimmed and lowercase. |
| Dedup | Same name and address collapse to one id. The kept row has the most votes. Cuisine tokens and `listed_in(type)` are unioned. |
| Stable id | Preparing the fixture twice yields the same id for the same name and address. |
| Dropped fields | Parquet has no `reviews_list`, `menu_item`, or `phone`. |
| Tests | `backend/tests/test_prepare.py` covers rating parse, cost parse, dedup, cuisine tokens, and stable ids, and passes offline. |

## Phase 2 — Load, facets, and hard filters

| Check | Pass when |
| --- | --- |
| Startup load | The API loads `CATALOG_PATH` into memory and can look up a restaurant by id. |
| Missing file | If parquet is missing, the process exits and the log names `prepare_dataset.py`. |
| Indexes | Location and cuisine lookups are available for filtering. |
| Location | Normalized exact match. A different neighborhood does not match. |
| Cuisine | Several selected cuisines are OR. One overlapping token is enough. |
| Budget edges | 499 is low, 500 and 1000 are medium, 1001 is high. |
| Null cost | A restaurant with null `cost_for_two` is excluded when a budget is set. |
| Null rating | A restaurant with null `rating` is excluded when a minimum is set. A rating equal to the minimum is included. |
| Facets | `GET /api/facets` returns only locations and cuisines present in the loaded catalog, lowercase cuisine tokens, budgets `low`, `medium`, `high`, and rating bounds 0 and 5. |
| Facets before load | `GET /api/facets` returns 503 if the catalog is not loaded. |
| Health | `GET /api/health` includes `catalogLoaded: true` and `restaurantCount` equal to the fixture catalog. |
| Tests | `backend/tests/test_filter.py` covers the budget edges, cuisine OR, null rating, and null cost, and passes with no model key. |

## Phase 3 — Recommendations without the model

Judge this phase with the model client unwired, or with explanations forced unavailable. Phase 4 replaces the success path.

| Check | Pass when |
| --- | --- |
| Request schema | Body accepts `location`, `budget`, `cuisines`, `minRating`, optional `preferences` (max 500 characters), and optional `limit` (default 5, maximum 5). |
| Response schema | Body includes `summary`, `explanations`, `matchedCount`, and `recommendations`. Each item has id, name, cuisines, location, rating, votes, cost for two, rest type, and reason. |
| Unknown location | HTTP 422. |
| Unknown budget | HTTP 422, including wrong case such as `Medium`. |
| Rating out of range | Below 0 or above 5 returns HTTP 422. |
| Empty cuisines | HTTP 422. |
| Preferences length | 500 characters is accepted. 501 returns HTTP 422. |
| `limit` | Omitted means 5. `0`, `6`, and negative values return HTTP 422. |
| Sort | Results are ordered by rating descending, then votes descending, then name ascending. Two identical requests return the same order. |
| Caps | At most 20 candidates are kept internally. The response contains at most `limit` rows. |
| `matchedCount` | Equals the number of restaurants that passed the filters, including rows past the first page. |
| Zero matches | HTTP 200, `explanations: "skipped"`, `matchedCount: 0`, empty `recommendations`, summary names the location. No model call. |
| Some matches, model not used yet | HTTP 200, `reason: null`, `explanations: "unavailable"`, summary says these are the highest-rated matches. |
| Catalog fields | Name, cuisine, rating, and cost on each item exist on that catalog row and satisfy the filters. |
| Tests | The API test covers 422 for an unknown location, 200 with the documented shape, and 200 for an empty match. The run does not download Hugging Face and does not read `LLM_API_KEY`. |

## Phase 4 — LLM ranking, reasons, and fallback

Use a fake client in `pytest`. A live key is not required to pass this phase.

| Check | Pass when |
| --- | --- |
| Model schema | The parsed model payload is `summary` plus `recommendations[{id, reason}]` only. |
| Prompt rules | The system prompt limits picks to supplied ids, ranks for the free-text preference, asks for two or three sentences that cite cuisine, cost, rest type, or liked dishes, forbids invented dishes, reviews, and awards, and requires JSON only. |
| Prompt contents | The user message includes structured preferences, the free-text preference or `none`, and at most 20 shortlist records. Records include id, name, cuisines, rating, votes, cost for two, rest type, and truncated liked dishes. Phone and reviews are absent. |
| Client | Calls an OpenAI-compatible chat endpoint using `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`, with a JSON schema, temperature about 0.2, and `LLM_TIMEOUT_SECONDS`. |
| Happy path | Valid ids come back in the model’s order, with reasons and `explanations: "available"`. The summary is the model summary. |
| Catalog wins | If the model echoes a different rating or cost, the response still shows the catalog value. |
| Unknown id | Dropped. |
| Duplicate id | The second copy is dropped. |
| Too many ids | The list is cut to `limit` after the guard. |
| All ids invalid, or an empty recommendation array | Selector order, `reason: null`, `explanations: "unavailable"`. |
| Long reason | Reason text is capped before it reaches the client. |
| Timeout, HTTP error, or prose | HTTP 200, selector order, null reasons, `explanations: "unavailable"`, summary says explanations are temporarily unavailable. |
| Zero matches | The fake client is not called. `explanations` stays `"skipped"`. |
| Logs | Latency, token usage when present, and whether fallback ran are logged. The API key and the full prompt are not logged. |
| Tests | `test_guard.py` and `test_recommend_fallback.py` cover the cases above. `pytest` does not contact a live provider. |

## Phase 5 — Preference form and result cards

Start the API on the fixture catalog and the Vite app. Submit through the browser.

| Check | Pass when |
| --- | --- |
| Facets on load | The location list and cuisine list match `GET /api/facets`. |
| Location control | The user can search and select a neighborhood. City names such as Delhi are not offered. |
| Budget | Three choices. The initial value is medium. |
| Cuisine | At least one cuisine is required. Labels are title case. The request body sends the lowercase token. |
| Rating | Control runs from 0 to 5 in steps of 0.5. The initial value is 3.5. |
| Preferences | Textarea is optional and stops at 500 characters. |
| Pending | The submit button disables and shows a pending label until the response arrives. |
| Success | A known location and cuisine show the summary, when present, and at most five cards. Each card shows name, cuisine, rating, cost for two, location, and reason. |
| Client purity | The browser does not reorder results, drop rows the API returned, or call the model directly. |
| Facets stay in sync | Removing a location or cuisine from the fixture and reloading facets removes it from the form. |

## Phase 6 — Empty, error, and unavailable states

| Check | Pass when |
| --- | --- |
| No matches | A query with `explanations: "skipped"` and an empty list shows an empty state that names the location and suggests relaxing the rating or changing budget. No error banner. No cards. |
| Explanations unavailable | Cards still show name, rating, cuisine, and cost. The API summary is shown. A note says written reasons are temporarily unavailable. |
| HTTP 422 | The validation message appears next to the form. The values the user entered stay filled in. |
| Select safety | A location that is not in the facets cannot be submitted from the control. |
| Direct 422 | A 422 produced outside the form, such as a manual request, is still rendered if the UI receives it. |
| Network error or HTTP 500 | A retry message is shown. Cards from the last success stay on screen. |
| Catalog not ready | Facets 503 or a failed facets load disables submit and says the catalog is not ready. |
| Form retention | After a failed submit, the form still holds the entered values for that visit. |

## Phase 7 — Full catalog and a live model

This pass is manual. It uses the real dataset once. `pytest` still uses the fixture.

| Check | Pass when |
| --- | --- |
| Prepare | `python scripts/prepare_dataset.py --source huggingface` writes `backend/data/restaurants.parquet`, and `CATALOG_PATH` points at that file. |
| Health | `restaurantCount` is below the raw 51,700 rows. |
| Facets | Locations are Bengaluru neighborhoods, not other cities. |
| Live query | Banashankari, medium budget, North Indian, minimum rating 4, preference “family-friendly” returns HTTP 200 and at most five restaurants. |
| Filter hold | Every returned rating is at least 4, every cost for two is from 500 to 1000 inclusive, the location is Banashankari, and North Indian is among the cuisines. |
| Reasons | Each reason refers to fields visible on that card (cuisine, cost, rating, rest type, or liked dishes). It does not add an award, a review quote, or a dish that is not on the card. |
| Provider down | With the key removed, or `LLM_BASE_URL` pointed at a closed port, the same style of query still returns HTTP 200, cards with catalog facts, and `explanations: "unavailable"`. |
| Regression | `pytest` from `backend/` still exits 0 with no live provider. |

## Release gate

The project is accepted when all of the following are true:

1. Phases 0 through 7 pass.
2. `pytest` exits 0 on the fixture, with no Hugging Face download and no live model call.
3. The browser flow covers a successful recommendation, an empty match, and explanations unavailable.
4. `.env` and `LLM_API_KEY` are absent from the committed tree.
5. No out-of-scope feature was required to pass a check.

Record the result as pass or fail per phase:

| Phase | Result | Evidence |
| --- | --- | --- |
| 0 Scaffold | | |
| 1 Catalog | | |
| 2 Filters | | |
| 3 Ranked API | | |
| 4 Explanations | | |
| 5 Results UI | | |
| 6 Edge states | | |
| 7 Live catalog | | |
