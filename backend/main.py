import asyncio
import base64
import binascii
import json
import re
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.types import Scope

from . import ai, config, db, places, seed, taxonomy, timeutil
from .ai.demo import DEMO_SCENARIOS
from .models import (
    AnalyzeRequest, CategorySummary, Hazard, HazardAnalysis, MetaResponse,
    NearbyMatch, ReportSubmission, SubmissionResult,
)

MAX_IMAGE_BYTES = 6 * 1024 * 1024


class FrontendStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app = FastAPI(
    title="HazardMap",
    description="A public map of street hazards from community reports.",
    version="0.1.0",
)


class Broadcaster:
    def __init__(self) -> None:
        self._subscribers: Set["asyncio.Queue[str]"] = set()

    async def subscribe(self) -> "asyncio.Queue[str]":
        queue: "asyncio.Queue[str]" = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: "asyncio.Queue[str]") -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, payload: Dict[str, Any]) -> None:
        message = "event: {0}\ndata: {1}\n\n".format(event, json.dumps(payload, default=str))
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # drop slow clients so they don't stall a submit
                self.unsubscribe(queue)


broadcaster = Broadcaster()
_DATA_URL = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.S)


def _validate_image(image_b64: Optional[str]) -> Optional[str]:
    if not image_b64:
        return None
    match = _DATA_URL.match(image_b64.strip())
    if not match:
        raise HTTPException(status_code=400, detail="Photo must be an inline data URL of an image.")
    payload = match.group(2)
    if len(payload) * 3 // 4 > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Photo is larger than 6 MB. Please choose a smaller image.")
    try:
        base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Photo data is not valid base64.")
    return image_b64.strip()


def _analyze(text: Optional[str], image_b64: Optional[str], image_name: Optional[str]) -> HazardAnalysis:
    try:
        return ai.get_analyzer().analyze(text=text, image_b64=image_b64, image_name=image_name)
    except Exception:  # pragma: no cover
        from .ai.base import empty_analysis
        return empty_analysis("The analyzer failed unexpectedly. The report was still recorded.")


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    stats = db.category_counts()
    hazard_count, report_count = db.counts()
    summaries = [
        CategorySummary(
            key=category.key,
            label=category.label,
            icon=category.icon,
            blurb=category.blurb,
            hazard_count=stats.get(category.key, {}).get("hazards", 0),
            report_count=stats.get(category.key, {}).get("reports", 0),
            cluster_radius_m=category.cluster_radius_m,
            cluster_window_hours=category.cluster_window_hours,
        )
        for category in taxonomy.CATEGORIES
    ]
    return MetaResponse(
        ai=ai.get_status(),
        categories=summaries,
        severity_levels=list(taxonomy.SEVERITY_LEVELS),
        hazard_count=hazard_count,
        report_count=report_count,
        map_center=list(config.MAP_CENTER),
        demo_pin=list(config.DEMO_PIN),
        thresholds={
            "confidence_ceiling": config.CONFIDENCE_CEILING,
            "single_report_ceiling": config.SINGLE_REPORT_CEILING,
            "map_zoom": config.MAP_ZOOM,
        },
    )


@app.get("/api/scenarios")
def scenarios() -> List[Dict[str, Any]]:
    return [
        {
            "id": key,
            "category": scenario["category"],
            "label": taxonomy.get(str(scenario["category"])).label,
            "icon": taxonomy.get(str(scenario["category"])).icon,
            "severity": scenario["severity"],
            "image": "/assets/scenes/{0}.svg".format(key),
            "caption": scenario["summary"],
        }
        for key, scenario in DEMO_SCENARIOS.items()
    ]


@app.get("/api/hazards", response_model=List[Hazard])
def hazards(
    category: Optional[List[str]] = Query(default=None),
    severity: Optional[List[str]] = Query(default=None),
    hours: Optional[float] = Query(default=None, gt=0),
    min_reports: int = Query(default=1, ge=1),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
) -> List[Hazard]:
    results = db.list_hazards()
    if category:
        wanted = set(category)
        results = [item for item in results if item.category in wanted]
    if severity:
        wanted = set(severity)
        results = [item for item in results if item.severity in wanted]
    if hours is not None:
        results = [item for item in results if timeutil.hours_since(item.last_reported_at) <= hours]
    if min_reports > 1:
        results = [item for item in results if item.report_count >= min_reports]
    if min_confidence > 0:
        results = [item for item in results if item.confidence >= min_confidence]
    return results


@app.get("/api/hazards/{hazard_id}", response_model=Hazard)
def hazard_detail(hazard_id: str) -> Hazard:
    found = db.get_hazard(hazard_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Could not find that hazard.")
    return found


@app.get("/api/reports/{report_id}/photo")
def report_photo(report_id: str) -> Response:
    stored = db.get_photo(report_id)
    if not stored:
        raise HTTPException(status_code=404, detail="No photo for that report.")
    match = _DATA_URL.match(stored)
    if not match:
        raise HTTPException(status_code=500, detail="Stored photo is malformed.")
    try:
        payload = base64.b64decode(match.group(2))
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=500, detail="Stored photo is malformed.")
    return Response(
        content=payload,
        media_type=match.group(1),
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> Dict[str, Any]:
    if not (request.text and request.text.strip()) and not request.image_b64:
        raise HTTPException(status_code=400, detail="Send a photo, a description, or both.")
    image = _validate_image(request.image_b64)
    analysis = await run_in_threadpool(_analyze, request.text, image, request.image_name)
    nearby: List[NearbyMatch] = []
    if request.lat is not None and request.lon is not None:
        nearby = await run_in_threadpool(db.find_nearby, analysis.category, request.lat, request.lon)
    return {
        "analysis": json.loads(analysis.model_dump_json()),
        "nearby": [json.loads(item.model_dump_json()) for item in nearby],
        "would_merge_into": next((item.hazard_id for item in nearby if item.would_merge), None),
        "place": places.describe(request.lat, request.lon) if request.lat is not None and request.lon is not None else "",
        "ai": json.loads(ai.get_status().model_dump_json()),
    }


@app.post("/api/reports", response_model=SubmissionResult)
async def create_report(submission: ReportSubmission) -> SubmissionResult:
    has_text = bool(submission.text and submission.text.strip())
    if not has_text and not submission.image_b64:
        raise HTTPException(status_code=400, detail="Send a photo, a description, or both.")
    submission.image_b64 = _validate_image(submission.image_b64)
    analysis = submission.analysis
    if analysis is None:
        analysis = await run_in_threadpool(
            _analyze, submission.text, submission.image_b64, submission.image_name,
        )
    result = await run_in_threadpool(
        db.add_report, submission, analysis, None, places.describe(submission.lat, submission.lon),
    )
    await broadcaster.publish("hazard", json.loads(result.model_dump_json()))
    return result


@app.post("/api/demo/reset")
async def demo_reset() -> Dict[str, Any]:
    await run_in_threadpool(seed.reseed)
    hazard_count, report_count = db.counts()
    await broadcaster.publish("reset", {"hazard_count": hazard_count, "report_count": report_count})
    return {"ok": True, "hazard_count": hazard_count, "report_count": report_count}


@app.get("/api/stream")
async def stream() -> Response:
    from fastapi.responses import StreamingResponse

    async def events():
        queue = await broadcaster.subscribe()
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/healthz")
def healthz() -> JSONResponse:
    hazard_count, report_count = db.counts()
    return JSONResponse({
        "ok": True,
        "provider": ai.get_status().provider,
        "hazards": hazard_count,
        "reports": report_count,
    })


for _mount in ("css", "js", "assets", "vendor"):
    _directory = config.FRONTEND_DIR / _mount
    if _directory.is_dir():
        static = FrontendStaticFiles if _mount in {"css", "js"} else StaticFiles
        app.mount("/{0}".format(_mount), static(directory=str(_directory)), name=_mount)
