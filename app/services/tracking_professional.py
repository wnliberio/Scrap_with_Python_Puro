# app/services/tracking_professional.py - CÓDIGO COMPLETO CORREGIDO
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy import text, select, and_, func, desc
from sqlalchemy.orm import joinedload, selectinload, sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
import os

# CARGAR VARIABLES DE ENTORNO DESDE .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de sistema")
except Exception as e:
    print(f"⚠️ Error cargando .env: {e}")

# ===== CONFIGURACIÓN DE BASE DE DATOS PARA AZURE =====
try:
    # OPCIÓN 1: Importar engine existente (si está disponible)
    from app.db import engine
    print("✅ Usando engine existente del sistema")
except ImportError:
    try:
        # OPCIÓN 2: Importar desde dbb.py si existe  
        from app.dbb import engine
        print("✅ Usando engine desde dbb.py")
    except ImportError:
        # OPCIÓN 3: Construir para Azure MySQL con credenciales correctas
        def build_azure_database_url():
            # URL completa optimizada para Azure
            url = os.getenv("DATABASE_URL")
            if url and url.startswith("mysql"):
                return url
            
            # Construir desde componentes para Azure
            user = os.getenv("DB_USER", "administrador")
            password = os.getenv("DB_PASSWORD", "Mupi2024+11")
            host = os.getenv("DB_HOST", "asistentebase.mysql.database.azure.com")
            port = os.getenv("DB_PORT", "3306")
            database = os.getenv("DB_NAME", "asistentedb")
            
            # Escapar caracteres especiales en password (+ se convierte en %2B)
            import urllib.parse
            password_escaped = urllib.parse.quote_plus(password)
            
            return f"mysql+pymysql://{user}:{password_escaped}@{host}:{port}/{database}"

        DATABASE_URL = build_azure_database_url()
        print(f"🔗 Conectando a Azure MySQL: asistentebase.mysql.database.azure.com/asistentedb")
        
        # Engine con configuración para Azure MySQL
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True, 
            pool_recycle=280,
            connect_args={
                "ssl": {"ssl": True},  # Azure requiere SSL
                "charset": "utf8mb4"
            }
        )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@contextmanager
def get_session():
    """Context manager corregido para sesiones de BD"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# ===== FUNCIONES SIMPLIFICADAS (SIN ORM POR AHORA) =====

def get_paginas_activas() -> List[Dict[str, Any]]:
    """Obtiene todas las páginas disponibles para consulta ordenadas por display"""
    try:
        with get_session() as db:
            result = db.execute(text("""
                SELECT id, nombre, codigo, url, descripcion, orden_display 
                FROM de_paginas 
                WHERE activa = TRUE 
                ORDER BY orden_display, nombre
            """))
            
            paginas = []
            for row in result:
                paginas.append({
                    "id": row.id,
                    "nombre": row.nombre,
                    "codigo": row.codigo,
                    "url": row.url,
                    "descripcion": row.descripcion,
                    "orden_display": row.orden_display or 0
                })
            
            return paginas
            
    except Exception as e:
        print(f"Error obteniendo páginas: {e}")
        # Fallback con páginas hardcodeadas
        return [
            {"id": 1, "nombre": "SRI - RUC", "codigo": "ruc", "url": "https://srienlinea.sri.gob.ec/sri-en-linea/SriRucWeb/ConsultaRuc/Consultas/consultaRuc", "descripcion": "Consulta RUC", "orden_display": 1},
            {"id": 2, "nombre": "SRI - Deudas", "codigo": "deudas", "url": "https://srienlinea.sri.gob.ec/sri-en-linea/SriPagosWeb/ConsultaDeudasFirmesImpugnadas/Consultas/consultaDeudasFirmesImpugnadas", "descripcion": "Consulta Deudas", "orden_display": 2},
            {"id": 3, "nombre": "Fiscalía - Denuncias", "codigo": "denuncias", "url": "https://www.gestiondefiscalias.gob.ec/siaf/informacion/web/noticiasdelito/index.php", "descripcion": "Consulta Denuncias", "orden_display": 3}
        ]

def get_pagina_by_codigo(codigo: str) -> Optional[Dict[str, Any]]:
    """Obtiene una página específica por su código"""
    try:
        with get_session() as db:
            result = db.execute(text(
                "SELECT id, nombre, codigo, url, descripcion FROM de_paginas WHERE codigo = :codigo AND activa = TRUE"
            ), {"codigo": codigo})
            
            row = result.first()
            if not row:
                return None
                
            return {
                "id": row.id,
                "nombre": row.nombre,
                "codigo": row.codigo,
                "url": row.url,
                "descripcion": row.descripcion
            }
    except Exception as e:
        print(f"Error obteniendo página {codigo}: {e}")
        return None

def get_clientes_with_filters(estado: Optional[str] = None, fecha_desde: Optional[str] = None, 
                             fecha_hasta: Optional[str] = None, q: Optional[str] = None) -> List[Dict[str, Any]]:
    """Obtiene clientes con filtros y proceso activo si existe"""
    try:
        with get_session() as db:
            # Query base
            query = """
                SELECT c.*, p.id as proceso_id, p.job_id, p.estado as proceso_estado 
                FROM de_clientes c
                LEFT JOIN de_procesos p ON c.id = p.cliente_id 
                    AND p.estado IN ('Pendiente', 'En_Proceso')
                WHERE 1=1
            """
            params = {}
            
            # Aplicar filtros
            if estado and estado != "Todos":
                query += " AND c.estado = :estado"
                params["estado"] = estado
                
            if fecha_desde:
                query += " AND DATE(c.fecha_creacion) >= :fecha_desde"
                params["fecha_desde"] = fecha_desde
                
            if fecha_hasta:
                query += " AND DATE(c.fecha_creacion) <= :fecha_hasta"
                params["fecha_hasta"] = fecha_hasta
                
            if q and q.strip():
                query += " AND (c.nombre LIKE :q OR c.apellido LIKE :q OR c.ci LIKE :q OR c.ruc LIKE :q)"
                params["q"] = f"%{q.strip()}%"
            
            query += " ORDER BY c.fecha_creacion DESC LIMIT 100"
            
            result = db.execute(text(query), params)
            
            clientes = []
            for row in result:
                # Proceso activo si existe
                proceso_activo = None
                if row.proceso_id:
                    proceso_activo = {
                        "id": row.proceso_id,
                        "job_id": row.job_id,
                        "estado": row.proceso_estado
                    }
                
                clientes.append({
                    "id": row.id,
                    "nombre": row.nombre,
                    "apellido": row.apellido,
                    "ci": row.ci,
                    "ruc": row.ruc,
                    "tipo": row.tipo,
                    "monto": float(row.monto) if row.monto else None,
                    "fecha": row.fecha.isoformat() if row.fecha else None,
                    "estado": row.estado,
                    "fecha_creacion": row.fecha_creacion.isoformat() if row.fecha_creacion else None,
                    "proceso_activo": proceso_activo
                })
            
            return clientes
            
    except Exception as e:
        print(f"Error obteniendo clientes: {e}")
        return []

def update_cliente_estado(cliente_id: int, estado: str, mensaje_error: Optional[str] = None) -> bool:
    """Actualiza el estado de un cliente"""
    try:
        with get_session() as db:
            db.execute(text(
                "UPDATE de_clientes SET estado = :estado WHERE id = :cliente_id"
            ), {"estado": estado, "cliente_id": cliente_id})
            return True
    except Exception as e:
        print(f"Error actualizando cliente {cliente_id}: {e}")
        return False

def crear_proceso_completo(cliente_id: int, job_id: str, paginas_codigos: List[str], 
                          headless: bool = False, generate_report: bool = True) -> int:
    """Crea un proceso completo con todas sus consultas individuales Y ejecuta los flows"""
    try:
        with get_session() as db:
            # 1. Obtener datos del cliente SEPARADOS
            cliente_result = db.execute(text(
                "SELECT nombre, apellido, ci, ruc, tipo, monto, fecha FROM de_clientes WHERE id = :cliente_id"
            ), {"cliente_id": cliente_id})
            
            cliente_row = cliente_result.first()
            if not cliente_row:
                raise ValueError(f"Cliente {cliente_id} no encontrado")
            
            # Extraer campos individuales
            nombre = (cliente_row.nombre or "").strip()
            apellido = (cliente_row.apellido or "").strip()
            ci = (cliente_row.ci or "").strip()
            ruc = (cliente_row.ruc or "").strip()
            tipo = cliente_row.tipo
            monto = cliente_row.monto
            fecha = cliente_row.fecha
            
            print(f"📋 Datos del cliente separados:")
            print(f"   Nombre: '{nombre}', Apellido: '{apellido}'")
            print(f"   CI: '{ci}', RUC: '{ruc}'")
            print(f"   Tipo: '{tipo}', Monto: {monto}")
            
            # 2. Crear proceso
            proceso_result = db.execute(text("""
                INSERT INTO de_procesos (cliente_id, job_id, tipo_alerta, monto_usd, fecha_alerta, 
                                       estado, headless, generate_report, total_paginas_solicitadas, 
                                       fecha_creacion)
                VALUES (:cliente_id, :job_id, :tipo_alerta, :monto_usd, :fecha_alerta, 
                        'Pendiente', :headless, :generate_report, :total_paginas, NOW())
            """), {
                "cliente_id": cliente_id,
                "job_id": job_id,
                "tipo_alerta": tipo,
                "monto_usd": monto,
                "fecha_alerta": fecha,
                "headless": headless,
                "generate_report": generate_report,
                "total_paginas": len(paginas_codigos)
            })
            
            # Obtener ID del proceso creado
            proceso_id = proceso_result.lastrowid
            
            # 3. Crear consultas individuales
            for codigo in paginas_codigos:
                # Obtener página
                pagina_result = db.execute(text(
                    "SELECT id FROM de_paginas WHERE codigo = :codigo AND activa = TRUE"
                ), {"codigo": codigo})
                
                pagina_row = pagina_result.first()
                if pagina_row:
                    db.execute(text("""
                        INSERT INTO de_consultas (proceso_id, pagina_id, estado, max_intentos)
                        VALUES (:proceso_id, :pagina_id, 'Pendiente', 2)
                    """), {
                        "proceso_id": proceso_id,
                        "pagina_id": pagina_row.id
                    })
            
            # 4. Actualizar estado del cliente
            db.execute(text(
                "UPDATE de_clientes SET estado = 'Procesando' WHERE id = :cliente_id"
            ), {"cliente_id": cliente_id})
            
            print(f"✅ Proceso {proceso_id} creado para cliente {cliente_id} con {len(paginas_codigos)} consultas")
            
            # 5. NUEVO: Disparar el job usando campos separados
            try:
                from app.routers.consultas import _worker, ConsultasBody
                from app.models.schemas import QueryItem
                import threading
                
                # Construir items usando campos separados
                items = []
                
                for codigo in paginas_codigos:
                    print(f"🔍 Procesando página: {codigo}")
                    
                    if codigo == "google":
                        # Google requiere nombre completo
                        if nombre and apellido:
                            nombre_completo = f"{nombre} {apellido}"
                            items.append(QueryItem(tipo="google", valor=nombre_completo))
                            print(f"   ✅ Google: '{nombre_completo}'")
                        else:
                            print(f"   ❌ Google omitido: falta nombre o apellido")
                    
                    elif codigo == "ruc":
                        # RUC requiere RUC válido (13 dígitos)
                        if ruc and len(ruc) == 13 and ruc.isdigit():
                            items.append(QueryItem(tipo="ruc", valor=ruc))
                            print(f"   ✅ RUC: '{ruc}'")
                        else:
                            print(f"   ❌ RUC omitido: RUC inválido '{ruc}'")
                    
                    elif codigo == "deudas":
                        # Deudas requiere RUC válido (13 dígitos)
                        if ruc and len(ruc) == 13 and ruc.isdigit():
                            items.append(QueryItem(tipo="deudas", valor=ruc))
                            print(f"   ✅ Deudas: '{ruc}'")
                        else:
                            print(f"   ❌ Deudas omitido: RUC inválido '{ruc}'")
                    
                    elif codigo == "denuncias":
                        # Denuncias requiere nombre completo
                        if nombre and apellido:
                            nombre_completo = f"{nombre} {apellido}"
                            items.append(QueryItem(tipo="denuncias", valor=nombre_completo))
                            print(f"   ✅ Denuncias: '{nombre_completo}'")
                        else:
                            print(f"   ❌ Denuncias omitido: falta nombre o apellido")
                    
                    elif codigo == "interpol":
                        # INTERPOL requiere solo apellido
                        if apellido:
                            items.append(QueryItem(tipo="interpol", valor=apellido, apellidos=apellido))
                            print(f"   ✅ INTERPOL: apellido '{apellido}'")
                        else:
                            print(f"   ❌ INTERPOL omitido: falta apellido")
                    
                    elif codigo == "mercado_valores":
                        # Mercado de Valores requiere RUC válido (13 dígitos)
                        if ruc and len(ruc) == 13 and ruc.isdigit():
                            items.append(QueryItem(tipo="mercado_valores", valor=ruc))
                            print(f"   ✅ Mercado Valores: '{ruc}'")
                        else:
                            print(f"   ❌ Mercado Valores omitido: RUC inválido '{ruc}'")
                    
                    elif codigo == "contraloria":
                        # Contraloría requiere CI válida (10 dígitos)
                        if ci and len(ci) == 10 and ci.isdigit():
                            items.append(QueryItem(tipo="contraloria", valor=ci))
                            print(f"   ✅ Contraloría: '{ci}'")
                        else:
                            print(f"   ❌ Contraloría omitido: CI inválida '{ci}'")
                    
                    elif codigo == "supercias_persona":
                        # Supercias Persona requiere CI válida (10 dígitos)
                        if ci and len(ci) == 10 and ci.isdigit():
                            items.append(QueryItem(tipo="supercias_persona", valor=ci))
                            print(f"   ✅ Supercias Persona: '{ci}'")
                        else:
                            print(f"   ❌ Supercias Persona omitido: CI inválida '{ci}'")
                    
                    elif codigo == "predio_quito":
                        # Predio Quito requiere apellidos nombres (en ese orden)
                        if nombre and apellido:
                            apellidos_nombres = f"{apellido} {nombre}"
                            items.append(QueryItem(tipo="predio_quito", valor=apellidos_nombres))
                            print(f"   ✅ Predio Quito: '{apellidos_nombres}'")
                        else:
                            print(f"   ❌ Predio Quito omitido: falta nombre o apellido")
                    
                    elif codigo == "predio_manta":
                        # Predio Manta requiere nombres completos (asumo igual que Quito)
                        if nombre and apellido:
                            nombre_completo = f"{nombre} {apellido}"
                            items.append(QueryItem(tipo="predio_manta", valor=nombre_completo))
                            print(f"   ✅ Predio Manta: '{nombre_completo}'")
                        else:
                            print(f"   ❌ Predio Manta omitido: falta nombre o apellido")
                    
                    else:
                        print(f"   ❓ Tipo desconocido: {codigo}")
                
                if items:
                    # Crear el job body con metadatos separados
                    job_body = ConsultasBody(
                        items=items,
                        headless=headless,
                        generate_report=generate_report,
                        informe_meta={
                            "tipo_alerta": tipo,
                            "monto_usd": float(monto) if monto else None,
                            "fecha_alerta": fecha.isoformat() if fecha else None
                        }
                    )
                    
                    # Disparar el worker
                    print(f"🚀 Disparando worker para job {job_id} con {len(items)} items válidos")
                    t = threading.Thread(target=_worker, args=(job_id, job_body), daemon=True)
                    t.start()
                else:
                    print("⚠️ No se crearon items válidos, no se ejecutará el worker")
                    
            except Exception as e:
                print(f"❌ Error disparando worker: {e}")
                import traceback
                traceback.print_exc()
                # No fallar el proceso por esto, solo logearlo
            
            return proceso_id
            
    except Exception as e:
        print(f"Error creando proceso: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    

# ===== FUNCIONES STUB (PARA IMPLEMENTAR DESPUÉS) =====

def get_proceso_by_job_id(job_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un proceso completo por job_id - STUB"""
    # TODO: Implementar después
    return None

def get_detalles_cliente_modal(cliente_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene detalles completos de un cliente para el modal - STUB"""
    # TODO: Implementar después
    return None

def iniciar_proceso(proceso_id: int) -> bool:
    """Marca un proceso como iniciado - STUB"""
    # TODO: Implementar después
    return True

def finalizar_proceso(job_id: str, estado_final: Optional[str] = None, 
                     mensaje_error: Optional[str] = None) -> bool:
    """Finaliza un proceso - STUB"""
    # TODO: Implementar después
    return True

def actualizar_consulta_por_codigo(proceso_id: int, pagina_codigo: str, 
                                  datos_actualizacion: Dict[str, Any]) -> bool:
    """Actualiza una consulta específica - STUB"""
    # TODO: Implementar después
    return True