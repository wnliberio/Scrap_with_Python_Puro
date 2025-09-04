# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.consultas import router as consultas_router
from app.routers.reports import router as reports_router
from app.routers.lista import router as lista_router  # <-- NUEVO

app = FastAPI(title="Consultas Públicas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(consultas_router, prefix="/api")
app.include_router(reports_router,   prefix="/api")
app.include_router(lista_router,     prefix="/api")  # <-- NUEVO

@app.get("/")
def root():
    return {"ok": True, "service": "Consultas Públicas API"}
