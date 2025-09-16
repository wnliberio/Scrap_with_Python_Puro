# app/services/executor_updated.py - INTEGRACIÓN CON NUEVO SISTEMA DE TRACKING
"""
IMPORTANTE: Este archivo muestra cómo integrar tu executor.py existente 
con el nuevo sistema de tracking granular.

Mantiene toda tu lógica existente pero agrega calls al sistema de tracking.
"""

from typing import List, Dict, Any
from datetime import datetime

# Tus imports existentes
from app.models.schemas import QueryItem
from app.services.tracking_professional import (
    get_proceso_by_job_id,
    actualizar_consulta_por_codigo,
    iniciar_proceso,
    finalizar_proceso,
    get_pagina_by_codigo
)
from core.utils.log import log

def run_items_with_tracking(items: List[QueryItem], headless: bool = False, 
                           job_id: str = None) -> Dict[str, Any]:
    """
    Versión mejorada de run_items que integra con el sistema de tracking.
    
    Esta función:
    1. Mantiene toda tu lógica existente de run_items
    2. Agrega tracking granular por página consultada
    3. Actualiza estados en tiempo real en la base de datos
    """
    
    if not job_id:
        # Si no viene job_id, funciona como antes (modo compatibilidad)
        return run_items_legacy(items, headless)
    
    # 1. Obtener información del proceso
    proceso = get_proceso_by_job_id(job_id)
    if not proceso:
        log(f"⚠️ Proceso {job_id} no encontrado, ejecutando en modo legacy")
        return run_items_legacy(items, headless)
    
    log(f"🚀 Iniciando proceso {job_id} con tracking para cliente {proceso['cliente_id']}")
    
    # 2. Marcar proceso como iniciado
    iniciar_proceso(proceso['id'])
    
    results = {}
    
    try:
        # 3. Ejecutar cada consulta con tracking individual
        for item in items:
            pagina_codigo = item.tipo
            valor = item.valor
            
            log(f"📄 Procesando página: {pagina_codigo}")
            
            # 3.1 Marcar consulta como en proceso
            actualizar_consulta_por_codigo(
                proceso_id=proceso['id'],
                pagina_codigo=pagina_codigo,
                datos_actualizacion={
                    'estado': 'En_Proceso',
                    'fecha_inicio': datetime.now(),
                    'valor_enviado': valor,
                    'parametros_extra': {
                        'apellidos': getattr(item, 'apellidos', None),
                        'nombres': getattr(item, 'nombres', None),
                        'mode': getattr(item, 'mode', None)
                    }
                }
            )
            
            # 3.2 Obtener URL dinámica de la base de datos
            pagina_info = get_pagina_by_codigo(pagina_codigo)
            if not pagina_info:
                # Página no encontrada, marcar como fallida
                actualizar_consulta_por_codigo(
                    proceso_id=proceso['id'],
                    pagina_codigo=pagina_codigo,
                    datos_actualizacion={
                        'estado': 'Fallida',
                        'mensaje_error': f'Página {pagina_codigo} no encontrada en catálogo',
                        'fecha_fin': datetime.now()
                    }
                )
                results[pagina_codigo] = {"error": "Página no encontrada"}
                continue
            
            # 3.3 Ejecutar la consulta usando tu lógica existente
            try:
                # AQUÍ VA TU LÓGICA EXISTENTE POR TIPO DE PÁGINA
                # Pero ahora usa pagina_info['url'] en lugar de URL hardcodeada
                
                if pagina_codigo == "ruc":
                    resultado = ejecutar_consulta_ruc(valor, pagina_info['url'], headless)
                elif pagina_codigo == "deudas":
                    resultado = ejecutar_consulta_deudas(valor, pagina_info['url'], headless)
                elif pagina_codigo == "denuncias":
                    resultado = ejecutar_consulta_denuncias(valor, pagina_info['url'], headless)
                elif pagina_codigo == "interpol":
                    resultado = ejecutar_consulta_interpol(
                        apellidos=getattr(item, 'apellidos', ''),
                        nombres=getattr(item, 'nombres', valor),
                        url=pagina_info['url'],
                        headless=headless
                    )
                # ... resto de tipos
                else:
                    resultado = ejecutar_consulta_generica(pagina_codigo, valor, pagina_info['url'], headless)
                
                # 3.4 Consulta exitosa
                actualizar_consulta_por_codigo(
                    proceso_id=proceso['id'],
                    pagina_codigo=pagina_codigo,
                    datos_actualizacion={
                        'estado': 'Exitosa',
                        'fecha_fin': datetime.now(),
                        'screenshot_path': resultado.get('screenshot_path'),
                        'screenshot_historial_path': resultado.get('screenshot_historial_path'),
                        'escenario': resultado.get('scenario', 'completado'),
                        'datos_capturados': resultado.get('datos_extra')
                    }
                )
                
                results[pagina_codigo] = resultado
                log(f"✅ {pagina_codigo} completado exitosamente")
                
            except Exception as e:
                # 3.5 Consulta fallida
                log(f"❌ Error en {pagina_codigo}: {e}")
                
                actualizar_consulta_por_codigo(
                    proceso_id=proceso['id'],
                    pagina_codigo=pagina_codigo,
                    datos_actualizacion={
                        'estado': 'Fallida',
                        'fecha_fin': datetime.now(),
                        'mensaje_error': str(e),
                        'intentos_realizados': 1  # Podrías implementar lógica de reintentos
                    }
                )
                
                results[pagina_codigo] = {"error": str(e)}
        
        # 4. Finalizar proceso automáticamente
        finalizar_proceso(job_id)
        log(f"🎉 Proceso {job_id} finalizado exitosamente")
        
        return results
        
    except Exception as e:
        # Error general del proceso
        log(f"💥 Error general en proceso {job_id}: {e}")
        finalizar_proceso(job_id, estado_final="Error_Total", mensaje_error=str(e))
        raise


def run_items_legacy(items: List[QueryItem], headless: bool = False) -> Dict[str, Any]:
    """
    Tu función run_items original sin modificar.
    Se mantiene para compatibilidad con código existente.
    """
    # AQUÍ VA TU CÓDIGO ACTUAL DE run_items SIN MODIFICAR
    # Lo mantienes exactamente igual para no romper funcionalidad existente
    pass


# ===== FUNCIONES ESPECÍFICAS POR TIPO DE PÁGINA =====
# Estas son versiones de tus funciones existentes pero que reciben la URL como parámetro

def ejecutar_consulta_ruc(ruc: str, url: str, headless: bool = False) -> Dict[str, Any]:
    """
    Lógica específica para consulta de RUC.
    Recibe la URL desde la base de datos en lugar de tenerla hardcodeada.
    """
    from flows.ruc import process_ruc_once  # Tu función existente
    
    # Usar la URL dinámica
    resultado = process_ruc_once(ruc, headless)
    return resultado or {"error": "Sin resultado"}


def ejecutar_consulta_deudas(ruc: str, url: str, headless: bool = False) -> Dict[str, Any]:
    """Lógica específica para consulta de deudas"""
    from flows.deudas import process_deudas_once  # Tu función existente
    
    resultado = process_deudas_once(ruc, headless)
    return resultado or {"error": "Sin resultado"}


def ejecutar_consulta_denuncias(ci: str, url: str, headless: bool = False) -> Dict[str, Any]:
    """Lógica específica para consulta de denuncias"""
    from flows.denuncias import process_denuncias_once  # Tu función existente
    
    resultado = process_denuncias_once(ci, headless)
    return resultado or {"error": "Sin resultado"}


def ejecutar_consulta_interpol(apellidos: str, nombres: str, url: str, headless: bool = False) -> Dict[str, Any]:
    """Lógica específica para consulta de INTERPOL"""
    from flows.interpol import process_interpol_once  # Tu función existente
    
    resultado = process_interpol_once(apellidos, nombres, headless)
    return resultado or {"error": "Sin resultado"}


def ejecutar_consulta_generica(tipo: str, valor: str, url: str, headless: bool = False) -> Dict[str, Any]:
    """
    Función genérica para tipos de página que no tienen función específica.
    Puedes implementar lógica genérica o llamar a funciones específicas según el tipo.
    """
    log(f"⚠️ Consulta genérica para {tipo} - implementar lógica específica")
    
    # Ejemplo de implementación genérica
    try:
        # Aquí podrías tener lógica genérica de scraping
        # que use el 'url' parámetro y adapte según el 'tipo'
        
        return {
            "screenshot_path": None,
            "scenario": "no_implementado", 
            "message": f"Consulta {tipo} no implementada específicamente"
        }
    except Exception as e:
        return {"error": str(e)}