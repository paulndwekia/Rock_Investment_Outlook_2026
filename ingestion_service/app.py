import os
import secrets
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row

app = FastAPI(
    title="Kenya Investment Intelligence Data API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Authorization"],
)

def connection():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)

def verify_read_token(authorization: str | None = Header(default=None)):
    expected = os.getenv("API_READ_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="API access is not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorised")

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].casefold() != "bearer":
        raise HTTPException(status_code=401, detail="Unauthorised")

    supplied = parts[1]
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorised")
    return True

@app.get("/health")
def health():
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "checked_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        raise HTTPException(status_code=503, detail="Data store unavailable")

@app.get("/v1/overview")
def overview(_: bool = Depends(verify_read_token)):
    try:
        with connection() as conn:
            totals = conn.execute("""
                SELECT COUNT(*)::bigint AS total_observations,
                       COUNT(DISTINCT dataset)::int AS dataset_count,
                       MAX(observed_at) AS latest_observation
                FROM market_observations
            """).fetchone()
            datasets = conn.execute("""
                SELECT dataset, COUNT(*)::bigint AS observations,
                       MAX(observed_at) AS last_observed_at,
                       (ARRAY_AGG(source_name ORDER BY observed_at DESC))[1] AS source_name
                FROM market_observations
                GROUP BY dataset ORDER BY dataset
            """).fetchall()
            series = conn.execute("""
                WITH selected_series AS (
                    SELECT dataset, series, unit
                    FROM market_observations
                    GROUP BY dataset, series, unit
                    ORDER BY COUNT(*) DESC, MAX(observed_at) DESC, dataset, series
                    LIMIT 1
                )
                SELECT observation.dataset, observation.observed_at,
                       observation.series, observation.value,
                       observation.unit, observation.source_name
                FROM market_observations AS observation
                JOIN selected_series AS selected
                  ON observation.dataset = selected.dataset
                 AND observation.series = selected.series
                 AND observation.unit IS NOT DISTINCT FROM selected.unit
                ORDER BY observation.observed_at DESC
                LIMIT 120
            """).fetchall()
        series.reverse()
        return {
            "status": "ok",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_observations": totals["total_observations"],
            "dataset_count": totals["dataset_count"],
            "latest_observation": totals["latest_observation"].isoformat() if totals["latest_observation"] else None,
            "datasets": [{**row, "last_observed_at": row["last_observed_at"].isoformat() if row["last_observed_at"] else None} for row in datasets],
            "market_series": [{**row, "observed_at": row["observed_at"].isoformat()} for row in series],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Research data is temporarily unavailable")

@app.get("/v1/series/{dataset}/{series_name}")
def get_series(
    dataset: str,
    series_name: str,
    limit: int = Query(default=500, ge=1, le=5000),
    _: bool = Depends(verify_read_token),
):
    try:
        with connection() as conn:
            rows = conn.execute("""
                SELECT observed_at, dataset, series, value, unit, source_name
                FROM market_observations
                WHERE dataset = %s AND series = %s
                ORDER BY observed_at DESC LIMIT %s
            """, (dataset, series_name, limit)).fetchall()
        rows.reverse()
        return [{**row, "observed_at": row["observed_at"].isoformat()} for row in rows]
    except Exception:
        raise HTTPException(status_code=503, detail="Research data is temporarily unavailable")
