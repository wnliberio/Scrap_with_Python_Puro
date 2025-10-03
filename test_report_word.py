# test_report_word.py
from app.services.report_builder import build_report_docx
from datetime import date
import os

# Usar las rutas reales de los screenshots que ya generaste
results = {
    'funcion_judicial': {
        'success': True,
        'nombre_buscado': 'José Adolfo Macías Villamar',
        'screenshots': [
            'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page1.png',
            'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page2.png',
            'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page3.png',
            'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page4.png'
        ],
        'total_pages': 4,
        'scenario': 'results_found',
        'mensaje': 'Se encontraron procesos judiciales en 4 página(s)',
        # Retrocompatibilidad
        'screenshot_path': 'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page1.png',
        'screenshot_historial_path': 'sri_ruc_output/screenshots/funcion_judicial_josé_adolfo_macías_villamar_page2.png'
    }
}

meta = {
    'tipo_alerta': 'Consulta Judicial Test V25',
    'monto_usd': 50000.00,
    'fecha_alerta': date(2025, 10, 3)
}

print("Generando reporte Word...")
path = build_report_docx('test_v25_fito', meta, results)
print(f'\n✅ Reporte generado: {path}')
print(f'\nAbre el archivo para verificar que tenga las 4 páginas numeradas:')
print(f'  - Figura 1. Función Judicial - Página 1 de 4')
print(f'  - Figura 2. Función Judicial - Página 2 de 4')
print(f'  - Figura 3. Función Judicial - Página 3 de 4')
print(f'  - Figura 4. Función Judicial - Página 4 de 4')