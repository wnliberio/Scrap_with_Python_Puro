# main_deudas.py
import argparse, json
from flows.deudas import process_deudas
from core.utils.log import log
from core.utils.tee import start_tee, stop_tee
from core.config import LOG_FILE

def main():
    ap = argparse.ArgumentParser(description="Consulta SRI Deudas (firmes/impugnadas) con captura final.")
    ap.add_argument("--id", nargs="+", help="Uno o más identificadores (cédula 10 dígitos o RUC 13).")
    ap.add_argument("--headless", action="store_true", help="Headless (no recomendado por captcha/pyautogui).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", dest="log", action="store_true", help="Activa log a archivo (por defecto).")
    g.add_argument("--no-log", dest="log", action="store_false", help="Desactiva log a archivo.")
    ap.set_defaults(log=True)

    args = ap.parse_args()

    if args.log:
        start_tee(append=True)
        log(f"\nBitácora activa: {LOG_FILE}")

    try:
        idents = args.id or ["2300531528001"]  # ejemplo: RUC 13 o cédula 10
        headless = bool(args.headless)

        for idx, ident in enumerate(idents, 1):
            log(f"\n[{idx}/{len(idents)}] DEUDAS objetivo: {ident}")
            data = process_deudas(ident, headless=headless)
            print(json.dumps({"ident": ident, "result": data}, ensure_ascii=False, indent=2))

        log("\n🏁 Proceso DEUDAS completado.")
    finally:
        if args.log:
            stop_tee()

if __name__ == "__main__":
    main()
