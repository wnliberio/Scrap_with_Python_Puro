# app/models/schemas.py
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, constr

# Incluye mercado_valores, interpol, google y contraloria
TipoItem = Literal["ruc", "deudas", "denuncias", "mercado_valores", "interpol", "google", "contraloria"]

class QueryItem(BaseModel):
    tipo: TipoItem = Field(..., description="Tipo de consulta (ruc | deudas | denuncias | mercado_valores | interpol | google | contraloria)")

    # Valor principal (se usa para todos los tipos; p.ej.: texto para google, cédula 10 dígitos para contraloria)
    valor: constr(strip_whitespace=True, min_length=2, max_length=120) = Field(
        ..., description="Dato requerido por la página (RUC/Cédula/Nombres/Entidad/Apellidos/Texto de búsqueda)"
    )

    # Opcionales para INTERPOL (libre elección)
    apellidos: Optional[constr(strip_whitespace=True, min_length=1, max_length=80)] = Field(
        None, description="(INTERPOL) Apellidos. Puedes dejarlo vacío si solo envías nombres."
    )
    nombres: Optional[constr(strip_whitespace=True, min_length=1, max_length=80)] = Field(
        None, description="(INTERPOL) Nombres. Puedes dejarlo vacío si solo envías apellidos."
    )

    # Compat Mercado de Valores; el backend fuerza auto+solve
    mode: Optional[Literal["auto", "ident", "nombre"]] = Field(
        None, description="(Opcional) Modo de búsqueda para mercado_valores; el backend usará 'auto'."
    )
    solve: Optional[bool] = Field(
        False, description="(Opcional) Ignorado por el backend; el captcha se resuelve internamente."
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

