from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.component_engine import (
    get_all_components,
    compare_components,
    compute_tradeoff_analysis
)
from services.material_engine import get_material_intelligence
from services.rag_engine import retrieve_knowledge
from services.llm_engine import generate_engineering_insight

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app = FastAPI(
    title="CompBench AI",
    description="Automotive Component Benchmarking API",
    version="1.0.0"
)

# Enable CORS for browser access from local interfaces (127.0.0.1, localhost, LAN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class ComparisonRequest(BaseModel):
    component_a_id: str
    component_b_id: str


class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 3


class MaterialIntelligenceRequest(BaseModel):
    material_a: str
    material_b: str
    process_a: str = "Stamping"
    process_b: str = "Stamping"
    component_a_id: str = None
    component_b_id: str = None
    top_k: int = 3


class AnalyzeRequest(BaseModel):
    component_a_id: str
    component_b_id: str
    top_k: int = 3


@app.get("/")
def home(request: Request):
    accept_header = request.headers.get("accept", "")
    # Serve interactive frontend dashboard to web browsers
    if "text/html" in accept_header or "application/json" not in accept_header:
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    # Return status payload for automated JSON API consumers
    return {
        "message": "Welcome to CompBench AI",
        "status": "Running"
    }


@app.get("/dashboard")
def dashboard():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Dashboard index.html not found")


@app.get("/components")
def components():
    return get_all_components()


@app.post("/compare")
def compare(request: ComparisonRequest):
    try:
        return compare_components(
            request.component_a_id,
            request.component_b_id
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


@app.post("/knowledge/retrieve")
def get_knowledge(request: KnowledgeQueryRequest):
    return retrieve_knowledge(
        request.query,
        request.top_k
    )


@app.post("/material-intelligence")
def material_intelligence_endpoint(request: MaterialIntelligenceRequest):
    comp_a = None
    comp_b = None
    if request.component_a_id and request.component_b_id:
        try:
            comparison = compare_components(request.component_a_id, request.component_b_id)
            comp_a = comparison.get("component_a")
            comp_b = comparison.get("component_b")
        except Exception:
            pass

    return get_material_intelligence(
        material_a=request.material_a,
        material_b=request.material_b,
        process_a=request.process_a,
        process_b=request.process_b,
        component_a=comp_a,
        component_b=comp_b,
        query_rag=True,
        rag_top_k=request.top_k
    )


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        comparison = compare_components(
            request.component_a_id,
            request.component_b_id
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    comp_name = comparison.get("component_name", "component")
    comp_a = comparison.get("component_a", {})
    comp_b = comparison.get("component_b", {})

    rag_query = (
        f"Trade-offs of replacing {comp_a.get('material')} {comp_name} ({comp_a.get('manufacturing_process')}) "
        f"with {comp_b.get('material')} {comp_name} ({comp_b.get('manufacturing_process')}) in automotive engineering"
    )

    knowledge = retrieve_knowledge(rag_query, top_k=request.top_k)
    insight = generate_engineering_insight(comparison, knowledge)

    return {
        "component_name": comp_name,
        "comparison": comparison,
        "retrieved_knowledge": knowledge,
        "insight": insight,
        "disclaimers": {
            "dataset": "Synthetic benchmark dataset generated for academic and demonstration purposes.",
            "knowledge_base": "General automotive engineering educational reference material — not official OEM or Caresoft proprietary teardown data."
        }
    }
