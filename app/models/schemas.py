# app/models/schemas.py
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, constr

TipoItem = Literal["ruc", "deudas", "denuncias"]

class QueryItem(BaseModel):
    tipo: TipoItem = Field(..., description="Tipo de consulta (ruc | deudas | denuncias)")
    valor: constr(strip_whitespace=True, min_length=2, max_length=50) = Field(
        ..., description="Dato requerido por la página (RUC/Cédula/Nombres)"
    )

class ConsultasRequest(BaseModel):
    items: List[QueryItem] = Field(..., description="Lista de consultas a ejecutar en secuencia")
    modo: Literal["async"] = Field("async", description="Solo async por ahora")
    headless: bool = Field(False, description="Ejecutar headless (no recomendado por captcha/pyautogui)")

class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
