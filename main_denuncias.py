# main_denuncias.py
import argparse, json
from flows.denuncias import process_denuncias
from core.utils.log import log
from core.utils.tee import start_tee, stop_tee
from core.config import LOG_FILE

def main():
    ap = argparse.ArgumentParser(description="Consulta Fiscalías - Noticias del Delito (denuncias) con captura final.")
    ap.add_argument("--nombres", nargs="+", help="Uno o más nombres completos a consultar.")
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
        nombres_list = args.nombres or ["Juan Perez"]  # ejemplo
        headless = bool(args.headless)

        for idx, nombre in enumerate(nombres_list, 1):
            log(f"\n[{idx}/{len(nombres_list)}] DENUNCIAS objetivo: {nombre}")
            data = process_denuncias(nombre, headless=headless)
            print(json.dumps({"nombres": nombre, "result": data}, ensure_ascii=False, indent=2))

        log("\n🏁 Proceso DENUNCIAS completado.")
    finally:
        if args.log:
            stop_tee()

if __name__ == "__main__":
    main()
