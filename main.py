from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Callable

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class WebhookSettings(BaseModel):
    github_webhook_secret: str | None = None


def get_settings() -> WebhookSettings:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        # TODO: throttle this warning in the future to avoid log spam.
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


def extract_login(payload: dict[str, Any], key: str) -> str | None:
    actor = payload.get(key) or {}
    if isinstance(actor, dict):
        login = actor.get("login")
        if isinstance(login, str):
            return login
    return None


def looks_like_bot(login: str | None) -> bool:
    return bool(login and login.endswith("[bot]"))


def handle_workflow_run(payload: dict[str, Any]) -> None:
    workflow_run = payload.get("workflow_run") or {}
    repository = payload.get("repository") or {}
    action = payload.get("action")
    repo_name = repository.get("full_name", "<unknown>")
    run_id = workflow_run.get("id")
    conclusion = workflow_run.get("conclusion")
    head_branch = workflow_run.get("head_branch")
    actor_login = extract_login(workflow_run, "actor") or extract_login(payload, "sender")

    logger.info(
        "workflow_run event: action=%s id=%s conclusion=%s repo=%s branch=%s actor=%s bot=%s",
        action,
        run_id,
        conclusion,
        repo_name,
        head_branch,
        actor_login,
        looks_like_bot(actor_login),
    )


def handle_check_suite(payload: dict[str, Any]) -> None:
    check_suite = payload.get("check_suite") or {}
    repository = payload.get("repository") or {}
    action = payload.get("action")
    status_value = check_suite.get("status")
    conclusion = check_suite.get("conclusion")
    repo_name = repository.get("full_name", "<unknown>")
    head_branch = check_suite.get("head_branch")
    actor_login = extract_login(payload, "sender")

    logger.info(
        "check_suite event: action=%s status=%s conclusion=%s repo=%s branch=%s actor=%s bot=%s",
        action,
        status_value,
        conclusion,
        repo_name,
        head_branch,
        actor_login,
        looks_like_bot(actor_login),
    )


def handle_pull_request(payload: dict[str, Any]) -> None:
    pull_request = payload.get("pull_request") or {}
    action = payload.get("action")
    number = pull_request.get("number") or payload.get("number")
    repo_name = payload.get("repository", {}).get("full_name", "<unknown>")
    merged = pull_request.get("merged")
    sender_login = extract_login(payload, "sender")
    author_login = extract_login(pull_request, "user")

    logger.info(
        "pull_request event: action=%s number=%s merged=%s repo=%s author=%s sender=%s sender_bot=%s",
        action,
        number,
        merged,
        repo_name,
        author_login,
        sender_login,
        looks_like_bot(sender_login),
    )


EventHandler = Callable[[dict[str, Any]], None]
EVENT_HANDLERS: dict[str, EventHandler] = {
    "workflow_run": handle_workflow_run,
    "check_suite": handle_check_suite,
    "pull_request": handle_pull_request,
}


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
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to decode webhook payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    handler = EVENT_HANDLERS.get(x_github_event)
    if handler:
        handler(payload)
    else:
        logger.info("Unhandled GitHub event type: %s", x_github_event)

    return {"status": "accepted"}


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
