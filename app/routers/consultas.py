# app/routers/consultas.py
from __future__ import annotations

import uuid
import threading
import traceback
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.utils.log import log
from app.models.schemas import QueryItem  # reutilizamos tu schema de items
from app.services.executor import run_items
from app.services.report_store import generate_and_persist_report

router = APIRouter()

# ----------------------------
# Job store en memoria
# ----------------------------
_JOBS: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


class ConsultasBody(BaseModel):
    items: list[QueryItem] = Field(..., description="Lista de consultas")
    modo: str = Field("async", description="Solo async")
    headless: bool = False

    # Meta para informe (opcional)
    informe_meta: Optional[Dict[str, Any]] = None
    generate_report: Optional[bool] = False


def _set_job(job_id: str, payload: Dict[str, Any]) -> None:
    with _LOCK:
        _JOBS[job_id] = payload


def _get_job(job_id: str) -> Dict[str, Any]:
    with _LOCK:
        return _JOBS.get(job_id, {"status": "not_found"})


def _worker(job_id: str, body: ConsultasBody) -> None:
    try:
        log(f"🧵 Worker iniciado para job {job_id}")
        # Ejecutar las consultas en secuencia (tu lógica existente)
        results = run_items(items=body.items, headless=body.headless)

        out: Dict[str, Any] = {"results": results}

        # ¿Generar informe?
        if body.generate_report:
            try:
                meta = body.informe_meta or {}
                rep = generate_and_persist_report(
                    job_id=job_id,
                    results=results,
                    meta=meta,
                )
                # Asegurarnos que sea SIEMPRE un dict con estas claves
                if not isinstance(rep, dict) or "report_id" not in rep or "report_path" not in rep:
                    raise RuntimeError("generate_and_persist_report() debe retornar {'report_id', 'report_path'}")
                out["report_id"] = rep["report_id"]
                out["report_path"] = rep["report_path"]
            except Exception as e:
                tb = traceback.format_exc()
                log(f"⚠️ Error generando/persistiendo reporte: {e}\n{tb}")
                # No hacemos fail del job por el informe; solo lo registramos
                out["report_error"] = str(e)

        _set_job(job_id, {"status": "done", "data": out})
        log(f"✅ Job {job_id} terminado.")
    except Exception as e:
        tb = traceback.format_exc()
        log(f"⚠️ Error en worker de consultas:  {e}\n{tb}")
        _set_job(job_id, {"status": "error", "error": str(e)})


@router.post("/consultas")
def create_consultas(body: ConsultasBody):
    """
    Crea un job y lanza un hilo que ejecuta las consultas.
    """
    job_id = uuid.uuid4().hex
    _set_job(job_id, {"status": "queued"})
    t = threading.Thread(target=_worker, args=(job_id, body), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@router.get("/consultas/{job_id}/status")
def job_status(job_id: str):
    st = _get_job(job_id)
    if st.get("status") == "not_found":
        # Para no romper front: devolver 200 con not_found o lanzar 404.
        # Mantengo 200 como venías manejándolo.
        return {"job_id": job_id, "status": "not_found"}
    # Estructura estable para el front
    return {
        "job_id": job_id,
        "status": st.get("status"),
        "data": st.get("data"),
        "error": st.get("error"),
    }
