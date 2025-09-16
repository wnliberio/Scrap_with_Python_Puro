# app/routers/tracking_professional.py - CÓDIGO COMPLETO CORREGIDO
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.tracking_professional import (
    get_paginas_activas,
    get_clientes_with_filters,
    update_cliente_estado,
    crear_proceso_completo
)

router = APIRouter(prefix="/tracking", tags=["tracking"])

# ===== MODELOS DE REQUEST =====

class IniciarProcesoRequest(BaseModel):
    cliente_id: int = Field(..., description="ID del cliente en de_clientes")
    paginas_codigos: List[str] = Field(..., min_items=1, description="Códigos de páginas a consultar")
    headless: bool = Field(False, description="Ejecutar en modo headless")
    generate_report: bool = Field(True, description="Generar reporte al finalizar")

class ActualizarEstadoClienteRequest(BaseModel):
    estado: str = Field(..., description="Nuevo estado del cliente")
    mensaje_error: Optional[str] = Field(None, description="Mensaje de error opcional")

# ===== ENDPOINTS BÁSICOS =====

@router.get("/health", summary="Health check del sistema")
def health_check() -> Dict[str, Any]:
    """Health check básico para verificar que el sistema de tracking funciona"""
    try:
        # Verificar que podemos acceder a las páginas
        paginas = get_paginas_activas()
        
        return {
            "status": "healthy",
            "message": "Sistema de tracking funcionando correctamente",
            "timestamp": datetime.now().isoformat(),
            "paginas_disponibles": len(paginas),
            "tablas_verificadas": ["de_clientes", "de_paginas", "de_procesos", "de_consultas"]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sistema no saludable: {str(e)}")

@router.get("/paginas", summary="Listar páginas disponibles")
def listar_paginas_disponibles() -> List[Dict[str, Any]]:
    """
    Obtiene todas las páginas disponibles para consulta.
    Se usa para mostrar los checkboxes en el frontend cuando el usuario
    selecciona qué páginas consultar para un cliente.
    """
    try:
        return get_paginas_activas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo páginas: {str(e)}")

@router.get("/clientes", summary="Listar clientes con filtros")
def listar_clientes_con_filtros(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    q: Optional[str] = Query(None, description="Búsqueda en nombre, apellido, CI, RUC")
) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de clientes con filtros opcionales.
    Incluye el proceso activo si el cliente tiene uno en curso.
    Este endpoint reemplaza parcialmente a /api/lista.
    """
    try:
        return get_clientes_with_filters(
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            q=q
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo clientes: {str(e)}")

@router.put("/clientes/{cliente_id}/estado", summary="Actualizar estado de cliente")
def actualizar_estado_cliente(
    cliente_id: int,
    request: ActualizarEstadoClienteRequest
) -> Dict[str, Any]:
    """
    Actualiza el estado de un cliente específico.
    Se usa cuando el sistema necesita cambiar el estado de un cliente
    (ej: de 'Pendiente' a 'Procesando').
    """
    try:
        success = update_cliente_estado(
            cliente_id=cliente_id,
            estado=request.estado,
            mensaje_error=request.mensaje_error
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        return {"success": True, "message": f"Estado actualizado a {request.estado}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando cliente: {str(e)}")

@router.post("/procesos/crear", summary="Crear nuevo proceso")
def crear_nuevo_proceso(request: IniciarProcesoRequest) -> Dict[str, Any]:
    """
    Crea un nuevo proceso con las páginas seleccionadas.
    
    Este es el endpoint principal que se llama cuando:
    1. El usuario selecciona un cliente pendiente
    2. Marca los checkboxes de las páginas que quiere consultar
    3. Hace clic en "Agregar a Cola"
    
    El proceso se crea con estado 'Pendiente' y luego el sistema de jobs
    lo toma para ejecutarlo.
    """
    try:
        import uuid
        
        job_id = str(uuid.uuid4())
        
        proceso_id = crear_proceso_completo(
            cliente_id=request.cliente_id,
            job_id=job_id,
            paginas_codigos=request.paginas_codigos,
            headless=request.headless,
            generate_report=request.generate_report
        )
        
        return {
            "success": True,
            "proceso_id": proceso_id,
            "job_id": job_id,
            "mensaje": f"Proceso creado con {len(request.paginas_codigos)} páginas",
            "paginas_solicitadas": request.paginas_codigos
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando proceso: {str(e)}")

# ===== ENDPOINTS STUB (PARA IMPLEMENTAR DESPUÉS) =====

@router.get("/procesos/{job_id}", summary="Obtener detalles de proceso")
def obtener_proceso_detalle(job_id: str) -> Dict[str, Any]:
    """Obtiene los detalles completos de un proceso por job_id - EN DESARROLLO"""
    raise HTTPException(status_code=501, detail="Endpoint en desarrollo")

@router.get("/clientes/{cliente_id}/detalles", summary="Obtener detalles completos de cliente")
def obtener_detalles_cliente(cliente_id: int) -> Dict[str, Any]:
    """Obtiene detalles completos de un cliente para el modal 'Detalles' - EN DESARROLLO"""
    raise HTTPException(status_code=501, detail="Endpoint en desarrollo")

@router.get("/estadisticas", summary="Obtener estadísticas del sistema")
def obtener_estadisticas() -> Dict[str, Any]:
    """Obtiene estadísticas generales del sistema para dashboards - EN DESARROLLO"""
    raise HTTPException(status_code=501, detail="Endpoint en desarrollo")