# TensorZero GitHub CI bot

We want to automate fixing CI and other GitHub Action failures.

## FastAPI service

The project uses [uv](https://docs.astral.sh/uv/) for dependency management. The service exposes a single `GET /hello` endpoint that returns a JSON greeting.

### Setup

```bash
uv sync
```

### Run the server

```bash
uv run main.py
```

By default the server listens on `0.0.0.0:3000`. Override with `HOST` or `PORT` environment variables if needed.

Once running, open `http://localhost:3000/hello` to see the greeting response.

### Setting up forwarding

Follow [Smee's docs to set up forwarding](https://docs.github.com/en/webhooks/using-webhooks/handling-webhook-deliveries)

`smee -u $WEBHOOK_PROXY_URL --path /webhook --port 3000`