"""
AI Trip Planner - FastAPI Backend
"""
import sys
import os
import logging
import concurrent.futures

# Force UTF-8 on stdout/stderr so emoji in agent logs don't crash on Windows.
# reconfigure() is safe even when stdout has no .buffer (e.g. uvicorn capture mode).
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass  # stream is not reconfigurable (e.g. already redirected) — ignore

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_engine.core.orchestrator import Orchestrator
from ai_engine.core.llm.groq import GroqProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Route all agent print() calls through logging so they always appear
# in uvicorn logs even when stdout is not a real TTY (deployed environments).
_builtin_print = print
def print(*args, **kwargs):  # noqa: A001
    kwargs.pop('file', None)  # always write to logger, not a custom file
    msg = ' '.join(str(a) for a in args)
    logging.getLogger('agent').info(msg)

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

    # Hard wall-clock limit: 5 minutes. Prevents a single hung TCP connection
    # (e.g. Groq / Overpass timeout) from freezing the server worker indefinitely.
    PLAN_TIMEOUT_SECONDS = 300

    try:
        orchestrator = get_orchestrator()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(orchestrator.run, request.query.strip())
            try:
                state = future.result(timeout=PLAN_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                logger.error("Pipeline exceeded %ds wall-clock limit", PLAN_TIMEOUT_SECONDS)
                raise HTTPException(
                    status_code=504,
                    detail=(
                        f"Planning timed out after {PLAN_TIMEOUT_SECONDS}s. "
                        "External APIs (Groq, OpenStreetMap) may be slow — please try again."
                    ),
                )

        if state.current_stage == "done":
            # Prefer optimizer result when it has days; fall back to planner result
            opt = state.optimization_result
            plan = opt if (opt and opt.get("days")) else state.selected_plan

            # Merge meals from planner days into optimizer days
            # (optimizer drops meals; planner always has them)
            if plan is opt and opt.get("days") and state.selected_plan.get("days"):
                planner_days = {d["day_number"]: d for d in state.selected_plan["days"]}
                for day in plan["days"]:
                    dn = day.get("day_number")
                    if dn in planner_days and not day.get("meals"):
                        day["meals"] = planner_days[dn].get("meals", [])

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
    except HTTPException:
        raise  # Re-raise FastAPI exceptions as-is
    except UnicodeEncodeError as e:
        logger.warning(f"Unicode logging error (non-fatal): {e}")
        raise HTTPException(status_code=500, detail=f"Unicode encoding error in pipeline output: {e}")
    except Exception as e:
        logger.exception("Unexpected error during planning")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

if os.path.exists("ui"):
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
