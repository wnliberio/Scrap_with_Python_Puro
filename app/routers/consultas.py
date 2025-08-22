# app/routers/consultas.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.models.schemas import ConsultasRequest, JobCreateResponse, JobStatusResponse
from app.jobs.manager import create_job, get_job, list_jobs

router = APIRouter(prefix="/consultas", tags=["consultas"])

@router.post("", response_model=JobCreateResponse)
def crear_job(payload: ConsultasRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items vacío")
    job_id = create_job(payload.items, headless=payload.headless)
    return JobCreateResponse(job_id=job_id, status="queued")

@router.get("/{job_id}", response_model=JobStatusResponse)
def estado_job(job_id: str):
    info = get_job(job_id)
    if info.get("status") == "error" and info.get("error") == "job_not_found":
        raise HTTPException(status_code=404, detail="job no encontrado")
    return JobStatusResponse(job_id=job_id, status=info["status"], data=info.get("data"), error=info.get("error"))

@router.get("", response_model=Dict[str, Any])
def listar():
    return list_jobs()
