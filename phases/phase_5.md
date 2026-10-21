# Phase 5 Design Specification: Intelligent Routing & Failover Engine

This document provides a comprehensive overview of **Phase 5: Intelligent Routing & Failover Engine** implemented in the LLM Gateway Platform.

---

## 1. Objectives
1. **Multi-Model Routing**: Allow users to explicitly target standard models, or use policy-based algorithms to select healthy providers dynamically.
2. **Provider Health Telemetry**: Automatically persist running success rates, consecutive failures, and EWMA latencies in the database for each provider.
3. **Passive Circuit Breakers**: Open circuits for unhealthy providers (consecutive failures $\ge 3$ or success rate $<50\%$), routing traffic away from them.
4. **Dynamic Failover Retry Loop**: Intercept API failure responses, log statistics, and immediately failover through a user-specified or automatic fallback chain.
5. **Real-Time Health UI**: Render circuit statuses, success rates, and request metadata visually in the client panel.

---

## 2. Directory Structure of Phase 5 Changes
```text
llm-gateway/
│
├── alembic/
│   └── versions/
│       └── e7b9b2a1a8c4_add_provider_metrics_table.py  # [NEW] Table schema for provider health metrics
│
├── app/
│   ├── api/
│   │   ├── gateway.py                                 # Core chat post endpoint returning resolved target
│   │   └── status.py                                  # GET /api/providers/health endpoint
│   │
│   ├── core/
│   │   └── config.py                                  # Added speed ranks and default model configs
│   │
│   ├── models/
│   │   └── provider_metric.py                         # [NEW] ProviderMetric table structure
│   │
│   ├── schemas/
│   │   └── gateway.py                                 # Enhanced ChatRequest input schemas (policy, fallback chain)
│   │
│   ├── services/
│   │   ├── cost_service.py                            # [NEW] Cost computations and cheapest model resolver
│   │   ├── provider_health_service.py                 # [NEW] Circuit breaker state updates & EWMA latency
│   │   └── routing_service.py                         # [NEW] Policy router & failover sequence evaluator
│   │
│   └── static/
│       ├── index.html                                 # Downstream Provider Health telemetry card
│       └── app.js                                     # Fetches health data and renders Playground routing selectors
│
└── tests/
    └── test_routing_failover.py                       # [NEW] Failover scenarios & policy verification scripts
```

---

## 3. Database Schema: `provider_metrics`
Tracks rolling availability statistics for downstream providers (`openai`, `gemini`, `deepseek`, `groq`):
* `provider` (String, Primary Key)
* `avg_latency_ms` (Integer): Exponentially Weighted Moving Average (EWMA) with smoothing coefficient $\alpha = 0.2$.
* `success_rate` (Numeric): Percentage of completed calls versus failures.
* `consecutive_failures` (Integer): Running fail count before circuit opens.
* `health_status` (String): `"healthy"`, `"degraded"`, or `"unhealthy"`.
* `total_requests` / `total_failures` / `last_failure_at`

---

## 4. Routing Algorithms & Policies
* **Cheapest**: Resolves to the healthy provider offering the lowest average USD price per token.
* **Fastest**: Routes to the healthy provider showing the lowest rolling EWMA latency.
* **Best Quality**: Routes to the healthy provider with the highest quality rank (e.g. OpenAI GPT-4o).
* **Auto**: Dynamic classification based on prompt string length:
  * Short ($<100$ chars): Cheapest model (high speed, low cost).
  * Medium ($<500$ chars): Balanced model (Gemini).
  * Long ($\ge 500$ chars): Best quality model (OpenAI).

---

## 5. Failover Sequence
During a chat completion request, the sequence follows:
1. Select target provider based on the specified model, policy, or fallback list.
2. Attempt execution via `ProviderManager`.
3. If successful:
   - Record latency and success metric in `provider_metrics`.
   - Log successful usage and return response.
4. If failure occurs:
   - Increment `consecutive_failures` and record failed attempt in metrics database.
   - Circuit transitions to degraded or unhealthy if thresholds are crossed.
   - Advance to the next configured fallback provider in the chain and retry execution.
5. If all fallbacks are exhausted, raise HTTP 502 Bad Gateway with diagnostic logs.
