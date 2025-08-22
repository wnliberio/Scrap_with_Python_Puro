# app/jobs/manager.py
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, Future
from uuid import uuid4
from threading import Lock
from core.utils.log import log
from app.models.schemas import QueryItem
from app.services.executor import run_items

# Un solo worker para evitar múltiples navegadores peleando por el cursor / focus
_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_JOBS: Dict[str, Dict[str, Any]] = {}
_LOCK = Lock()

def create_job(items: List[QueryItem], headless: bool = False) -> str:
    job_id = str(uuid4())
    with _LOCK:
        _JOBS[job_id] = {"status": "queued", "data": None, "error": None, "future": None}
    log(f"🧾 Job creado: {job_id} con {len(items)} item(s)")

    def _task():
        try:
            with _LOCK:
                _JOBS[job_id]["status"] = "running"
            log(f"▶️ Job {job_id} iniciado")
            data = run_items(items, headless=headless)
            with _LOCK:
                _JOBS[job_id]["status"] = "done"
                _JOBS[job_id]["data"] = data
            log(f"✅ Job {job_id} finalizado")
        except Exception as e:
            with _LOCK:
                _JOBS[job_id]["status"] = "error"
                _JOBS[job_id]["error"] = str(e)
            log(f"❌ Job {job_id} error: {e}")

    fut: Future = _EXECUTOR.submit(_task)
    with _LOCK:
        _JOBS[job_id]["future"] = fut
    return job_id

def get_job(job_id: str) -> Dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return {"status": "error", "error": "job_not_found"}
        # no devolvemos el Future
        return {"status": job["status"], "data": job["data"], "error": job["error"]}

def list_jobs() -> Dict[str, Any]:
    with _LOCK:
        return {jid: {"status": j["status"]} for jid, j in _JOBS.items()}
