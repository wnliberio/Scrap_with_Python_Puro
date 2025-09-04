# app/routers/reports.py  (añadir al final del archivo)
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db import engine

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/by-job/{job_id}")
def get_report_by_job(job_id: str):
    """
    Retorna el último reporte para un job_id (si existe).
    """
    sql = text("""
        SELECT id, job_id, file_path, created_at
        FROM reports
        WHERE job_id = :jid
        ORDER BY id DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"jid": job_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="No hay reporte para ese job_id")
        return {
            "id": row["id"],
            "job_id": row["job_id"],
            "file_path": row["file_path"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
