# app/models/schemas.py
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, constr

# -------- Nuevos modelos para el informe --------
class InformeMeta(BaseModel):
    tipo_alerta: Optional[str] = Field(None, description="Tipo de alerta (ej. Venta vehículo, Venta casa)")
    monto_usd: Optional[float] = Field(None, description="Monto en USD asociado a la alerta")
    fecha_alerta: Optional[str] = Field(None, description="Fecha ISO-8601 (YYYY-MM-DD) de la alerta")

# Incluye todas las páginas + funcion_judicial
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
    "funcion_judicial",
]

class QueryItem(BaseModel):
    tipo: TipoItem = Field(
        ...,
        description="Tipo de consulta (ruc | deudas | denuncias | mercado_valores | interpol | google | contraloria | supercias_persona | predio_quito | predio_manta | funcion_judicial)"
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

class ConsultasBody(BaseModel):
    """
    Modelo principal para iniciar un proceso de consultas.
    """
    items: List[QueryItem] = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Lista de consultas a ejecutar (máximo 50)"
    )
    
    # Configuración de ejecución
    headless: bool = Field(
        default=True, 
        description="Ejecutar en modo headless (sin interfaz gráfica). False útil para debugging."
    )
    
    # Metadatos del informe/proceso
    meta: Optional[InformeMeta] = Field(
        None, 
        description="Metadatos opcionales para el informe final"
    )

class JobStatusResponse(BaseModel):
    """
    Respuesta del estado de un job/proceso.
    """
    job_id: str
    status: Literal["queued", "running", "completed", "error", "not_found"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None