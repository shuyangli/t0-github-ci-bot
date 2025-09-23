from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/hello")
async def hello() -> dict[str, str]:
    return {"message": "Hello from the TensorZero CI bot"}

@app.post("/webhook")
async def print_webhook_body(request: Request) -> dict[str, str]:
    body = await request.json()
    print(body)
    return {"message": "Hello from the TensorZero CI bot"}

def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
