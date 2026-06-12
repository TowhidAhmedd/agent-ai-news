# 🤖 AI News Agent

> **Automated daily AI news briefing — 100% free-tier, production-grade.**  
> Discovers → Extracts → Scores → Deduplicates → Summarizes → Ranks → Emails  
> Powered by **LangGraph**, **LangChain**, and free-tier LLMs (Groq / OpenRouter / Gemini).

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Multi-agent pipeline** | 8-node LangGraph workflow |
| **18+ RSS sources** | Official lab blogs + tech media |
| **LLM relevance scoring** | 0–100 score per article |
| **Near-duplicate detection** | Jaccard title similarity |
| **AI-generated summaries** | Executive summary + key takeaways + why it matters |
| **Beautiful HTML email** | Dark-header responsive newsletter |
| **Daily schedule** | 06:30 AM configurable via cron |
| **LangSmith observability** | Full trace per pipeline run |
| **REST API** | FastAPI dashboard + manual trigger |
| **SQLite persistence** | Articles, runs, email logs |
| **Docker deploy** | Single `docker compose up -d` |
| **100% free tier** | Groq / OpenRouter / Gemini free APIs |

---

## 🏗 Architecture

```
START
  │
  ▼
┌─────────────────┐
│ Discovery Agent │  ← 18+ RSS feeds (async batch fetch)
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Extraction Agent     │  ← newspaper3k + BeautifulSoup fallback
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Scoring Agent        │  ← LLM batch scoring (0-100)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Dedup Agent          │  ← URL normalisation + Jaccard similarity
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Summarization Agent  │  ← LLM: executive summary + takeaways
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Ranking Agent        │  ← Composite score × category weight
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Newsletter Agent     │  ← Jinja2 HTML email renderer
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Email Agent          │  ← SMTP with retry (tenacity)
└──────────┬───────────┘
           │
          END
```

---

## 🚀 Quick Start (Docker — recommended)

### 1. Clone and configure

```bash
git clone <your-repo-url> ai-news-agent
cd ai-news-agent
cp .env.example .env
```

### 2. Fill in `.env`

Open `.env` and set **at minimum**:

```env
# Pick ONE free LLM provider:
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxx          # https://console.groq.com (free)

# Email (Gmail with App Password):
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # 16-char App Password
EMAIL_FROM=you@gmail.com
EMAIL_TO=towhid4635@gmail.com

# Optional — LangSmith tracing (free):
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=ls__xxxx
```

### 3. Launch

```bash
docker compose up -d
```

That's it. The agent will:
- Start the API at `http://localhost:8000`
- Schedule a daily run at 06:30 AM (Asia/Dhaka timezone)
- Send your first briefing tomorrow morning

### 4. Trigger manually (first test)

```bash
curl -X POST http://localhost:8000/run-now
```

---

## 🖥 Local Development (without Docker)

```bash
# Create venv
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Copy and edit config
cp .env.example .env

# Init DB
python -c "from app.repositories.database import init_db; init_db()"

# Start server
python -m uvicorn app.main:app --reload --port 8000
```

---

## 🔑 Free LLM Provider Setup

### Option A: Groq (recommended — fastest)
1. Sign up at https://console.groq.com
2. Create an API key
3. Set in `.env`:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_key
   GROQ_MODEL=llama-3.1-8b-instant
   ```

### Option B: OpenRouter
1. Sign up at https://openrouter.ai
2. Set in `.env`:
   ```env
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-your_key
   OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
   ```

### Option C: Google Gemini
1. Get key at https://aistudio.google.com
2. Set in `.env`:
   ```env
   LLM_PROVIDER=gemini
   GOOGLE_API_KEY=AIza_your_key
   GEMINI_MODEL=gemini-1.5-flash
   ```

---

## 📧 Gmail SMTP Setup

Gmail requires an **App Password** (not your regular password):

1. Enable 2-Factor Authentication on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Create a new App Password → select "Mail"
4. Copy the 16-character password into `SMTP_PASSWORD`

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_FROM=your@gmail.com
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check + config summary |
| `GET` | `/metrics` | Run statistics |
| `GET` | `/news/latest` | Latest top articles (JSON) |
| `GET` | `/runs` | Pipeline run history |
| `POST` | `/run-now` | Trigger pipeline immediately |
| `GET` | `/newsletter/latest` | View latest HTML newsletter in browser |

---

## 🔭 LangSmith Observability

1. Sign up free at https://smith.langchain.com
2. Create a project named `ai-news-agent`
3. Set in `.env`:
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGSMITH_API_KEY=ls__your_key
   LANGSMITH_PROJECT=ai-news-agent
   ```

Every pipeline run will appear as a traced workflow with node-level latency, token usage, and error details.

---

## ➕ Adding RSS Feeds

Edit `app/services/rss_feeds.py` — add a `FeedConfig` to either `LAB_FEEDS` or `MEDIA_FEEDS`:

```python
FeedConfig("My Custom Blog", "https://myblog.com/rss.xml", "media"),
```

Or add at runtime:
```python
from app.services.rss_feeds import add_feed
add_feed("New Feed", "https://example.com/rss", "research")
```

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio pytest-cov

# All tests
pytest

# Unit tests only (fast, no network)
pytest tests/unit/

# With coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 📁 Project Structure

```
ai-news-agent/
├── app/
│   ├── agents/
│   │   ├── discovery_agent.py      # RSS fetching
│   │   ├── extraction_agent.py     # Full-text extraction
│   │   ├── scoring_agent.py        # LLM relevance scoring
│   │   ├── dedup_agent.py          # Duplicate detection
│   │   ├── summarization_agent.py  # LLM summaries
│   │   ├── ranking_agent.py        # Top-N selection + trends
│   │   ├── newsletter_agent.py     # HTML rendering
│   │   └── email_agent.py          # SMTP delivery
│   ├── graph/
│   │   └── workflow.py             # LangGraph pipeline
│   ├── models/
│   │   └── article.py              # Pydantic state models
│   ├── repositories/
│   │   ├── database.py             # SQLAlchemy ORM
│   │   └── run_repo.py             # DB persistence
│   ├── api/
│   │   └── routes.py               # FastAPI endpoints
│   ├── scheduler/
│   │   └── job.py                  # APScheduler config
│   ├── services/
│   │   └── rss_feeds.py            # Feed registry
│   ├── templates/
│   │   └── newsletter.html         # Jinja2 email template
│   ├── utils/
│   │   ├── config.py               # Pydantic settings
│   │   ├── logger.py               # Structured logging
│   │   └── llm_factory.py          # LLM provider factory
│   └── main.py                     # FastAPI app + lifespan
├── tests/
│   ├── unit/                       # Fast, no I/O
│   ├── integration/                # Mocked HTTP/LLM
│   └── test_workflow.py            # E2E pipeline tests
├── data/                           # SQLite database (git-ignored)
├── logs/                           # Log files (git-ignored)
├── .env.example                    # Config template
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` / `openrouter` / `gemini` |
| `MAX_ARTICLES_PER_RUN` | `100` | Articles fetched before scoring |
| `TOP_N_ARTICLES` | `10` | Articles in final newsletter |
| `MIN_RELEVANCE_SCORE` | `40` | Discard articles below this score |
| `SCHEDULE_HOUR` | `6` | Run hour (0-23) |
| `SCHEDULE_MINUTE` | `30` | Run minute (0-59) |
| `TIMEZONE` | `Asia/Dhaka` | Any pytz timezone |
| `DATABASE_URL` | `sqlite:///./data/news_agent.db` | SQLite or PostgreSQL |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |

---

## 🐛 Troubleshooting

**No email received?**
- Check `GET /runs` — look at `email_sent` and `error_message`
- Verify Gmail App Password (not your main password)
- Check spam folder

**LLM errors?**
- Verify your API key is set and has quota
- Check `GET /runs` for error details
- Try switching `LLM_PROVIDER` to another free option

**Docker build fails?**
- Ensure Docker has at least 2GB RAM available
- Try `docker compose build --no-cache`

---

## 📄 License

MIT — free for personal and commercial use.
