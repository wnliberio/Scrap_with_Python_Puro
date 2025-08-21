# main.py
import argparse, json
from flows.ruc import process_ruc
from core.utils.log import log
from core.utils.tee import start_tee, stop_tee
from core.config import LOG_FILE

def main():
    ap = argparse.ArgumentParser(description="Consulta RUC (SRI) con captura final de pantalla.")
    ap.add_argument("--ruc", nargs="+", help="Uno o más RUC a consultar (se procesan secuencialmente).")
    ap.add_argument("--headless", action="store_true", help="Headless. NO recomendado por captcha/pyautogui.")

    # Bandera de logging a archivo
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", dest="log", action="store_true", help="Activa log a archivo (por defecto).")
    g.add_argument("--no-log", dest="log", action="store_false", help="Desactiva log a archivo.")
    ap.set_defaults(log=True)

    args = ap.parse_args()

    # Activa bitácora (si corresponde)
    if args.log:
        start_tee(append=True)
        log(f"\nBitácora activa: {LOG_FILE}")

    try:
        rucs = args.ruc or ["2300142457001"]
        headless = bool(args.headless)

        for idx, ruc in enumerate(rucs, 1):
            log(f"\n[{idx}/{len(rucs)}] RUC objetivo: {ruc}")
            data = process_ruc(ruc, headless=headless)
            print(json.dumps({"ruc": ruc, "result": data}, ensure_ascii=False, indent=2))

        log("\n🏁 Proceso completado.")
    finally:
        # Cierra la bitácora si estaba activa
        if args.log:
            stop_tee()

if __name__ == "__main__":
    main()
