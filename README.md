# ⚡ RouteForge: Enterprise LLM Gateway & AI Governance Engine

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

**RouteForge** is a production-ready, high-performance **Unified LLM Gateway and AI Governance Platform** built with **FastAPI**, **PostgreSQL (pgvector)**, and **Redis**.

It solves the operational challenges of using LLMs in production: single-provider lock-in, unexpected downtime, runaway API costs, prompt injection attacks, sensitive PII leaks, and lack of real-time visibility.

---

## 🚀 Key Highlights & Architecture

```text
                               ┌────────────────────────────────────────┐
                               │           Client / App Request         │
                               └───────────────────┬────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │       RouteForge Gateway Engine        │
                               └───────────────────┬────────────────────┘
                                                   │
             ┌──────────────────────┬──────────────┴─────────────┬──────────────────────┐
             ▼                      ▼                            ▼                      ▼
   ┌───────────────────┐  ┌───────────────────┐        ┌───────────────────┐  ┌───────────────────┐
   │   Guardrails &    │  │  Semantic Caching │        │  Rate Limiter &   │  │  Prompt Registry  │
   │   PII Masking     │  │  (Redis / Vector) │        │  Tier Quotas      │  │  & A/B Testing    │
   └─────────┬─────────┘  └─────────┬─────────┘        └─────────┬─────────┘  └─────────┬─────────┘
             │                      │                            │                      │
             └──────────────────────┴──────────────┬─────────────┴──────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │    Dynamic Failover & Routing Engine   │
                               └───────────────────┬────────────────────┘
                                                   │
             ┌──────────────────────┬──────────────┴─────────────┬──────────────────────┐
             ▼                      ▼                            ▼                      ▼
      ┌─────────────┐        ┌─────────────┐              ┌─────────────┐        ┌─────────────┐
      │   Gemini    │        │   OpenAI    │              │    Groq     │        │  DeepSeek   │
      └─────────────┘        └─────────────┘              └─────────────┘        └─────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │ Observability, Traces & Benchmarking   │
                               └────────────────────────────────────────┘
```

---

## 🛡️ Core Capabilities

### 1. 🔄 Multi-Provider Unified Routing & Auto-Failover
- Drop-in OpenAI-compatible request payload structure.
- Seamlessly routes across **Google Gemini**, **OpenAI**, **Groq**, and **DeepSeek**.
- Automatic circuit breaker: detects provider errors or high latency and immediately switches to secondary fallback providers with zero client interruption.

### 2. 🔒 AI Safety Guardrails & PII Redaction
- **PII Detection & Masking**: Real-time redaction of Emails, Phone Numbers, Social Security Numbers (SSN), Credit Cards, and API Keys before they hit LLM servers.
- **Prompt Injection & Jailbreak Defense**: Detects adversarial prompts (`ignore previous instructions`, `DAN mode`, `bypass safety filters`) and enforces configurable block/warn actions.
- **Developer Safety Sandbox**: Interactive console in the UI to dry-run prompts against governance policies.

### 3. ⚡ Smart Semantic & Exact Prompt Caching
- **Exact Match Caching**: Delivers sub-millisecond responses for repeated queries.
- **Semantic Caching with Vector Embeddings**: Cosine similarity matching (`>= 0.90`) to recognize semantically identical queries and reuse responses, cutting external API costs by up to 90%.
- Backed by **Redis** with automatic in-memory fallback.

### 4. 📊 Observability, Tracing & Cost Analytics
- Real-time latency tracking, stage-by-stage timing breakdowns (`trace_xxxx`), and failover logs.
- Token consumption and cost calculation per request, model, and tenant.
- Native integration with **Langfuse** tracing.

### 5. 🧪 Prompt Registry, Versioning & Evaluation
- Git-like prompt template versioning (`v1`, `v2`, `staging`, `production`).
- Variable injection and schema validation.
- Live A/B testing experiment traffic splitting.
- Built-in **LLM-as-a-Judge** scoring mechanism for output quality evaluation.

### 6. 🏆 Scientific Model Benchmarking Platform
- Side-by-side multi-trial benchmark execution.
- Computes **P50 (Median)** latency, **P95** latency, standard deviation, and throughput ($tokens/sec$).
- Dynamic model leaderboard to compare models across cost, speed, and reliability.

### 7. 🔑 Multi-Tenant API Key Management & Rate Limiting
- Tenant-scoped API key generation (`gw_live_...`) with automatic hashing.
- Sliding window rate limiting and tiered monthly quota enforcement (`free`, `pro`, `enterprise`).

---

## 💻 Tech Stack

- **Framework**: FastAPI (Python 3.11)
- **ASGI Server**: Uvicorn
- **Database & ORM**: PostgreSQL, `pgvector`, SQLAlchemy 2.0 (async), AsyncPG, Alembic
- **Caching**: Redis (with built-in local memory fallback)
- **Security**: JWT (`python-jose`), Passlib (`bcrypt`)
- **LLM SDKs**: Google GenAI (`google-genai`), OpenAI SDK, Groq, DeepSeek
- **Dashboard UI**: Modern dark-mode SPA built with vanilla HTML5, CSS3 glassmorphism, and JavaScript (zero build step required)
- **Containerization**: Docker & Docker Compose

---

## 🛠️ Quickstart (Run Locally)

### Prerequisites
- Python 3.11+
- PostgreSQL (or use Docker)

### 1. Clone the repository
```bash
git clone https://github.com/Sidra51/RouteForge.git
cd RouteForge
```

### 2. Set up virtual environment
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Fill in your database URL and provider API keys in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/llm_gateway
JWT_SECRET_KEY=your_generated_secret_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
```

### 4. Initialize Database
```powershell
python init_db.py
```

### 5. Run the Application
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser:
* **Interactive UI Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🐳 Run with Docker Compose

Run the entire stack (FastAPI Gateway, PostgreSQL with pgvector, Redis, and PgAdmin) with one command:

```bash
docker-compose up --build -d
```

- **Gateway & Dashboard**: `http://localhost:8000`
- **PgAdmin Database Manager**: `http://localhost:5050` (`admin@gateway.local` / `admin`)

---

## 📡 API Usage Example

Send completions via standard OpenAI-compatible format through the RouteForge Gateway:

```python
import openai

client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/api/v1/gateway",
    api_key="gw_live_your_gateway_key_here"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash", # or "gpt-4o", "deepseek-chat", "llama3-70b-8192"
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in two sentences."}
    ]
)

print(response.choices[0].message.content)
```

---

## 🧪 Testing

Execute test suites for each phase:

```powershell
# Test Guardrails & PII redaction
python tests/test_guardrails.py

# Test Prompt Registry & A/B testing
python tests/test_prompt_registry.py

# Test Model Benchmarking engine
python tests/test_benchmarking.py
```

---

## 🌐 Free Cloud Deployment

| Component | Recommended Platform | Guide |
| :--- | :--- | :--- |
| **Gateway Service** | **Render.com** / **Koyeb** | Connect this GitHub repo and deploy using Dockerfile |
| **PostgreSQL Database** | **Neon.tech** | Free serverless PostgreSQL (supports `postgresql+asyncpg://`) |
| **Redis Cache** | **Upstash.com** | Free serverless Redis (or rely on built-in in-memory fallback) |

---

## 📄 License

This project is licensed under the MIT License.
