# Tactica24

Conversational football research, evidence-backed market analysis, exact bookmaker-market verification, and booking-code creation.

## Architecture

1. **Understand the request** — Gemini parses ordinary language into a structured market request. Groq is used as a fallback language-model parser if Gemini request parsing fails.
2. **Research online** — Gemini uses Google Search grounding to find current fixtures and public football evidence. Source URLs are returned with the analysis.
3. **Analyse** — the model ranks only candidates supported by retrieved evidence. It must preserve the requested market, line and time interval. Unsupported minute-specific claims are rejected.
4. **Verify bookmaker market** — Manage Bet Codes searches the selected bookmaker, discovers the exact event and market, resolves the pick, and only returns a code after provider verification.

API-Football and FootyStats are not used by the active pipeline. No demo fixtures or mock statistics are substituted when live research fails.

## Environment variables

Copy `.env.example` and set the secrets in Vercel Project Settings → Environment Variables:

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.5-flash`
- `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-120b`
- `SLIP_BUILDER=manage_bet_codes`
- `MANAGE_BET_CODES_BASE_URL=https://api.managebetcodes.app/v1`
- `MANAGE_BET_CODES_API_KEY`
- `MANAGE_BET_CODES_BOOKMAKER=sportybet` (or `onexbet`)
- `MANAGE_BET_CODES_TIMEOUT_SECONDS=45`

Gemini is the required live web-research provider. Groq provides parser fallback; it is not treated as a live web source by itself. Keep all keys server-side and never commit them.

## Probability and safety

AI-generated probabilities are estimates, not calibrated historical hit rates or guarantees. The default `T24_REQUIRE_CALIBRATED=false` allows estimates to proceed to exact bookmaker market verification; the UI and API retain the uncalibrated status. Set it to `true` only when a sufficient timestamped out-of-sample dataset exists for the exact market and period.

A booking code is not produced unless the requested event and exact market are discovered and verified by Manage Bet Codes. No market or time period is silently substituted. Manage Bet Codes creates shareable booking codes; it does not place stakes or access bookmaker wallets.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | AI, research and booking-provider readiness |
| `POST /api/parse-rule` | Parse a natural-language request |
| `POST /api/scout-matches` | Grounded web research and analysis |
| `POST /api/generate-code` | Verify and build a code from explicit selections |
| `POST /api/chat` | Conversational streaming pipeline |
| `POST /api/pipeline` | Pipeline alias |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The live pipeline requires a valid Gemini key and Manage Bet Codes key. No API-Football key or Neon database is required for a fresh search. Historical tracking and calibration can be added separately.
