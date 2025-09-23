# app/routers/tracking_professional.py - VERSIÓN CON EXECUTOR CONECTADO
from __future__ import annotations
from fastapi.responses import FileResponse
import os
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
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
    cliente_id: int = Field(..., description="ID del cliente en de_clientes_rpa")
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
            "tablas_verificadas": ["de_clientes_rpa", "de_paginas_rpa", "de_procesos_rpa", "de_consultas_rpa"]
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

# ===== FUNCIÓN HELPER PARA CONVERTIR A QueryItem =====

# FRAGMENTO DE app/routers/tracking_professional.py
# SOLO LA FUNCIÓN _convertir_a_query_items QUE NECESITA SER ARREGLADA

def _convertir_a_query_items(cliente_data: Dict[str, Any], paginas_codigos: List[str]) -> List[Dict[str, Any]]:
    """
    Convierte los códigos de páginas en QueryItems compatibles con el executor existente.
    """
    from app.db import SessionLocal
    from app.db.models_new import DePagina, DeCliente
    
    db = SessionLocal()
    try:
        # Obtener cliente
        cliente = db.query(DeCliente).filter(DeCliente.id == cliente_data['id']).first()
        if not cliente:
            raise ValueError("Cliente no encontrado")
        
        items = []
        for codigo in paginas_codigos:
            # Determinar valor según código de página
            valor = None
            apellidos = None
            nombres = None
            
            if codigo in ['ruc', 'deudas', 'mercado_valores']:
                valor = cliente.ruc
            elif codigo in ['contraloria', 'supercias_persona', 'predio_quito', 'predio_manta']:
                valor = cliente.ci
            elif codigo in ['denuncias', 'google', 'funcion_judicial']:  # ✅ AGREGADO funcion_judicial
                valor = f"{cliente.apellido} {cliente.nombre}".strip()
            elif codigo == 'interpol':
                valor = cliente.apellido
                apellidos = cliente.apellido
                nombres = cliente.nombre
            
            if valor:
                item = {
                    "tipo": codigo,
                    "valor": valor
                }
                
                # Agregar campos opcionales para INTERPOL
                if apellidos:
                    item["apellidos"] = apellidos
                if nombres:
                    item["nombres"] = nombres
                
                items.append(item)
        
        return items
    finally:
        db.close()

# ===== ENDPOINT PRINCIPAL - CREAR Y EJECUTAR PROCESO =====

@router.post("/procesos/crear", summary="Crear y ejecutar nuevo proceso")
def crear_nuevo_proceso(
    request: IniciarProcesoRequest, 
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Crea un nuevo proceso con las páginas seleccionadas Y LO EJECUTA.
    
    Este es el endpoint principal que se llama cuando:
    1. El usuario selecciona un cliente pendiente
    2. Marca los checkboxes de las páginas que quiere consultar
    3. Hace clic en "Agregar a Cola"
    
    AHORA: El proceso se crea, se registra en BD Y se envía al executor real.
    """
    try:
        import uuid
        
        job_id = str(uuid.uuid4())
        
        # 1. Crear proceso en BD
        proceso_id = crear_proceso_completo(
            cliente_id=request.cliente_id,
            job_id=job_id,
            paginas_codigos=request.paginas_codigos,
            headless=request.headless,
            generate_report=request.generate_report
        )
        
        # 2. Obtener datos del cliente para el executor
        from app.services.tracking_professional import get_clientes_with_filters
        clientes = get_clientes_with_filters()
        cliente = next((c for c in clientes if c['id'] == request.cliente_id), None)
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # 3. Convertir a formato QueryItem para el executor
        query_items = _convertir_a_query_items(cliente, request.paginas_codigos)
        
        # 4. Enviar al executor real usando el job manager existente
        background_tasks.add_task(
            _ejecutar_proceso_en_background,
            job_id,
            query_items,
            request.headless,
            request.generate_report
        )
        
        return {
            "success": True,
            "proceso_id": proceso_id,
            "job_id": job_id,
            "mensaje": f"Proceso creado y enviado al executor con {len(request.paginas_codigos)} páginas",
            "paginas_solicitadas": request.paginas_codigos,
            "items_generados": len(query_items)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando proceso: {str(e)}")

# ===== FUNCIÓN DE BACKGROUND PARA EJECUTAR =====

async def _ejecutar_proceso_en_background(
    job_id: str, 
    query_items: List[Dict[str, Any]], 
    headless: bool,
    generate_report: bool
):
    """
    Ejecuta el proceso en background usando el executor existente.
    """
    try:
        print(f"🚀 Iniciando ejecución de proceso {job_id}")
        print(f"📋 Items a ejecutar: {[item['tipo'] for item in query_items]}")
        
        # Importar el executor existente
        from app.jobs.manager import create_job, get_job
        from app.models.schemas import QueryItem
        
        # Convertir a objetos QueryItem
        items = []
        for item_dict in query_items:
            item = QueryItem(
                tipo=item_dict["tipo"],
                valor=item_dict["valor"],
                apellidos=item_dict.get("apellidos"),
                nombres=item_dict.get("nombres")
            )
            items.append(item)
        
        # Crear job usando el manager existente
        executor_job_id = create_job(items, headless=headless)
        print(f"📤 Job enviado al executor: {executor_job_id}")
        
        # Esperar que termine y sincronizar resultado
        import asyncio
        while True:
            await asyncio.sleep(2)  # Revisar cada 2 segundos
            
            job_status = get_job(executor_job_id)
            print(f"🔍 Estado del job {executor_job_id}: {job_status['status']}")
            
            if job_status["status"] == "done":
                # Job terminado exitosamente
                print(f"✅ Job {executor_job_id} completado")
                
                # Sincronizar resultado con sistema de tracking
                resultado = {
                    "job_id": job_id,
                    "status": "done",
                    "data": job_status.get("data", {})
                }
                
                # Llamar al servicio de sincronización
                from app.services.sincronizacion_service import sincronizar_job_completado
                await sincronizar_job_completado(job_id, resultado)
                
                break
                
            elif job_status["status"] == "error":
                # Job falló
                print(f"❌ Job {executor_job_id} falló: {job_status.get('error')}")
                
                # Actualizar estado del cliente a Error
                from app.services.tracking_professional import get_proceso_by_job_id
                proceso = get_proceso_by_job_id(job_id)
                if proceso:
                    from app.services.sincronizacion_service import actualizar_cliente_estado
                    await actualizar_cliente_estado(
                        proceso['cliente_id'], 
                        'Error', 
                        job_status.get('error', 'Error en ejecución')
                    )
                
                break
                
    except Exception as e:
        print(f"💥 Error ejecutando proceso en background: {e}")
        import traceback
        traceback.print_exc()

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

# AGREGAR ESTAS LÍNEAS AL FINAL DE app/routers/tracking_professional.py

# ===== IMPORTS ADICIONALES (AGREGAR AL INICIO DEL ARCHIVO) =====
#from fastapi.responses import FileResponse
#import os

# ===== ENDPOINT DE DESCARGA (AGREGAR AL FINAL DEL ARCHIVO) =====

@router.get("/reportes/{proceso_id}/download", summary="Descargar reporte de proceso")
def descargar_reporte_proceso(proceso_id: int) -> FileResponse:
    """
    Descarga el reporte DOCX de un proceso específico.
    Se usa desde el botón "Descargar Reporte" en el modal de detalles.
    """
    try:
        # Importar modelos necesarios
        from app.db import SessionLocal
        from app.db.models_new import DeReporte
        
        db = SessionLocal()
        try:
            # Buscar reporte por proceso_id
            reporte = db.query(DeReporte).filter(
                DeReporte.proceso_id == proceso_id,
                DeReporte.generado_exitosamente == True
            ).first()
            
            if not reporte:
                raise HTTPException(
                    status_code=404, 
                    detail="Reporte no encontrado o no generado exitosamente"
                )
            
            # Verificar que el archivo existe físicamente
            if not reporte.ruta_archivo or not os.path.exists(reporte.ruta_archivo):
                raise HTTPException(
                    status_code=404, 
                    detail="Archivo de reporte no encontrado en el sistema"
                )
            
            print(f"📥 Descargando reporte: {reporte.nombre_archivo}")
            print(f"📁 Ruta: {reporte.ruta_archivo}")
            
            # Retornar archivo para descarga
            return FileResponse(
                path=reporte.ruta_archivo,
                filename=reporte.nombre_archivo or f"reporte_proceso_{proceso_id}.docx",
                media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                headers={
                    "Content-Disposition": f"attachment; filename=\"{reporte.nombre_archivo or f'reporte_proceso_{proceso_id}.docx'}\""
                }
            )
            
        finally:
            db.close()
            
    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    except Exception as e:
        print(f"❌ Error descargando reporte proceso {proceso_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno descargando reporte: {str(e)}"
        )

# REEMPLAZAR la función listar_reportes_tracking en app/routers/tracking_professional.py

@router.get("/reportes", summary="Listar todos los reportes disponibles")
def listar_reportes_tracking(
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    solo_exitosos: bool = Query(True, description="Solo reportes generados exitosamente")
) -> List[Dict[str, Any]]:
    """
    Lista todos los reportes generados por el sistema de tracking.
    Se puede usar para crear una página de administración de reportes.
    """
    try:
        from app.db import SessionLocal
        from app.db.models_new import DeReporte, DeCliente
        
        db = SessionLocal()
        try:
            query = db.query(DeReporte)
            
            # Aplicar filtros
            if cliente_id:
                query = query.filter(DeReporte.cliente_id == cliente_id)
            
            # FIX: Verificar que fecha_desde sea string válido
            if fecha_desde and isinstance(fecha_desde, str) and fecha_desde.strip():
                try:
                    fecha_desde_dt = datetime.strptime(fecha_desde.strip(), "%Y-%m-%d")
                    query = query.filter(DeReporte.fecha_generacion >= fecha_desde_dt)
                except ValueError as e:
                    print(f"⚠️ Fecha desde inválida ignorada: {fecha_desde} - {e}")
            
            # FIX: Verificar que fecha_hasta sea string válido
            if fecha_hasta and isinstance(fecha_hasta, str) and fecha_hasta.strip():
                try:
                    fecha_hasta_dt = datetime.strptime(fecha_hasta.strip(), "%Y-%m-%d")
                    query = query.filter(DeReporte.fecha_generacion <= fecha_hasta_dt)
                except ValueError as e:
                    print(f"⚠️ Fecha hasta inválida ignorada: {fecha_hasta} - {e}")
            
            if solo_exitosos:
                query = query.filter(DeReporte.generado_exitosamente == True)
            
            reportes = query.order_by(DeReporte.fecha_generacion.desc()).all()
            
            # Enriquecer con información del cliente
            resultado = []
            for reporte in reportes:
                # Obtener información del cliente
                cliente = db.query(DeCliente).filter(DeCliente.id == reporte.cliente_id).first()
                
                # Verificar si el archivo existe
                archivo_existe = (reporte.ruta_archivo and 
                                os.path.exists(reporte.ruta_archivo))
                
                resultado.append({
                    'id': reporte.id,
                    'proceso_id': reporte.proceso_id,
                    'job_id': reporte.job_id,
                    'cliente': {
                        'id': cliente.id,
                        'nombre': cliente.nombre,
                        'apellido': cliente.apellido,
                        'ci': cliente.ci,
                        'ruc': cliente.ruc
                    } if cliente else None,
                    'tipo_alerta': reporte.tipo_alerta,
                    'monto_usd': reporte.monto_usd,
                    'fecha_alerta': reporte.fecha_alerta.isoformat() if reporte.fecha_alerta else None,
                    'nombre_archivo': reporte.nombre_archivo,
                    'url_descarga': reporte.url_descarga,
                    'tamano_bytes': reporte.tamano_bytes,
                    'tipo_archivo': reporte.tipo_archivo,
                    'generado_exitosamente': reporte.generado_exitosamente,
                    'fecha_generacion': reporte.fecha_generacion.isoformat(),
                    'archivo_existe': archivo_existe
                })
            
            print(f"✅ Reportes listados correctamente: {len(resultado)} encontrados")
            return resultado
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error listando reportes: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error listando reportes: {str(e)}")

@router.get("/clientes/{cliente_id}/reportes", summary="Obtener reportes de un cliente específico")
def obtener_reportes_cliente(cliente_id: int) -> List[Dict[str, Any]]:
    """
    Obtiene todos los reportes de un cliente específico.
    Se usa en el modal de detalles del cliente.
    """
    return listar_reportes_tracking(cliente_id=cliente_id, solo_exitosos=True)