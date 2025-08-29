# app/routers/consultas.py
from __future__ import annotations

import threading
import uuid
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from app.models.schemas import ConsultasRequest, JobCreateResponse, JobStatusResponse
from app.services.executor import run_items
from core.utils.log import log

# Persistencia de reportes
from app.services.report_store import persist_report

router = APIRouter(prefix="", tags=["consultas"])

# -------------------------
# Memoria de jobs en proceso
# -------------------------
_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()

class _JobState(BaseModel):
    job_id: str
    status: str  # queued | running | done | error
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # meta para informe/persistencia
    informe_meta: Optional[Dict[str, Any]] = None
    generate_report: bool = False
    persisted: bool = False  # para no duplicar guardado


def _extract_first_screenshot_path(results: Dict[str, Any]) -> Optional[str]:
    """
    Busca de forma flexible una ruta de screenshot en el dict de resultados.
    Soportamos claves: screenshot_path, captura_ruta, screenshot_historial_path.
    """
    if not results:
        return None

    # results tiene forma {tipo: payload, ...}
    for _, payload in results.items():
        if not isinstance(payload, dict):
            continue
        # priorizamos screenshot_path principal
        for key in ("screenshot_path", "captura_ruta"):
            if key in payload and payload.get(key):
                return payload.get(key)
        # si hay historial
        if "screenshot_historial_path" in payload and payload.get("screenshot_historial_path"):
            return payload.get("screenshot_historial_path")

    return None


def _run_job(job_id: str, req: ConsultasRequest):
    with _JOBS_LOCK:
        _JOBS[job_id]["status"] = "running"

    try:
        data = run_items(req.items, headless=req.headless)  # Ejecuta el flujo secuencial
        with _JOBS_LOCK:
            _JOBS[job_id]["data"] = data
            _JOBS[job_id]["status"] = "done"
    except Exception as e:
        log(f"❌ Error en job {job_id}: {e}")
        with _JOBS_LOCK:
            _JOBS[job_id]["error"] = str(e)
            _JOBS[job_id]["status"] = "error"

    # Intento de persistencia (si fue pedido y aún no se ha persistido)
    try:
        with _JOBS_LOCK:
            st = _JOBS.get(job_id, {})
            do_persist = bool(st.get("generate_report"))
            was_persisted = bool(st.get("persisted"))
            meta = st.get("informe_meta") or {}
            results = st.get("data") or {}

        if do_persist and not was_persisted and (_JOBS[job_id]["status"] == "done"):
            # Elegimos una ruta de archivo; por ahora la PRIMERA screenshot disponible
            file_path = _extract_first_screenshot_path(results)
            if not file_path:
                log("ℹ️ Persistencia omitida: no se encontró screenshot en resultados.")
            else:
                # Extraemos meta
                tipo_alerta = (meta.get("tipo_alerta") if isinstance(meta, dict) else None) or "N/A"
                monto_usd = meta.get("monto_usd") if isinstance(meta, dict) else None
                fecha_alerta = meta.get("fecha_alerta") if isinstance(meta, dict) else None

                # Guardamos snapshot de resultados junto al archivo
                report_id = persist_report(
                    job_id=job_id,
                    tipo_alerta=tipo_alerta,
                    monto_usd=monto_usd,
                    fecha_alerta=fecha_alerta,
                    file_path=file_path,                 # también soporta report_path
                    data_snapshot={
                        "job_id": job_id,
                        "results": results,
                        "meta": meta,
                    },
                )
                log(f"✅ Reporte persistido (id={report_id})")

                with _JOBS_LOCK:
                    _JOBS[job_id]["persisted"] = True

    except Exception as e:
        log(f"⚠️ Persistencia de reporte falló: {e}")


@router.post("/consultas", response_model=JobCreateResponse)
def create_consultas(req: ConsultasRequest):
    """
    Crea un job async para ejecutar las consultas.
    Si llegan 'informe_meta' + 'generate_report=True', al terminar se guardará un registro en 'reports'.
    """
    job_id = uuid.uuid4().hex

    with _JOBS_LOCK:
        _JOBS[job_id] = _JobState(
            job_id=job_id,
            status="queued",
            data=None,
            error=None,
            informe_meta=(req.informe_meta.dict() if req.informe_meta else None),
            generate_report=bool(req.generate_report),
            persisted=False,
        ).dict()

    # Lanzamos en background
    th = threading.Thread(target=_run_job, args=(job_id, req), daemon=True)
    th.start()

    return JobCreateResponse(job_id=job_id, status="queued")


@router.get("/consultas/{job_id}", response_model=JobStatusResponse)
def get_consulta_status(job_id: str):
    with _JOBS_LOCK:
        st = _JOBS.get(job_id)
        if not st:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        return JobStatusResponse(job_id=job_id, status=st["status"], data=st.get("data"), error=st.get("error"))
