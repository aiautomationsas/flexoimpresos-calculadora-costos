import unittest
from src.logic.calculators.calculadora_costos_escala import CalculadoraCostosEscala, DatosEscala
from src.logic.calculators.calculadora_desperdicios import OpcionDesperdicio
from src.config.constants import (
    VELOCIDAD_MAQUINA_NORMAL, MO_MONTAJE, MO_IMPRESION, MO_TROQUELADO,
    VALOR_GR_TINTA, RENTABILIDAD_ETIQUETAS, DESPERDICIO_ETIQUETAS,
    ANCHO_MAXIMO_MAQUINA, GAP_PISTAS_ETIQUETAS, MM_COLOR, GAP_FIJO,
    INCREMENTO_ANCHO_SIN_TINTAS, INCREMENTO_ANCHO_TINTAS, 
    GAP_AVANCE_ETIQUETAS, GAP_AVANCE_MANGAS, MO_SELLADO, MO_CORTE,
    FACTOR_TINTA_AREA, CANTIDAD_TINTA_ESTANDAR, INCREMENTO_ANCHO_MANGAS
)

class TestCalculadoraCostosEscala(unittest.TestCase):

    def setUp(self):
        self.calc = CalculadoraCostosEscala()
        self.escalas_base = [1000]
        self.ancho_base = 80.0
        self.avance_base = 120.0
        self.pistas_base = 2
        self.valor_material_fijo = 1800.0
        self.valor_acabado_fijo = 500.0

        self.num_tintas_posibles = [0, 1, 4, 7]
        self.bool_opciones = [True, False]
        self.unidad_montaje_dientes_opciones = [None, 100.0]
        self.tipo_grafado_id_opciones = [None, 1, 4] # Para mangas

    def test_todas_las_combinaciones(self):
        print("\n--- INICIANDO TEST DE TODAS LAS COMBINACIONES ---")
        test_case_count = 0
        
        for es_manga in self.bool_opciones:
            for num_tintas in self.num_tintas_posibles:
                for troquel_existe in self.bool_opciones:
                    for planchas_por_separado in self.bool_opciones:
                        for unidad_montaje_dientes in self.unidad_montaje_dientes_opciones:
                            # Considerar tipo_grafado_id solo si es_manga es True
                            if es_manga:
                                for tipo_grafado_id in self.tipo_grafado_id_opciones:
                                    test_case_count += 1
                                    print(f"\n--- Ejecutando Caso de Prueba #{test_case_count} ---")
                                    print(f"Es Manga: {es_manga}, Tintas: {num_tintas}, Troquel Existe: {troquel_existe}, Planchas por Separado: {planchas_por_separado}, Unidad Montaje Dientes: {unidad_montaje_dientes}, Tipo Grafado ID: {tipo_grafado_id}")
                                    
                                    datos = DatosEscala(
                                        escalas=self.escalas_base,
                                        pistas=self.pistas_base,
                                        ancho=self.ancho_base,
                                        avance=self.avance_base,
                                        avance_total=0.0, # Se calcula internamente
                                        desperdicio=0.0, # Se calcula internamente
                                        troquel_existe=troquel_existe,
                                        planchas_por_separado=planchas_por_separado,
                                        unidad_montaje_dientes=unidad_montaje_dientes
                                    )
                                    
                                    try:
                                        resultados = self.calc.calcular_costos_por_escala(
                                            datos=datos,
                                            num_tintas=num_tintas,
                                            valor_plancha=None, # Dejar que se calcule
                                            valor_troquel=None, # Dejar que se calcule
                                            valor_material=self.valor_material_fijo,
                                            valor_acabado=self.valor_acabado_fijo,
                                            es_manga=es_manga,
                                            tipo_grafado_id=tipo_grafado_id
                                        )
                                        self.assertIsNotNone(resultados)
                                        self.assertGreater(len(resultados), 0)
                                        print(f"Resultados calculados exitosamente para la escala {resultados[0]['escala']}:")
                                        for key, value in resultados[0].items():
                                            if isinstance(value, float):
                                                print(f"  {key}: {value:.2f}")
                                            else:
                                                print(f"  {key}: {value}")
                                    except Exception as e:
                                        self.fail(f"Fallo en la combinación (Manga): {e}")
                            else: # Es etiqueta
                                test_case_count += 1
                                print(f"\n--- Ejecutando Caso de Prueba #{test_case_count} ---")
                                print(f"Es Manga: {es_manga}, Tintas: {num_tintas}, Troquel Existe: {troquel_existe}, Planchas por Separado: {planchas_por_separado}, Unidad Montaje Dientes: {unidad_montaje_dientes}")
                                
                                datos = DatosEscala(
                                    escalas=self.escalas_base,
                                    pistas=self.pistas_base,
                                    ancho=self.ancho_base,
                                    avance=self.avance_base,
                                    avance_total=0.0, # Se calcula internamente
                                    desperdicio=0.0, # Se calcula internamente
                                    troquel_existe=troquel_existe,
                                    planchas_por_separado=planchas_por_separado,
                                    unidad_montaje_dientes=unidad_montaje_dientes
                                )
                                
                                try:
                                    resultados = self.calc.calcular_costos_por_escala(
                                        datos=datos,
                                        num_tintas=num_tintas,
                                        valor_plancha=None,
                                        valor_troquel=None,
                                        valor_material=self.valor_material_fijo,
                                        valor_acabado=self.valor_acabado_fijo,
                                        es_manga=es_manga
                                    )
                                    self.assertIsNotNone(resultados)
                                    self.assertGreater(len(resultados), 0)
                                    print(f"Resultados calculados exitosamente para la escala {resultados[0]['escala']}:")
                                    for key, value in resultados[0].items():
                                        if isinstance(value, float):
                                            print(f"  {key}: {value:.2f}")
                                        else:
                                            print(f"  {key}: {value}")
                                except Exception as e:
                                    self.fail(f"Fallo en la combinación (Etiqueta): {e}")

        print(f"--- {test_case_count} Casos de Prueba Ejecutados ---")

if __name__ == '__main__':
    unittest.main()
