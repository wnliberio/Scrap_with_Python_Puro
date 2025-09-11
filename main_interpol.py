# main_interpol.py
import argparse, json
from flows.interpol import run_interpol_search 

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: INTERPOL Notificaciones rojas")
    parser.add_argument("-a", "--apellidos", type=str, default=None,
                        help="Apellidos (ej: 'MACIAS VILLAMAR')")
    parser.add_argument("-n", "--nombres", type=str, default=None,
                        help="Nombres (ej: 'JOSE ADOLFO')")
    parser.add_argument("-H", "--headless", type=int, default=0,
                        help="1=headless, 0=visible")
    args = parser.parse_args()

    data = run_interpol_search (args.apellidos, args.nombres, headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

#Para probar:   
# Caso CON resultados (Escenario 1)
#python main_interpol.py -a "MACIAS VILLAMAR" -n "JOSE ADOLFO"

# Caso SIN resultados (Escenario 2)
#python main_interpol.py -a "CRIOLLO SAGUINGA"  sawe_