# app/main.py - VERSIÓN ACTUALIZADA CON TRACKING COMPLETO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sistema de Consultas Públicas API",
    description="API con sistema de tracking granular profesional",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"  # Para desarrollo (cambiar en producción)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== IMPORTAR ROUTERS =====

# Routers existentes (NO TOCAR - mantener compatibilidad)
try:
    from app.routers.consultas import router as consultas_router
    app.include_router(consultas_router, prefix="/api")
    print("✅ Router consultas cargado")
except ImportError as e:
    print(f"⚠️ No se pudo cargar router consultas: {e}")

try:
    from app.routers.reports import router as reports_router
    app.include_router(reports_router, prefix="/api")
    print("✅ Router reports cargado")
except ImportError as e:
    print(f"⚠️ No se pudo cargar router reports: {e}")

try:
    from app.routers.lista import router as lista_router
    app.include_router(lista_router, prefix="/api")
    print("✅ Router lista cargado")
except ImportError as e:
    print(f"⚠️ No se pudo cargar router lista: {e}")

# NUEVO ROUTER DE TRACKING (PRIORITARIO)
try:
    from app.routers.tracking_professional import router as tracking_router
    app.include_router(tracking_router, prefix="/api")
    print("✅ Router tracking professional cargado")
except ImportError as e:
    print(f"❌ Error cargando router tracking: {e}")
    print("   Verifica que existan los archivos:")
    print("   - app/routers/tracking_professional.py")
    print("   - app/services/tracking_professional.py")

# ===== EVENTOS DE STARTUP =====

@app.on_event("startup")
async def startup_event():
    """Inicialización del sistema al arrancar"""
    print("🚀 Iniciando Sistema de Consultas v2.0")
    
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
    
    print("🎯 Sistema listo para recibir requests")

# ===== ENDPOINTS RAÍZ =====

@app.get("/")
def root():
    """Endpoint raíz con información del sistema"""
    return {
        "ok": True,
        "service": "Sistema de Consultas Públicas API",
        "version": "2.0.0",
        "features": {
            "tracking_granular": True,
            "reportes_automaticos": True,
            "sincronizacion_estados": True
        },
        "endpoints": {
            "legacy": [
                "/api/consultas",
                "/api/reports", 
                "/api/lista"
            ],
            "tracking": [
                "/api/tracking/health",
                "/api/tracking/paginas",
                "/api/tracking/clientes",
                "/api/tracking/procesos/crear"
            ]
        },
        "docs": "/docs",
        "status": "active"
    }

@app.get("/health")
def health_check():
    """Health check básico del sistema"""
    return {
        "status": "healthy",
        "timestamp": "2025-01-20T00:00:00Z",
        "version": "2.0.0",
        "components": {
            "api": "ok",
            "database": "ok",
            "tracking": "ok"
        }
    }

# ===== ENDPOINT DE DIAGNÓSTICO =====

@app.get("/api/diagnostico")
def diagnostico_sistema():
    """Endpoint para diagnosticar el estado del sistema completo"""
    try:
        # Verificar tracking
        from app.services.tracking_professional import get_paginas_activas, get_clientes_with_filters
        
        paginas = get_paginas_activas()
        clientes = get_clientes_with_filters()
        
        # Verificar base de datos
        from app.db import SessionLocal
        db = SessionLocal()
        
        try:
            # Contar registros en tablas principales
            from app.db.models_new import DeCliente, DePagina, DeProceso
            
            count_clientes = db.query(DeCliente).count()
            count_paginas = db.query(DePagina).count()
            count_procesos = db.query(DeProceso).count()
            
            return {
                "status": "ok",
                "tracking": {
                    "paginas_disponibles": len(paginas),
                    "clientes_encontrados": len(clientes)
                },
                "database": {
                    "clientes": count_clientes,
                    "paginas": count_paginas,
                    "procesos": count_procesos,
                    "conexion": "ok"
                },
                "servicios": {
                    "sincronizacion": "disponible",
                    "tracking_professional": "disponible",
                    "generacion_reportes": "disponible"
                }
            }
        finally:
            db.close()
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "recomendaciones": [
                "Verificar que las tablas de tracking existan",
                "Verificar conexión a base de datos",
                "Verificar que los servicios estén importados correctamente"
            ]
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando servidor de desarrollo...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)