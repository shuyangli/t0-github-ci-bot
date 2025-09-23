# TensorZero GitHub CI bot

We want to automate fixing CI and other GitHub Action failures.

## FastAPI service

The project uses [uv](https://docs.astral.sh/uv/) for dependency management. The service exposes:
- `GET /health` for a basic health check.
- `POST /webhook` to receive GitHub events. We currently support `workflow_run`, `check_suite`, and `pull_request` payloads and log details needed for downstream automation. If `GITHUB_WEBHOOK_SECRET` is set, the service verifies `X-Hub-Signature-256`; when unset, verification is skipped with a warning (local testing only).

### Setup

```bash
uv sync
```

### Run the server

```bash
# Optional but strongly recommended outside local testing
export GITHUB_WEBHOOK_SECRET=your-shared-secret
uv run main.py
```

By default the server listens on `0.0.0.0:3000`. Override with `HOST` or `PORT` environment variables if needed.

Once running, verify the service at `http://localhost:3000/health`.

### Local webhook forwarding

During development you can forward GitHub webhooks to your local server using a tunneling tool such as [Smee](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries):

```bash
smee -u $WEBHOOK_PROXY_URL --path /webhook --port 3000
```

Ensure the secret configured in GitHub matches `GITHUB_WEBHOOK_SECRET` when signature verification is enabled.
