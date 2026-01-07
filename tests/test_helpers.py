"""
Tests unitarios para el módulo src/utils/helpers.py

Estos tests verifican las funciones helper utilizadas para reducir
código duplicado en los ajustes administrativos.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.utils.helpers import (
    get_rentabilidad_default,
    parse_numeric_input
)
from src.config.constants import RENTABILIDAD_ETIQUETAS, RENTABILIDAD_MANGAS


class TestGetRentabilidadDefault(unittest.TestCase):
    """Tests para get_rentabilidad_default()."""
    
    def test_etiqueta_desde_datos_cargados(self):
        """Retorna rentabilidad de etiquetas cuando datos_cargados indica es_manga=False."""
        datos = {'es_manga': False, 'other_field': 'value'}
        resultado = get_rentabilidad_default(datos)
        self.assertEqual(resultado, RENTABILIDAD_ETIQUETAS)
        
    def test_manga_desde_datos_cargados(self):
        """Retorna rentabilidad de mangas cuando datos_cargados indica es_manga=True."""
        datos = {'es_manga': True, 'other_field': 'value'}
        resultado = get_rentabilidad_default(datos)
        self.assertEqual(resultado, RENTABILIDAD_MANGAS)
        
    def test_datos_cargados_sin_es_manga(self):
        """Retorna rentabilidad de etiquetas cuando es_manga no está en datos."""
        datos = {'other_field': 'value'}
        resultado = get_rentabilidad_default(datos)
        self.assertEqual(resultado, RENTABILIDAD_ETIQUETAS)
        
    @patch('src.utils.helpers.st')
    def test_sin_datos_cargados_etiqueta(self, mock_st):
        """Usa session_state cuando datos_cargados es None (etiqueta)."""
        mock_st.session_state.get.return_value = False
        resultado = get_rentabilidad_default(None)
        self.assertEqual(resultado, RENTABILIDAD_ETIQUETAS)
        mock_st.session_state.get.assert_called_with('es_manga', False)
        
    @patch('src.utils.helpers.st')
    def test_sin_datos_cargados_manga(self, mock_st):
        """Usa session_state cuando datos_cargados es None (manga)."""
        mock_st.session_state.get.return_value = True
        resultado = get_rentabilidad_default(None)
        self.assertEqual(resultado, RENTABILIDAD_MANGAS)


class TestParseNumericInput(unittest.TestCase):
    """Tests para parse_numeric_input()."""
    
    def test_valor_valido(self):
        """Parsea correctamente un valor numérico válido."""
        valor, error = parse_numeric_input("123.45")
        self.assertEqual(valor, 123.45)
        self.assertIsNone(error)
        
    def test_valor_entero(self):
        """Parsea correctamente un valor entero."""
        valor, error = parse_numeric_input("100")
        self.assertEqual(valor, 100.0)
        self.assertIsNone(error)
        
    def test_valor_con_espacios(self):
        """Parsea valor con espacios alrededor."""
        valor, error = parse_numeric_input("  50.5  ")
        self.assertEqual(valor, 50.5)
        self.assertIsNone(error)
        
    def test_string_vacio(self):
        """Retorna valor por defecto para string vacío."""
        valor, error = parse_numeric_input("", default_value=10.0)
        self.assertEqual(valor, 10.0)
        self.assertIsNone(error)
        
    def test_string_solo_espacios(self):
        """Retorna valor por defecto para string con solo espacios."""
        valor, error = parse_numeric_input("   ", default_value=25.0)
        self.assertEqual(valor, 25.0)
        self.assertIsNone(error)
        
    def test_valor_invalido(self):
        """Retorna error para valor no numérico."""
        valor, error = parse_numeric_input("abc", default_value=0.0)
        self.assertEqual(valor, 0.0)
        self.assertIsNotNone(error)
        self.assertIn("numérico", error.lower())
        
    def test_min_value_violated(self):
        """Retorna error cuando valor es menor que min_value."""
        valor, error = parse_numeric_input("5", default_value=10.0, min_value=10.0)
        self.assertEqual(valor, 10.0)
        self.assertIsNotNone(error)
        self.assertIn("mayor o igual", error)
        
    def test_max_value_violated(self):
        """Retorna error cuando valor es mayor que max_value."""
        valor, error = parse_numeric_input("150", default_value=50.0, max_value=100.0)
        self.assertEqual(valor, 50.0)
        self.assertIsNotNone(error)
        self.assertIn("menor o igual", error)
        
    def test_valor_dentro_rango(self):
        """Acepta valor dentro del rango permitido."""
        valor, error = parse_numeric_input("50", min_value=0.0, max_value=100.0)
        self.assertEqual(valor, 50.0)
        self.assertIsNone(error)
        
    def test_valor_en_limite_inferior(self):
        """Acepta valor igual al límite inferior."""
        valor, error = parse_numeric_input("10", min_value=10.0)
        self.assertEqual(valor, 10.0)
        self.assertIsNone(error)
        
    def test_valor_en_limite_superior(self):
        """Acepta valor igual al límite superior."""
        valor, error = parse_numeric_input("100", max_value=100.0)
        self.assertEqual(valor, 100.0)
        self.assertIsNone(error)
        
    def test_valor_negativo_permitido(self):
        """Permite valores negativos si no hay min_value."""
        valor, error = parse_numeric_input("-25.5")
        self.assertEqual(valor, -25.5)
        self.assertIsNone(error)
        
    def test_valor_decimal_muy_pequeno(self):
        """Parsea correctamente valores decimales muy pequeños."""
        valor, error = parse_numeric_input("0.001")
        self.assertEqual(valor, 0.001)
        self.assertIsNone(error)
        
    def test_valor_grande(self):
        """Parsea correctamente valores grandes."""
        valor, error = parse_numeric_input("1000000.99")
        self.assertEqual(valor, 1000000.99)
        self.assertIsNone(error)


class TestCasosDeUsoReales(unittest.TestCase):
    """Tests que simulan casos de uso reales de la aplicación."""
    
    def test_rentabilidad_valida(self):
        """Simula input de rentabilidad válido."""
        valor, error = parse_numeric_input("45.5", default_value=40.0, min_value=0.1, max_value=100.0)
        self.assertEqual(valor, 45.5)
        self.assertIsNone(error)
        
    def test_rentabilidad_fuera_rango(self):
        """Simula rentabilidad fuera del rango permitido."""
        valor, error = parse_numeric_input("120", default_value=40.0, min_value=0.1, max_value=100.0)
        self.assertEqual(valor, 40.0)  # Retorna default
        self.assertIsNotNone(error)
        
    def test_precio_material(self):
        """Simula input de precio de material."""
        valor, error = parse_numeric_input("1800.50", default_value=0.0, min_value=0.0)
        self.assertEqual(valor, 1800.50)
        self.assertIsNone(error)
        
    def test_precio_troquel(self):
        """Simula input de precio de troquel."""
        valor, error = parse_numeric_input("825000", default_value=0.0, min_value=0.0)
        self.assertEqual(valor, 825000.0)
        self.assertIsNone(error)
        
    def test_mangas_vs_etiquetas_rentabilidad(self):
        """Verifica que los defaults de rentabilidad son diferentes."""
        datos_manga = {'es_manga': True}
        datos_etiqueta = {'es_manga': False}
        
        rent_manga = get_rentabilidad_default(datos_manga)
        rent_etiqueta = get_rentabilidad_default(datos_etiqueta)
        
        # Los valores deberían ser diferentes
        self.assertNotEqual(rent_manga, rent_etiqueta)
        # Mangas típicamente tienen mayor rentabilidad
        self.assertGreater(rent_manga, rent_etiqueta)


if __name__ == '__main__':
    unittest.main(verbosity=2)
