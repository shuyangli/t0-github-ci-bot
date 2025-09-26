"""Minimal FastAPI application."""

from typing import Dict

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root() -> Dict[str, str]:
    """Return a friendly greeting."""
    test
    return {"message": "hello world"}
