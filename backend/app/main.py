import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.answer import answer_question
from app.config import Settings, get_settings
from app.evaluate import EvalStatus, start_eval_in_background
from app.indexer import index_documents
from app.llm import get_provider
from app.loaders import load_bytes, load_directory
from app.models import ChatRequest, ChatResponse, FeedbackRequest, GapItem, SourceDoc
from app.ratelimit import RateLimiter
from app.store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("docsdesk")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.llm = get_provider(settings)
    app.state.store = get_store(settings)
    app.state.eval_status = EvalStatus()
    app.state.chat_limiter = RateLimiter(max_requests=settings.chat_rate_limit, window_seconds=60)

    if app.state.store.chunk_count() == 0:
        docs = load_directory(settings.sample_docs_dir)
        chunks = index_documents(docs, app.state.store, app.state.llm, settings.max_chunk_chars)
        log.info("Indexed %d sample documents into %d chunks", len(docs), chunks)
    yield


app = FastAPI(title="DocsDesk API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)


def require_admin(x_admin_token: str = Header(default=""), settings: Settings = Depends(get_settings)) -> None:
    if not settings.admin_token:
        raise HTTPException(503, "Admin endpoints are disabled until ADMIN_TOKEN is set.")
    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Invalid admin token.")


def client_key(request: Request) -> str:
    # Render and most hosts put the real client address first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/info")
def info(request: Request) -> dict:
    s: Settings = request.app.state.settings
    return {
        "company": s.company_name,
        "provider": request.app.state.llm.name,
        "chat_model": s.gemini_chat_model if request.app.state.llm.name == "gemini" else "fake",
        "persistent_store": request.app.state.store.persistent,
        "chunks": request.app.state.store.chunk_count(),
        "public_dashboard": s.public_dashboard,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    if not request.app.state.chat_limiter.allow(client_key(request)):
        raise HTTPException(429, "Too many questions in a minute. Please wait a moment.")
    s: Settings = request.app.state.settings
    response, _ = answer_question(
        body.question,
        request.app.state.store,
        request.app.state.llm,
        company=s.company_name,
        top_k=s.top_k,
        min_similarity=s.min_similarity,
    )
    return response


@app.post("/api/feedback", status_code=204)
def feedback(body: FeedbackRequest, request: Request) -> None:
    request.app.state.store.log_feedback(body.question, body.answer, body.helpful)


@app.get("/api/sources", response_model=list[SourceDoc])
def sources(request: Request) -> list[SourceDoc]:
    return request.app.state.store.list_sources()


def dashboard_access(request: Request, x_admin_token: str = Header(default="")) -> None:
    s: Settings = request.app.state.settings
    if not s.public_dashboard:
        require_admin(x_admin_token, s)


@app.get("/api/gaps", response_model=list[GapItem], dependencies=[Depends(dashboard_access)])
def gaps(request: Request, limit: int = 100) -> list[GapItem]:
    return request.app.state.store.list_gaps(min(limit, 500))


@app.get("/api/eval/latest")
def latest_eval(request: Request) -> dict:
    report = request.app.state.store.latest_eval_report()
    return {"status": request.app.state.eval_status.as_dict(), "report": report}


@app.post("/api/admin/eval", status_code=202, dependencies=[Depends(require_admin)])
def run_eval(request: Request) -> dict:
    s: Settings = request.app.state.settings
    started = start_eval_in_background(
        request.app.state.store, request.app.state.llm, s, request.app.state.eval_status, s.eval_delay_seconds
    )
    if not started:
        raise HTTPException(409, "An evaluation is already running.")
    return request.app.state.eval_status.as_dict()


@app.post("/api/admin/documents", dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile, request: Request) -> dict:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 5 MB.")
    try:
        doc = load_bytes(file.filename or "upload.txt", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    s: Settings = request.app.state.settings
    chunks = index_documents([doc], request.app.state.store, request.app.state.llm, s.max_chunk_chars)
    return {"doc_id": doc.doc_id, "title": doc.title, "chunks": chunks}


@app.delete("/api/admin/documents/{doc_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_document(doc_id: str, request: Request) -> None:
    if not request.app.state.store.delete_document(doc_id):
        raise HTTPException(404, "Document not found.")


@app.post("/api/admin/reindex", dependencies=[Depends(require_admin)])
def reindex(request: Request) -> dict:
    s: Settings = request.app.state.settings
    docs = load_directory(s.sample_docs_dir)
    chunks = index_documents(docs, request.app.state.store, request.app.state.llm, s.max_chunk_chars)
    return {"documents": len(docs), "chunks": chunks}
