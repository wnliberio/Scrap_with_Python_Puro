# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.consultas import router as consultas_router
from app.routers.reports import router as reports_router  # <-- asegura que exista este router

app = FastAPI(title="Consultas Públicas API")

# Ajusta según tu front (para local, * está ok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Montamos ambos routers con prefijo /api (ruta oficial) ----
app.include_router(consultas_router, prefix="/api")
app.include_router(reports_router,   prefix="/api")

# ---- (Opcional) Soporte sin prefijo, por si el front trae BASE sin /api ----
# Esto permite que funcionen /consultas y /reports también.
app.include_router(consultas_router)   # sin prefijo
app.include_router(reports_router)     # sin prefijo

@app.get("/")
def root():
    return {"ok": True, "service": "Consultas Públicas API"}

@app.get("/health")
def health():
    return {"status": "ok"}
