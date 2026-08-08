"""FastAPI wrapper for the Zepto support-assistant LangGraph pipeline."""
from fastapi import FastAPI

from schemas import AskRequest, AskResponse
from graph import run_assistant
from ingest import get_or_build_collection

app = FastAPI(title="Zepto Support Assistant")


@app.on_event("startup")
def _startup():
    # Warm the ChromaDB collection (embeds + indexes the 8 docs on first run).
    get_or_build_collection()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = run_assistant(request.query)
    return AskResponse(**result)
