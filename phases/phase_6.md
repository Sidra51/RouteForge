# Phase 6 Design Specification: Observability & Tracing

This document provides a comprehensive overview of **Phase 6: Observability & Tracing** implemented in the LLM Gateway Platform.

---

## 1. Objectives
1. **Correlation Tracing**: Assign a unique trace correlation ID (`trace_xxxxx`) to every request entering the gateway.
2. **Transaction Timelines**: Persist structured timeline stage logs mapping pipeline milestones with latency offset timestamps.
3. **Failovers Tracking**: Log individual retry/failover attempts detailing provider status, latency, costs, and downstream errors.
4. **Error Aggregation**: Categorize errors under specific telemetry types (`rate_limit_exceeded`, `token_quota_exceeded`, `authentication_error`, `provider_error`, `provider_unavailable`, or `routing_error`).
5. **Observability UI**: Display interactive trace lists, stages, retry details, and charts (latency EWMA compare and error doughnuts) in the SPA panel.

---

## 2. Directory Structure of Phase 6 Changes
```text
llm-gateway/
│
├── alembic/
│   └── versions/
│       └── 68a542bcdaab_add_request_traces_and_trace_id.py  # [NEW] Migrations for traces table
│
├── app/
│   ├── api/
│   │   ├── gateway.py                                 # Generates trace_id and returns X-Trace-ID header
│   │   └── observability.py                           # [NEW] Telemetry list, details, errors, throughput APIs
│   │
│   ├── core/
│   │   └── config.py                                  # Added STORE_FULL_PAYLOAD and Langfuse variables
│   │
│   ├── models/
│   │   ├── request_trace.py                           # [NEW] RequestTrace database mapping
│   │   └── usage.py                                   # Added trace_id column to UsageLog
│   │
│   ├── services/
│   │   ├── trace_service.py                           # [NEW] Life-cycle updates for trace records and stages
│   │   └── langfuse_service.py                        # [NEW] external Langfuse LLMOps agent sync
│   │
│   └── static/
│       ├── index.html                                 # Observability tab widgets and Timeline Details modal
│       ├── app.js                                     # Fetches telemetry, updates Chart.js plots and timelines
│       └── style.css                                  # Styles vertical flow diagrams and attempts cards
│
└── tests/
    └── test_observability_tracing.py                 # [NEW] Integration test suite for tracing pipeline
```

---

## 3. Database Schema: `request_traces`
Logs execution states and parameters for user requests:
* `id` (UUID, Primary Key)
* `trace_id` (String, unique indexed): e.g. `trace_abcd12345678`
* `user_id` (UUID, ForeignKey): Nullable for unauthorized blocks.
* `prompt` / `response` (Text): Input and output content (truncated to 500 characters when `STORE_FULL_PAYLOAD = False`).
* `status_code` (Integer): Final response code.
* `error_type` / `error_message` (String/Text): Telemetry categorization.
* `timeline` (JSON): Stages array storing chronological events.
* `attempts` (JSON): Retries list mapping failover parameters.
* `total_latency_ms` (Integer): Complete transaction length.
* `created_at` (DateTime)

---

## 4. Timeline & Attempts Logging Specifications
* **Timeline stage items**:
  ```json
  {
    "stage": "received | limits_passed | routing_decision | provider_call:<provider> | response_returned",
    "timestamp": "ISO-8601 UTC string",
    "duration_ms": 125 // elapsed ms from trace creation
  }
  ```
* **Attempts retry items**:
  ```json
  {
    "attempt": 1,
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "status": "success | failed",
    "latency_ms": 450,
    "cost": 0.000056,
    "error": "..."
  }
  ```

---

## 5. UI Widgets & Inspector
1. **Interactive Trace Explorer**: Standard grid of user requests showing trace IDs, final outcome, latency, timestamps, and input/output previews.
2. **Timeline Inspector Modal**: 
   - A vertical line checklist rendering execution stages with active step color codes (success = green, info = blue, warning = orange, error = red).
   - Side-by-side retry detail boxes and input/output payload pre-blocks.
3. **Provider comparison chart**: Double-y-axis bar chart comparing rolling latencies and success percentages across active providers.
4. **Error categories doughnut**: Breakdown of error types.
