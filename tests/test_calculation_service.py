"""
Tests unitarios para CalculationService.

Verifica la lógica de negocio del servicio de cálculo de cotizaciones.
"""

import unittest
from src.logic.services.calculation_service import (
    CalculationService, 
    CalculationInput, 
    CalculationResult
)
from src.config.constants import (
    FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS,
    RENTABILIDAD_ETIQUETAS, RENTABILIDAD_MANGAS
)


class TestCalculationServiceValidation(unittest.TestCase):
    """Tests para validación de input."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def _crear_input_basico(self, **kwargs):
        """Helper para crear input con valores por defecto."""
        defaults = {
            'es_manga': False,
            'ancho': 80.0,
            'avance': 120.0,
            'pistas': 2,
            'escalas': [1000],
            'num_tintas': 4,
            'material_id': 1,
            'adhesivo_id': 1,
            'acabado_id': 1,
            'valor_material_base': 1800.0,
            'valor_acabado': 500.0,
        }
        defaults.update(kwargs)
        return CalculationInput(**defaults)
    
    def test_validacion_exitosa(self):
        """Input válido pasa la validación."""
        input_data = self._crear_input_basico()
        es_valido, error = self.service.validar_input(input_data)
        self.assertTrue(es_valido)
        self.assertIsNone(error)
        
    def test_escalas_vacias(self):
        """Falla si escalas está vacía."""
        input_data = self._crear_input_basico(escalas=[])
        es_valido, error = self.service.validar_input(input_data)
        self.assertFalse(es_valido)
        self.assertIn("escala", error.lower())
        
    def test_ancho_cero(self):
        """Falla si ancho es cero."""
        input_data = self._crear_input_basico(ancho=0)
        es_valido, error = self.service.validar_input(input_data)
        self.assertFalse(es_valido)
        self.assertIn("ancho", error.lower())
        
    def test_etiqueta_sin_adhesivo(self):
        """Falla si es etiqueta sin adhesivo."""
        input_data = self._crear_input_basico(es_manga=False, adhesivo_id=None)
        es_valido, error = self.service.validar_input(input_data)
        self.assertFalse(es_valido)
        self.assertIn("adhesivo", error.lower())
        
    def test_manga_sin_adhesivo_es_valido(self):
        """Manga sin adhesivo es válido."""
        input_data = self._crear_input_basico(es_manga=True, adhesivo_id=None)
        es_valido, error = self.service.validar_input(input_data)
        self.assertTrue(es_valido)
        
    def test_tintas_fuera_rango(self):
        """Falla si tintas está fuera del rango 0-7."""
        input_data = self._crear_input_basico(num_tintas=8)
        es_valido, error = self.service.validar_input(input_data)
        self.assertFalse(es_valido)
        self.assertIn("tintas", error.lower())


class TestAjusteAnchoManga(unittest.TestCase):
    """Tests para ajuste de ancho en mangas."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def test_funda_transparente(self):
        """0 tintas aplica fórmula de funda transparente."""
        ancho_ajustado, error = self.service.ajustar_ancho_manga(80.0, num_tintas=0)
        # (80 * 2) + 6 = 166
        self.assertEqual(ancho_ajustado, 166.0)
        self.assertIsNone(error)
        
    def test_funda_transparente_excede_maximo(self):
        """Funda transparente que excede 415mm genera error."""
        ancho_ajustado, error = self.service.ajustar_ancho_manga(210.0, num_tintas=0)
        # (210 * 2) + 6 = 426 > 415
        self.assertEqual(ancho_ajustado, 426.0)
        self.assertIsNotNone(error)
        self.assertIn("415", error)
        
    def test_manga_con_tintas(self):
        """Manga con tintas aplica fórmula estándar."""
        ancho_ajustado, error = self.service.ajustar_ancho_manga(80.0, num_tintas=4)
        # (80 * 2) + 20 = 180
        esperado = (80.0 * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
        self.assertEqual(ancho_ajustado, esperado)
        self.assertIsNone(error)


class TestProcesarTroquelExiste(unittest.TestCase):
    """Tests para conversión de troquel_existe a booleano."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def test_string_si(self):
        self.assertTrue(self.service.procesar_troquel_existe("Sí"))
        
    def test_string_no(self):
        self.assertFalse(self.service.procesar_troquel_existe("No"))
        
    def test_string_true(self):
        self.assertTrue(self.service.procesar_troquel_existe("true"))
        
    def test_string_false(self):
        self.assertFalse(self.service.procesar_troquel_existe("false"))
        
    def test_int_positivo(self):
        self.assertTrue(self.service.procesar_troquel_existe(1))
        
    def test_int_cero(self):
        self.assertFalse(self.service.procesar_troquel_existe(0))
        
    def test_bool_true(self):
        self.assertTrue(self.service.procesar_troquel_existe(True))
        
    def test_bool_false(self):
        self.assertFalse(self.service.procesar_troquel_existe(False))


class TestAjusteTintas(unittest.TestCase):
    """Tests para ajuste de tintas por acabado."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def test_acabado_especial_incrementa_tinta(self):
        """Acabados especiales (3,4,5,6) incrementan +1 tinta."""
        for acabado_id in [3, 4, 5, 6]:
            with self.subTest(acabado_id=acabado_id):
                tintas_ajustadas, error = self.service.ajustar_tintas_por_acabado(4, acabado_id, es_manga=False)
                self.assertEqual(tintas_ajustadas, 5)
                self.assertIsNone(error)
                
    def test_acabado_normal_no_incrementa(self):
        """Acabados normales no incrementan tintas."""
        tintas_ajustadas, error = self.service.ajustar_tintas_por_acabado(4, acabado_id=1, es_manga=False)
        self.assertEqual(tintas_ajustadas, 4)
        self.assertIsNone(error)
        
    def test_manga_no_incrementa(self):
        """Mangas nunca incrementan tintas por acabado."""
        tintas_ajustadas, error = self.service.ajustar_tintas_por_acabado(4, acabado_id=3, es_manga=True)
        self.assertEqual(tintas_ajustadas, 4)
        self.assertIsNone(error)
        
    def test_excede_maximo_7(self):
        """Error si ajuste excede 7 tintas."""
        tintas_ajustadas, error = self.service.ajustar_tintas_por_acabado(7, acabado_id=3, es_manga=False)
        # 7 + 1 = 8 > 7 máximo
        self.assertEqual(tintas_ajustadas, 7)  # Retorna original
        self.assertIsNotNone(error)
        self.assertIn("máximo", error.lower())


class TestCalculoPlancha(unittest.TestCase):
    """Tests para cálculo de planchas separadas."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def test_redondeo_plancha_separado(self):
        """Aplica fórmula CEILING(valor/0.7, 10000)."""
        # 373176 / 0.7 = 533108.57 -> CEIL a 10000 = 540000
        resultado = self.service.calcular_valor_plancha_separado(373176.0)
        self.assertEqual(resultado, 540000.0)
        
    def test_valor_none(self):
        """Retorna None si valor es None."""
        resultado = self.service.calcular_valor_plancha_separado(None)
        self.assertIsNone(resultado)
        
    def test_valor_cero(self):
        """Retorna None si valor es 0."""
        resultado = self.service.calcular_valor_plancha_separado(0.0)
        self.assertIsNone(resultado)


class TestCalculoCompleto(unittest.TestCase):
    """Tests de integración para el cálculo completo."""
    
    def setUp(self):
        self.service = CalculationService()
        
    def _crear_input_basico(self, **kwargs):
        """Helper para crear input con valores por defecto."""
        defaults = {
            'es_manga': False,
            'ancho': 80.0,
            'avance': 120.0,
            'pistas': 2,
            'escalas': [1000, 2500, 5000],
            'num_tintas': 4,
            'material_id': 1,
            'adhesivo_id': 1,
            'acabado_id': 1,
            'valor_material_base': 1800.0,
            'valor_acabado': 500.0,
            'troquel_existe': False,
            'num_paquetes': 1,
        }
        defaults.update(kwargs)
        return CalculationInput(**defaults)
    
    def test_calculo_etiqueta_exitoso(self):
        """Cálculo completo de etiqueta retorna resultados."""
        input_data = self._crear_input_basico()
        resultado = self.service.calcular(input_data)
        
        self.assertTrue(resultado.success)
        self.assertIsNotNone(resultado.resultados)
        self.assertEqual(len(resultado.resultados), 3)  # 3 escalas
        self.assertIsNone(resultado.error_message)
        
    def test_calculo_manga_exitoso(self):
        """Cálculo completo de manga retorna resultados."""
        input_data = self._crear_input_basico(
            es_manga=True,
            adhesivo_id=None,
            acabado_id=None,
            valor_acabado=0
        )
        resultado = self.service.calcular(input_data)
        
        self.assertTrue(resultado.success)
        self.assertIsNotNone(resultado.resultados)
        
    def test_datos_persistir_incluidos(self):
        """Resultado incluye datos para persistir."""
        input_data = self._crear_input_basico()
        resultado = self.service.calcular(input_data)
        
        self.assertTrue(resultado.success)
        self.assertIsNotNone(resultado.datos_persistir)
        self.assertIn('valor_material', resultado.datos_persistir)
        self.assertIn('num_tintas', resultado.datos_persistir)
        self.assertIn('ancho', resultado.datos_persistir)
        
    def test_calculo_con_ajustes_admin(self):
        """Cálculo respeta ajustes administrativos."""
        input_data = self._crear_input_basico(
            valor_material_ajustado=2500.0,
            rentabilidad_ajustada=50.0
        )
        resultado = self.service.calcular(input_data)
        
        self.assertTrue(resultado.success)
        self.assertEqual(resultado.datos_persistir['valor_material'], 2500.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
