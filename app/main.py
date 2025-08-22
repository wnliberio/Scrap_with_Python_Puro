# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.consultas import router as consultas_router

app = FastAPI(title="Consultas Públicas API")

# Ajusta los orígenes a tu Front (puedes dejar * en local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consultas_router, prefix="/api")

@app.get("/")
def root():
    return {"ok": True, "service": "Consultas Públicas API"}
