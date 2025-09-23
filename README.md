# TensorZero GitHub CI bot

We want to automate fixing CI and other GitHub Action failures.

## FastAPI service

The project uses [uv](https://docs.astral.sh/uv/) for dependency management. The service exposes:
- `GET /health` for a simple health check.
- `POST /webhook` to receive GitHub `workflow_run` failure events. If `GITHUB_WEBHOOK_SECRET` is set, the service verifies the `X-Hub-Signature-256` header. When the secret is unset, signature checks are skipped (log warning) — suitable only for local testing.

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

By default the server listens on `0.0.0.0:8000`. Override with `HOST` or `PORT` environment variables if needed.

Once running, verify the service at `http://localhost:8000/health`.

### Local webhook forwarding

During development you can forward GitHub webhooks to your local server using a tunneling tool such as [Smee](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries):

```bash
smee -u $WEBHOOK_PROXY_URL --path /webhook --port 8000
```

Ensure the secret configured in GitHub matches `GITHUB_WEBHOOK_SECRET` when signature verification is enabled.
