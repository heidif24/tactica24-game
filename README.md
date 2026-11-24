# Tactica24

**Conversational football analysis → fixture and market validation → verified bookmaker booking code.**

Tactica24 is designed to interpret a natural-language request, analyse eligible fixtures, rank candidate selections, validate the exact market at a chosen bookmaker, and return a code only after the booking provider confirms it. It does not place stakes.

## Important operating rules

- Demo mode never creates a real booking code.
- A model probability is an estimate, not a guaranteed win rate. The existing corner Poisson model is not yet calibrated against a large, timestamped historical dataset.
- A market must match the requested event, market, outcome, line and time period. The system must not silently replace an unavailable interval market with a full-match market.
- Booking is strict: every requested pick must resolve and the resulting code must pass provider load-back verification. Partial or unverified codes are not displayed as successful.
- Manage Bet Codes is a third-party booking-code service, not a bookmaker. It charges API credits for booking and its available markets depend on the target bookmaker.

## Current implementation

- FastAPI backend with streaming pipeline (POST /api/pipeline) and conversational alias (POST /api/chat).
- Natural-language parsing with deterministic fallback and optional OpenAI/Anthropic parsing.
- Existing corner-interval scouting engine and configurable live stats providers.
- Booking adapters: demo-only mock, legacy generic partner API, and Manage Bet Codes.
- Manage Bet Codes adapter uses POST /v1/resolve then strict POST /v1/book, rejects odds changes, requires all picks to resolve, and requires verified=true plus a complete returned pick list.
- Exact market metadata is required by the booking adapter. The current corner-interval scout does not yet populate canonical bookmaker market keys; consequently, first-five/first-fifteen interval selections are deliberately rejected until a real exact interval market is discovered and mapped. This prevents an incorrect full-match substitute.

## Run locally

    git clone https://github.com/heidif24/tactica24-game.git
    cd tactica24-game
    python -m venv .venv
    # Windows: .venv\Scripts\activate
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Open http://localhost:8000. Default mock mode is for interface and pipeline testing only.

## Configure Manage Bet Codes

Create an API key in your Manage Bet Codes account and add it as a server-side secret. Never expose it in frontend JavaScript or commit it to Git.

    STATS_PROVIDER=api_football
    API_FOOTBALL_KEY=your_stats_provider_key
    SLIP_BUILDER=manage_bet_codes
    MANAGE_BET_CODES_BASE_URL=https://api.managebetcodes.app/v1
    MANAGE_BET_CODES_API_KEY=mbc_live_your_key
    MANAGE_BET_CODES_BOOKMAKER=sportybet
    MANAGE_BET_CODES_TIMEOUT_SECONDS=35
    LLM_PROVIDER=openai
    OPENAI_API_KEY=your_llm_key

Supported bookmaker identifiers must be checked against the provider's live bookmaker catalog. Examples in its documentation include sportybet, bet9ja, onexbet, msport, and betking.

Official provider references:
- API overview and capabilities: https://managebetcodes.app/docs
- Event search and available markets: https://managebetcodes.app/docs/search
- Resolve selections: https://managebetcodes.app/docs/resolve
- Book and verify: https://managebetcodes.app/docs/book
- Quickstart and API keys: https://managebetcodes.app/docs/quickstart

The provider's resolve plan expires after 10 minutes. Booking costs API credits per created code. Check your account's current plan, quota and credit balance before live use.

## Live data and model limitations

The current live statistics integrations provide fixture and aggregate corner information, but do not yet provide reliable interval-by-interval historical samples for every fixture. A fixed first-15-minute share is an assumption, not observed event-level evidence. Tactica24 must label this limitation and must not present uncalibrated estimates as validated probabilities.

Before describing any selection as high-confidence, add:
1. Timestamped historical event and market data, including the requested exact interval.
2. Walk-forward/out-of-sample backtesting with leakage controls.
3. Calibration (reliability curves, Brier score and log loss) by market and competition.
4. Market-price comparison and odds movement checks.
5. Minimum sample thresholds and a no-pick outcome when evidence is insufficient.

## API

| Endpoint | Purpose |
|---|---|
| GET /api/health | Runtime/provider configuration |
| POST /api/parse-rule | Parse a natural-language rule |
| POST /api/scout-matches | Run the current statistical scout |
| POST /api/generate-code | Build a code from explicit selections |
| POST /api/chat | Conversational pipeline (SSE) |
| POST /api/pipeline | Pipeline (SSE) |

## Safety and transparency

Tactica24 does not guarantee outcomes, place stakes, or encourage chasing losses. The user makes the final decision and submits any wager manually. Do not deploy with mock providers and mistake the demo output for live data.
