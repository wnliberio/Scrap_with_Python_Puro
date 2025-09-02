# app/db/__init__.py
from __future__ import annotations

import os
import re
import json
import urllib.parse as up
from typing import Dict, Any, Optional, List

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, date

# --- Zona horaria Ecuador (para created_at) ---
try:
    import pytz
    ECUADOR_TZ = pytz.timezone("America/Guayaquil")
    def get_ec_time() -> datetime:
        return datetime.now(ECUADOR_TZ)
except Exception:
    # Fallback si no hay pytz
    def get_ec_time() -> datetime:
        return datetime.now()

# ---------------------------------------------------------------------
# URL de conexión (acepta JDBC en .env: URL=jdbc:mysql://host:3306/db)
# ---------------------------------------------------------------------
def _build_sqlalchemy_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("URL") or ""
    if url.startswith("jdbc:mysql://"):
        # jdbc:mysql://host:port/db?params
        m = re.match(r"^jdbc:mysql://([^:/]+)(?::(\d+))?/([^?]+)(\?.*)?$", url)
        if m:
            host, port, db, qs = m.groups()
            port = port or "3306"
            qs = qs or ""

            user = os.getenv("DB_USER") or ""
            pwd  = os.getenv("DB_PASSWORD") or ""
            auth = f"{up.quote(user)}:{up.quote(pwd)}@" if (user or pwd) else ""

            # asegurar charset
            if "charset=" not in qs:
                qs = (qs + "&" if qs else "?") + "charset=utf8mb4"
            # Azure requiere transporte seguro
            if "ssl=" not in qs and "sslmode=" not in qs:
                qs = (qs + "&" if qs else "?") + "ssl=true"

            return f"mysql+pymysql://{auth}{host}:{port}/{db}{qs}"

    if url:
        return url  # ya viene en formato SQLAlchemy

    # Construcción por componentes si no hay URL/JDBC
    user = os.getenv("DB_USER", "")
    pwd  = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "test")
    auth = f"{up.quote(user)}:{up.quote(pwd)}@" if (user or pwd) else ""
    return f"mysql+pymysql://{auth}{host}:{port}/{name}?charset=utf8mb4&ssl=true"

def _connect_args_for_mysql(url: str) -> Dict[str, Any]:
    # Azure MySQL con require_secure_transport=ON necesita TLS
    if url.startswith("mysql+pymysql://"):
        return {"ssl": {"ssl": True}}
    return {}

# --- Engine / Session / Base -------------------------------------------------
DATABASE_URL = _build_sqlalchemy_url()
CONNECT_ARGS = _connect_args_for_mysql(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_recycle=280,
    connect_args=CONNECT_ARGS,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# --- Modelo ORM alineado a tu tabla existente -------------------------------
class Report(Base):
    __tablename__ = "reports"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    job_id        = Column(String(64), nullable=False)
    tipo_alerta   = Column(String(200), nullable=False)
    monto_usd     = Column(Float, nullable=True)
    fecha_alerta  = Column(Date, nullable=True)
    file_path     = Column(String(600), nullable=False)   # ruta al DOCX
    data_snapshot = Column(Text, nullable=False)          # JSON (resultados/meta)
    created_at    = Column(DateTime, nullable=False, default=get_ec_time)

# --- Helpers para tabla ------------------------------------------------------
def create_tables() -> None:
    Base.metadata.create_all(engine)

def list_reports(fecha_desde: Optional[str], fecha_hasta: Optional[str]) -> List[Dict[str, Any]]:
    """
    Lista por rango en created_at. fechas en formato YYYY-MM-DD (opcionales).
    """
    sess = SessionLocal()
    try:
        q = sess.query(Report)
        if fecha_desde:
            q = q.filter(Report.created_at >= f"{fecha_desde} 00:00:00")
        if fecha_hasta:
            q = q.filter(Report.created_at <= f"{fecha_hasta} 23:59:59")
        q = q.order_by(Report.created_at.desc())
        out: List[Dict[str, Any]] = []
        for r in q.all():
            out.append({
                "id": r.id,
                "job_id": r.job_id,
                "tipo_alerta": r.tipo_alerta,
                "monto_usd": r.monto_usd,
                "fecha_alerta": r.fecha_alerta.isoformat() if r.fecha_alerta else None,
                "file_path": r.file_path,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return out
    finally:
        sess.close()

def get_report_path(report_id: int) -> Optional[str]:
    sess = SessionLocal()
    try:
        r = sess.query(Report).filter(Report.id == report_id).first()
        return r.file_path if r else None
    finally:
        sess.close()

__all__ = [
    "engine", "SessionLocal", "Base",
    "Report",
    "create_tables", "list_reports", "get_report_path",
    "DATABASE_URL",
]
