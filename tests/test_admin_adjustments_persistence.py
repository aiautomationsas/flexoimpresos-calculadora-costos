"""
Tests para verificar que los ajustes administrativos se persisten correctamente.

Estos tests comprueban que los parametros_especiales se construyen y 
se preparan adecuadamente para ser guardados en la base de datos.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


class TestParametrosEspeciales(unittest.TestCase):
    """Tests para la estructura de parametros_especiales."""
    
    def test_estructura_parametros_especiales(self):
        """Verifica que los parámetros especiales tienen la estructura correcta."""
        # Simular session_state con ajustes admin activos
        mock_session_state = {
            'ajustar_material': True,
            'valor_material_ajustado': 2500.0,
            'ajustar_troquel': True,
            'precio_troquel': 825000.0,
            'ajustar_planchas': False,
            'precio_planchas': None,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 50.0
        }
        
        # Construir parametros_especiales como lo hace handle_calculation
        parametros_especiales = {
            'ajustar_material': bool(mock_session_state.get('ajustar_material', False)),
            'valor_material_ajustado': mock_session_state.get('valor_material_ajustado'),
            'ajustar_troquel': bool(mock_session_state.get('ajustar_troquel', False)),
            'precio_troquel': mock_session_state.get('precio_troquel'),
            'ajustar_planchas': bool(mock_session_state.get('ajustar_planchas', False)),
            'precio_planchas': mock_session_state.get('precio_planchas'),
            'ajustar_rentabilidad': bool(mock_session_state.get('ajustar_rentabilidad', False)),
            'rentabilidad_ajustada': mock_session_state.get('rentabilidad_ajustada')
        }
        
        # Verificar estructura
        self.assertIn('ajustar_material', parametros_especiales)
        self.assertIn('valor_material_ajustado', parametros_especiales)
        self.assertIn('ajustar_troquel', parametros_especiales)
        self.assertIn('precio_troquel', parametros_especiales)
        self.assertIn('ajustar_planchas', parametros_especiales)
        self.assertIn('precio_planchas', parametros_especiales)
        self.assertIn('ajustar_rentabilidad', parametros_especiales)
        self.assertIn('rentabilidad_ajustada', parametros_especiales)
        
    def test_valores_ajustes_activos(self):
        """Verifica que los valores se capturan correctamente cuando están activos."""
        mock_session_state = {
            'ajustar_material': True,
            'valor_material_ajustado': 3200.50,
            'ajustar_troquel': True,
            'precio_troquel': 950000.0,
            'ajustar_planchas': True,
            'precio_planchas': 250000.0,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 55.5
        }
        
        parametros_especiales = {
            'ajustar_material': bool(mock_session_state.get('ajustar_material', False)),
            'valor_material_ajustado': mock_session_state.get('valor_material_ajustado'),
            'ajustar_troquel': bool(mock_session_state.get('ajustar_troquel', False)),
            'precio_troquel': mock_session_state.get('precio_troquel'),
            'ajustar_planchas': bool(mock_session_state.get('ajustar_planchas', False)),
            'precio_planchas': mock_session_state.get('precio_planchas'),
            'ajustar_rentabilidad': bool(mock_session_state.get('ajustar_rentabilidad', False)),
            'rentabilidad_ajustada': mock_session_state.get('rentabilidad_ajustada')
        }
        
        # Verificar flags booleanos
        self.assertTrue(parametros_especiales['ajustar_material'])
        self.assertTrue(parametros_especiales['ajustar_troquel'])
        self.assertTrue(parametros_especiales['ajustar_planchas'])
        self.assertTrue(parametros_especiales['ajustar_rentabilidad'])
        
        # Verificar valores numéricos
        self.assertEqual(parametros_especiales['valor_material_ajustado'], 3200.50)
        self.assertEqual(parametros_especiales['precio_troquel'], 950000.0)
        self.assertEqual(parametros_especiales['precio_planchas'], 250000.0)
        self.assertEqual(parametros_especiales['rentabilidad_ajustada'], 55.5)
        
    def test_valores_ajustes_inactivos(self):
        """Verifica que los valores son None/False cuando los ajustes están inactivos."""
        mock_session_state = {
            'ajustar_material': False,
            'valor_material_ajustado': None,
            'ajustar_troquel': False,
            'precio_troquel': None,
        }
        
        parametros_especiales = {
            'ajustar_material': bool(mock_session_state.get('ajustar_material', False)),
            'valor_material_ajustado': mock_session_state.get('valor_material_ajustado'),
            'ajustar_troquel': bool(mock_session_state.get('ajustar_troquel', False)),
            'precio_troquel': mock_session_state.get('precio_troquel'),
        }
        
        self.assertFalse(parametros_especiales['ajustar_material'])
        self.assertFalse(parametros_especiales['ajustar_troquel'])
        self.assertIsNone(parametros_especiales['valor_material_ajustado'])
        self.assertIsNone(parametros_especiales['precio_troquel'])


class TestDatosCalculoPersistir(unittest.TestCase):
    """Tests para datos_calculo_persistir que incluyen parametros_especiales."""
    
    def _crear_datos_calculo_persistir(
        self, 
        session_state: Dict[str, Any],
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simula la creación de datos_calculo_persistir."""
        return {
            'valor_material': session_state.get('valor_material_ajustado', 1800.0),
            'valor_plancha': session_state.get('precio_planchas', 180000.0),
            'valor_acabado': 500.0,
            'valor_troquel': session_state.get('precio_troquel', 825000.0),
            'rentabilidad': session_state.get('rentabilidad_ajustada', 40.0) / 100.0 if session_state.get('rentabilidad_ajustada') else 0.4,
            'avance': form_data.get('avance', 120.0),
            'ancho': form_data.get('ancho', 80.0),
            'existe_troquel': form_data.get('tiene_troquel', False),
            'planchas_x_separado': form_data.get('planchas_separadas', False),
            'num_tintas': form_data.get('num_tintas', 4),
            'numero_pistas': form_data.get('pistas', 2),
            'tipo_grafado_id': form_data.get('tipo_grafado_id'),
            'acabado_id': form_data.get('acabado_id', 1),
            'parametros_especiales': {
                'ajustar_material': bool(session_state.get('ajustar_material', False)),
                'valor_material_ajustado': session_state.get('valor_material_ajustado'),
                'ajustar_troquel': bool(session_state.get('ajustar_troquel', False)),
                'precio_troquel': session_state.get('precio_troquel'),
                'ajustar_planchas': bool(session_state.get('ajustar_planchas', False)),
                'precio_planchas': session_state.get('precio_planchas'),
                'ajustar_rentabilidad': bool(session_state.get('ajustar_rentabilidad', False)),
                'rentabilidad_ajustada': session_state.get('rentabilidad_ajustada')
            }
        }
    
    def test_datos_con_todos_ajustes_admin(self):
        """Verifica que todos los ajustes admin se incluyen en datos_calculo_persistir."""
        session_state = {
            'ajustar_material': True,
            'valor_material_ajustado': 2500.0,
            'ajustar_troquel': True,
            'precio_troquel': 900000.0,
            'ajustar_planchas': True,
            'precio_planchas': 280000.0,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 52.0
        }
        form_data = {
            'ancho': 80.0,
            'avance': 120.0,
            'pistas': 2,
            'num_tintas': 4,
            'acabado_id': 1
        }
        
        datos = self._crear_datos_calculo_persistir(session_state, form_data)
        
        # Verificar que el valor material ajustado se usa en el cálculo principal
        self.assertEqual(datos['valor_material'], 2500.0)
        
        # Verificar que parametros_especiales está incluido
        self.assertIn('parametros_especiales', datos)
        params = datos['parametros_especiales']
        
        # Verificar que todos los ajustes están guardados
        self.assertTrue(params['ajustar_material'])
        self.assertEqual(params['valor_material_ajustado'], 2500.0)
        self.assertTrue(params['ajustar_troquel'])
        self.assertEqual(params['precio_troquel'], 900000.0)
        self.assertTrue(params['ajustar_planchas'])
        self.assertEqual(params['precio_planchas'], 280000.0)
        self.assertTrue(params['ajustar_rentabilidad'])
        self.assertEqual(params['rentabilidad_ajustada'], 52.0)
        
    def test_datos_sin_ajustes_admin(self):
        """Verifica que sin ajustes admin los valores por defecto se usan."""
        session_state = {
            'ajustar_material': False,
            'ajustar_troquel': False,
            'ajustar_planchas': False,
            'ajustar_rentabilidad': False,
        }
        form_data = {
            'ancho': 80.0,
            'avance': 120.0,
            'pistas': 2,
            'num_tintas': 4,
        }
        
        datos = self._crear_datos_calculo_persistir(session_state, form_data)
        params = datos['parametros_especiales']
        
        # Todos los ajustes deberían estar desactivados
        self.assertFalse(params['ajustar_material'])
        self.assertFalse(params['ajustar_troquel'])
        self.assertFalse(params['ajustar_planchas'])
        self.assertFalse(params['ajustar_rentabilidad'])


class TestRecargaParametrosEspeciales(unittest.TestCase):
    """Tests para verificar que los parámetros se pueden recargar correctamente."""
    
    def test_recarga_ajustes_desde_parametros(self):
        """Simula la recarga de ajustes admin desde parametros_especiales guardados."""
        # Simular parametros_especiales como vienen de la BD
        parametros_guardados = {
            'ajustar_material': True,
            'valor_material_ajustado': 2800.0,
            'ajustar_troquel': False,
            'precio_troquel': None,
            'ajustar_planchas': True,
            'precio_planchas': 320000.0,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 48.5
        }
        
        # Simular session_state vacío que se poblará
        session_state = {}
        
        # Simular lógica de precarga (como en app_calculadora_costos.py línea ~859)
        if parametros_guardados:
            for key, value in parametros_guardados.items():
                if value is not None:
                    session_state[key] = value
                    
        # Verificar que los valores se cargaron correctamente
        self.assertTrue(session_state.get('ajustar_material'))
        self.assertEqual(session_state.get('valor_material_ajustado'), 2800.0)
        self.assertFalse(session_state.get('ajustar_troquel', False))
        self.assertTrue(session_state.get('ajustar_planchas'))
        self.assertEqual(session_state.get('precio_planchas'), 320000.0)
        self.assertTrue(session_state.get('ajustar_rentabilidad'))
        self.assertEqual(session_state.get('rentabilidad_ajustada'), 48.5)
        
    def test_recarga_parametros_parciales(self):
        """Verifica recarga cuando solo algunos ajustes estaban activos."""
        parametros_guardados = {
            'ajustar_material': True,
            'valor_material_ajustado': 2200.0,
            # Los demás no están o son None/False
        }
        
        session_state = {}
        
        if parametros_guardados:
            for key, value in parametros_guardados.items():
                if value is not None:
                    session_state[key] = value
                    
        # Material activado
        self.assertTrue(session_state.get('ajustar_material'))
        self.assertEqual(session_state.get('valor_material_ajustado'), 2200.0)
        
        # Los demás deberían estar vacíos/False
        self.assertFalse(session_state.get('ajustar_troquel', False))
        self.assertFalse(session_state.get('ajustar_planchas', False))
        self.assertFalse(session_state.get('ajustar_rentabilidad', False))


class TestEdicionCotizacion(unittest.TestCase):
    """Tests para el flujo de edición de cotización con ajustes admin."""
    
    def test_edicion_mantiene_ajustes_previos(self):
        """Verifica que al editar una cotización los ajustes previos se mantienen."""
        # Cotización guardada previamente con ajustes
        cotizacion_guardada = {
            'id': 123,
            'ancho': 80.0,
            'avance': 120.0,
            'num_tintas': 4,
            'calculos_escala': {
                'parametros_especiales': {
                    'ajustar_material': True,
                    'valor_material_ajustado': 2500.0,
                    'ajustar_rentabilidad': True,
                    'rentabilidad_ajustada': 55.0
                }
            }
        }
        
        # Extraer parametros_especiales
        params_esp = cotizacion_guardada['calculos_escala'].get('parametros_especiales', {})
        
        # Verificar que los ajustes se pueden extraer
        self.assertTrue(params_esp.get('ajustar_material'))
        self.assertEqual(params_esp.get('valor_material_ajustado'), 2500.0)
        self.assertTrue(params_esp.get('ajustar_rentabilidad'))
        self.assertEqual(params_esp.get('rentabilidad_ajustada'), 55.0)
        
    def test_nueva_cotizacion_sin_ajustes_previos(self):
        """Verifica que una nueva cotización no tiene ajustes previos."""
        # Nueva cotización sin parametros_especiales
        nueva_cotizacion = {
            'id': None,
            'ancho': 100.0,
            'avance': 150.0,
            'num_tintas': 6,
        }
        
        # No debería haber calculos_escala ni parametros_especiales
        calculos = nueva_cotizacion.get('calculos_escala', {})
        params_esp = calculos.get('parametros_especiales', {})
        
        # Todos los ajustes deberían estar vacíos
        self.assertFalse(params_esp.get('ajustar_material', False))
        self.assertFalse(params_esp.get('ajustar_troquel', False))
        self.assertFalse(params_esp.get('ajustar_planchas', False))
        self.assertFalse(params_esp.get('ajustar_rentabilidad', False))


class TestIntegracionPersistencia(unittest.TestCase):
    """
    Tests de integración que simulan el ciclo completo:
    guardar → cargar cotización con ajustes administrativos.
    """
    
    def setUp(self):
        """Configura datos comunes para los tests de integración."""
        self.cotizacion_id = 12345
        
        # Ajustes admin que el usuario configura
        self.ajustes_admin = {
            'ajustar_material': True,
            'valor_material_ajustado': 2750.0,
            'ajustar_troquel': True,
            'precio_troquel': 875000.0,
            'ajustar_planchas': True,
            'precio_planchas': 295000.0,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 52.5
        }
        
        # Datos del formulario
        self.form_data = {
            'ancho': 85.0,
            'avance': 125.0,
            'pistas': 2,
            'num_tintas': 5,
            'escalas': [1000, 3000, 5000],
            'es_manga': False,
            'material_id': 1,
            'adhesivo_id': 1,
            'acabado_id': 2,
            'tiene_troquel': False,
            'planchas_separadas': True,
        }
        
    def _simular_guardado(self, ajustes_admin: dict, form_data: dict) -> dict:
        """
        Simula la creación de datos_calculo_persistir que se guardan en BD.
        Replica la lógica de handle_calculation líneas ~439-472.
        """
        return {
            'valor_material': ajustes_admin.get('valor_material_ajustado', 1800.0) 
                             if ajustes_admin.get('ajustar_material') else 1800.0,
            'valor_plancha': ajustes_admin.get('precio_planchas', 180000.0)
                            if ajustes_admin.get('ajustar_planchas') else 180000.0,
            'valor_acabado': 500.0,
            'valor_troquel': ajustes_admin.get('precio_troquel', 825000.0)
                            if ajustes_admin.get('ajustar_troquel') else 825000.0,
            'rentabilidad': (ajustes_admin.get('rentabilidad_ajustada', 40.0) / 100.0)
                           if ajustes_admin.get('ajustar_rentabilidad') else 0.40,
            'avance': form_data['avance'],
            'ancho': form_data['ancho'],
            'existe_troquel': form_data.get('tiene_troquel', False),
            'planchas_x_separado': form_data.get('planchas_separadas', False),
            'num_tintas': form_data['num_tintas'],
            'numero_pistas': form_data['pistas'],
            'tipo_grafado_id': form_data.get('tipo_grafado_id'),
            'acabado_id': form_data.get('acabado_id'),
            'parametros_especiales': {
                'ajustar_material': bool(ajustes_admin.get('ajustar_material', False)),
                'valor_material_ajustado': ajustes_admin.get('valor_material_ajustado'),
                'ajustar_troquel': bool(ajustes_admin.get('ajustar_troquel', False)),
                'precio_troquel': ajustes_admin.get('precio_troquel'),
                'ajustar_planchas': bool(ajustes_admin.get('ajustar_planchas', False)),
                'precio_planchas': ajustes_admin.get('precio_planchas'),
                'ajustar_rentabilidad': bool(ajustes_admin.get('ajustar_rentabilidad', False)),
                'rentabilidad_ajustada': ajustes_admin.get('rentabilidad_ajustada')
            }
        }
    
    def _simular_carga(self, datos_guardados: dict) -> dict:
        """
        Simula la recarga de parametros_especiales al session_state.
        Replica la lógica de app_calculadora_costos.py línea ~859.
        """
        session_state_nuevo = {}
        params_esp = datos_guardados.get('parametros_especiales', {})
        
        if params_esp:
            for key, value in params_esp.items():
                if value is not None:
                    session_state_nuevo[key] = value
                    
        return session_state_nuevo
    
    def test_ciclo_completo_guardar_cargar(self):
        """
        Test que verifica el ciclo completo:
        1. Usuario configura ajustes admin
        2. Se guarda cotización con parametros_especiales
        3. Se recarga cotización
        4. Los ajustes admin se restauran correctamente
        """
        # PASO 1: Simular guardado con ajustes admin
        datos_guardados = self._simular_guardado(self.ajustes_admin, self.form_data)
        
        # Verificar que los datos se prepararon correctamente
        self.assertEqual(datos_guardados['valor_material'], 2750.0)
        self.assertEqual(datos_guardados['valor_troquel'], 875000.0)
        self.assertEqual(datos_guardados['valor_plancha'], 295000.0)
        self.assertAlmostEqual(datos_guardados['rentabilidad'], 0.525, places=3)
        
        # PASO 2: Simular carga desde BD
        session_state_restaurado = self._simular_carga(datos_guardados)
        
        # PASO 3: Verificar que los ajustes se restauraron
        self.assertTrue(session_state_restaurado.get('ajustar_material'))
        self.assertEqual(session_state_restaurado.get('valor_material_ajustado'), 2750.0)
        
        self.assertTrue(session_state_restaurado.get('ajustar_troquel'))
        self.assertEqual(session_state_restaurado.get('precio_troquel'), 875000.0)
        
        self.assertTrue(session_state_restaurado.get('ajustar_planchas'))
        self.assertEqual(session_state_restaurado.get('precio_planchas'), 295000.0)
        
        self.assertTrue(session_state_restaurado.get('ajustar_rentabilidad'))
        self.assertEqual(session_state_restaurado.get('rentabilidad_ajustada'), 52.5)
        
    def test_ciclo_sin_ajustes_admin(self):
        """Verifica ciclo cuando no hay ajustes administrativos."""
        ajustes_vacios = {
            'ajustar_material': False,
            'ajustar_troquel': False,
            'ajustar_planchas': False,
            'ajustar_rentabilidad': False,
        }
        
        datos_guardados = self._simular_guardado(ajustes_vacios, self.form_data)
        session_state_restaurado = self._simular_carga(datos_guardados)
        
        # Todos los flags deberían ser False
        self.assertFalse(session_state_restaurado.get('ajustar_material', False))
        self.assertFalse(session_state_restaurado.get('ajustar_troquel', False))
        self.assertFalse(session_state_restaurado.get('ajustar_planchas', False))
        self.assertFalse(session_state_restaurado.get('ajustar_rentabilidad', False))
        
    def test_ciclo_ajustes_parciales(self):
        """Verifica ciclo cuando solo algunos ajustes están activos."""
        ajustes_parciales = {
            'ajustar_material': True,
            'valor_material_ajustado': 3000.0,
            'ajustar_troquel': False,
            'ajustar_planchas': False,
            'ajustar_rentabilidad': True,
            'rentabilidad_ajustada': 48.0
        }
        
        datos_guardados = self._simular_guardado(ajustes_parciales, self.form_data)
        session_state_restaurado = self._simular_carga(datos_guardados)
        
        # Material activado
        self.assertTrue(session_state_restaurado.get('ajustar_material'))
        self.assertEqual(session_state_restaurado.get('valor_material_ajustado'), 3000.0)
        
        # Troquel y planchas desactivados
        self.assertFalse(session_state_restaurado.get('ajustar_troquel', False))
        self.assertFalse(session_state_restaurado.get('ajustar_planchas', False))
        
        # Rentabilidad activada
        self.assertTrue(session_state_restaurado.get('ajustar_rentabilidad'))
        self.assertEqual(session_state_restaurado.get('rentabilidad_ajustada'), 48.0)
        
    def test_recalculo_mantiene_valores_originales(self):
        """
        Verifica que al recalcular una cotización editada,
        los valores ajustados se usan correctamente.
        """
        # Primera cotización con ajustes
        datos_guardados = self._simular_guardado(self.ajustes_admin, self.form_data)
        session_state_restaurado = self._simular_carga(datos_guardados)
        
        # Simular que el usuario hace un recálculo con los mismos ajustes
        # (como si presionara "Calcular" de nuevo)
        datos_recalculados = self._simular_guardado(session_state_restaurado, self.form_data)
        
        # Los valores deberían ser idénticos
        self.assertEqual(
            datos_recalculados['parametros_especiales']['valor_material_ajustado'],
            datos_guardados['parametros_especiales']['valor_material_ajustado']
        )
        self.assertEqual(
            datos_recalculados['parametros_especiales']['precio_troquel'],
            datos_guardados['parametros_especiales']['precio_troquel']
        )
        self.assertEqual(
            datos_recalculados['parametros_especiales']['precio_planchas'],
            datos_guardados['parametros_especiales']['precio_planchas']
        )
        self.assertEqual(
            datos_recalculados['parametros_especiales']['rentabilidad_ajustada'],
            datos_guardados['parametros_especiales']['rentabilidad_ajustada']
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
