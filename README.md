# 🚀 Enterprise LLM Gateway & AI Governance Platform

An end-to-end, high-performance **Enterprise LLM Gateway** built with FastAPI, PostgreSQL, Redis, and SQLAlchemy 2.0. The platform unifies multi-provider routing (Gemini, OpenAI, Groq, DeepSeek), smart semantic prompt caching, real-time observability tracing, AI guardrails with PII masking, prompt versioning with A/B testing, and scientific model evaluation benchmarks with P50/P95 latency percentiles.

---

## 🌟 Key Architecture & Features

```text
                               ┌───────────────────────────────────┐
                               │       Client / App Request        │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │      FastAPI Gateway Engine       │
                               └─────────────────┬─────────────────┘
                                                 │
            ┌──────────────────────┬─────────────┴────────────┬──────────────────────┐
            ▼                      ▼                          ▼                      ▼
  ┌───────────────────┐  ┌───────────────────┐      ┌───────────────────┐  ┌───────────────────┐
  │   Guardrails &    │  │  Semantic Caching │      │  Rate Limiter &   │  │   Prompt Registry │
  │   PII Masking     │  │  (Redis / Vector) │      │  Quota Enforcer   │  │   & A/B Testing   │
  └─────────┬─────────┘  └─────────┬─────────┘      └─────────┬─────────┘  └─────────┬─────────┘
            │                      │                          │                      │
            └──────────────────────┴─────────────┬────────────┴──────────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │   Dynamic Failover & Router Engine│
                               └─────────────────┬─────────────────┘
                                                 │
            ┌──────────────────────┬─────────────┴────────────┬──────────────────────┐
            ▼                      ▼                          ▼                      ▼
     ┌─────────────┐        ┌─────────────┐            ┌─────────────┐        ┌─────────────┐
     │   Gemini    │        │   OpenAI    │            │    Groq     │        │  DeepSeek   │
     └─────────────┘        └─────────────┘            └─────────────┘        └─────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │ Phase 6 Observability & Benchmarks│
                               └───────────────────────────────────┘
```

### Complete Phase Capability Matrix:
1. **Phase 1 — Authentication & Security**: Secure JWT user management, bcrypt password hashing, token refreshes, and tenant isolation.
2. **Phase 2 — API Key Management**: Tenant-scoped API key generation (`gw_live_...`), revocation, usage tracking, and automated expiration policies.
3. **Phase 3 — Multi-Provider Gateway**: Standardized unified OpenAI-compatible payload structure with failover routing between Gemini, OpenAI, Groq, and DeepSeek.
4. **Phase 4 — Rate Limiting & Tiered Quotas**: Configurable plan quotas (`free`, `pro`, `enterprise`), sliding window rate limiting, token & request spend tracking.
5. **Phase 5 — Dynamic Health & Circuit Breaker**: Continuous health checks, error threshold detection, latency tracking, and automatic provider failover routing.
6. **Phase 6 — Observability & Tracing**: End-to-end request lifecycle logging, stage timing breakdowns (`trace_xxxx`), failover attempt histories, and optional Langfuse tracing integration.
7. **Phase 7 — Exact & Semantic Prompt Caching**: High-performance exact match and cosine vector similarity semantic caching backed by Redis (with memory fallback) to cut API cost and latency by up to 90%.
8. **Phase 8 — AI Guardrails & Content Moderation**: Regex PII redaction (email, SSN, credit cards, API keys), prompt injection detection, input/output size validation, and dry-run audit logs.
9. **Phase 9 — Prompt Registry, Versioning & Evaluation**: Git-like prompt template management, variable schema validation preview, A/B experiment routing, and LLM-as-a-Judge quality scoring.
10. **Phase 10 — Model Evaluation & Benchmarking Platform**: Automated multi-trial model comparison matrix calculating P50 (median) latency, P95 latency, standard deviation, throughput ($tokens/sec$), and multi-dimensional model leaderboards.

---

## 🛠️ Local Development & Quickstart

### Option A: Local Python Environment

1. **Clone and setup virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in your database URL and API keys:
   ```powershell
   cp .env.example .env
   ```

3. **Initialize Database**:
   ```powershell
   python init_db.py
   ```

4. **Start Application Server**:
   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
   ```
   Open your browser at `http://127.0.0.1:9000` to access the SPA Management Dashboard!

---

### Option B: Docker Compose (Full Stack)

Run PostgreSQL, Redis, PgAdmin, and FastAPI Gateway together with one command:

```bash
docker-compose up --build -d
```
Access points:
- **LLM Gateway Dashboard**: `http://localhost:8000`
- **PgAdmin Dashboard**: `http://localhost:5050` (Login: `admin@gateway.local` / `admin`)

---

## 🚀 Free Cloud Deployment Roadmap

To deploy this project to production for free, follow this step-by-step architecture:

### 1. Hosted PostgreSQL (Free Tier)
- **Supabase** or **Neon.tech**: Free managed PostgreSQL database with `pgvector` support.
- Set `DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<dbname>`

### 2. Hosted Redis (Free Tier)
- **Upstash Redis**: Free serverless Redis instance.
- Set `REDIS_URL=rediss://default:<password>@<host>:6379/0`

### 3. FastAPI Gateway Deployment
- **Koyeb** or **Render**: Deploy the included `Dockerfile` directly from your GitHub repository.
- Configure Environment Variables (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`).

---

## 🧪 Test Suite Execution

Run automated integration test suites across phases:

```powershell
# Phase 8: Guardrails & Content Moderation
python tests/test_guardrails.py

# Phase 9: Prompt Registry & Evaluation
python tests/test_prompt_registry.py

# Phase 10: Scientific Model Benchmarking
python tests/test_benchmarking.py
```

---

## 📄 License
MIT License. Built with ❤️ for scalable AI engineering.
