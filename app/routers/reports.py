# app/routers/reports.py
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse

from app.dbb import list_reports, get_report_path

router = APIRouter()

@router.get("/reports")
def api_list_reports(
    fecha_desde: Optional[str] = Query(default=None),
    fecha_hasta: Optional[str] = Query(default=None),
    only_docx: bool = Query(default=True),
):
    return list_reports(fecha_desde, fecha_hasta, only_docx)

@router.get("/reports/{report_id}/download")
def api_download_report(report_id: int):
    path = get_report_path(report_id)
    if not path:
        raise HTTPException(status_code=404, detail="report not found")
    fname = path.replace("\\", "/").split("/")[-1]
    return FileResponse(path, media_type="application/octet-stream", filename=fname)
