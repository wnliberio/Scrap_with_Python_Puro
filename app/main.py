# app/main.py - VERSIÓN CON DAEMON AUTOMÁTICO

# ⚠️ CRÍTICO: Cargar .env ANTES de cualquier otra importación
from app.load_env import verificar_credenciales

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema de Consultas Función Judicial",
    description="Sistema automatizado con procesamiento en background",
    version="3.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"  # Para desarrollo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== IMPORTAR ROUTERS =====

# Router de Tracking (principal)
try:
    from app.routers.tracking_professional import router as tracking_router
    app.include_router(tracking_router, prefix="/api")
    print("✅ Router tracking professional cargado")
except ImportError as e:
    print(f"❌ Error cargando router tracking: {e}")

# Router del Daemon (NUEVO)
try:
    from app.routers.daemon import router as daemon_router
    app.include_router(daemon_router, prefix="/api")
    print("✅ Router daemon cargado")
except ImportError as e:
    print(f"❌ Error cargando router daemon: {e}")

# Router de Reports (si existe)
try:
    from app.routers.reports import router as reports_router
    app.include_router(reports_router, prefix="/api")
    print("✅ Router reports cargado")
except ImportError as e:
    print(f"⚠️ Router reports no disponible: {e}")

# ===== EVENTOS DE STARTUP =====

@app.on_event("startup")
async def startup_event():
    """Inicialización del sistema al arrancar"""
    print("🚀 Iniciando Sistema de Consultas v3.0")
    
    # Verificar conexión a base de datos
    try:
        from app.db import engine
        print("✅ Conexión a base de datos verificada")
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
    
    # Verificar tablas de tracking
    try:
        from app.services.tracking_professional import get_paginas_activas
        paginas = get_paginas_activas()
        print(f"✅ Sistema de tracking iniciado - {len(paginas)} páginas disponibles")
    except Exception as e:
        print(f"⚠️ Sistema de tracking no disponible: {e}")
    
    # Verificar daemon
    try:
        from app.services.daemon_procesador import obtener_estado_daemon
        estado = obtener_estado_daemon()
        print(f"✅ Daemon disponible - Estado: {'Running' if estado['running'] else 'Stopped'}")
    except Exception as e:
        print(f"⚠️ Daemon no disponible: {e}")
    
    print("🎯 Sistema listo para recibir requests")
    print("\n" + "="*60)
    print("📌 ENDPOINTS IMPORTANTES:")
    print("   POST /api/daemon/iniciar   - Iniciar procesamiento automático")
    print("   POST /api/daemon/detener   - Detener procesamiento")
    print("   GET  /api/daemon/estado    - Ver estado del daemon")
    print("   GET  /api/tracking/clientes - Ver clientes (con filtros)")
    print("="*60 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar el sistema"""
    print("🛑 Cerrando sistema...")
    
    # Detener daemon si está corriendo
    try:
        from app.services.daemon_procesador import detener_daemon, obtener_estado_daemon
        estado = obtener_estado_daemon()
        if estado.get('running'):
            print("⏹️  Deteniendo daemon...")
            detener_daemon()
            print("✅ Daemon detenido")
    except Exception as e:
        print(f"⚠️ Error deteniendo daemon: {e}")
    
    print("👋 Sistema cerrado")

# ===== ENDPOINTS RAÍZ =====

@app.get("/")
def root():
    """Endpoint raíz con información del sistema"""
    return {
        "ok": True,
        "service": "Sistema de Consultas Función Judicial",
        "version": "3.0.0",
        "features": {
            "tracking_granular": True,
            "procesamiento_automatico": True,
            "daemon_controlable": True,
            "solo_funcion_judicial": True
        },
        "endpoints": {
            "daemon": [
                "/api/daemon/iniciar",
                "/api/daemon/detener",
                "/api/daemon/estado"
            ],
            "tracking": [
                "/api/tracking/health",
                "/api/tracking/paginas",
                "/api/tracking/clientes"
            ]
        },
        "docs": "/docs",
        "status": "active"
    }

@app.get("/health")
def health_check():
    """Health check completo del sistema"""
    health_status = {
        "status": "healthy",
        "timestamp": "2025-01-20T00:00:00Z",
        "version": "3.0.0",
        "components": {}
    }
    
    # Verificar BD
    try:
        from app.db import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["components"]["database"] = "ok"
    except Exception as e:
        health_status["components"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Verificar tracking
    try:
        from app.services.tracking_professional import get_paginas_activas
        paginas = get_paginas_activas()
        health_status["components"]["tracking"] = f"ok ({len(paginas)} páginas)"
    except Exception as e:
        health_status["components"]["tracking"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Verificar daemon
    try:
        from app.services.daemon_procesador import obtener_estado_daemon
        estado = obtener_estado_daemon()
        health_status["components"]["daemon"] = "running" if estado["running"] else "stopped"
    except Exception as e:
        health_status["components"]["daemon"] = f"error: {str(e)}"
    
    return health_status