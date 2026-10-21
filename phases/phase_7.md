# Phase 7 Design Draft: Proposed Roadmap Candidates

This document outlines proposed candidates for **Phase 7** of the LLM Gateway Platform. Developers can review these proposals to choose the next milestone.

---

## Candidate A: Semantic & Exact Prompt Caching (Recommended)

### 1. Objectives
* Save cost and achieve near-0ms latencies for redundant queries.
* Support exact string match caches for identical prompts.
* Support **Semantic Similarity Caching** for prompts that are conceptually identical but phrased slightly differently (e.g., *"How is the weather today?"* vs *"What's the weather like today?"*).

### 2. Architecture & Components
* **Exact Cache**: Redis key-value cache mapping hashed prompt strings directly to parsed LLM outputs (TTL configurable).
* **Semantic Cache**:
  * Utilize an embedded vector store (such as `sqlite-vss` or `pgvector` inside PostgreSQL) to store prompt embeddings.
  * Compute cosine similarity against historical prompts during request routing.
  * If a high similarity match (e.g. threshold $\ge 0.92$) is found, serve the cached answer immediately.
* **Service Integrations**:
  * `app/services/cache_service.py` to intercept requests early in the `route_request` sequence.
  * Embeddings generation helper using `gemini-2.0-flash` or local models.

---

## Candidate B: Guardrails, Content Moderation & Masking

### 1. Objectives
* Enforce enterprise compliance, toxicity filtering, and sensitive data protection.
* Filter prompts and completions before forwarding or returning them.

### 2. Architecture & Components
* **PII Masking**: Mask phone numbers, email addresses, SSNs, or API tokens using pattern matching (regex) and Named Entity Recognition (NER) models.
* **Toxicity / Safety Guard**: Evaluate prompt and response safety scores against configured moderation APIs (such as OpenAI's Moderation API or Google's safety settings) or open-source local checkers.
* **Rejections**: Return structured HTTP 400 or HTTP 403 responses if guardrails are violated, logging violation metrics in the traces.

---

## Candidate C: Admin Management Console

### 1. Objectives
* Introduce administrator visual controls for user accounts and tier limits.
* Manage quotas and active states dynamically via the UI dashboard.

### 2. Architecture & Components
* **Role-Based Access Controls (RBAC)**: Ensure only users with `role = "ADMIN"` can view or query administration endpoints.
* **Management UI**:
  * Users directory list with active toggles and role assigners.
  * Custom override fields to modify RPM limits, daily caps, or monthly tokens direct from the visual panel.
  * Aggregate spending dashboards across all system tenants.

---

## Candidate D: Usage Alerts & Slack/Discord Webhooks

### 1. Objectives
* Alert administrators and developers when quota limits are approaching.
* Set thresholds for notification warnings.

### 2. Architecture & Components
* **Quota Checks**: Periodic check script or real-time event hook evaluating usage.
* **Notifications**:
  * Trigger Slack or Discord channel webhook payloads when a user key reaches 80% or 100% of its monthly token limit.
  * Enable threshold emails via SMTP integration.
