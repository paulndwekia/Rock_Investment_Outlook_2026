import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="Kenya Investment Intelligence Data API", version="1.0.0")

# Read-only API. Do not add a public write/import endpoint here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)

def connection():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)

@app.get("/health")
def health():
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "checked_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        raise HTTPException(status_code=503, detail="Data store unavailable")

@app.get("/v1/overview")
def overview():
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
                SELECT observed_at, series, value, unit, source_name
                FROM market_observations
                WHERE series = (
                    SELECT series FROM market_observations
                    GROUP BY series ORDER BY COUNT(*) DESC LIMIT 1
                )
                ORDER BY observed_at DESC LIMIT 120
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
    except Exception:
        raise HTTPException(status_code=503, detail="Research data is temporarily unavailable")

@app.get("/v1/series/{dataset}/{series_name}")
def get_series(dataset: str, series_name: str, limit: int = Query(default=500, ge=1, le=5000)):
    try:
        with connection() as conn:
            rows = conn.execute("""
                SELECT observed_at, dataset, series, value, unit, source_name, source_reference
                FROM market_observations
                WHERE dataset = %s AND series = %s
                ORDER BY observed_at DESC LIMIT %s
            """, (dataset, series_name, limit)).fetchall()
        rows.reverse()
        return [{**row, "observed_at": row["observed_at"].isoformat()} for row in rows]
    except Exception:
        raise HTTPException(status_code=503, detail="Research data is temporarily unavailable")
