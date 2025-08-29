# app/db.py
import os
import json
import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, quote_plus

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Date, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# -------------------------
# Helpers de entorno
# -------------------------

def _as_bool(v: Optional[str], default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def _jdbc_to_sqlalchemy_url(jdbc_url: str, user_env: Optional[str], pass_env: Optional[str]) -> str:
    """
    Convierte:
      jdbc:mysql://host:port/dbname
    a:
      mysql+pymysql://user:pass@host:port/dbname?charset=utf8mb4

    Si la URL **JDBC** NO trae credenciales, usa DB_USER/DB_PASSWORD del entorno.
    Si vinieran embebidas (raro en JDBC), también las respeta.
    """
    if not jdbc_url.startswith("jdbc:"):
        raise ValueError("La URL indicada no parece JDBC (debería iniciar con 'jdbc:').")

    # Quitamos el prefijo 'jdbc:' para que urlparse entienda el esquema mysql://
    parsed = urlparse(jdbc_url[len("jdbc:"):])  # ej. mysql://host:3306/db
    if parsed.scheme != "mysql":
        raise ValueError("Solo se soporta esquema 'mysql' en la URL JDBC.")

    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    dbname = (parsed.path or "/").lstrip("/") or ""

    # Credenciales: primero intentamos desde la URL, si no, desde env
    user = parsed.username or user_env
    pwd = parsed.password or pass_env
    if not user or not pwd:
        raise ValueError("Faltan credenciales: define DB_USER y DB_PASSWORD (o inclúyelas en la URL).")

    # Escapar credenciales por seguridad (caracteres especiales)
    user_q = quote_plus(user)
    pwd_q = quote_plus(pwd)

    return f"mysql+pymysql://{user_q}:{pwd_q}@{host}:{port}/{dbname}?charset=utf8mb4"

def _build_database_url() -> str:
    """
    Prioridades:
      1) URL o JDBC_URL (formato JDBC)  -> convertir a SQLAlchemy
      2) Variables separadas DB_*       -> armar SQLAlchemy
      3) DATABASE_URL (fallback)
    """
    jdbc = os.getenv("URL") or os.getenv("JDBC_URL")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")

    if jdbc:
        return _jdbc_to_sqlalchemy_url(jdbc, db_user, db_pass)

    # Variables separadas
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    if all([db_user, db_pass, db_host, db_port, db_name]):
        return f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}?charset=utf8mb4&ssl_ca=./ca-cert.pem&ssl_disabled=false"

    # Fallback a cadena completa
    return os.getenv("DATABASE_URL", "")

DATABASE_URL = _build_database_url()

# Pool y logging opcional
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_ECHO = _as_bool(os.getenv("DB_ECHO"), False)

# SSL (Azure MySQL suele requerirlo)
def _infer_azure(url: str) -> bool:
    return "database.azure.com" in url or (os.getenv("DB_HOST") or "").endswith("database.azure.com")

DB_SSL = _as_bool(os.getenv("DB_SSL"), default=_infer_azure(DATABASE_URL))

# -------------------------
# Engine y sesión
# -------------------------

Base = declarative_base()

_connect_args: Dict[str, Any] = {}
if DATABASE_URL.startswith("mysql+pymysql"):
    if DB_SSL:
        # Usar CA bundle de certifi si está disponible
        try:
            import certifi  # pip install certifi
            _connect_args["ssl"] = {"ca": certifi.where()}
        except Exception:
            # Si no hay certifi, que el driver negocie; si el proveedor obliga CA explícita,
            # instala certifi o pasa tu CA manualmente
            pass

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada. Define URL (JDBC) o DB_* en .env")

_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=DB_ECHO,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=_engine)

# -------------------------
# Modelo
# -------------------------

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tipo_alerta = Column(String(200), nullable=False)
    monto_usd = Column(Float, nullable=True)
    fecha_alerta = Column(Date, nullable=True)

    report_path = Column(String(600), nullable=False)  # ruta al .docx final
    data_json = Column(Text, nullable=False)          # JSON con resultados y metadatos

# -------------------------
# API de persistencia
# -------------------------

def create_tables():
    Base.metadata.create_all(_engine)

def get_session():
    return SessionLocal()

def save_report(meta: Dict[str, Any], report_path: str, data: Dict[str, Any]) -> int:
    """
    Inserta un registro en 'reports' y retorna su ID.
    meta = {"tipo_alerta": str, "monto_usd": float|None, "fecha_alerta": "YYYY-MM-DD"|date|None}
    """
    sess = get_session()
    try:
        fecha = meta.get("fecha_alerta")
        if isinstance(fecha, str):
            try:
                fecha = datetime.date.fromisoformat(fecha)
            except Exception:
                fecha = None

        r = Report(
            tipo_alerta=(meta or {}).get("tipo_alerta", "Alerta"),
            monto_usd=(meta or {}).get("monto_usd", None),
            fecha_alerta=fecha,
            report_path=report_path,
            data_json=json.dumps(data or {}, ensure_ascii=False),
        )
        sess.add(r)
        sess.commit()
        sess.refresh(r)
        return r.id
    finally:
        sess.close()

def list_reports(fecha_desde: Optional[str], fecha_hasta: Optional[str]) -> List[Dict[str, Any]]:
    """
    Lista de reportes por rango en created_at (YYYY-MM-DD).
    """
    sess = get_session()
    try:
        q = sess.query(Report)
        if fecha_desde:
            q = q.filter(Report.created_at >= f"{fecha_desde} 00:00:00")
        if fecha_hasta:
            q = q.filter(Report.created_at <= f"{fecha_hasta} 23:59:59")
        q = q.order_by(Report.created_at.desc())
        rows = q.all()
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "tipo_alerta": r.tipo_alerta,
                "monto_usd": r.monto_usd,
                "fecha_alerta": r.fecha_alerta.isoformat() if r.fecha_alerta else None,
                "report_path": r.report_path,
            })
        return out
    finally:
        sess.close()

def get_report_path(report_id: int) -> Optional[str]:
    sess = get_session()
    try:
        r = sess.query(Report).filter(Report.id == report_id).first()
        return r.report_path if r else None
    finally:
        sess.close()
