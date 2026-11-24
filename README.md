# SlipForge

**Natural-language betting rule → Poisson corner scouting → 1xBet booking code**

Complete, runnable end-to-end app. Default mode (`mock` + `mock`) needs **zero API keys** and produces real pipeline output with sample fixtures and a deterministic booking code.

> **Disclaimer**  
> Automating 1xBet (or any bookmaker) almost certainly violates their Terms of Service and can get accounts banned. The Playwright builder is included for research; prefer `SLIP_BUILDER=mock` or an official partner API.

---

## One-command start

```bash
git clone https://github.com/heidif24/tactica24-game.git
cd tactica24-game

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # defaults: mock stats + mock builder

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — the dashboard is served by FastAPI.

Click a preset chip → **Run Pipeline**. You should see:
1. Rule parsed  
2. Fixtures scanned + ranked by Poisson P(0 corners)  
3. Mock market match  
4. Booking code like `SF1A2B3C4D`

---

## Go live (optional)

### Stats

```env
STATS_PROVIDER=api_football
API_FOOTBALL_KEY=your_key_here
# If using RapidAPI instead of api-sports.io direct:
# API_FOOTBALL_BASE=https://api-football-v1.p.rapidapi.com/v3
# API_FOOTBALL_HOST=api-football-v1.p.rapidapi.com
```

Or FootyStats:

```env
STATS_PROVIDER=footystats
FOOTYSTATS_KEY=your_key_here
```

### Slip builder

```env
SLIP_BUILDER=playwright
ONEXBET_BASE_URL=https://1xbet.ng
HEADLESS=false          # watch the browser while tuning selectors
playwright install chromium
```

All DOM selectors live in `backend/builders/playwright_builder.py` → `SELECTORS` dict. Update them when 1xBet changes their markup; core flow stays untouched.

Or plug a third-party booking API:

```env
SLIP_BUILDER=api
BOOKING_API_URL=https://your-partner.example
BOOKING_API_KEY=...
```

### LLM parser (optional)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Without an LLM key the deterministic parser covers common corner-interval prompts.

---

## Architecture

| Stage | Endpoint | Module |
|-------|----------|--------|
| 1 Parse rule | `POST /api/parse-rule` | `backend/parser.py` |
| 2 Scout | `POST /api/scout-matches` | `backend/stats_engine.py` |
| 3 Build slip | `POST /api/generate-code` | `backend/builders/*` |
| Full SSE | `POST /api/pipeline` | `backend/main.py` |
| UI | `GET /` | `frontend/index.html` |

### Poisson model

```
λ = (0.55·c90_for + 0.45·opp_c90_against) × first15_share × (window_min / 15)
P(X=0) = e^(-λ)
fair_odds = 1 / P
```

Selections below `min_probability` are dropped; top `max_legs` by probability are returned.

Missing / suspended 1xBet micro-markets are skipped; remaining legs still save.

---

## Project tree

```
backend/
  main.py
  models.py
  parser.py
  stats_engine.py
  builders/
    __init__.py
    mock_builder.py
    playwright_builder.py
    api_builder.py
frontend/
  index.html
.env.example
requirements.txt
README.md
```

---

## License

MIT — no warranty. Not financial advice. Use at your own risk.
