# main_predio_manta.py
import argparse, json
from flows.predio_manta import run_predio_manta

def main():
    p = argparse.ArgumentParser(description="Prueba aislada: Predio Manta")
    p.add_argument("-v", "--valor", required=True,
                   help="Cédula (10), RUC (13), Pasaporte (AAA999999) o Apellidos/Nombres")
    p.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = p.parse_args()

    data = run_predio_manta(args.valor.strip(), headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
