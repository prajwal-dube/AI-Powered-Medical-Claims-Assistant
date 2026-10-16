import io
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pypdf import PdfReader

from .extraction import PROMPT_VERSION, local_extract, remote_extract
from .review import review_claim
from .storage import connect, insert_claim, list_claims


def db_path() -> str:
    return os.getenv("DATABASE_PATH", "data/claims.db")


@asynccontextmanager
async def lifespan(_: FastAPI):
    with connect(db_path()):
        pass
    yield


app = FastAPI(title="Medical Claims Assistant (synthetic data)", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/claims", status_code=201)
async def upload_claim(file: UploadFile = File(...)):
    name = Path(file.filename or "unnamed").name[:120]
    suffix = Path(name).suffix.lower()
    if suffix not in {".txt", ".pdf"}:
        raise HTTPException(415, "Only .txt and text-based .pdf are supported")
    maximum = int(os.getenv("MAX_UPLOAD_BYTES", "2097152"))
    raw = await file.read(maximum + 1)
    await file.close()
    if len(raw) > maximum:
        raise HTTPException(413, "Document exceeds configured size limit")
    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(raw), strict=False)
            if len(reader.pages) > 10:
                raise HTTPException(413, "PDF exceeds 10 pages")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = raw.decode("utf-8")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Cannot read document") from None
    if not text.strip():
        raise HTTPException(422, "No extractable text; scanned PDFs require OCR")
    mode = os.getenv("EXTRACTOR_MODE", "demo").lower()
    if mode not in {"demo", "remote"}:
        raise HTTPException(503, "Invalid extractor configuration")
    if mode == "remote":
        base = os.getenv("LLM_BASE_URL", "")
        model = os.getenv("LLM_MODEL", "")
        key = os.getenv("LLM_API_KEY", "")
        if not all([base, model, key]):
            raise HTTPException(503, "Remote extractor is not configured")
        try:
            fields = await remote_extract(text, base, model, key)
        except Exception:
            raise HTTPException(502, "Remote extraction failed; check provider and schema support") from None
    else:
        fields = local_extract(text)
    result = insert_claim(db_path(), name, mode, PROMPT_VERSION, fields, review_claim)
    return result


@app.get("/claims")
def claims(limit: int = 100):
    if not 1 <= limit <= 500:
        raise HTTPException(422, "limit must be between 1 and 500")
    return list_claims(db_path(), limit)


@app.get("/stats")
def stats():
    # Dashboard summary uses the same bounded result window as /claims.
    items = list_claims(db_path(), 500)
    return {"total_in_window": len(items), "flagged_in_window": sum(bool(x.flags) for x in items),
            "flag_counts": {code: sum(code == f.code for x in items for f in x.flags)
                            for code in sorted({f.code for x in items for f in x.flags})},
            "window_limit": 500}
