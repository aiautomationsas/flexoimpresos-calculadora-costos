"""
Tests para DBManager.get_config_mangas() y actualizar_config_mangas()
(tabla config_mangas_termoencogibles). Separado de test_config_mangas.py
porque database.py importa streamlit; en entornos donde streamlit no puede
importarse (conflicto de versión streamlit/starlette) solo este módulo falla
en collection, sin afectar los tests de los calculadores.
"""

import unittest
from unittest.mock import MagicMock

from src.data.database import DBManager


class TestDBManagerConfigMangas(unittest.TestCase):
    """Tests para DBManager.get_config_mangas() y actualizar_config_mangas()."""

    def setUp(self):
        self.mock_supabase = MagicMock()
        self.db = DBManager(self.mock_supabase)

    def test_get_config_mangas_existente(self):
        """Retorna un ConfigMangasTermoencogibles cuando la fila existe."""
        mock_response = MagicMock()
        mock_response.data = {
            'rentabilidad': 50.0,
            'costo_troquel_base': 900000.0,
            'actualizado_en': '2026-09-24T10:00:00+00:00',
        }
        (self.mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = mock_response

        config = self.db.get_config_mangas()

        self.assertIsNotNone(config)
        self.assertEqual(config.rentabilidad, 50.0)
        self.assertEqual(config.costo_troquel_base, 900000.0)
        self.mock_supabase.table.assert_called_with('config_mangas_termoencogibles')

    def test_get_config_mangas_sin_fila(self):
        """Retorna None cuando no hay fila en la tabla."""
        mock_response = MagicMock()
        mock_response.data = None
        (self.mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .maybe_single.return_value
            .execute.return_value) = mock_response

        config = self.db.get_config_mangas()

        self.assertIsNone(config)

    def test_get_config_mangas_excepcion(self):
        """Retorna None si la consulta lanza una excepción."""
        self.mock_supabase.table.side_effect = Exception("network error")

        config = self.db.get_config_mangas()

        self.assertIsNone(config)

    def test_actualizar_config_mangas_exitoso(self):
        """Retorna True y envía los nuevos valores al hacer update."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, 'rentabilidad': 50.0, 'costo_troquel_base': 900000.0}]
        (self.mock_supabase.table.return_value
            .update.return_value
            .eq.return_value
            .execute.return_value) = mock_response

        resultado = self.db.actualizar_config_mangas(50.0, 900000.0)

        self.assertTrue(resultado)
        update_call_args = self.mock_supabase.table.return_value.update.call_args[0][0]
        self.assertEqual(update_call_args['rentabilidad'], 50.0)
        self.assertEqual(update_call_args['costo_troquel_base'], 900000.0)

    def test_actualizar_config_mangas_sin_respuesta(self):
        """Retorna False cuando la respuesta no trae datos."""
        mock_response = MagicMock()
        mock_response.data = None
        (self.mock_supabase.table.return_value
            .update.return_value
            .eq.return_value
            .execute.return_value) = mock_response

        resultado = self.db.actualizar_config_mangas(50.0, 900000.0)

        self.assertFalse(resultado)

    def test_actualizar_config_mangas_excepcion(self):
        """Retorna False si el update lanza una excepción."""
        self.mock_supabase.table.side_effect = Exception("network error")

        resultado = self.db.actualizar_config_mangas(50.0, 900000.0)

        self.assertFalse(resultado)


if __name__ == '__main__':
    unittest.main(verbosity=2)
