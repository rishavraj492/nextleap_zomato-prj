# Implementation Plan

Phase-by-phase build of the restaurant recommender in [problemStatement.md](problemStatement.md), following [architecture.md](architecture.md).

Each phase leaves the repo runnable and tested. Later phases add behavior on top of earlier ones. Do not call Hugging Face or a live model from the default test suite.

## How the phases map to the product

| Phase | Problem-statement step | What exists when the phase ends |
| --- | --- | --- |
| 0. Scaffold | — | Backend and frontend projects, config, and a test runner |
| 1. Catalog | Data ingestion | Clean parquet from the Zomato dataset, plus a tiny fixture |
| 2. Filter | Integration layer, hard constraints | In-memory catalog, facets, and filters for location, cuisine, budget, and rating |
| 3. Ranked API | Integration layer, candidate prep | `POST /api/recommendations` ordered by rating and votes, no model yet |
| 4. Explanations | Recommendation engine | LLM ranking, reasons, summary, and fallback when the model fails |
| 5. Results UI | User input and output display | Form and cards for a successful recommendation |
| 6. Edge states | Output display | Empty matches, validation errors, and missing explanations |
| 7. Real catalog check | End-to-end workflow | One manual pass against the full Bengaluru catalog and a live model |

## Working agreements

- Python 3.11+, FastAPI, Pydantic, pandas, pyarrow, and the Hugging Face `datasets` library on the backend. React + Vite on the frontend.
- Budget bands, candidate cap (20), and result cap (5) live in `backend/app/config.py`.
- Location values are Bengaluru neighborhoods from the catalog (`Banashankari`, `Koramangala 5th Block`), not city names.
- The model returns ids and reasons only. Name, cuisine, rating, and cost always come from the catalog.
- Secrets stay in environment variables. `LLM_API_KEY` is never committed or sent to the browser.
- Out of scope for every phase: accounts, booking, live Zomato search, embeddings, maps, cities outside Bengaluru, and fine-tuning.

```text
backend/
  app/
    main.py
    config.py
    api/facets.py
    api/recommendations.py
    schemas/request.py
    schemas/response.py
    schemas/llm.py
    services/catalog.py
    services/filter.py
    services/select.py
    services/recommend.py
    services/llm_client.py
    services/prompt.py
  scripts/prepare_dataset.py
  tests/
  data/
frontend/
  src/App.tsx
  src/api.ts
  src/components/PreferenceForm.tsx
  src/components/Results.tsx
```

Create files in the phase that first needs them. Empty modules are not required up front.

---

## Phase 0 — Scaffold

**Outcome.** A developer can install dependencies, start the API, start the web app, and run an empty test suite.

**Tasks**

1. Create the backend package layout above and a `backend/requirements.txt` with FastAPI, Uvicorn, Pydantic, pandas, pyarrow, datasets, httpx, and pytest.
2. Add `backend/app/config.py` with budget bands (low under 500, medium 500–1000 inclusive, high above 1000), `CANDIDATE_CAP = 20`, `RESULT_CAP = 5`, catalog path, model name, base URL, and timeout (default 20 seconds). Read overrides from the environment.
3. Add `backend/app/main.py` with a FastAPI app, CORS for the Vite dev origin, and `GET /api/health` returning process status. Catalog-loaded can be `false` until Phase 2.
4. Add `backend/.env.example` documenting `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `CATALOG_PATH`, and `LLM_TIMEOUT_SECONDS`.
5. Scaffold the Vite React app in `frontend/` with a single page that renders the project title.
6. Add a root `.gitignore` for `.env`, `__pycache__`, `node_modules`, `backend/data/restaurants.parquet`, and frontend build output. Keep `backend/data/fixtures/` commit-able.

**Done when**

- `uvicorn app.main:app` from `backend/` serves `GET /api/health`.
- `npm run dev` in `frontend/` shows the placeholder page.
- `pytest` from `backend/` exits 0.

---

## Phase 1 — Catalog preparation

**Outcome.** Raw Zomato rows become one restaurant per name and address, with parsed rating and cost. Tests use a checked-in fixture and never download the dataset.

**Tasks**

1. Add `backend/data/fixtures/zomato_sample.csv` with a handful of rows that mirror the real columns: `url`, `address`, `name`, `online_order`, `book_table`, `rate`, `votes`, `phone`, `location`, `rest_type`, `dish_liked`, `cuisines`, `approx_cost(for two people)`, `reviews_list`, `menu_item`, `listed_in(type)`, `listed_in(city)`. Include:
   - The same restaurant listed twice under different `listed_in(type)` values
   - `rate` values `4.1/5`, `NEW`, `-`, and blank
   - Costs `300`, `1,200`, and blank
   - A row with several cuisines and a row with null cuisines
2. Implement `backend/scripts/prepare_dataset.py` so it can read either a local CSV or the Hugging Face dataset `ManikaSaini/zomato-restaurant-recommendation`:
   - Parse `rate` to a float. `NEW`, `-`, and blanks become null.
   - Parse cost by stripping commas. Non-numeric values become null.
   - Split cuisines on commas, trim, and lowercase into `cuisine_tokens`. Keep the original display string.
   - Normalize `online_order` and `book_table` to booleans.
   - Deduplicate on `name` + `address`. Keep the row with the most votes. Union cuisine tokens and `listed_in(type)` across duplicates.
   - Set `id` to a stable hash of `name` + `address`.
   - Drop `reviews_list`, `menu_item`, and `phone`.
   - Truncate `dish_liked` to a short string for prompts.
   - Write `restaurants.parquet` and `facets.json` (sorted unique locations and cuisine tokens).
3. Point the default CLI at the fixture so `python scripts/prepare_dataset.py --source fixture` works with no network. A separate `--source huggingface` flag downloads the real dataset.
4. Add `backend/tests/test_prepare.py` for rating parse, cost parse, dedup, cuisine tokens, and stable ids.

**Done when**

- The fixture run writes parquet and facets.
- Duplicate listings collapse to one id.
- `4.1/5` becomes `4.1`, and `NEW` / `-` / blank become null.
- `1,200` becomes `1200`.
- Tests pass offline.

---

## Phase 2 — Load, facets, and hard filters

**Outcome.** The API serves form options from the catalog and can answer “which restaurants match these constraints?” without a model.

**Tasks**

1. Implement `backend/app/services/catalog.py` to read parquet into restaurant objects and build a location → restaurants map and a cuisine token → restaurants map. Look up by `id`.
2. Load the catalog at startup from `CATALOG_PATH`. If the file is missing, exit with a log line that names `prepare_dataset.py`.
3. Implement `backend/app/services/filter.py`:
   - Location: exact match on the normalized location.
   - Cuisine: OR across selected tokens.
   - Budget: inclusive band from config. Drop null `cost_for_two` when a budget is set.
   - Minimum rating: `rating >= min`. Drop null ratings when a minimum is set.
4. Add `GET /api/facets` returning locations, lowercase cuisines, budgets, and rating bounds 0–5. Return 503 if facets are requested before the catalog is loaded.
5. Extend `GET /api/health` with `catalogLoaded` and `restaurantCount`.
6. Add `backend/tests/test_filter.py` on the fixture catalog: budget edges 499, 500, 1000, and 1001; cuisine OR; null rating excluded when a minimum is set; null cost excluded when a budget is set.

**Done when**

- Health reports the fixture restaurant count.
- Facets list only locations and cuisines present in that catalog.
- Filter tests cover the edges above and pass without a model key.

---

## Phase 3 — Recommendations without the model

**Outcome.** A client can submit preferences and receive up to five catalog-backed restaurants, ordered by rating, then votes, then name.

**Tasks**

1. Add Pydantic request and response models in `backend/app/schemas/request.py` and `response.py` matching the architecture:
   - Request: `location`, `budget`, `cuisines`, `minRating`, optional `preferences` (max 500 characters), optional `limit` (default 5, max 5).
   - Response: `summary`, `explanations`, `matchedCount`, and `recommendations` with id, name, cuisines, location, rating, votes, cost for two, rest type, and reason.
2. Validate in the route: unknown location, unknown budget, rating outside 0–5, and an empty cuisine list return 422.
3. Implement `backend/app/services/select.py`. Sort matches by rating descending, votes descending, name ascending. Keep at most 20.
4. Implement `backend/app/services/recommend.py` for this phase only:
   - Zero matches: HTTP 200, `explanations: "skipped"`, `matchedCount: 0`, empty list, summary that names the location. Do not call a model.
   - Otherwise: take the first `limit` of the shortlist, set `reason` to null, `explanations` to `"unavailable"`, and a summary that states these are the highest-rated matches. The explanation status changes to `"available"` in Phase 4 when the model succeeds.
5. Add `POST /api/recommendations`.
6. Add an API test that uses the fixture catalog: 422 for an unknown location, 200 with the documented shape for a known query, and 200 with an empty list when filters match nothing.

**Done when**

- The endpoint returns catalog fields only.
- Order is stable across repeated calls.
- `matchedCount` is the filter count, not the page size.
- Tests do not download Hugging Face and do not read `LLM_API_KEY`.

---

## Phase 4 — LLM ranking, reasons, and fallback

**Outcome.** Matching requests are ranked by Groq, with a written reason and an optional summary. Provider failures still return the Phase 3 cards.

**Tasks**

1. Add `backend/app/schemas/llm.py` for the model payload: `summary` and `recommendations[{id, reason}]`. The JSON schema sent to Groq marks every property required and sets `additionalProperties` to false. Groq strict structured outputs reject a looser schema.
2. Implement `backend/app/services/prompt.py`. The system prompt requires:
   - Recommend only supplied ids.
   - Rank for the free-text preference. Rating and cost are already satisfied.
   - Two or three sentences per reason, citing cuisine, cost, rest type, or liked dishes.
   - No invented dishes, reviews, or awards.
   - JSON only.
   The user message includes structured preferences, the free-text preference or `"none"`, and the shortlist. Each shortlist record has id, name, cuisines, rating, votes, cost for two, rest type, and truncated liked dishes. Omit phone numbers and reviews.
3. Implement `backend/app/services/llm_client.py` with the existing `httpx` dependency. Call Groq’s OpenAI-compatible chat completions endpoint. Do not add the Groq SDK.
   - `POST {LLM_BASE_URL}/chat/completions`, with `LLM_BASE_URL` defaulting to `https://api.groq.com/openai/v1`.
   - `LLM_MODEL` defaults to `openai/gpt-oss-20b`, which supports strict JSON schema. `LLM_API_KEY` holds the Groq key.
   - Change those two defaults in `backend/app/config.py` and `backend/.env.example`. Phase 0 left them pointed at OpenAI.
   - Send `Authorization: Bearer <LLM_API_KEY>`.
   - Send `response_format` as `{ "type": "json_schema", "json_schema": { "name": "recommendations", "strict": true, "schema": ... } }`.
   - Temperature about 0.2. Do not also set `top_p`.
   - Omit fields Groq rejects: `logprobs`, `logit_bias`, `top_logprobs`, `messages[].name`, and `n` other than 1.
   - Timeout is `LLM_TIMEOUT_SECONDS`.
   - Parse the JSON string on `choices[0].message.content`. When Groq returns `usage`, log `prompt_tokens` and `completion_tokens`.
4. Add an output guard:
   - Drop unknown ids and duplicate ids.
   - Cap reasons by length.
   - Cap the list at `limit`.
   - Fill name, cuisine, rating, votes, cost, location, and rest type from the catalog.
   - If every id is invalid, use selector order and omit reasons.
5. Wire `recommend.py`:
   - On success, set `explanations` to `"available"` and use the model summary.
   - On timeout, HTTP error, or unparseable JSON, keep selector order, `reason: null`, `explanations: "unavailable"`, and a summary that says explanations are temporarily unavailable. HTTP status stays 200.
   - Log latency, token usage when the provider returns it, and whether the fallback ran. Do not log the API key or the full prompt.
6. Add `backend/tests/test_guard.py` and `backend/tests/test_recommend_fallback.py` with a fake client. Assert the prompt contains at most the 20 shortlist ids, unknown and duplicate ids are dropped, catalog fields win over anything echoed by the model, a client exception still returns cards, and zero matches never call the client.

**Done when**

- A fake model that returns valid ids produces ordered cards and reasons.
- A fake model that throws, times out, or returns prose still yields HTTP 200 and selector order.
- Defaults are Groq’s base URL and `openai/gpt-oss-20b`. Default `pytest` never contacts `api.groq.com` or any other live provider.

---

## Phase 5 — Preference form and result cards

**Outcome.** A person can submit preferences in the browser and read the top recommendations.

**Tasks**

1. Add `frontend/src/api.ts` for `GET /api/facets` and `POST /api/recommendations`. Point the base URL at the FastAPI dev server.
2. Build `PreferenceForm`:
   - Searchable location select fed by facets.
   - Budget radio or select, default medium.
   - Cuisine multi-select, at least one required. Display title case; submit the lowercase token.
   - Minimum rating control from 0 to 5 in steps of 0.5, default 3.5.
   - Optional preferences textarea, max 500 characters.
   - Submit button that disables and shows a pending label while the request runs.
3. Build `Results` for the success path: summary paragraph, then one card per item with name, cuisine, rating, cost for two, location, and reason.
4. Compose both in `App.tsx`. Load facets on startup.
5. The client renders the payload. It does not sort, filter again, or call the model.

**Done when**

- With the fixture catalog and a fake or live model, submitting a known location and cuisine shows up to five cards.
- Cuisine and location options disappear if they are removed from the fixture and facets are reloaded.
- The pending state is visible for the length of the request.

---

## Phase 6 — Empty, error, and unavailable states

**Outcome.** The page explains no matches, invalid input, and missing explanations without looking like a crash.

**Tasks**

1. Empty `recommendations` with `explanations: "skipped"`: name the location and suggest relaxing the minimum rating or choosing another budget. Do not show an error banner.
2. `explanations: "unavailable"`: still render catalog facts on each card, show the API summary, and add a short note that written reasons are temporarily unavailable.
3. HTTP 422: show the validation message next to the form and keep the values the user entered.
4. Network failure or HTTP 500: show a retry message. Leave the last successful results on screen if any exist.
5. Facets 503 or a failed facets load: disable submit and tell the user the catalog is not ready.

**Done when**

- A query that matches nothing shows the empty state and no cards.
- Stopping the model (or forcing fallback) still shows names, ratings, cuisines, and costs, plus the unavailable note.
- An unknown location cannot be submitted from the select. A direct 422 from the API is still rendered if it occurs.
- Reloading after a failed request does not clear the form.

---

## Phase 7 — Full catalog and a live model

**Outcome.** The same app runs on the real Hugging Face dataset and a real model key. This phase is a manual check, not a new feature.

**Tasks**

1. Run `python scripts/prepare_dataset.py --source huggingface` and point `CATALOG_PATH` at `backend/data/restaurants.parquet`.
2. Confirm health shows a deduplicated count well below the raw 51,700 rows, and facets locations are Bengaluru neighborhoods.
3. Set `LLM_API_KEY` to a Groq key. Leave `LLM_BASE_URL` and `LLM_MODEL` on the Phase 4 Groq defaults unless overriding them.
4. Exercise one query end to end, for example Banashankari, medium budget, North Indian, minimum rating 4, preference “family-friendly”.
5. Confirm the response lists at most five restaurants, every rating and cost satisfies the filters, and each reason refers to fields on that card.
6. Repeat with the key removed or the base URL pointed at a closed port. Cards still appear, `explanations` is `unavailable`, and the status is 200.

**Done when**

- The checklist above passes in the browser.
- `pytest` still passes with the fixture and no live provider.

## Suggested sequence

Finish Phases 0–3 before requesting a Groq API key. Phase 3 already demos filtering and ranking. Phase 4 is the only phase that needs Groq credentials, and its tests use a fake client. Phases 5 and 6 can be built against Phase 3 and then rechecked after Phase 4.
