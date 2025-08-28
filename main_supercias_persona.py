# main_supercias_persona.py
import argparse, json
from flows.supercias_persona import run_supercias_persona

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: Supercias – Consulta de Persona (Identificación/Nombre)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", "--ident", type=str, help="Cédula (exactamente 10 dígitos)")
    g.add_argument("-n", "--nombre", type=str, help='Nombre (p. ej.: "VELA VASCO MARCO ANTONIO")')

    parser.add_argument("-m", "--mode", type=str, default="auto", choices=["auto", "ident", "nombre"],
                        help="Modo (auto: si es 10 dígitos, usa Identificación; caso contrario, Nombre)")
    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = parser.parse_args()

    query = args.ident or args.nombre
    data = run_supercias_persona(query, mode=args.mode, headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
