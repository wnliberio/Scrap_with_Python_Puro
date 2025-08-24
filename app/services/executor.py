from typing import Dict, Any, List
from time import sleep
from core.utils.log import log

from flows.ruc import process_ruc
from flows.deudas import process_deudas
from flows.denuncias import process_denuncias
from flows.interpol import run_interpol_search  # 👈 nuevo

from app.models.schemas import QueryItem
from core.config import INTER_ITEM_DELAY_SECONDS


def _parse_interpol_valor(valor: str) -> (str, str):
    """
    Acepta:
      - 'APELLIDOS|NOMBRES'
      - 'APELLIDOS|'
      - '|NOMBRES'
      - 'APELLIDOS' (sin '|')
    Retorna (apellidos, nombres) ya normalizados.
    """
    v = (valor or "").strip()
    if "|" in v:
        a, b = v.split("|", 1)
        return " ".join(a.split()), " ".join((b or "").split())
    return " ".join(v.split()), ""


def run_items(items: List[QueryItem], headless: bool = False) -> Dict[str, Any]:
    """
    Ejecuta en SECUENCIA solo los items recibidos.
    Retorna dict tipo -> payload (p.ej. {"ruc": {...}, "deudas": {...}, "denuncias": {...}, "interpol": {...}})
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

        elif tipo == "interpol":  # 👈 nuevo caso
            apellidos, nombres = _parse_interpol_valor(valor)
            res = run_interpol_search(apellidos_o_full=apellidos, nombres=nombres, headless=headless)
            results["interpol"] = res

        else:
            results[tipo] = {"error": f"Tipo no soportado: {tipo}"}

        # Espera entre items
        if index < len(items):
            log(f"⏳ Esperando {INTER_ITEM_DELAY_SECONDS}s antes del siguiente item…")
            sleep(INTER_ITEM_DELAY_SECONDS)

    return results
