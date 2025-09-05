# test_timezone_conversion.py
"""
Script para probar que la conversión de timezone funciona
incluso con datos insertados directamente en la BD
"""

from app.dbb import engine, text, list_de_lista, convert_db_datetime_to_ecuador, ec_now_naive
from datetime import datetime

def insertar_directo_bd():
    """Inserta un registro directamente en BD para simular inserción externa"""
    
    print("🔧 Insertando registro directo en BD (simulando sistema externo)...")
    
    sql = text("""
        INSERT INTO de_lista 
        (nombre, apellido, ci, ruc, tipo, monto, fecha, fecha_creacion)
        VALUES 
        ('Test Externo', 'Sistema Directo', '1234567890', '1234567890001', 'Test BD', 999.99, '2025-09-05', NOW())
    """)
    
    with engine.begin() as conn:
        conn.execute(sql)
        print("✅ Registro insertado directamente en BD con NOW()")

def insertar_desde_python():
    """Inserta un registro desde Python para comparar"""
    
    from app.dbb import insert_de_lista
    from datetime import date
    
    print("🐍 Insertando registro desde Python...")
    
    record_id = insert_de_lista(
        nombre="Test Python",
        apellido="Sistema Python", 
        ci="0987654321",
        ruc="0987654321001",
        tipo="Test Python",
        monto=888.88,
        fecha=date(2025, 9, 5)
    )
    
    print(f"✅ Registro insertado desde Python - ID: {record_id}")

def mostrar_diferencias():
    """Muestra cómo se ven las fechas de ambos registros"""
    
    print("\n📋 COMPARANDO FECHAS DE AMBOS REGISTROS:")
    print("="*60)
    
    # Obtener registros
    registros = list_de_lista()
    
    # Buscar nuestros registros de prueba
    test_externo = next((r for r in registros if r['nombre'] == 'Test Externo'), None)
    test_python = next((r for r in registros if r['nombre'] == 'Test Python'), None)
    
    if test_externo:
        print(f"🔧 Insertado directo en BD:")
        print(f"   Fecha mostrada: {test_externo['fecha_creacion']}")
        print(f"   (Convertida automáticamente a Ecuador)")
    
    if test_python:
        print(f"🐍 Insertado desde Python:")
        print(f"   Fecha mostrada: {test_python['fecha_creacion']}")
        print(f"   (Ya estaba en hora Ecuador)")
    
    # Mostrar hora actual para referencia
    hora_actual = ec_now_naive()
    print(f"\n🕐 Hora actual Ecuador: {hora_actual}")

def verificar_conversion_raw():
    """Verifica la conversión comparando datos raw de BD vs convertidos"""
    
    print("\n🔍 VERIFICANDO CONVERSIÓN RAW:")
    print("="*60)
    
    # Obtener datos raw sin conversión
    sql = text("SELECT nombre, fecha_creacion FROM de_lista WHERE nombre LIKE 'Test%' ORDER BY id_lista DESC LIMIT 2")
    
    with engine.begin() as conn:
        rows = conn.execute(sql).mappings().all()
        
        for r in rows:
            fecha_raw = r["fecha_creacion"]
            fecha_convertida = convert_db_datetime_to_ecuador(fecha_raw)
            
            print(f"📝 {r['nombre']}:")
            print(f"   BD raw: {fecha_raw}")
            print(f"   Convertida: {fecha_convertida}")
            print(f"   Diferencia: {abs((datetime.now() - fecha_raw).total_seconds())} segundos del servidor")

def limpiar_registros_test():
    """Limpia los registros de prueba"""
    
    respuesta = input("\n🧹 ¿Limpiar registros de prueba? (s/N): ").lower()
    if respuesta == 's':
        sql = text("DELETE FROM de_lista WHERE nombre LIKE 'Test%'")
        with engine.begin() as conn:
            result = conn.execute(sql)
            print(f"✅ {result.rowcount} registros de prueba eliminados")
    else:
        print("❌ Registros de prueba mantenidos")

def main():
    """Función principal del test"""
    
    print("🧪 PROBANDO CONVERSIÓN DE TIMEZONE")
    print("="*60)
    print("Este test verifica que las fechas se muestren correctamente")
    print("sin importar cómo se insertaron en la BD\n")
    
    try:
        # 1. Insertar registros de ambas formas
        insertar_directo_bd()
        insertar_desde_python()
        
        # 2. Mostrar cómo se ven las fechas
        mostrar_diferencias()
        
        # 3. Verificar conversión raw
        verificar_conversion_raw()
        
        # 4. Limpiar (opcional)
        limpiar_registros_test()
        
        print("\n🎯 ¡Test completado! Las fechas deben mostrarse en hora Ecuador")
        print("💡 Esto significa que tu frontend SIEMPRE verá hora Ecuador")
        print("   sin importar cómo se insertaron los datos en la BD")
        
    except Exception as e:
        print(f"❌ Error en el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()