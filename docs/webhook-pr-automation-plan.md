# GitHub Webhook → PR Automation Plan

## Goals
- Receive GitHub workflow failure notifications via `/webhook`.
- Triage and analyze failures automatically.
- Use TensorZero-hosted LLMs to propose and apply fixes.
- Open a pull request with automated validation results and feed back merge signals to TensorZero.

## High-Level Flow
1. GitHub sends a `workflow_run` (or `check_suite`) failure payload to `/webhook`.
2. Service validates the signature and enqueues an automation job.
3. Worker checks out the repository, gathers failure context, and builds an LLM prompt.
4. Worker queries TensorZero for a model-generated patch suggestion, applies it, runs validation, and prepares artifacts.
5. Worker pushes changes, opens a PR, and streams merge outcomes back to TensorZero.

## Work Breakdown Structure

### 1. Webhook Ingestion
- Define FastAPI `POST /webhook` endpoint with a Pydantic model covering required GitHub fields (repository, workflow run, conclusion, head SHA, branch).
- Verify `X-Hub-Signature-256` using shared secret; respond with 401 on mismatch.
- Return 202 quickly after validation; insert raw payload + metadata into a persistence layer for traceability.
- Implement idempotency guard keyed on workflow run ID to avoid duplicate processing.
- Emit structured logs and basic counters for observability.

### 2. Background Job Orchestration
- Introduce an internal queue abstraction (initially in-memory) to decouple webhook handling from long-running work.
- Track job lifecycle (`pending`, `cloning`, `analysis`, `patching`, `testing`, `pr`, `feedback`, `failed`, `completed`) in a lightweight store (SQLite file or JSON log) to support retries and metrics.
- Provide administrative helpers (CLI or endpoint) to inspect and retry jobs.

### 3. Repository Access & Workspace Management
- Authenticate as GitHub App or PAT with repo permissions; document credential setup.
- Clone target repository and checkout failing branch into a disposable workspace (e.g., `/tmp/t0-ci-bot/<job-id>`).
- Download workflow logs/artifacts using GitHub REST API for deeper context where possible.
- Guard against disk bloat: enforce size/time limits, clean up workspace on completion.

### 4. Failure Context Builder
- Parse workflow logs to extract failing steps, commands, and stack traces.
- Collect relevant repository metadata: latest commit diff, language hints, dependency manifests, test configuration.
- Normalize data into a structured prompt input (e.g., JSON template) for the LLM.
- Provide summarization heuristics to keep prompt within token budget (e.g., truncating logs, sampling key files).

### 5. TensorZero Deployment & Configuration
- Deploy a dedicated TensorZero instance using the upstream `docker-compose` templates (adapter + router + Postgres/Redis backends as required by the chosen stack).
- Configure connectors for target foundation models (OpenAI, Anthropic, etc.), mapping environment secrets into the compose stack and documenting required variables.
- Expose the TensorZero HTTP API internally (e.g., `http://tensorzero:8000/v1`) and secure it with auth tokens; rotate credentials via secrets manager.
- Set up persistence (Postgres) to capture prompts, completions, and feedback signals for later analysis.
- Establish monitoring basics: health checks on the TensorZero services, log shipping, and storage retention limits.

### 6. Language Model Integration via TensorZero
- Implement a client wrapper that calls TensorZero's completion endpoints (OpenAI-compatible) with timeout, retry, and streaming support.
- Design prompt template guiding the model to: diagnose failure, propose fix, output patch as unified diff; version prompts for later experimentation.
- Sanitize payloads (no secrets) and log prompts/responses with sensitive data redacted; rely on TensorZero's audit logging for replicated storage.
- Handle token-limit or API errors gracefully with retries/backoff and fallback strategies (e.g., smaller context prompt, alternative model route).
- Capture TensorZero response IDs to correlate downstream outcomes and enable reinforcement data collection.

### 7. Patch Application & Validation
- Parse LLM diff into file operations; apply with safeguards (reject large/binary files, conflict detection).
- Auto-run validation commands derived from workflow context (e.g., `pytest`, `npm test`), with configurable overrides and timeouts.
- Collect test output and summary for inclusion in the PR body.
- On failure, record diagnostics and mark job status for manual review.

### 8. GitHub PR Automation & Feedback Loop
- Create feature branch (`ci-bot/fix-<workflow-run-id>`), commit applied changes, push via GitHub API.
- Open PR referencing failing workflow, embed failure summary, changes made, TensorZero response ID, and validation results.
- Monitor the PR lifecycle (merged, closed without merge, additional commits) using GitHub webhooks or polling.
- Emit feedback events to TensorZero via its feedback API, tagging the original response ID with outcome signals (merge success, reviewer comments, revert, etc.).
- Optionally comment on the workflow run or commit with a link to the PR and update job state accordingly.

### 9. Error Handling, Observability, and Ops
- Emit structured logs (JSON) for each stage; integrate with metrics/monitoring as future work.
- Implement retry policies for transient failures (network, rate limits, LLM timeouts) with exponential backoff and circuit breakers.
- Provide status endpoint (e.g., `/healthz`, `/jobs/<id>`) for operational visibility.
- Define alerting guidelines for repeated failures or LLM misbehaviour.

### 10. Configuration & Secrets Management
- Store GitHub secrets, TensorZero auth tokens, and upstream model keys via environment variables or a secret manager abstraction.
- Allow configuration of repo allowlist, TensorZero deployment URL/model selection, validation command overrides, and resource limits.
- Document bootstrapping steps in README and add `.env.example` to illustrate required settings.

### 11. Testing & Hardening
- Unit tests: webhook validation, queue orchestration, prompt builder, TensorZero client, diff applier, GitHub PR client.
- Integration tests using recorded GitHub webhook payload fixtures and simulated repos.
- Dry-run mode for development: run full flow without pushing PR (logs intended commands + diff + TensorZero request preview).
- Security review checklist (secret handling, sandboxed execution, rate limiting) before production use.
- Add canary workflows to validate TensorZero deployment and PR feedback loop end-to-end.

## Immediate Next Steps
1. Scaffold `/webhook` endpoint with signature verification and minimal payload validation.
2. Add in-memory queue + job state tracking scaffolding.
3. Define TensorZero client interface, environment variables, and local deployment instructions leveraging the upstream compose files.
4. Decide on initial persistence (SQLite vs JSON) and stub interfaces for repo checkout and LLM interactions.
