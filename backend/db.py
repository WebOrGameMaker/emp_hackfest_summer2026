import json
import sqlite3
import threading
import uuid
from typing import Dict, List, Optional, Sequence, Tuple

from . import clustering, config, confidence, taxonomy, timeutil
from .models import (
    ConfidenceBreakdown, Hazard, HazardAnalysis, NearbyMatch, Report,
    ReportSubmission, SubmissionResult,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS hazards (
    id                  TEXT PRIMARY KEY,
    category            TEXT NOT NULL,
    severity            TEXT NOT NULL,
    lat                 REAL NOT NULL,
    lon                 REAL NOT NULL,
    location_type       TEXT NOT NULL,
    obstruction         INTEGER NOT NULL DEFAULT 0,
    vehicle_access      TEXT NOT NULL,
    pedestrian_access   TEXT NOT NULL,
    summary             TEXT NOT NULL DEFAULT '',
    place               TEXT NOT NULL DEFAULT '',
    confidence          REAL NOT NULL DEFAULT 0,
    confidence_json     TEXT NOT NULL DEFAULT '{}',
    spread_m            REAL NOT NULL DEFAULT 0,
    first_reported_at   TEXT NOT NULL,
    last_reported_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id            TEXT PRIMARY KEY,
    hazard_id     TEXT NOT NULL REFERENCES hazards(id) ON DELETE CASCADE,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    text          TEXT,
    photo         TEXT,
    reporter      TEXT NOT NULL DEFAULT 'Anonymous',
    created_at    TEXT NOT NULL,
    analysis_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_hazard ON reports(hazard_id);
CREATE INDEX IF NOT EXISTS idx_hazards_category ON hazards(category);
"""

# one connection per thread — sharing one with check_same_thread=False corrupted the file
_lock = threading.RLock()
_local = threading.local()
_schema_ready = False


def connect() -> sqlite3.Connection:
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is not None:
        return conn
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA foreign_keys = ON")
    _local.conn = conn
    global _schema_ready
    if not _schema_ready:
        with _lock:
            if not _schema_ready:
                conn.executescript(SCHEMA)
                conn.commit()
                _schema_ready = True
    return conn


def ensure_healthy() -> bool:
    if not config.DB_PATH.exists():
        return False
    try:
        probe = sqlite3.connect(str(config.DB_PATH), timeout=5.0)
        try:
            result = probe.execute("PRAGMA quick_check").fetchone()
            if result and str(result[0]).lower() == "ok":
                return False
        finally:
            probe.close()
    except sqlite3.DatabaseError:
        pass
    quarantine = config.DB_PATH.with_suffix(".corrupt")
    for path in (
        config.DB_PATH,
        config.DB_PATH.with_name(config.DB_PATH.name + "-wal"),
        config.DB_PATH.with_name(config.DB_PATH.name + "-shm"),
    ):
        if path.exists():
            path.replace(quarantine) if path == config.DB_PATH else path.unlink()
    global _schema_ready
    _schema_ready = False
    _local.__dict__.pop("conn", None)
    return True


def reset() -> None:
    with _lock:
        conn = connect()
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM hazards")
        conn.commit()


def _report_from_row(row: sqlite3.Row) -> Report:
    photo = row["photo"]
    return Report(
        id=row["id"],
        hazard_id=row["hazard_id"],
        lat=row["lat"],
        lon=row["lon"],
        text=row["text"],
        has_photo=bool(photo),
        photo_url="/api/reports/{0}/photo".format(row["id"]) if photo else None,
        reporter=row["reporter"],
        created_at=row["created_at"],
        analysis=HazardAnalysis(**json.loads(row["analysis_json"])),
    )


def _hazard_from_row(row: sqlite3.Row, reports: Sequence[Report]) -> Hazard:
    rules = taxonomy.get(row["category"])
    breakdown: Optional[ConfidenceBreakdown] = None
    raw = row["confidence_json"]
    if raw and raw != "{}":
        try:
            breakdown = ConfidenceBreakdown(**json.loads(raw))
        except (ValueError, TypeError):
            breakdown = None
    return Hazard(
        id=row["id"],
        category=row["category"],
        label=rules.label,
        icon=rules.icon,
        severity=row["severity"],
        lat=row["lat"],
        lon=row["lon"],
        location_type=row["location_type"],
        obstruction=bool(row["obstruction"]),
        vehicle_access=row["vehicle_access"],
        pedestrian_access=row["pedestrian_access"],
        summary=row["summary"],
        place=row["place"],
        report_count=len(reports),
        photo_count=sum(1 for report in reports if report.has_photo),
        confidence=row["confidence"],
        confidence_breakdown=breakdown,
        first_reported_at=row["first_reported_at"],
        last_reported_at=row["last_reported_at"],
        spread_m=row["spread_m"],
        reports=sorted(list(reports), key=lambda r: r.created_at, reverse=True),
    )


def _reports_by_hazard() -> Dict[str, List[Report]]:
    grouped: Dict[str, List[Report]] = {}
    for row in connect().execute("SELECT * FROM reports ORDER BY created_at"):
        grouped.setdefault(row["hazard_id"], []).append(_report_from_row(row))
    return grouped


def list_hazards(include_reports: bool = True) -> List[Hazard]:
    grouped = _reports_by_hazard() if include_reports else {}
    return [
        _hazard_from_row(row, grouped.get(row["id"], []))
        for row in connect().execute("SELECT * FROM hazards ORDER BY last_reported_at DESC")
    ]


def get_hazard(hazard_id: str) -> Optional[Hazard]:
    conn = connect()
    row = conn.execute("SELECT * FROM hazards WHERE id = ?", (hazard_id,)).fetchone()
    if row is None:
        return None
    reports = [
        _report_from_row(report_row)
        for report_row in conn.execute(
            "SELECT * FROM reports WHERE hazard_id = ? ORDER BY created_at", (hazard_id,),
        )
    ]
    return _hazard_from_row(row, reports)


def get_photo(report_id: str) -> Optional[str]:
    row = connect().execute("SELECT photo FROM reports WHERE id = ?", (report_id,)).fetchone()
    return row["photo"] if row and row["photo"] else None


def counts() -> Tuple[int, int]:
    conn = connect()
    hazards = conn.execute("SELECT COUNT(*) AS n FROM hazards").fetchone()["n"]
    reports = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
    return hazards, reports


def category_counts() -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {
        key: {"hazards": 0, "reports": 0} for key in taxonomy.category_keys()
    }
    query = """
        SELECT h.category AS category,
               COUNT(DISTINCT h.id) AS hazards,
               COUNT(r.id) AS reports
        FROM hazards h
        LEFT JOIN reports r ON r.hazard_id = h.id
        GROUP BY h.category
    """
    for row in connect().execute(query):
        stats.setdefault(row["category"], {"hazards": 0, "reports": 0}).update(
            {"hazards": row["hazards"], "reports": row["reports"]}
        )
    return stats


def find_nearby(category: str, lat: float, lon: float) -> List[NearbyMatch]:
    return clustering.evaluate(category, lat, lon, list_hazards())


def _recompute(conn: sqlite3.Connection, hazard_id: str) -> Hazard:
    rows = list(conn.execute(
        "SELECT * FROM reports WHERE hazard_id = ? ORDER BY created_at", (hazard_id,),
    ))
    reports = [_report_from_row(row) for row in rows]
    hazard_row = conn.execute("SELECT * FROM hazards WHERE id = ?", (hazard_id,)).fetchone()
    category = hazard_row["category"]
    lat, lon = clustering.centroid(reports)
    spread = clustering.spread_m(reports, lat, lon)
    severity = clustering.worst_severity([report.analysis.severity for report in reports])
    vehicle = clustering.worst_access([report.analysis.vehicle_access for report in reports])
    pedestrian = clustering.worst_access([report.analysis.pedestrian_access for report in reports])
    location_type = clustering.dominant(
        [report.analysis.location_type for report in reports],
        taxonomy.get(category).default_location_type,
    )
    obstruction = any(report.analysis.obstruction for report in reports)
    first_at = reports[0].created_at if reports else timeutil.now_iso()
    last_at = max(report.created_at for report in reports) if reports else timeutil.now_iso()
    # show the clearest description, not the newest
    best = max(reports, key=lambda report: report.analysis.confidence)
    breakdown = confidence.score(reports, category, spread, last_at)
    conn.execute(
        """
        UPDATE hazards SET
            severity = ?, lat = ?, lon = ?, location_type = ?,
            obstruction = ?, vehicle_access = ?, pedestrian_access = ?,
            summary = ?, confidence = ?, confidence_json = ?, spread_m = ?,
            first_reported_at = ?, last_reported_at = ?
        WHERE id = ?
        """,
        (
            severity, lat, lon, location_type, 1 if obstruction else 0, vehicle,
            pedestrian, best.analysis.summary, breakdown.value, breakdown.model_dump_json(),
            spread, first_at, last_at, hazard_id,
        ),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM hazards WHERE id = ?", (hazard_id,)).fetchone()
    return _hazard_from_row(updated, reports)


def add_report(
    submission: ReportSubmission,
    analysis: HazardAnalysis,
    created_at: Optional[str] = None,
    place: str = "",
) -> SubmissionResult:
    with _lock:
        conn = connect()
        timestamp = created_at or timeutil.now_iso()
        matches = clustering.evaluate(
            analysis.category, submission.lat, submission.lon, list_hazards(), when=timestamp,
        )
        chosen = clustering.choose(matches)
        merged = chosen is not None
        previous_confidence: Optional[float] = None
        previous_count = 0
        explanation = ""
        if chosen is not None:
            hazard_id = chosen.hazard_id
            previous_confidence = chosen.confidence
            previous_count = chosen.report_count
            explanation = chosen.reason
        else:
            hazard_id = "hz_" + uuid.uuid4().hex[:10]
            rules = taxonomy.get(analysis.category)
            near_miss = next(iter(matches), None)
            if near_miss is not None:
                explanation = near_miss.reason
            else:
                explanation = (
                    "No open {0} hazard within {1:.0f}m, so this starts a new one.".format(
                        rules.label.lower(), rules.cluster_radius_m
                    )
                )
            conn.execute(
                """
                INSERT INTO hazards (
                    id, category, severity, lat, lon, location_type,
                    obstruction, vehicle_access, pedestrian_access, summary,
                    place, confidence, confidence_json, spread_m,
                    first_reported_at, last_reported_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    hazard_id, analysis.category, analysis.severity, submission.lat,
                    submission.lon, analysis.location_type,
                    1 if analysis.obstruction else 0, analysis.vehicle_access,
                    analysis.pedestrian_access, analysis.summary, place, 0.0, "{}",
                    0.0, timestamp, timestamp,
                ),
            )
        report_id = "rp_" + uuid.uuid4().hex[:10]
        conn.execute(
            """
            INSERT INTO reports (
                id, hazard_id, lat, lon, text, photo, reporter, created_at,
                analysis_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                report_id, hazard_id, submission.lat, submission.lon,
                (submission.text or "").strip() or None, submission.image_b64,
                (submission.reporter or "Anonymous").strip() or "Anonymous",
                timestamp, analysis.model_dump_json(),
            ),
        )
        conn.commit()
        hazard = _recompute(conn, hazard_id)
        report = next((item for item in hazard.reports if item.id == report_id), None)
        assert report is not None
        return SubmissionResult(
            report=report,
            hazard=hazard,
            merged=merged,
            previous_confidence=previous_confidence,
            previous_report_count=previous_count,
            merge_explanation=explanation,
        )
