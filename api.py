"""
AI Trip Planner - FastAPI Backend
"""
import sys
import io
import os
import logging

# Fix Windows charmap error — force stdout/stderr to UTF-8
# so emoji in orchestrator logs (rocket, checkmarks, etc.) don't crash the process
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_engine.core.orchestrator import Orchestrator
from ai_engine.core.llm.groq import GroqProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Trip Planner",
    description="Multi-agent AI system for personalized travel itineraries",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    query: str

_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        logger.info("Initializing pipeline...")
        llm = GroqProvider()
        _orchestrator = Orchestrator(llm=llm, verbose=True)
    return _orchestrator

@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Trip Planner"}

@app.post("/api/plan")
def create_plan(request: PlanRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    logger.info(f"Planning request: {request.query[:80]}")
    try:
        orchestrator = get_orchestrator()
        state = orchestrator.run(request.query.strip())
        if state.current_stage == "done":
            plan = state.optimization_result or state.selected_plan
            return {
                "success": True,
                "itinerary": plan,
                "timing": state.timing,
                "stages": state.completed_stages,
            }
        else:
            error_msgs = [f"[{e['stage']}] {e['error']}" for e in state.errors]
            return {
                "success": False,
                "error": f"Pipeline stopped at '{state.current_stage}'. " + "; ".join(error_msgs),
                "timing": state.timing,
                "stages": state.completed_stages,
            }
    except UnicodeEncodeError as e:
        # Swallow encoding errors from console logging — pipeline still ran
        logger.warning(f"Unicode logging error (non-fatal): {e}")
        state = getattr(e, '__context__', None)
        raise HTTPException(status_code=500, detail=f"Unicode encoding error in pipeline output: {e}")
    except Exception as e:
        logger.exception("Unexpected error during planning")
        raise HTTPException(status_code=500, detail=str(e))

if os.path.exists("ui"):
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
