# main_predio_quito.py
import argparse, json
from flows.predio_quito import run_predio_quito

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: Predios – Quito (Apellidos y Nombres)")
    parser.add_argument("-n", "--nombres", required=True, help='Apellidos y Nombres (ej.: "VELA VASCO MARCO ANTONIO")')
    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = parser.parse_args()

    data = run_predio_quito(args.nombres.strip(), headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
