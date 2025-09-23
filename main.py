from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class Repository(BaseModel):
    full_name: str = Field(..., alias="full_name")
    html_url: str | None = Field(None, alias="html_url")


class WorkflowRun(BaseModel):
    id: int
    name: str
    head_branch: str | None = Field(None, alias="head_branch")
    head_sha: str | None = Field(None, alias="head_sha")
    conclusion: str | None
    event: str
    html_url: str | None = Field(None, alias="html_url")


class WorkflowRunPayload(BaseModel):
    repository: Repository
    workflow_run: WorkflowRun
    action: str | None = None


class WebhookSettings(BaseModel):
    github_webhook_secret: str | None = None


def get_settings() -> WebhookSettings:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set; webhook signature verification is disabled")
    return WebhookSettings(github_webhook_secret=secret)


def verify_signature(secret: str | None, signature_header: str | None, payload: bytes) -> None:
    if not secret:
        return
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")
    digest_name, _, received_signature = signature_header.partition("=")
    if digest_name != "sha256" or not received_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported signature format")
    computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_signature, computed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"message": "OK"}


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    settings: WebhookSettings = Depends(get_settings),
) -> dict[str, Any]:
    body = await request.body()
    verify_signature(settings.github_webhook_secret, x_hub_signature_256, body)

    try:
        payload = WorkflowRunPayload.model_validate_json(body)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc

    logger.info(
        "Received %s event for workflow_run id=%s conclusion=%s repo=%s",
        x_github_event,
        payload.workflow_run.id,
        payload.workflow_run.conclusion,
        payload.repository.full_name,
    )

    if x_github_event != "workflow_run":
        logger.info("Ignoring unsupported GitHub event: %s", x_github_event)

    return {"status": "accepted"}


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
