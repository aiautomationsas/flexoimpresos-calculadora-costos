"""
Tests para el uso del costo de troquel fijo (costo_troquel_base_mangas) en
los calculadores de litografía y de costos por escala, para fundas/mangas
termoencogibles. Los tests de DBManager.get_config_mangas()/actualizar_config_mangas()
viven en tests/test_database_config_mangas.py (se separan porque database.py
importa streamlit y este módulo no debe depender de ese import).
"""

import unittest
from unittest.mock import MagicMock

from src.logic.calculators.calculadora_litografia import CalculadoraLitografia
from src.logic.calculators.calculadora_costos_escala import CalculadoraCostosEscala
from src.config.constants import COSTO_TROQUEL_BASE_MANGAS


class TestCalculadoraLitografiaTroquelMangas(unittest.TestCase):
    """Tests para calcular_valor_troquel() con costo_troquel_base_mangas."""

    def setUp(self):
        self.calc = CalculadoraLitografia()
        self.datos = MagicMock()
        self.datos.ancho = 100.0
        self.datos.avance = 100.0
        self.datos.pistas = 1

    def test_manga_troquel_fijo_sin_division_en_todo_grafado(self):
        """Mangas: el troquel es el costo fijo, sin dividir, para cualquier grafado (1-4)."""
        for grafado in (1, 2, 3, 4):
            with self.subTest(grafado=grafado):
                resultado = self.calc.calcular_valor_troquel(
                    self.datos, repeticiones=1, es_manga=True,
                    tipo_grafado_id=grafado, costo_troquel_base_mangas=900000.0
                )
                self.assertEqual(resultado['valor'], 900000.0)
                self.assertEqual(resultado['detalles']['costo_troquel_base_mangas'], 900000.0)

    def test_manga_troquel_no_depende_del_tamano(self):
        """Una manga grande (que antes superaba el mínimo de 700.000) sigue con el costo fijo."""
        self.datos.ancho = 420.0
        self.datos.avance = 400.0
        resultado = self.calc.calcular_valor_troquel(
            self.datos, repeticiones=6, es_manga=True, tipo_grafado_id=1,
            costo_troquel_base_mangas=825000.0
        )
        self.assertEqual(resultado['valor'], 825000.0)

    def test_manga_sin_costo_base_usa_fallback_constante(self):
        """Sin costo_troquel_base_mangas (falla la BD), usa COSTO_TROQUEL_BASE_MANGAS de constants.py."""
        resultado = self.calc.calcular_valor_troquel(
            self.datos, repeticiones=1, es_manga=True, tipo_grafado_id=1
        )
        self.assertEqual(resultado['valor'], COSTO_TROQUEL_BASE_MANGAS)

    def test_etiquetas_no_afectadas_por_costo_base_mangas(self):
        """Etiquetas (es_manga=False) ignoran costo_troquel_base_mangas aunque se pase."""
        resultado_con_param = self.calc.calcular_valor_troquel(
            self.datos, repeticiones=1, es_manga=False,
            tipo_grafado_id=4, costo_troquel_base_mangas=900000.0
        )
        resultado_sin_param = self.calc.calcular_valor_troquel(
            self.datos, repeticiones=1, es_manga=False, tipo_grafado_id=4
        )
        self.assertEqual(resultado_con_param['valor'], resultado_sin_param['valor'])


class TestCalculadoraCostosEscalaTroquelMangas(unittest.TestCase):
    """Tests para CalculadoraCostosEscala.calcular_valor_troquel() con costo_troquel_base_mangas."""

    def setUp(self):
        self.calc = CalculadoraCostosEscala()
        self.datos = MagicMock()
        self.datos.ancho = 100.0
        self.datos.avance = 100.0
        self.datos.pistas = 1

    def test_manga_con_costo_base_fijo(self):
        resultado = self.calc.calcular_valor_troquel(
            self.datos, es_manga=True, tipo_grafado_id=4, repeticiones=1,
            costo_troquel_base_mangas=900000.0
        )
        self.assertEqual(resultado, 900000.0)

    def test_manga_sin_costo_base_usa_fallback_constante(self):
        """Sin costo_troquel_base_mangas, usa COSTO_TROQUEL_BASE_MANGAS sin dividir, para cualquier grafado."""
        resultado = self.calc.calcular_valor_troquel(
            self.datos, es_manga=True, tipo_grafado_id=1, repeticiones=1
        )
        self.assertEqual(resultado, COSTO_TROQUEL_BASE_MANGAS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
