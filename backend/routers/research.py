"""
Deep research — multi-step, cited answers via Tavily's Research endpoint, as an
opt-in alternative to the quick single-shot search grounding already used in
chat.py (search_service.py, untouched).

Tavily's Research is genuinely asynchronous (a task can take anywhere from
~10s to a few minutes), so this is a dedicated start+poll endpoint pair rather
than woven into the streaming /api/chat response — matching Tavily's own
design instead of forcing a long-running task into that already-complex
pipeline.

  POST /api/research/start  {query}       -> {request_id}
  GET  /api/research/{request_id}         -> current status (+ report when done)

Same optional-API-key posture as chat/document (dependencies=_auth in main.py);
public within that. Rate-limited separately and more strictly than chat, since
each research task costs meaningfully more Tavily credits than a quick search.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rate_limit import limiter
from services import tavily_service

router = APIRouter()


class ResearchStartBody(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    model: str = Field("auto", pattern=r"^(mini|pro|auto)$")


@router.post("/research/start")
@limiter.limit("3/minute")
async def start_research(request: Request, body: ResearchStartBody):
    """Kick off a deep-research task. Returns a request_id to poll. 503 if
    Tavily isn't configured; 502 if Tavily itself fails to accept the task."""
    if not tavily_service.tavily_enabled():
        raise HTTPException(status_code=503, detail="Live research is not configured on this server.")
    request_id = await tavily_service.start_research(body.query, model=body.model)
    if not request_id:
        raise HTTPException(status_code=502, detail="Could not start the research task. Try again shortly.")
    return {"request_id": request_id}


@router.get("/research/{request_id}")
@limiter.limit("30/minute")
async def get_research(request: Request, request_id: str):
    """Poll a research task. Returns Tavily's status dict as-is: at minimum
    {"status": "pending"|"in_progress"|"completed"|"failed", ...}; a completed
    task includes the synthesized report and citations. 404 if the id is
    unknown to Tavily; 503 if unconfigured."""
    if not tavily_service.tavily_enabled():
        raise HTTPException(status_code=503, detail="Live research is not configured on this server.")
    result = await tavily_service.get_research_result(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown or expired research task.")
    return result
