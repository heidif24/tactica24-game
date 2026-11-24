# SlipForge

**Natural-language betting rule → statistical scouting → 1xBet booking code**

SlipForge turns plain-English corner rules into validated selections, ranks them with a Poisson early-interval model, matches them against 1xBet markets, and (optionally) builds a saved betslip to retrieve a booking code.

> **Important disclaimer**  
> Automating interactions with 1xBet (or any bookmaker) almost certainly violates their Terms of Service and can result in account suspension or legal consequences. This project is provided for educational and research purposes. Use the Playwright builder at your own risk. Prefer the mock / external API adapters for safe testing.

---

## Architecture (4 stages)

1. **Parse Rule** (`/api/parse-rule`) — LLM + deterministic fallback → strict Pydantic schema  
2. **Scout Matches** (`/api/scout-matches`) — pluggable `StatsProvider` + Poisson engine  
3. **Generate Code** (`/api/generate-code`) — Playwright browser builder **or** external booking API  
4. **Dashboard** — dark trading-terminal UI with live SSE progress feed

---

## Quick start

```bash
# 1. Clone & enter
git clone https://github.com/heidif24/tactica24-game.git
cd tactica24-game

# 2. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Playwright browsers (only needed for Adapter A)
playwright install chromium

# 4. Environment
cp .env.example .env
# edit .env — at minimum leave STATS_PROVIDER=mock and SLIP_BUILDER=mock

# 5. Run backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 6. Open the dashboard
# simply open frontend/index.html in a browser
# or serve it:  python -m http.server 3000 --directory frontend
```

The UI talks to `http://localhost:8000` by default (CORS enabled).

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `STATS_PROVIDER` | `mock` | `mock` \| `api_football` \| `footystats` |
| `API_FOOTBALL_KEY` | — | RapidAPI / API-Football key |
| `FOOTYSTATS_KEY` | — | FootyStats API key |
| `SLIP_BUILDER` | `mock` | `mock` \| `playwright` \| `api` |
| `ONEXBET_BASE_URL` | `https://1xbet.ng` | Target 1xBet domain |
| `HEADLESS` | `true` | Playwright headless mode |
| `BOOKING_API_URL` | — | External slip-booking endpoint |
| `BOOKING_API_KEY` | — | Bearer token for external API |
| `OPENAI_API_KEY` | — | Optional LLM rule parser |
| `LLM_PROVIDER` | `none` | `none` \| `openai` \| `anthropic` \| `gemini` |

---

## Project layout

```
backend/
  main.py                 # FastAPI + SSE
  models.py               # Pydantic schemas
  parser.py               # Rule parser (LLM + fallback)
  stats_engine.py         # Poisson engine + StatsProvider
  builders/
    __init__.py
    playwright_builder.py # Stealth Chromium + selectors dict
    api_builder.py        # External booking API adapter
    mock_builder.py       # Deterministic demo builder
frontend/
  index.html              # Single-file dark terminal UI
.env.example
requirements.txt
README.md
```

---

## Core math (early-interval corners)

```
λ = weighted_corner_rate × (window_minutes / 90)
P(X = 0) = e^(-λ)
fair_odds = 1 / P(X = 0)
```

`weighted_corner_rate` blends the team’s corners-for per 90 and the opponent’s corners-against per 90, then applies a first-15-minute split factor (configurable, default ≈ 0.22 of full-match corners occur in the opening 15 minutes).

---

## Safety & graceful degradation

- Missing or suspended micro-markets are skipped; remaining valid legs are still saved.
- All Playwright selectors live in a single `SELECTORS` dictionary at the top of `playwright_builder.py`.
- Configurable timeouts and retry logic.
- Mock provider + mock builder let the entire pipeline run offline with realistic sample data.

---

## License

MIT — use at your own risk. No warranty. Not financial advice.
