# app/models/schemas.py
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, constr

# -------- Nuevos modelos para el informe --------
class InformeMeta(BaseModel):
    tipo_alerta: Optional[str] = Field(None, description="Tipo de alerta (ej. Venta vehículo, Venta casa)")
    monto_usd: Optional[float] = Field(None, description="Monto en USD asociado a la alerta")
    fecha_alerta: Optional[str] = Field(None, description="Fecha ISO-8601 (YYYY-MM-DD) de la alerta")

# Incluye mercado_valores, interpol, google, contraloria, supercias_persona y predios
TipoItem = Literal[
    "ruc",
    "deudas",
    "denuncias",
    "mercado_valores",
    "interpol",
    "google",
    "contraloria",
    "supercias_persona",
    "predio_quito",
    "predio_manta",
]

class QueryItem(BaseModel):
    tipo: TipoItem = Field(
        ...,
        description="Tipo de consulta (ruc | deudas | denuncias | mercado_valores | interpol | google | contraloria | supercias_persona | predio_quito | predio_manta)"
    )

    # Valor principal (se usa para todos los tipos)
    valor: constr(strip_whitespace=True, min_length=2, max_length=120) = Field(
        ...,
        description="Dato requerido por la página (RUC/Cédula/Nombres/Entidad/Apellidos/Texto de búsqueda)"
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
        None, description="(Opcional) Para mercado_valores; el backend usará 'auto'."
    )
    solve: Optional[bool] = Field(
        False, description="(Opcional) Ignorado por el backend; el captcha se resuelve internamente."
    )

class ConsultasRequest(BaseModel):
    items: List[QueryItem] = Field(..., description="Lista de consultas a ejecutar en secuencia")
    modo: Literal["async"] = Field("async", description="Solo async por ahora")
    headless: bool = Field(False, description="Ejecutar headless (no recomendado por captcha/pyautogui)")

    # --------- NUEVO: metadata y bandera para generar informe/persistir ---------
    informe_meta: Optional[InformeMeta] = Field(None, description="Metadatos del informe (tipo alerta, monto, fecha)")
    generate_report: Optional[bool] = Field(False, description="Si es True, se persiste un registro en reports")
    # ---------------------------------------------------------------------------

class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
