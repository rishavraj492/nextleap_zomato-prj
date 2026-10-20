# Edge Cases

Corner scenarios for the restaurant recommender. Expected behavior comes from [architecture.md](architecture.md) and the phase checks in [implementation-plan.md](implementation-plan.md).

Each case lists the situation, the required outcome, and the phase that should prove it. Cases marked **out of scope** are not bugs in this version.

## 1. Dataset shape

The Hugging Face file has about 51,700 rows of Bengaluru restaurants. `location` is a neighborhood. The same restaurant is repeated once per `listed_in(type)` and `listed_in(city)`.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Same `name` + `address` on several rows with different `listed_in(type)` | One catalog row. Keep the duplicate with the most `votes`. Union cuisine tokens and listing types. | 1 |
| Same name, different address | Two restaurants. The dedup key is name and address together. | 1 |
| Two duplicates with equal `votes` | Still one row. The kept source row must be deterministic across runs. | 1 |
| Regenerating the parquet | `id` is a hash of name + address, so the same restaurant keeps the same id. | 1 |
| Raw row count is 51,700 | Health `restaurantCount` is the deduplicated count, lower than 51,700. | 7 |
| User asks for Delhi, Mumbai, or the city “Bangalore” | Those strings are not locations in this catalog. The location control only offers neighborhoods loaded from the data, such as Banashankari or Koramangala 5th Block. | 2, 5 |
| `reviews_list` is huge (up to about 1 MB) | Dropped at ingest. It is absent from parquet, prompts, and API responses. | 1, 4 |
| `menu_item` and `phone` | Dropped at ingest. The model never sees phone numbers. | 1, 4 |
| `dish_liked` is null | Catalog field is empty. The prompt omits it or sends an empty value. The card still renders. | 1, 4 |
| `dish_liked` is very long | Truncate before it is stored for prompts. | 1 |
| `url` present | Kept for an optional link. Recommendations do not depend on it. | 1 |

## 2. Field parsing

| Case | Expected outcome | Phase |
| --- | --- | --- |
| `rate` is `4.1/5` | `rating` is `4.1`. | 1 |
| `rate` is `NEW`, `-`, or blank | `rating` is null. | 1 |
| `rate` has surrounding spaces, such as ` 4.1/5 ` | Trim, then parse as `4.1`. | 1 |
| `rate` is not numeric after removing `/5` | `rating` is null. | 1 |
| `approx_cost(for two people)` is `300` | `cost_for_two` is `300`. | 1 |
| Cost is `1,200` | Commas stripped. `cost_for_two` is `1200`. | 1 |
| Cost is blank or non-numeric | `cost_for_two` is null. | 1 |
| `cuisines` is `North Indian, Mughlai, Chinese` | Display string keeps original casing. `cuisine_tokens` are `north indian`, `mughlai`, `chinese`. | 1 |
| Cuisine tokens have extra spaces | Trim each token before lowercasing. | 1 |
| `cuisines` is null or empty | Display string is empty. `cuisine_tokens` is empty. The restaurant matches no cuisine filter. | 1, 2 |
| `online_order` or `book_table` is `Yes` / `No` | Stored as booleans. | 1 |
| `online_order` or `book_table` is any other value | Stored as false. | 1 |
| `location`, `name`, or `rest_type` has leading or trailing space | Trim before dedup, indexing, and display. | 1 |
| `rest_type` is `Cafe, Casual Dining` | Keep the display string. Pass it through to the prompt. | 1, 4 |
| `listed_in(type)` differs across duplicates | `listed_types` is the union of those values. | 1 |

## 3. Budget bands

Bands are on `cost_for_two` in rupees: low is under 500, medium is 500 through 1,000 inclusive, high is above 1,000.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Cost is 499 | Matches low. Excluded from medium and high. | 2 |
| Cost is 500 | Matches medium. Excluded from low and high. | 2 |
| Cost is 1000 | Matches medium. Excluded from high. | 2 |
| Cost is 1001 | Matches high. Excluded from medium. | 2 |
| Cost is null and a budget is selected | Restaurant is excluded. | 2 |
| Budget omitted, unknown, or wrong case such as `Medium` | HTTP 422. | 3 |
| Bands change in `config.py` | Filter edges follow config. Tests should use the configured thresholds. | 2 |

## 4. Hard filters

Location, cuisine, budget, and minimum rating are applied in code. Free text never adds or removes rows.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Location matches except for case or surrounding space | Normalize both sides, then exact-match. `banashankari` and `Banashankari` match. `Koramangala` does not match `Koramangala 5th Block`. | 2 |
| Unknown location string | HTTP 422. | 3 |
| One cuisine selected | Restaurant matches when that token is in `cuisine_tokens`. | 2 |
| Several cuisines selected | OR. Any overlapping token qualifies. The restaurant does not need every selected cuisine. | 2 |
| Cuisine submitted in display case (`Chinese`) | Compare on the lowercase token `chinese`. | 2, 5 |
| Cuisine token that is not in the catalog | HTTP 422. | 3 |
| Empty cuisine list | HTTP 422. | 3 |
| `minRating` equal to the restaurant rating | Included. Comparison is `>=`. | 2 |
| `minRating` is 0 | A minimum is set, so null ratings are still excluded. Rated `0.0` is included. | 2 |
| `minRating` is 5 | Only restaurants rated exactly 5 remain eligible. | 2 |
| `minRating` is below 0 or above 5 | HTTP 422. | 3 |
| Rating is null and `minRating` is set | Excluded. | 2 |
| `preferences` is `family-friendly` or `quick service` | No extra hard filter. The shortlist is unchanged. The text is only in the prompt. | 3, 4 |
| `preferences` omitted, empty, or whitespace | Treated as no soft preference. The prompt receives `none`. | 4 |
| `preferences` length 500 | Accepted. | 3 |
| `preferences` length 501 | HTTP 422. | 3 |
| Every restaurant fails the filters | HTTP 200, `matchedCount: 0`, `recommendations: []`, `explanations: "skipped"`, summary names the location. The model is not called. | 3, 4 |
| Filters match 1 or 3 restaurants | Return all of them. Caps apply only as maximums. | 3 |
| Filters match more than 20 | Candidate selector keeps 20. `matchedCount` stays the full filter count. | 3, 4 |

## 5. Candidate order

Sort key: rating descending, votes descending, name ascending.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Same rating, different votes | Higher votes first. | 3 |
| Same rating and votes, different names | Alphabetical by name, ascending. | 3 |
| Same rating, votes, and name | Input order after the sort must be stable across requests. | 3 |
| Exactly 20 matches | All 20 go to the model. The response still contains at most `limit` rows. | 4 |
| `limit` omitted | Default 5. | 3 |
| `limit` is 1 | One card. The model may still see up to 20 candidates. | 3, 4 |
| `limit` is 5 | Five cards when at least five candidates exist. | 3 |
| `limit` is 0, 6, or negative | HTTP 422. | 3 |

## 6. Model output

The model may rank and explain. It may not invent catalog facts.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Valid JSON, ids from the shortlist, new order | Response follows the model order. Name, cuisines, rating, votes, cost, location, and rest type are copied from the catalog. | 4 |
| Model echoes a different rating or cost | Catalog values replace them. | 4 |
| Id that was not in the shortlist | Dropped. | 4 |
| Same id twice | Second copy dropped. | 4 |
| Mix of valid and invalid ids | Keep valid ids in the model’s order. | 4 |
| More recommendations than `limit` | Truncate to `limit` after the guard. | 4 |
| Fewer recommendations than `limit` | Return what remains after the guard. | 4 |
| Empty `recommendations` array | Treated as no valid ids. Fall back to selector order and omit reasons. | 4 |
| Every id invalid | Selector order, `reason: null`, `explanations: "unavailable"`. | 4 |
| `summary` is `""` | Allowed. The UI shows cards without a summary paragraph. | 4, 5 |
| `reason` longer than the cap | Truncate before the response is sent. | 4 |
| `reason` is null on an otherwise valid id | Keep the card. The UI leaves the explanation area empty for that card. | 4, 5 |
| JSON wrapped in prose or markdown | Unparseable. Use the fallback. | 4 |
| Provider timeout | HTTP 200, selector order, `explanations: "unavailable"`, summary says explanations are temporarily unavailable. | 4 |
| Provider HTTP error, including 429 and 500 | Same fallback. Status stays 200. | 4 |
| `LLM_API_KEY` missing, or `LLM_BASE_URL` refuses connections | Same fallback. This must not look like zero restaurants matched. | 4, 7 |
| Model returns a restaurant the filters excluded | Impossible if the guard only accepts shortlist ids. If one appears, drop it. | 4 |
| Soft preference conflicts with a hard filter | Hard filters already ran. The model only reorders the shortlist. | 4 |
| Prompt contents | At most 20 restaurants. Each record is id, name, cuisines, rating, votes, cost for two, rest type, and truncated liked dishes. No phone, no reviews. | 4 |
| Repeated identical requests | Temperature about 0.2. Order can still vary. Tests must not require identical model wording. | 4 |

Fallback payload:

- HTTP 200
- Order is rating, then votes, then name
- `reason` is null
- `explanations` is `"unavailable"`
- `matchedCount` is still the filter count

Zero matches never call the client, so they stay `explanations: "skipped"` even when the provider is down.

## 7. Startup and catalog load

| Case | Expected outcome | Phase |
| --- | --- | --- |
| `restaurants.parquet` missing | Process exits. The log names `scripts/prepare_dataset.py`. | 2 |
| Parquet is empty | Process stays up. Facets are empty. Every recommendation request matches nothing. | 2 |
| Parquet is unreadable | Process exits with the load error. | 2 |
| `GET /api/facets` or `GET /api/health` before load finishes | Facets return 503. Health may report `catalogLoaded: false`. | 2 |
| `facets.json` is stale relative to parquet | The API builds facets from the loaded catalog, so the form matches search. | 2 |
| Concurrent recommendation requests | Catalog indexes are read-only after load. Requests do not mutate them. | 3 |

`GET /api/health` after a good load includes `catalogLoaded: true` and `restaurantCount`.

## 8. API contract

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Unknown location, unknown budget, rating out of range, or no cuisine | HTTP 422 with a validation message. | 3 |
| Catalog failed during startup | The process is down, so clients see a connection error. A catalog error after startup on the recommendation path is HTTP 500. | 2, 3 |
| Extra JSON fields on the request | Ignored by Pydantic, or rejected if the model is configured to forbid extras. Pick one and test it. | 3 |
| `minRating` sent as `4` rather than `4.0` | Accepted. | 3 |
| Response when the model succeeds | `explanations: "available"`, summary from the model, reasons on each card. | 4 |
| Response when nothing matches | `explanations: "skipped"`, empty `recommendations`. | 3 |

## 9. Web client

The client renders the API payload. It does not filter or rank again.

| Case | Expected outcome | Phase |
| --- | --- | --- |
| Facets load | Location and cuisine options are exactly the payload. Cuisine labels are title case. Submitted cuisine values stay lowercase. | 5 |
| Default form | Budget medium. Minimum rating 3.5. Preferences empty. Submit stays disabled until one cuisine is selected. | 5 |
| Submit in flight | Button shows a pending state and ignores further clicks. | 5 |
| A newer request finishes before an older one | Render the latest request only. | 5 |
| Successful recommendations | Summary when non-empty. Each card shows name, cuisine, rating, cost for two, location, and reason. | 5 |
| `matchedCount` is 0 | Empty state names the location and suggests relaxing the rating or changing budget. No error banner. | 6 |
| `explanations` is `"unavailable"` | Cards still show catalog facts. A note says written reasons are temporarily unavailable. | 6 |
| HTTP 422 | Message shown by the form. Entered values stay in place. | 6 |
| Network error or HTTP 500 | Retry message. Previous successful cards stay on screen when there were any. | 6 |
| Facets request returns 503 or fails | Submit disabled. Copy says the catalog is not ready. | 6 |
| Reload after a failed submit | Form fields are still what the user entered during that visit. A full browser refresh may reset them. | 6 |
| Restaurant name or reason is long | Card wraps or truncates visually. The API has already capped reason length. | 5, 6 |
| `reason` is null on a card while explanations are available | That card omits the explanation paragraph. Other cards still show theirs. | 6 |

## 10. Fixture rows the tests need

`backend/data/fixtures/zomato_sample.csv` has to make the cases above executable offline:

- One restaurant listed twice with different `listed_in(type)` and different vote counts
- Two rows with the same name and different addresses
- `rate` values `4.1/5`, `NEW`, `-`, and blank
- Costs `300`, `499`, `500`, `1000`, `1001`, `1,200`, and blank
- A multi-cuisine cell and a null cuisine cell
- A shared rating with different votes, and a shared rating and votes with different names
- At least one neighborhood and cuisine used by the API examples (`Banashankari`, `north indian`)

Default `pytest` uses this fixture only. It does not download Hugging Face and does not call a live model.

## 11. Live check

Phase 7 repeats a slice of the table against the real catalog:

- Health count is deduplicated.
- Facet locations are neighborhoods.
- A query such as Banashankari, medium, North Indian, minimum rating 4, preference “family-friendly” returns at most five rows, and every row satisfies the filters.
- Reasons mention only facts on that card.
- Removing the API key, or pointing `LLM_BASE_URL` at a closed port, still returns HTTP 200 cards with `explanations: "unavailable"`.

## 12. Out of scope

These are not edge cases to implement:

- Accounts, saved preferences, or history
- Booking, ordering, or live Zomato search
- Vector search or embeddings
- Map pins or geocoding addresses
- Restaurants outside Bengaluru
- Fine-tuned models
- Personalized ranking from past visits
