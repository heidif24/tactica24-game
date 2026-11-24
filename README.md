# Tactica24

Conversational football analysis, exact bookmaker-market discovery, historical probability calibration, and verified booking-code creation.

## Deployment

This repository is a Python FastAPI application. Vercel's FastAPI runtime entrypoint is declared in the root `pyproject.toml`:

    [tool.vercel]
    entrypoint = "backend.main:app"

The FastAPI application serves the dashboard at `/` and API endpoints under `/api`. Vercel uses the root `requirements.txt` to install Python dependencies.

## What is implemented

- Conversational request parsing with OpenAI/Anthropic support and deterministic fallback.
- Supported statistical families: corners (full-match and requested intervals), full-match goals, BTTS, 1X2 and double chance.
- Minute-level goal, BTTS, result and card markets are not inferred from full-match aggregate rates.
- API-Football and FootyStats fixture/statistics adapters; missing statistics are not replaced with fabricated team averages.
- Manage Bet Codes market discovery using bookmaker capability catalogues, event search, event-specific markets or canonical market catalogue fallback.
- Strict selection resolution, strict booking, odds-change rejection, and provider load-back verification.
- A code is returned only if every requested selection is resolved, booked and provider-verified.
- Conversational SSE endpoint at `POST /api/chat`, with recent prompt context.
- GitHub Actions checks Python compilation and automated tests.

## Probability calibration is required for live booking

Raw Poisson outputs are model estimates, not proven hit rates. Live code creation is blocked by default unless the requested market/period has enough timestamped out-of-sample calibration evidence.

Set `T24_CALIBRATION_FILE=data/historical_outcomes.csv` and provide a CSV with these columns:

    market_category,sub_market,time_window,model_version,predicted_probability,outcome,predicted_at,kickoff_at,settled_at

Each row must be a genuine out-of-sample forecast recorded before kick-off, with the same model_version as the running model (currently tactica24-poisson-v2). Outcomes are 1 for the selected event occurring and 0 otherwise. kickoff_at must fall after predicted_at and before settled_at. The default minimum is 200 observations for the exact market/sub-market/period and 30 observations in the probability bin. Tactica24 uses a conservative 95% Wilson lower confidence bound rather than treating the raw hit rate as certainty.

A blank schema template is included at `data/historical_outcomes.template.csv`. It is not historical data and does not make the app live-ready. Do not fill it with invented or retrospectively fitted predictions.

## Manage Bet Codes configuration

Create an API key at https://managebetcodes.app/dashboard/api. The key must be stored only as a server-side Vercel environment variable.

    SLIP_BUILDER=manage_bet_codes
    MANAGE_BET_CODES_BASE_URL=https://api.managebetcodes.app/v1
    MANAGE_BET_CODES_API_KEY=mbc_live_your_key
    MANAGE_BET_CODES_BOOKMAKER=sportybet
    MANAGE_BET_CODES_TIMEOUT_SECONDS=35
    T24_REQUIRE_CALIBRATED=true
    T24_CALIBRATION_FILE=data/historical_outcomes.csv

For live fixtures and team statistics:

    STATS_PROVIDER=api_football
    API_FOOTBALL_KEY=your_api_football_key
    API_FOOTBALL_BASE=https://v3.football.api-sports.io

For conversational AI:

    LLM_PROVIDER=openai
    OPENAI_API_KEY=your_openai_api_key

Supported bookmaker codes and market availability are read from Manage Bet Codes' live catalogue. Do not assume every bookmaker exposes event-market details or every market. A missing/ambiguous market is rejected.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Provider, AI and calibration readiness |
| `POST /api/parse-rule` | Parse a natural-language request |
| `POST /api/scout-matches` | Statistical analysis and ranking |
| `POST /api/generate-code` | Build a code from explicit selections |
| `POST /api/chat` | Conversational streaming pipeline |
| `POST /api/pipeline` | Pipeline alias |

## Run locally

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

The default provider settings are mock/demo. Mock mode never produces a bookmaker code.

## Important boundaries

- Manage Bet Codes creates shareable booking codes; it does not place a stake or access bookmaker wallets.
- No market is silently substituted.
- No incomplete or unverified code is presented as successful.
- Historical calibration is market- and period-specific. A calibrated full-match goals profile does not validate first-five-minute corners.
- Betting outcomes are uncertain; no probability or selection guarantees a win.
