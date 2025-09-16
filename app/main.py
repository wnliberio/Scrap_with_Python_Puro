# app/main.py - ACTUALIZADO CON TRACKING
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Tus routers existentes (NO TOCAR)
from app.routers.consultas import router as consultas_router
from app.routers.reports import router as reports_router
from app.routers.lista import router as lista_router

# AGREGAR ESTA LÍNEA - NUEVO ROUTER DE TRACKING:
from app.routers.tracking_professional import router as tracking_router

app = FastAPI(title="Consultas Públicas API - Con Tracking")
from app.routers.tracking_professional import router as tracking_router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tracking_router, prefix="/api")
# Crear tablas al inicio
@app.on_event("startup")
async def create_tables():
    """Crear tablas de tracking al iniciar"""
    try:
        # Solo imprimir mensaje por ahora
        print("✅ Sistema de tracking inicializado")
    except Exception as e:
        print(f"⚠️ Error en startup: {e}")

# Routers existentes (NO TOCAR)
app.include_router(consultas_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(lista_router, prefix="/api")

# AGREGAR ESTA LÍNEA - INCLUIR EL ROUTER DE TRACKING:
app.include_router(tracking_router, prefix="/api")

@app.get("/")
def root():
    return {
        "ok": True, 
        "service": "Consultas Públicas API", 
        "tracking": "disponible en /api/tracking/*",
        "endpoints": [
            "/api/consultas",
            "/api/reports", 
            "/api/lista",
            "/api/tracking"
        ]
    }