# app/routers/reports.py
import os
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any

from app.dbb import list_reports, get_report_path

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("", response_model=List[Dict[str, Any]])
def get_reports(
    fecha_desde: Optional[str] = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    """
    Lista informes, con filtro opcional por rango de fechas (sobre created_at).
    """
    return list_reports(fecha_desde, fecha_hasta)

@router.get("/{report_id}/download")
def download_report(report_id: int):
    """
    Descarga un informe DOCX.
    """
    path = get_report_path(report_id)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        filename=filename)
