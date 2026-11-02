# Table — AI restaurant recommendations for Bengaluru

Structured filters narrow a real Zomato catalog. A large language model ranks the shortlist and explains each pick in plain language.

**Live demo:** [https://nextleap-zomato-prj.vercel.app](https://nextleap-zomato-prj.vercel.app)  
**API:** [https://adaptable-hope-production-5116.up.railway.app/api/health](https://adaptable-hope-production-5116.up.railway.app/api/health)  
**Dataset:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)

---

## System prompt

Defined in `backend/app/services/prompt.py` and sent as the `system` message on every ranking call:

```text
Rank only supplied ids for the free-text preference. Rating and cost already match.
One short sentence per reason, citing only cuisine, cost, rest type, or liked dishes given below.
Do not invent dishes, reviews, or awards.
JSON only. Summary may be empty. Return at most 5 ids.
```

The matching `user` message is compact JSON. It carries the structured filters, the free-text preference (or `"none"`), and at most **20** shortlist restaurants. Each restaurant is aliased as `"1"`…`"20"` so the model never sees long catalog hashes. Fields sent per row: `id`, `name`, `cuisines`, `cost`, `type`, and optional truncated `dishes`. Rating, votes, phone, and reviews stay off the prompt.

---

## Response schema

### Model output (strict JSON schema to Groq)

```json
{
  "summary": "string",
  "recommendations": [
    {
      "id": "string",
      "reason": "string"
    }
  ]
}
```

Every property is required. `additionalProperties` is `false`. The server maps aliases back to catalog ids, drops unknown or duplicate ids, length-caps each reason, and fills display fields from the parquet catalog—not from the model.

### API response (`POST /api/recommendations`)

```json
{
  "summary": "string",
  "explanations": "available | unavailable | skipped",
  "matchedCount": 0,
  "recommendations": [
    {
      "id": "string",
      "name": "string",
      "cuisines": "string",
      "location": "string",
      "rating": 4.1,
      "votes": 775,
      "costForTwo": 800,
      "restType": "Casual Dining",
      "reason": "string | null"
    }
  ]
}
```

`explanations` is `skipped` when nothing matched, `unavailable` when the model fails and selector order is returned without reasons, and `available` when guarded model reasons are present.

---

## What changed across prompt versions and why

| Version | What changed | Why |
| --- | --- | --- |
| **v1** | Longer system text: recommend only supplied ids; rank for free-text preference; rating/cost already satisfied; **two or three sentences** per reason; cite cuisine, cost, rest type, liked dishes; no invented dishes/reviews/awards; JSON only. User payload included **full catalog ids**, rating, votes, and longer liked-dish strings. | First working ranking contract from the architecture plan: clear rules, grounded reasons, structured output. |
| **v2 (current)** | Shorter system text; **one short sentence** per reason; explicit **“Return at most 5 ids”**; restaurant ids become **`1`…`20`** aliases restored on the server; drop rating/votes from the prompt; liked dishes capped at **40** characters and omitted when empty; compact JSON (no spaces); `max_tokens` **512**; reasoning effort **low**. | Live calls on `openai/gpt-oss-120b` (Groq) hit an 8K tokens/minute budget. v1 prompts were too large per search; v2 keeps ranking quality while leaving headroom for multiple searches in the same minute. |

Source of truth for the live string: `SYSTEM_PROMPT` in `backend/app/services/prompt.py`.

---

## How the scope limit is enforced

The model never sees the full catalog. Scope is enforced in layers:

1. **Hard filters first** — location, cuisine, budget band, and minimum rating run in code (`filter_restaurants`). Only matching rows can enter the shortlist.
2. **Shortlist cap** — `CANDIDATE_CAP = 20`. Selector order (rating, then votes) picks the prompt set; anything beyond that never reaches the model.
3. **Prompt rules** — system text allows only supplied ids, forbids invented facts, and caps returns at 5.
4. **Strict schema** — Groq `response_format` is a closed JSON schema; prose and extra keys are rejected at parse time.
5. **Server guard** — `apply_guard` drops unknown and duplicate ids, restores catalog identity via aliases, truncates reasons (`REASON_MAX_CHARS = 180`), and stops at `limit` (max **5**).
6. **Request bounds** — `preferences` max 500 characters; `limit` is `1…5`.
7. **Product scope** — no accounts, booking, live Zomato search, embeddings, maps, cities outside Bengaluru, or fine-tuning. Those are omitted from the API and UI, not left to the model.

If the model call fails or every id is invalid, the API still returns selector-ordered cards with `explanations: "unavailable"` so a provider outage is not mistaken for “no matches.”

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 19, TypeScript, Vite |
| Backend | FastAPI, Pydantic, Uvicorn |
| Catalog | pandas + pyarrow parquet (~12.5k Bengaluru restaurants in memory) |
| LLM | Groq OpenAI-compatible chat completions (`openai/gpt-oss-120b`), strict JSON schema via `httpx` (no vendor SDK) |
| Hosting | Vercel (static frontend), Railway (API) |
| Data prep / tests | `datasets`, `pytest` (dev requirements) |

---

## Local development

```bash
# API
cd backend
python -m venv .venv
# activate .venv, then:
pip install -r requirements-dev.txt
cp .env.example .env   # set LLM_API_KEY for explanations
uvicorn app.main:app --reload --port 8000

# Web
cd frontend
npm install
npm run dev
```

Without `VITE_API_BASE_URL`, the UI talks to `http://127.0.0.1:8000`. Production sets that variable to the Railway origin (no trailing slash).

More detail: `docs/architecture.md`, `docs/deployment-plan.md`, `docs/eval.md`.
