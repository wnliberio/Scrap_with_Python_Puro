from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, constr

# 👉 Añadimos 'interpol' a los tipos soportados
TipoItem = Literal["ruc", "deudas", "denuncias", "interpol"]

class QueryItem(BaseModel):
    tipo: TipoItem = Field(
        ...,
        description="Tipo de consulta (ruc | deudas | denuncias | interpol)"
    )
    valor: constr(strip_whitespace=True, min_length=1, max_length=100) = Field(
        ...,
        description=(
            "Dato requerido por la página. "
            "RUC/Cédula para ruc/deudas, Nombres completos para denuncias, "
            "e Interpol usa 'APELLIDOS|NOMBRES' (uno o ambos, puede ser '|NOMBRES' o 'APELLIDOS|')."
        ),
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
