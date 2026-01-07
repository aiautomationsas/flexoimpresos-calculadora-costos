"""
Test de regresión para el caso del cliente MACROLAB ASOCIADOS S.A.S.
Caso: Etiqueta 27x32mm debía elegir unidad pequeña (80/88/102) en lugar de 120

Este test verifica que el sistema priorice unidades más pequeñas cuando el gap
está dentro del umbral aceptable (3.5mm).
"""
import unittest
from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio


class TestUnitSelectionPriority(unittest.TestCase):
    """Tests para verificar la priorización de unidades pequeñas en etiquetas"""
    
    def test_prefer_smaller_unit_with_similar_gap_etiquetas(self):
        """
        CASO DEL CLIENTE (Etiquetas):
        - Avance: 32mm
        - Gap estándar: 3mm
        - Sistema debe preferir unidad pequeña sobre 120 cuando gaps son similares
        """
        calc = CalculadoraDesperdicio(es_manga=False)
        mejor_opcion = calc.obtener_mejor_opcion(avance_mm=32.0)
        
        # La unidad debe ser una de las pequeñas, NO la 120
        self.assertIn(
            mejor_opcion.dientes, 
            [64.0, 80.0, 84.0, 88.0, 96.0, 102.0, 108.0, 112.0],
            f"Para etiquetas se esperaba unidad pequeña, pero eligió {mejor_opcion.dientes}"
        )
        
        # El gap debe ser aceptable (≤ 3.5mm)
        self.assertLessEqual(
            mejor_opcion.desperdicio, 
            3.5,
            f"Gap {mejor_opcion.desperdicio}mm excede umbral aceptable de 3.5mm"
        )
    
    def test_mangas_mantiene_comportamiento_original(self):
        """
        Para MANGAS el comportamiento debe ser el original:
        - Priorizar menor gap absoluto
        """
        calc = CalculadoraDesperdicio(es_manga=True)
        opciones = calc.calcular_todas_opciones(avance_mm=32.0)
        
        # Verificar que las opciones están ordenadas por gap (menor primero)
        for i in range(len(opciones) - 1):
            self.assertLessEqual(
                abs(opciones[i].desperdicio), 
                abs(opciones[i+1].desperdicio) + 0.0001,  # Pequeño margen por flotantes
                "Para mangas, las opciones deben ordenarse por gap (menor primero)"
            )
    
    def test_etiquetas_ordenan_por_dientes_dentro_umbral(self):
        """
        Verifica que las opciones con gap aceptable se ordenen por dientes primero
        """
        calc = CalculadoraDesperdicio(es_manga=False)
        opciones = calc.calcular_todas_opciones(avance_mm=32.0)
        
        # Filtrar solo opciones con gap ≤ 3.5
        opciones_aceptables = [op for op in opciones if op.desperdicio <= 3.5]
        
        if len(opciones_aceptables) > 1:
            # Verificar que están ordenadas por dientes (menor primero)
            for i in range(len(opciones_aceptables) - 1):
                self.assertLessEqual(
                    opciones_aceptables[i].dientes, 
                    opciones_aceptables[i+1].dientes,
                    "Opciones aceptables deben ordenarse por dientes (menor primero)"
                )
    
    def test_caso_cliente_27x32mm(self):
        """
        Test específico para el caso del cliente:
        - Ancho: 27mm, Avance: 32mm
        - Pistas: 4, Tintas: 4
        - Sistema eligió 120, debía elegir 80/88/102
        """
        calc = CalculadoraDesperdicio(es_manga=False)
        mejor_opcion = calc.obtener_mejor_opcion(avance_mm=32.0)
        
        # Imprimir información para debug
        print(f"\nCaso cliente 27x32mm:")
        print(f"  Mejor opción: Unidad {mejor_opcion.dientes}")
        print(f"  Repeticiones: {mejor_opcion.repeticiones}")
        print(f"  Gap: {mejor_opcion.desperdicio:.4f}mm")
        
        # La unidad NO debe ser 120
        self.assertNotEqual(
            mejor_opcion.dientes, 
            120.0,
            "El sistema no debería elegir unidad 120 cuando hay opciones pequeñas con gap aceptable"
        )


class TestUmbralGapAceptable(unittest.TestCase):
    """Tests para verificar el comportamiento del umbral de gap"""
    
    def test_opciones_fuera_umbral_ordenadas_por_gap(self):
        """
        Cuando todas las opciones están fuera del umbral, deben ordenarse por gap
        """
        calc = CalculadoraDesperdicio(es_manga=False)
        
        # Usar un avance que genere gaps grandes
        opciones = calc.calcular_todas_opciones(avance_mm=50.0)
        
        # Filtrar opciones fuera del umbral
        opciones_fuera = [op for op in opciones if op.desperdicio > 3.5]
        
        if len(opciones_fuera) > 1:
            # Verificar ordenamiento por gap
            for i in range(len(opciones_fuera) - 1):
                self.assertLessEqual(
                    abs(opciones_fuera[i].desperdicio), 
                    abs(opciones_fuera[i+1].desperdicio) + 0.0001,
                    "Opciones fuera de umbral deben ordenarse por gap"
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)
