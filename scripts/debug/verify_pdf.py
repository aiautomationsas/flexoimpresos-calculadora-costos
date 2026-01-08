"""
Script para verificar la generación de PDFs después del refactoring.
Genera un PDF de prueba con datos ficticios para asegurar que el pipeline funciona.
"""
import sys
import os
import logging
from datetime import datetime

# Añadir directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.pdf.pdf_generator import CotizacionPDF
from src.config.logging_config import configure_root_logger

# Configurar logger
configure_root_logger()
logger = logging.getLogger(__name__)

def verificar_generacion_pdf():
    print("Iniciando prueba de generación de PDF...")
    
    # Datos de prueba mínimos necesarios
    datos_cotizacion = {
        'id': 9999,
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'cliente': {
            'nombre': 'Cliente de Prueba S.A.S.',
            'nit': '900.123.456-7',
            'contacto': 'Juan Pérez',
            'telefono': '3001234567',
            'email': 'juan@cliente.com',
            'direccion': 'Calle 123 # 45-67',
            'ciudad': 'Bogotá',
            'vendedor': 'Comercial Prueba'
        },
        'producto': {
            'referencia': 'ETIQUETA PRUEBA REFACTORING',
            'descripcion': 'Etiqueta de prueba para verificar integridad PDF',
            'material': {
                'id': 1,
                'nombre': 'Polipropileno Blanco',
                'descripcion': 'Material estándar'
            },
            'adhesivo': {
                'id': 1,
                'nombre': 'Caucho',
                'descripcion': 'Adhesivo agresivo'
            },
            'acabado': {
                'id': 1,
                'nombre': 'Barniz UV',
                'descripcion': 'Brillante'
            },
            'dimensiones': {
                'ancho': 100.0,
                'alto': 150.0, # Avance
            },
            'tintas': {
                'cantidad': 4,
                'colores': ['C', 'M', 'Y', 'K']
            },
            'troquel': {
                'existente': True,
                'tipo': 'Magnético',
                'estado': 'Bueno'
            }
        },
        'escalas': [
            {
                'cantidad': 1000,
                'precio_unitario': 250.0,
                'total': 250000.0,
                'tiempo_entrega': '5 días hábiles'
            },
            {
                'cantidad': 5000,
                'precio_unitario': 180.0,
                'total': 900000.0,
                'tiempo_entrega': '7 días hábiles'
            }
        ],
        'resultados': [
             {'cantidad': 1000, 'total': 250000, 'valor_unidad': 250},
             {'cantidad': 5000, 'total': 900000, 'valor_unidad': 180}
        ],
        'condiciones': {
            'validez': '15 días',
            'forma_pago': 'Crédito 30 días',
            'entrega': 'En planta'
        },
        'observaciones': 'Prueba generada automáticamente post-refactoring.',
        'consecutivo': 12345
    }
    
    try:
        pdf_gen = CotizacionPDF()
        pdf_bytes = pdf_gen.generar_pdf(datos_cotizacion)
        
        if pdf_bytes and len(pdf_bytes) > 0:
            output_file = "prueba_generacion_pdf.pdf"
            with open(output_file, "wb") as f:
                f.write(pdf_bytes)
            print(f"✅ EXITO: PDF generado correctamente ({len(pdf_bytes)} bytes)")
            print(f"✅ Archivo guardado en: {os.path.abspath(output_file)}")
            return True
        else:
            print("❌ ERROR: El generador retornó bytes vacíos")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPCION: Error generando PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verificar_generacion_pdf()
