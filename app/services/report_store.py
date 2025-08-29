# app/services/report_store.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Dict

from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal, Base, engine
from app.db.models import Report  # asegúrate que existe el modelo Report con JSON, etc.

# Asegura que la metadata esté creada (por si alguien importa este módulo sin pasar por app.main)
Base.metadata.create_all(bind=engine)


def persist_report(
    *,
    job_id: str,
    tipo_alerta: Optional[str] = None,
    monto_usd: Optional[float] = None,
    fecha_alerta: Optional[str] = None,   # YYYY-MM-DD
    file_path: Optional[str] = None,      # alias preferido
    report_path: Optional[str] = None,    # alias alterno (si te llega con este nombre)
    data_snapshot: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Inserta un registro en la tabla 'reports' y retorna su ID.

    NOTA: Usa un manejo de sesión explícito (no generator) para evitar:
          "'generator' object has no attribute 'rollback'".
    """
    # Normalizar la ruta (aceptar file_path o report_path)
    final_path = file_path or report_path

    # Parsear fecha_alerta a date si viene como string
    fecha_dt = None
    if fecha_alerta:
        try:
            # Intentar yyyy-mm-dd (formato típico)
            fecha_dt = datetime.strptime(fecha_alerta, "%Y-%m-%d").date()
        except Exception:
            # Si falla, lo dejamos en None y guardamos el string original en snapshot
            if data_snapshot is None:
                data_snapshot = {}
            data_snapshot["_fecha_alerta_raw"] = fecha_alerta

    session = SessionLocal()
    try:
        rec = Report(
            job_id=job_id,
            tipo_alerta=tipo_alerta,
            monto_usd=monto_usd,
            fecha_alerta=fecha_dt,
            file_path=final_path,           # en tu modelo puede llamarse file_path o report_path; usa el campo correcto
            data_snapshot=data_snapshot or {},
        )
        session.add(rec)
        session.commit()
        session.refresh(rec)
        return rec.id
    except SQLAlchemyError as e:
        session.rollback()
        # Re-lanzamos con más contexto (útil para el log del router)
        raise RuntimeError(f"DB error while persisting report: {e}") from e
    finally:
        session.close()
