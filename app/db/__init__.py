# app/db/__init__.py - VERSIÓN CON CARGA AUTOMÁTICA DE .env
from __future__ import annotations

import os
import re
import urllib.parse as up
from typing import Dict, Any
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ⚠️ ASEGURAR QUE EL .env SE CARGUE
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)  # No sobrescribir si ya está cargado
except ImportError:
    print("⚠️ python-dotenv no instalado. Variables de entorno podrían no cargarse.")
except Exception as e:
    print(f"⚠️ Error cargando .env: {e}")

# --- Zona horaria Ecuador (para created_at) ---
try:
    import pytz
    ECUADOR_TZ = pytz.timezone("America/Guayaquil")
    from datetime import datetime
    def get_ec_time() -> datetime:
        return datetime.now(ECUADOR_TZ)
except Exception:
    from datetime import datetime
    def get_ec_time() -> datetime:
        return datetime.now()

# ---------------------------------------------------------------------
# URL de conexión (acepta JDBC en .env: URL=jdbc:mysql://host:3306/db)
# ---------------------------------------------------------------------
def _build_sqlalchemy_url() -> str:
    """
    Construye la URL de SQLAlchemy desde variables de entorno.
    Soporta:
    1. DATABASE_URL directamente
    2. URL en formato JDBC (jdbc:mysql://...)
    3. Variables separadas (DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, DB_PORT)
    """
    # OPCIÓN 1: DATABASE_URL ya en formato SQLAlchemy
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("mysql+pymysql://"):
        return database_url
    
    # OPCIÓN 2: URL en formato JDBC
    url = os.getenv("URL")
    if url and url.startswith("jdbc:mysql://"):
        # jdbc:mysql://host:port/db?params
        m = re.match(r"^jdbc:mysql://([^:/]+)(?::(\d+))?/([^?]+)(\?.*)?$", url)
        if m:
            host, port, db, qs = m.groups()
            port = port or "3306"
            qs = qs or ""

            user = os.getenv("DB_USER") or ""
            pwd  = os.getenv("DB_PASSWORD") or ""
            
            if not user or not pwd:
                raise RuntimeError(
                    "⚠️ ERROR: DB_USER y DB_PASSWORD son requeridos para URL JDBC.\n"
                    "Verifica que estén en tu archivo .env"
                )
            
            auth = f"{up.quote(user)}:{up.quote(pwd)}@"

            # Asegurar charset
            if "charset=" not in qs:
                qs = (qs + "&" if qs else "?") + "charset=utf8mb4"
            
            return f"mysql+pymysql://{auth}{host}:{port}/{db}{qs}"
    
    # OPCIÓN 3: Variables separadas
    user = os.getenv("DB_USER")
    pwd  = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME")
    
    # Validar que existan las credenciales mínimas
    if not user or not pwd or not name:
        error_msg = (
            "⚠️ ERROR: Credenciales de base de datos incompletas.\n"
            "Verifica que tu archivo .env contenga:\n"
            f"  - DB_USER: {'✅' if user else '❌ FALTANTE'}\n"
            f"  - DB_PASSWORD: {'✅' if pwd else '❌ FALTANTE'}\n"
            f"  - DB_HOST: {host}\n"
            f"  - DB_PORT: {port}\n"
            f"  - DB_NAME: {'✅' if name else '❌ FALTANTE'}\n"
        )
        raise RuntimeError(error_msg)
    
    auth = f"{up.quote(user)}:{up.quote(pwd)}@"
    return f"mysql+pymysql://{auth}{host}:{port}/{name}?charset=utf8mb4"


def _connect_args_for_mysql(url: str) -> Dict[str, Any]:
    """
    Configuración SSL para Azure MySQL si es necesario.
    """
    if url.startswith("mysql+pymysql://"):
        # Azure MySQL requiere SSL
        try:
            import certifi
            return {"ssl": {"ca": certifi.where()}}
        except ImportError:
            # Fallback sin verificación de certificado
            return {"ssl": {"ssl": True}}
    return {}


# --- Engine / Session / Base -------------------------------------------------
try:
    DATABASE_URL = _build_sqlalchemy_url()
    CONNECT_ARGS = _connect_args_for_mysql(DATABASE_URL)
    
    engine = create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
        pool_recycle=280,
        connect_args=CONNECT_ARGS,
        echo=False  # Cambiar a True para debugging SQL
    )
    
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base = declarative_base()
    
    print("✅ Engine de base de datos creado correctamente")
    
except Exception as e:
    print(f"❌ ERROR CRÍTICO creando engine de BD: {e}")
    print("\n📋 CHECKLIST DE SOLUCIÓN:")
    print("1. ¿Existe el archivo .env en la raíz del proyecto?")
    print("2. ¿python-dotenv está instalado? (pip install python-dotenv)")
    print("3. ¿Las variables DB_USER, DB_PASSWORD, DB_NAME están en .env?")
    print("4. ¿El servidor MySQL está corriendo?")
    raise


# --- Dependency para FastAPI -------------------------------------------------
def get_db():
    """
    Dependency para FastAPI que provee una sesión de BD.
    
    Uso:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Función de testing ------------------------------------------------------
def test_connection():
    """
    Prueba la conexión a la base de datos.
    Retorna True si conecta, False si falla.
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        print("✅ Conexión a base de datos verificada")
        return True
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        return False


# --- Exportaciones -----------------------------------------------------------
__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "test_connection",
    "get_ec_time"
]