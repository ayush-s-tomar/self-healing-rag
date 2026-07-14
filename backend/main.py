import os
import shutil
import tempfile

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retrieval import ingest_pdf, collection_is_empty, reset_collection
from graph import run_query

app = FastAPI(title="Self-Healing RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend URL before going public
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    grounded: bool | None
    retry_count: int
    final_status: str
    trace: list
    sources: list


@app.get("/health")
def health():
    return {"status": "ok", "collection_empty": collection_is_empty()}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        num_chunks = ingest_pdf(tmp_path, source_name=file.filename)
    finally:
        os.remove(tmp_path)

    if num_chunks == 0:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in this PDF (it may be scanned/image-based).",
        )

    return {"filename": file.filename, "chunks_ingested": num_chunks}


@app.post("/reset")
def reset():
    reset_collection()
    return {"status": "collection reset"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if collection_is_empty():
        raise HTTPException(
            status_code=400,
            detail="No documents have been ingested yet. Upload a PDF via /ingest first.",
        )

    final_state = run_query(request.query)

    sources = list({
        c["source"] for c in final_state.get("retrieved_chunks", [])
    })

    return QueryResponse(
        answer=final_state.get("answer", ""),
        grounded=final_state.get("grounded"),
        retry_count=final_state.get("retry_count", 0),
        final_status=final_state.get("final_status", "unknown"),
        trace=final_state.get("trace", []),
        sources=sources,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
