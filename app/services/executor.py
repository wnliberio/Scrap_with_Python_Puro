# app/services/executor.py
from typing import Dict, Any, List
from time import sleep
from core.utils.log import log
from flows.ruc import process_ruc
from flows.deudas import process_deudas
from flows.denuncias import process_denuncias
from app.models.schemas import QueryItem
from core.config import INTER_ITEM_DELAY_SECONDS

def run_items(items: List[QueryItem], headless: bool = False) -> Dict[str, Any]:
    """
    Ejecuta en SECUENCIA solo los items recibidos.
    Retorna dict tipo -> payload (p.ej. {"ruc": {...}, "deudas": {...}, "denuncias": {...}})
    """
    results: Dict[str, Any] = {}
    for index, it in enumerate(items, start=1):
        tipo = it.tipo.lower()
        valor = it.valor.strip()
        log(f"⚙️ Ejecutando item {index}/{len(items)}: {tipo} → {valor}")

        if tipo == "ruc":
            res = process_ruc(valor, headless=headless)
            results["ruc"] = res
        elif tipo == "deudas":
            res = process_deudas(valor, headless=headless)
            results["deudas"] = res
        elif tipo == "denuncias":
            res = process_denuncias(valor, headless=headless)
            results["denuncias"] = res
        else:
            results[tipo] = {"error": f"Tipo no soportado: {tipo}"}

        # Espera entre items
        if index < len(items):
            log(f"⏳ Esperando {INTER_ITEM_DELAY_SECONDS}s antes del siguiente item…")
            sleep(INTER_ITEM_DELAY_SECONDS)

    return results
