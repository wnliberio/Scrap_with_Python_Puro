# app/routers/reports.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from app.db import engine
import os

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

# ← AGREGAR ESTE ENDPOINT NUEVO
@router.get("/{report_id}/download")
def download_report(report_id: int):
    """
    Descarga el archivo de reporte por ID.
    """
    sql = text("SELECT file_path FROM reports WHERE id = :id")
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": report_id}).mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        file_path = row["file_path"]
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
        
        # Obtener solo el nombre del archivo
        filename = os.path.basename(file_path)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )