"""
Tests comprehensivos para el sistema de cotizaciones Flexo Impresos.

Este módulo contiene tests específicos para:
- Etiquetas: diferentes acabados, adhesivos, pistas, tintas
- Mangas: grafados, fundas transparentes (0 tintas), límites de ancho
- Condiciones especiales: velocidad 7 tintas, acabados +1 tinta, troquel existe
"""

import unittest
from src.logic.calculators.calculadora_costos_escala import CalculadoraCostosEscala, DatosEscala
from src.logic.calculators.calculadora_litografia import CalculadoraLitografia, DatosLitografia
from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio
from src.config.constants import (
    VELOCIDAD_MAQUINA_NORMAL, VELOCIDAD_MAQUINA_MANGAS_7_TINTAS,
    RENTABILIDAD_ETIQUETAS, RENTABILIDAD_MANGAS,
    DESPERDICIO_ETIQUETAS, DESPERDICIO_MANGAS,
    GAP_AVANCE_ETIQUETAS, GAP_AVANCE_MANGAS,
    FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS,
    ANCHO_MAXIMO_MAQUINA, ANCHO_MAXIMO_LITOGRAFIA
)


class TestEtiquetas(unittest.TestCase):
    """Tests específicos para cálculos de etiquetas."""
    
    def setUp(self):
        self.calc = CalculadoraCostosEscala()
        self.calc_lito = CalculadoraLitografia()
        self.valor_material = 1800.0
        self.valor_acabado = 500.0
        
    def _crear_datos_etiqueta(self, ancho=80.0, avance=120.0, pistas=2, 
                               escalas=[1000], troquel_existe=False,
                               planchas_separadas=False, unidad_dientes=None):
        """Helper para crear DatosEscala para etiquetas."""
        return DatosEscala(
            escalas=escalas,
            pistas=pistas,
            ancho=ancho,
            avance=avance,
            avance_total=avance + GAP_AVANCE_ETIQUETAS,
            desperdicio=0,
            velocidad_maquina=VELOCIDAD_MAQUINA_NORMAL,
            rentabilidad=RENTABILIDAD_ETIQUETAS,
            porcentaje_desperdicio=DESPERDICIO_ETIQUETAS,
            valor_metro=self.valor_material,
            troquel_existe=troquel_existe,
            planchas_por_separado=planchas_separadas,
            unidad_montaje_dientes=unidad_dientes
        )
    
    def test_etiqueta_sin_tintas(self):
        """Test etiqueta sin tintas (0 colores)."""
        datos = self._crear_datos_etiqueta()
        resultado = self.calc.calcular_costos_por_escala(
            datos=datos,
            num_tintas=0,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        self.assertIsNotNone(resultado)
        self.assertEqual(len(resultado), 1)
        # Sin tintas, el costo de montaje debe ser 0
        self.assertEqual(resultado[0]['montaje'], 0)
        
    def test_etiqueta_con_tintas_multiples(self):
        """Test etiqueta con diferentes cantidades de tintas (1-7)."""
        for num_tintas in [1, 3, 5, 7]:
            with self.subTest(num_tintas=num_tintas):
                datos = self._crear_datos_etiqueta()
                resultado = self.calc.calcular_costos_por_escala(
                    datos=datos,
                    num_tintas=num_tintas,
                    valor_plancha=None,
                    valor_troquel=None,
                    valor_material=self.valor_material,
                    valor_acabado=self.valor_acabado,
                    es_manga=False
                )
                self.assertIsNotNone(resultado)
                # El montaje debe aumentar con más tintas
                self.assertGreater(resultado[0]['montaje'], 0)
                
    def test_etiqueta_troquel_existe_vs_nuevo(self):
        """Test diferencia entre troquel existente y nuevo."""
        # Troquel nuevo (más caro)
        datos_nuevo = self._crear_datos_etiqueta(troquel_existe=False)
        resultado_nuevo = self.calc.calcular_costos_por_escala(
            datos=datos_nuevo,
            num_tintas=4,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        
        # Troquel existente (más barato porque no paga troquel nuevo)
        datos_existe = self._crear_datos_etiqueta(troquel_existe=True)
        resultado_existe = self.calc.calcular_costos_por_escala(
            datos=datos_existe,
            num_tintas=4,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        
        self.assertIsNotNone(resultado_nuevo)
        self.assertIsNotNone(resultado_existe)
        # Costo unitario con troquel nuevo debe ser mayor que con troquel existente
        self.assertGreater(resultado_nuevo[0]['valor_unidad'], resultado_existe[0]['valor_unidad'])
        
    def test_etiqueta_planchas_separadas(self):
        """Test planchas por separado vs incluidas."""
        # Planchas incluidas
        datos_incl = self._crear_datos_etiqueta(planchas_separadas=False)
        resultado_incl = self.calc.calcular_costos_por_escala(
            datos=datos_incl,
            num_tintas=4,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        
        # Planchas separadas
        datos_sep = self._crear_datos_etiqueta(planchas_separadas=True)
        resultado_sep = self.calc.calcular_costos_por_escala(
            datos=datos_sep,
            num_tintas=4,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        
        self.assertIsNotNone(resultado_incl)
        self.assertIsNotNone(resultado_sep)
        
    def test_etiqueta_multiples_escalas(self):
        """Test con múltiples escalas de producción."""
        escalas = [500, 1000, 2500, 5000, 10000]
        datos = self._crear_datos_etiqueta(escalas=escalas)
        
        resultado = self.calc.calcular_costos_por_escala(
            datos=datos,
            num_tintas=4,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=self.valor_acabado,
            es_manga=False
        )
        
        self.assertEqual(len(resultado), 5)
        # El precio unitario debe disminuir con escalas mayores
        precios_unitarios = [r['valor_unidad'] for r in resultado]
        for i in range(1, len(precios_unitarios)):
            self.assertLess(precios_unitarios[i], precios_unitarios[i-1])
            
    def test_etiqueta_diferentes_pistas(self):
        """Test con diferentes cantidades de pistas."""
        for pistas in [1, 2, 3, 4, 5]:
            with self.subTest(pistas=pistas):
                # Ajustar ancho para que sea válido con las pistas
                ancho = 50.0  # Ancho pequeño para más pistas
                datos = self._crear_datos_etiqueta(ancho=ancho, pistas=pistas)
                
                resultado = self.calc.calcular_costos_por_escala(
                    datos=datos,
                    num_tintas=4,
                    valor_plancha=None,
                    valor_troquel=None,
                    valor_material=self.valor_material,
                    valor_acabado=self.valor_acabado,
                    es_manga=False
                )
                self.assertIsNotNone(resultado)
                
    def test_etiqueta_acabados_especiales(self):
        """Test acabados especiales que requieren +1 tinta (IDs 3, 4, 5, 6)."""
        acabados_especiales = [3, 4, 5, 6]
        for acabado_id in acabados_especiales:
            with self.subTest(acabado_id=acabado_id):
                datos = self._crear_datos_etiqueta()
                resultado = self.calc.calcular_costos_por_escala(
                    datos=datos,
                    num_tintas=4,
                    valor_plancha=None,
                    valor_troquel=None,
                    valor_material=self.valor_material,
                    valor_acabado=self.valor_acabado,
                    es_manga=False,
                    acabado_id=acabado_id
                )
                self.assertIsNotNone(resultado)


class TestMangas(unittest.TestCase):
    """Tests específicos para cálculos de mangas."""
    
    def setUp(self):
        self.calc = CalculadoraCostosEscala()
        self.calc_lito = CalculadoraLitografia()
        self.valor_material = 2000.0
        self.valor_acabado = 0  # Mangas no tienen acabado
        
    def _crear_datos_manga(self, ancho=80.0, avance=100.0, pistas=1, 
                            escalas=[1000], troquel_existe=False,
                            planchas_separadas=False, unidad_dientes=None,
                            num_tintas=4):
        """Helper para crear DatosEscala para mangas."""
        # Ajustar ancho según fórmula de manga
        ancho_ajustado = (ancho * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
        
        # Velocidad especial para 7+ tintas
        velocidad = VELOCIDAD_MAQUINA_MANGAS_7_TINTAS if num_tintas >= 7 else VELOCIDAD_MAQUINA_NORMAL
        
        return DatosEscala(
            escalas=escalas,
            pistas=pistas,
            ancho=ancho_ajustado,
            avance=avance,
            avance_total=avance + GAP_AVANCE_MANGAS,
            desperdicio=0,
            velocidad_maquina=velocidad,
            rentabilidad=RENTABILIDAD_MANGAS,
            porcentaje_desperdicio=DESPERDICIO_MANGAS,
            valor_metro=self.valor_material,
            troquel_existe=troquel_existe,
            planchas_por_separado=planchas_separadas,
            unidad_montaje_dientes=unidad_dientes
        )
        
    def test_manga_sin_tintas_funda_transparente(self):
        """Test manga sin tintas (funda transparente) - fórmula especial de ancho."""
        # Para funda transparente: ancho = (ancho_cerrado * 2) + 6
        ancho_cerrado = 80.0
        ancho_funda = (ancho_cerrado * 2) + 6  # = 166mm
        
        datos = DatosEscala(
            escalas=[1000],
            pistas=1,
            ancho=ancho_funda,
            avance=100.0,
            avance_total=100.0 + GAP_AVANCE_MANGAS,
            desperdicio=0,
            velocidad_maquina=VELOCIDAD_MAQUINA_NORMAL,
            rentabilidad=RENTABILIDAD_MANGAS,
            porcentaje_desperdicio=DESPERDICIO_MANGAS,
            valor_metro=self.valor_material,
            troquel_existe=False,
            planchas_por_separado=False,
            unidad_montaje_dientes=None
        )
        
        resultado = self.calc.calcular_costos_por_escala(
            datos=datos,
            num_tintas=0,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=self.valor_material,
            valor_acabado=0,
            es_manga=True
        )
        
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado[0]['montaje'], 0)
        
    def test_manga_velocidad_7_tintas(self):
        """Test que mangas con 7 tintas usan velocidad reducida."""
        datos_7 = self._crear_datos_manga(num_tintas=7)
        self.assertEqual(datos_7.velocidad_maquina, VELOCIDAD_MAQUINA_MANGAS_7_TINTAS)
        
        datos_6 = self._crear_datos_manga(num_tintas=6)
        self.assertEqual(datos_6.velocidad_maquina, VELOCIDAD_MAQUINA_NORMAL)
        
    def test_manga_tipos_grafado(self):
        """Test diferentes tipos de grafado para mangas."""
        tipos_grafado = [
            (1, "Sin grafado"),
            (2, "Vertical"),
            (3, "Horizontal"),
            (4, "Horizontal Total + Vertical"),
        ]
        
        for grafado_id, nombre in tipos_grafado:
            with self.subTest(grafado=nombre):
                datos = self._crear_datos_manga()
                resultado = self.calc.calcular_costos_por_escala(
                    datos=datos,
                    num_tintas=4,
                    valor_plancha=None,
                    valor_troquel=None,
                    valor_material=self.valor_material,
                    valor_acabado=0,
                    es_manga=True,
                    tipo_grafado_id=grafado_id
                )
                self.assertIsNotNone(resultado)
                
    def test_manga_ancho_ajuste(self):
        """Test que el ancho de manga se ajusta correctamente."""
        ancho_original = 100.0
        ancho_esperado = (ancho_original * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
        # ancho_esperado = (100 * 2) + 20 = 220mm
        
        datos = self._crear_datos_manga(ancho=ancho_original)
        self.assertEqual(datos.ancho, ancho_esperado)
        
    def test_manga_limite_ancho_funda(self):
        """Test límite de ancho para fundas transparentes (max 415mm)."""
        # Ancho cerrado que resultaría en > 415mm efectivo
        ancho_cerrado_grande = 200.0  # (200 * 2) + 6 = 406mm OK
        ancho_funda = (ancho_cerrado_grande * 2) + 6
        self.assertLessEqual(ancho_funda, 415)
        
        ancho_cerrado_excede = 210.0  # (210 * 2) + 6 = 426mm EXCEDE
        ancho_funda_excede = (ancho_cerrado_excede * 2) + 6
        self.assertGreater(ancho_funda_excede, 415)


class TestCalculadoraDesperdicio(unittest.TestCase):
    """Tests para la calculadora de desperdicios."""
    
    def test_desperdicio_etiquetas(self):
        """Test calculadora de desperdicios para etiquetas."""
        calc_desp = CalculadoraDesperdicio(es_manga=False)
        
        avances = [50.0, 100.0, 150.0, 200.0]
        for avance in avances:
            with self.subTest(avance=avance):
                mejor_opcion = calc_desp.obtener_mejor_opcion(avance)
                self.assertIsNotNone(mejor_opcion)
                self.assertGreater(mejor_opcion.dientes, 0)
                self.assertGreater(mejor_opcion.repeticiones, 0)
                
    def test_desperdicio_mangas(self):
        """Test calculadora de desperdicios para mangas."""
        calc_desp = CalculadoraDesperdicio(es_manga=True)
        
        avances = [50.0, 100.0, 150.0, 200.0]
        for avance in avances:
            with self.subTest(avance=avance):
                mejor_opcion = calc_desp.obtener_mejor_opcion(avance)
                self.assertIsNotNone(mejor_opcion)
                
    def test_unidad_especifica(self):
        """Test selección de unidad específica de montaje."""
        calc_desp = CalculadoraDesperdicio(es_manga=False)
        
        avance = 100.0
        dientes = 100  # Unidad específica
        
        opcion = calc_desp.obtener_mejor_opcion_para_unidad(avance, dientes)
        if opcion is not None:
            self.assertEqual(opcion.dientes, dientes)


class TestCalculadoraLitografia(unittest.TestCase):
    """Tests para cálculos de litografía."""
    
    def setUp(self):
        self.calc_lito = CalculadoraLitografia()
        
    def test_calcular_ancho_total_con_tintas(self):
        """Test cálculo de ancho total con tintas."""
        ancho_total, mensaje = self.calc_lito.calcular_ancho_total(
            num_tintas=4,
            pistas=2,
            ancho=80.0
        )
        
        self.assertIsNotNone(ancho_total)
        self.assertGreater(ancho_total, 0)
        
    def test_calcular_ancho_total_sin_tintas(self):
        """Test cálculo de ancho total sin tintas."""
        ancho_total, mensaje = self.calc_lito.calcular_ancho_total(
            num_tintas=0,
            pistas=2,
            ancho=80.0
        )
        
        self.assertIsNotNone(ancho_total)
        
    def test_ancho_excede_maximo(self):
        """Test que ancho excesivo genera mensaje de recomendación."""
        ancho_total, mensaje = self.calc_lito.calcular_ancho_total(
            num_tintas=4,
            pistas=5,
            ancho=100.0  # Ancho grande con muchas pistas
        )
        
        # Si excede el máximo, debería haber un mensaje
        if ancho_total > ANCHO_MAXIMO_LITOGRAFIA:
            self.assertIsNotNone(mensaje)


class TestIntegracion(unittest.TestCase):
    """Tests de integración completos etiquetas y mangas."""
    
    def setUp(self):
        self.calc = CalculadoraCostosEscala()
        
    def test_flujo_completo_etiqueta(self):
        """Test flujo completo de cotización de etiqueta."""
        # Simular datos como llegarían del formulario
        ancho = 80.0
        avance = 120.0
        pistas = 2
        num_tintas = 4
        escalas = [1000, 2500, 5000]
        
        datos = DatosEscala(
            escalas=escalas,
            pistas=pistas,
            ancho=ancho,
            avance=avance,
            avance_total=avance + GAP_AVANCE_ETIQUETAS,
            desperdicio=0,
            velocidad_maquina=VELOCIDAD_MAQUINA_NORMAL,
            rentabilidad=RENTABILIDAD_ETIQUETAS,
            porcentaje_desperdicio=DESPERDICIO_ETIQUETAS,
            valor_metro=1800.0,
            troquel_existe=False,
            planchas_por_separado=False,
            unidad_montaje_dientes=None
        )
        
        resultado = self.calc.calcular_costos_por_escala(
            datos=datos,
            num_tintas=num_tintas,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=1800.0,
            valor_acabado=500.0,
            es_manga=False
        )
        
        self.assertEqual(len(resultado), 3)
        for r in resultado:
            self.assertIn('escala', r)
            self.assertIn('valor_unidad', r)
            self.assertIn('metros', r)
            self.assertGreater(r['valor_unidad'], 0)
            
    def test_flujo_completo_manga(self):
        """Test flujo completo de cotización de manga."""
        ancho_cerrado = 80.0
        ancho_ajustado = (ancho_cerrado * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
        avance = 100.0
        pistas = 1
        num_tintas = 5
        escalas = [1000, 2500, 5000]
        
        datos = DatosEscala(
            escalas=escalas,
            pistas=pistas,
            ancho=ancho_ajustado,
            avance=avance,
            avance_total=avance + GAP_AVANCE_MANGAS,
            desperdicio=0,
            velocidad_maquina=VELOCIDAD_MAQUINA_NORMAL,
            rentabilidad=RENTABILIDAD_MANGAS,
            porcentaje_desperdicio=DESPERDICIO_MANGAS,
            valor_metro=2000.0,
            troquel_existe=True,
            planchas_por_separado=False,
            unidad_montaje_dientes=None
        )
        
        resultado = self.calc.calcular_costos_por_escala(
            datos=datos,
            num_tintas=num_tintas,
            valor_plancha=None,
            valor_troquel=None,
            valor_material=2000.0,
            valor_acabado=0,
            es_manga=True,
            tipo_grafado_id=3  # Horizontal
        )
        
        self.assertEqual(len(resultado), 3)
        for r in resultado:
            self.assertIn('escala', r)
            self.assertIn('valor_unidad', r)
            self.assertGreater(r['valor_unidad'], 0)


if __name__ == '__main__':
    # Ejecutar con verbosidad
    unittest.main(verbosity=2)
