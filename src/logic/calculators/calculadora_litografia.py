from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import math
from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio, OpcionDesperdicio
from src.logic.calculators.calculadora_base import CalculadoraBase
from src.config.constants import (
    GAP_PISTAS_ETIQUETAS, GAP_AVANCE_ETIQUETAS, ANCHO_MAXIMO_LITOGRAFIA,
    VALOR_MM_PLANCHA, INCREMENTO_ANCHO_SIN_TINTAS, INCREMENTO_ANCHO_TINTAS
)

class DatosLitografia:
    """
    Clase para almacenar los datos necesarios para los cálculos de litografía.
    """
    def __init__(self, ancho: float, avance: float, pistas: int = 1,
                 planchas_por_separado: bool = True, incluye_troquel: bool = True,
                 troquel_existe: bool = False, gap: float = GAP_PISTAS_ETIQUETAS, 
                 gap_avance: float = GAP_AVANCE_ETIQUETAS, ancho_maximo: float = ANCHO_MAXIMO_LITOGRAFIA,
                 tipo_grafado: Optional[str] = None):
        self.ancho = ancho
        self.avance = avance
        self.pistas = pistas
        self.planchas_por_separado = planchas_por_separado
        self.incluye_troquel = incluye_troquel
        self.troquel_existe = troquel_existe
        self.gap = gap
        self.gap_avance = gap_avance
        self.ancho_maximo = ancho_maximo
        self.tipo_grafado = tipo_grafado
        # Calcular constante de troquel basada en el tipo de grafado
        self.constante_troquel = 1 if tipo_grafado == "Horizontal Total + Vertical" else 2

class CalculadoraLitografia(CalculadoraBase):
    """
    Calculadora para litografía que maneja los cálculos específicos de este proceso.
    """
    
    # Constantes específicas de litografía
    VALOR_MM_PLANCHA = VALOR_MM_PLANCHA  # Valor por mm de plancha
    ANCHO_MAXIMO = ANCHO_MAXIMO_LITOGRAFIA  # Ancho máximo permitido en mm
    
    def __init__(self):
        """Inicializa la calculadora de litografía."""
        super().__init__()
        self._calculadora_desperdicios = None
        self._calculadora_desperdicios_manga = None

    @property
    def calculadora_desperdicios(self) -> CalculadoraDesperdicio:
        """Devuelve la calculadora de desperdicios actual"""
        if self._calculadora_desperdicios is None:
            self._calculadora_desperdicios = CalculadoraDesperdicio(
                ancho_maquina=self.ANCHO_MAXIMO,
                gap_mm=GAP_AVANCE_ETIQUETAS  # Este gap solo se usa para etiquetas
            )
        return self._calculadora_desperdicios

    def _get_calculadora_desperdicios(self, es_manga: bool = False) -> CalculadoraDesperdicio:
        """
        Obtiene una instancia de CalculadoraDesperdicio configurada según el tipo
        """
        return CalculadoraDesperdicio(
            ancho_maquina=self.ANCHO_MAXIMO,
            gap_mm=GAP_AVANCE_ETIQUETAS,  # Este gap solo se usa para etiquetas
            es_manga=es_manga
        )

    def calcular_ancho_total(self, num_tintas: int, pistas: int, ancho: float) -> Tuple[float, Optional[str]]:
        """
        Calcula el ancho total según la fórmula:
        ROUNDUP(IF(B2=0, ((E3*D3-C3)+10), ((E3*D3-C3)+20)), -1)
        """
        # Usar el GAP de la clase base
        C3 = 0 if pistas <= 1 else self.GAP
        
        # Calcular D3 = ancho + C3
        d3 = ancho + C3
        
        # Calcular base = pistas * D3 - C3
        base = pistas * d3 - C3
        
        # Incremento según número de tintas
        incremento = INCREMENTO_ANCHO_SIN_TINTAS if num_tintas == 0 else INCREMENTO_ANCHO_TINTAS
        
        # Calcular resultado
        resultado = base + incremento
        
        # Redondear hacia arriba al siguiente múltiplo de 10
        ancho_redondeado = math.ceil(resultado / 10) * 10
        
        mensaje = None
        if ancho_redondeado > self.ANCHO_MAXIMO:
            # Excepción solicitada: ignorar advertencia para etiquetas de 50mm a 6 pistas
            es_caso_excepcion = (abs(ancho - 50.0) < 0.01 and int(pistas) == 6)
            if es_caso_excepcion:
                return ancho_redondeado, None
            # Calcular pistas recomendadas
            ancho_con_gap = ancho + C3
            pistas_recomendadas = math.floor((self.ANCHO_MAXIMO - incremento + C3) / ancho_con_gap)
            
            if ancho > self.ANCHO_MAXIMO:
                mensaje = f"ERROR: El ancho base ({ancho}mm) excede el máximo permitido ({self.ANCHO_MAXIMO}mm)"
            else:
                mensaje = f"ADVERTENCIA: El ancho total calculado ({ancho_redondeado}mm) excede el máximo permitido ({self.ANCHO_MAXIMO}mm). Se recomienda usar {pistas_recomendadas} pistas o menos."
        
        return ancho_redondeado, mensaje

    def calcular_desperdicio(self, datos: DatosLitografia, es_manga: bool = False) -> Dict:
        """
        Calcula el desperdicio y las opciones de impresión usando la calculadora de desperdicios
        """
        calculadora = self._get_calculadora_desperdicios(es_manga)
        return calculadora.generar_reporte(datos.avance)

    def obtener_mejor_opcion_desperdicio(self, datos: DatosLitografia, es_manga: bool = False) -> Optional[OpcionDesperdicio]:
        """
        Obtiene la mejor opción de desperdicio según el tipo de producto
        """
        calculadora = self._get_calculadora_desperdicios(es_manga)
        opciones = calculadora.calcular_todas_opciones(datos.avance)
        if not opciones:
            raise ValueError("No se encontraron opciones válidas para el avance especificado")
        
        return opciones[0]  # Ya está ordenado por desperdicio absoluto y dientes

    def validar_medidas(self, datos: DatosLitografia) -> bool:
        """
        Valida que las medidas estén dentro de los rangos permitidos
        """
        if datos.ancho <= 0:
            raise ValueError("El ancho debe ser mayor a 0")
        if datos.avance <= 0:
            raise ValueError("El avance debe ser mayor a 0")
        if datos.pistas <= 0:
            raise ValueError("El número de pistas debe ser mayor a 0")
        
        return True

    def calcular_precio_plancha(self, datos: DatosLitografia, num_tintas: int = 0, es_manga: bool = False) -> Dict:
        """
        Calcula el precio de la plancha utilizando el método base en CalculadoraBase.
        """
        try:
            print("\n=== INICIO CÁLCULO DE PLANCHA (Refactorizado) ===")
            print(f"Datos de entrada: Ancho={datos.ancho}, Pistas={datos.pistas}, Tintas={num_tintas}, Manga={es_manga}")
            
            # 1. Calcular Q3 (ancho total ajustado)
            q3_result = self._calcular_q3(num_tintas, datos.ancho, datos.pistas, es_manga)
            q3 = q3_result['q3']
            c3 = q3_result['c3']
            d3 = q3_result['d3']
            
            # 2. Calcular S3
            s3 = self.GAP_FIJO + q3
            
            # 3. Obtener mm de la unidad de montaje
            mejor_opcion = self.obtener_mejor_opcion_desperdicio(datos, es_manga)
            if not mejor_opcion:
                raise ValueError("No se pudo determinar la unidad de montaje")
            mm_unidad_montaje = mejor_opcion.medida_mm
            
            # 4. Llamar al método base para el cálculo
            resultado_base = self.calcular_precio_plancha_base(
                s3=s3,
                mm_unidad_montaje=mm_unidad_montaje,
                num_tintas=num_tintas,
                planchas_por_separado=datos.planchas_por_separado
            )
            
            # Enriquecer los detalles con información específica de Litografía para mantener compatibilidad
            resultado_base['detalles'].update({
                'q3': q3,
                'c3': c3,
                'd3': d3,
                'gap_fijo': self.GAP_FIJO,
                'es_manga': es_manga
            })
            
            return resultado_base
            
        except Exception as e:
            print(f"Error en cálculo de precio de plancha: {str(e)}")
            return {
                'precio': 0,
                'error': str(e),
                'detalles': None
            }

    def calcular_valor_troquel(self, datos: DatosLitografia, repeticiones: int, 
                            valor_mm: float = 100, troquel_existe: bool = False, 
                            tipo_grafado_id: Optional[int] = None, 
                            es_manga: bool = False) -> Dict:
        """
        Calcula el valor del troquel utilizando el método base en CalculadoraBase.
        """
        try:
            print("\n=== INICIO CÁLCULO TROQUEL (Refactorizado) ===")
            
            # Convertir tipo_grafado str a ID si es necesario (para compatibilidad con lógica base que espera ID)
            # Nota: CalculadoraBase usa IDs (1, 4) para mangas.
            # Si datos.tipo_grafado es string, mapearlo a ID 4 si es "Horizontal Total + Vertical", o dejar None
            tipo_grafado_id_final = tipo_grafado_id
            if tipo_grafado_id is None and datos.tipo_grafado == "Horizontal Total + Vertical":
                 tipo_grafado_id_final = 4
            
            resultado = self.calcular_valor_troquel_base(
                ancho=datos.ancho,
                avance=datos.avance,
                pistas=datos.pistas,
                repeticiones=repeticiones,
                es_manga=es_manga,
                troquel_existe=troquel_existe,
                tipo_grafado_id=tipo_grafado_id_final
            )
            
            return resultado
            
        except Exception as e:
            print(f"ERROR en cálculo troquel: {str(e)}")
            return {
                'error': str(e),
                'valor': 700000.0, # Valor mínimo por defecto en caso de error
                'detalles': {'error': str(e)}
            }

    def calcular_area_etiqueta(self, datos: DatosLitografia, num_tintas: int, 
                              medida_montaje: float, repeticiones: int, es_manga: bool = False) -> Dict:
        """
        Calcula el área de la etiqueta utilizando el método base en CalculadoraBase.
        """
        try:
            # 1. Calcular Q3 y S3
            q3_result = self._calcular_q3(num_tintas, datos.ancho, datos.pistas, es_manga)
            q3 = q3_result['q3']
            s3 = self.GAP_FIJO + q3
            
            # 2. Llamar al método base
            resultado = self.calcular_area_etiqueta_base(
                q3=q3,
                s3=s3,
                pistas=datos.pistas,
                medida_montaje=medida_montaje,
                repeticiones=repeticiones,
                num_tintas=num_tintas
            )
            
            # 3. Enriquecer con datos específicos de etiquetas si es necesario
            if not es_manga:
                f3 = self.calcular_ancho_total(num_tintas, datos.pistas, datos.ancho)
                # (Recalcular detalles de f3 si es necesario para debug, como en el código original,
                # o dejarlos fuera si no son críticos)
                # Mantener compatibilidad agregando F3 a detalles
                if isinstance(f3, tuple):
                     resultado['detalles']['f3'] = f3[0]
                else:
                     resultado['detalles']['f3'] = f3

            resultado['detalles']['es_manga'] = es_manga
            resultado['detalles']['gap_fijo'] = self.GAP_FIJO
            # Agregar c3 y d3 que se calculaban antes
            resultado['detalles']['c3'] = q3_result['c3']
            resultado['detalles']['d3'] = q3_result['d3']
            
            return resultado
            
        except Exception as e:
            print(f"Error en cálculo de área de etiqueta: {str(e)}")
            return {
                'error': str(e),
                'area': None,
                'detalles': None
            }
    
    def calcular_valor_tinta_etiqueta(self, area_etiqueta: float, num_tintas: int) -> Dict:
        """
        Calcula el valor de la tinta por etiqueta.
        """
        try:
            # Calcular valor por etiqueta
            valor_etiqueta = num_tintas * self.VALOR_MM2_TINTA * area_etiqueta
            
            return {
                'valor': valor_etiqueta,
                'detalles': {
                    'gramos_m2': self.GRAMOS_M2_TINTA,
                    'valor_mm2': self.VALOR_MM2_TINTA,
                    'area_etiqueta': area_etiqueta,
                    'num_tintas': num_tintas
                }
            }
        except Exception as e:
            return {
                'error': str(e),
                'valor': None,
                'detalles': None
            }
            
    def generar_reporte_completo(self, datos: DatosLitografia, num_tintas: int, es_manga: bool = False) -> Dict:
        """Genera un reporte completo con todos los cálculos"""
        try:
            # Inicializar resultado con valores por defecto
            resultado = {
                'ancho_total': self.calcular_ancho_total(num_tintas, datos.pistas, datos.ancho),
                'valor_tinta': 0  # Inicializar valor_tinta a 0 por defecto
            }
            
            # Cálculo de desperdicio
            resultado['desperdicio'] = self.calcular_desperdicio(datos, es_manga)
            
            # Obtener mejor opción de desperdicio
            mejor_opcion = self.obtener_mejor_opcion_desperdicio(datos, es_manga)
            
            if not mejor_opcion:
                return {
                    'error': 'No se encontró una opción válida de desperdicio',
                    'detalles': 'Revise los valores de ancho y avance'
                }
            
            # Cálculo de precio de plancha
            resultado['precio_plancha'] = self.calcular_precio_plancha(datos, num_tintas, es_manga)
            
            # Cálculo de valor de troquel
            if datos.incluye_troquel:
                resultado['valor_troquel'] = self.calcular_valor_troquel(
                    datos,
                    mejor_opcion.repeticiones,
                    troquel_existe=datos.troquel_existe,
                    es_manga=es_manga
                )
            
            # Cálculo de área de etiqueta
            calculo_area = self.calcular_area_etiqueta(
                datos, 
                num_tintas, 
                mejor_opcion.medida_mm, 
                mejor_opcion.repeticiones,
                es_manga
            )
            resultado['area_etiqueta'] = calculo_area
            resultado['unidad_montaje_sugerida'] = mejor_opcion.dientes
                
            # Calcular valor de tinta solo si hay tintas y el área se calculó correctamente
            if num_tintas > 0 and isinstance(calculo_area, dict) and 'area' in calculo_area and calculo_area['area'] is not None:
                try:
                    calculo_tinta = self.calcular_valor_tinta_etiqueta(
                        calculo_area['area'],
                        num_tintas
                    )
                    if isinstance(calculo_tinta, dict) and 'valor' in calculo_tinta and calculo_tinta['valor'] is not None:
                        resultado['valor_tinta'] = calculo_tinta['valor']
                    else:
                        print("Advertencia: El cálculo de tinta no devolvió un valor válido")
                except Exception as e:
                    print(f"Error al calcular valor de tinta: {str(e)}")
            else:
                print(f"No se calculó valor de tinta: num_tintas={num_tintas}, area_calculada={'Si' if isinstance(calculo_area, dict) and 'area' in calculo_area else 'No'}")
            
            return resultado
        except Exception as e:
            return {
                'error': str(e),
                'detalles': 'Error al generar el reporte completo',
                'valor_tinta': 0  # Asegurar que valor_tinta esté presente incluso en caso de error
            }

    def generar_debug_info(self, datos: DatosLitografia, num_tintas: int = 0, es_manga: bool = False) -> Dict:
        """
        Genera información detallada de depuración para comparar con Excel
        """
        debug_info = {
            "entradas": {
                "ancho": datos.ancho,
                "avance": datos.avance,
                "pistas": datos.pistas,
                "num_tintas": num_tintas,
                "es_manga": es_manga,
                "gap": datos.gap,
                "gap_avance": datos.gap_avance,
                "planchas_por_separado": datos.planchas_por_separado,
                "incluye_troquel": datos.incluye_troquel,
                "troquel_existe": datos.troquel_existe
            },
            "calculos_intermedios": {},
            "resultados": {}
        }
        
        try:
            # 1. Ancho total
            ancho_total = self.calcular_ancho_total(num_tintas, datos.pistas, datos.ancho)
            debug_info["calculos_intermedios"]["ancho_total"] = ancho_total
            
            # 2. Desperdicio
            reporte_desperdicio = self.calcular_desperdicio(datos, es_manga)
            debug_info["calculos_intermedios"]["reporte_desperdicio"] = reporte_desperdicio
            
            # Extraer datos de la mejor opción de desperdicio
            if reporte_desperdicio.get("mejor_opcion"):
                mejor_opcion = reporte_desperdicio["mejor_opcion"]
                debug_info["calculos_intermedios"]["mejor_opcion"] = {
                    "dientes": mejor_opcion.get("dientes"),
                    "repeticiones": mejor_opcion.get("repeticiones"),
                    "medida_mm": mejor_opcion.get("medida_mm"),
                    "desperdicio": mejor_opcion.get("desperdicio")
                }
            
            # 3. Precio de plancha (con detalles extendidos)
            calculo_plancha = self.calcular_precio_plancha(datos, num_tintas, es_manga)
            debug_info["calculos_intermedios"]["calculo_plancha"] = calculo_plancha
            
            # Agregar detalles adicionales del cálculo de la plancha
            if calculo_plancha.get("detalles"):
                detalles = calculo_plancha["detalles"]
                debug_info["calculos_intermedios"]["plancha_desglose"] = {
                    "valor_mm": detalles.get("valor_mm_plancha"), # Updated key
                    "gap_fijo": detalles.get("gap_fijo"),
                    "avance_fijo": detalles.get("avance_fijo"),
                    "ancho_total": detalles.get("ancho_total"),
                    "mm_unidad_montaje": detalles.get("mm_unidad_montaje"),
                    "s3": detalles.get("s3"),
                    "s4": detalles.get("s4"),
                    "formula": f"{detalles.get('valor_mm_plancha')} * {detalles.get('s3')} * {detalles.get('s4')} * {detalles.get('num_tintas')}",
                    "resultado": calculo_plancha.get("precio")
                }
            
            # 4. Área de etiqueta (factor crucial)
            area_etiqueta = None
            if reporte_desperdicio.get("mejor_opcion"):
                mejor_opcion = reporte_desperdicio["mejor_opcion"]
                calculo_area = self.calcular_area_etiqueta(
                    datos=datos, 
                    num_tintas=num_tintas,
                    medida_montaje=mejor_opcion.get("medida_mm"),
                    repeticiones=mejor_opcion.get("repeticiones"),
                    es_manga=es_manga
                )
                area_etiqueta = calculo_area.get("area")
                debug_info["calculos_intermedios"]["area_etiqueta"] = {
                    "valor": area_etiqueta,
                    "detalles": calculo_area.get("detalles")
                }
            
            # 5. Valor de tinta por etiqueta
            if area_etiqueta:
                calculo_tinta = self.calcular_valor_tinta_etiqueta(
                    area_etiqueta=area_etiqueta,
                    num_tintas=num_tintas
                )
                debug_info["calculos_intermedios"]["valor_tinta"] = {
                    "valor": calculo_tinta.get("valor"),
                    "detalles": calculo_tinta.get("detalles")
                }
            
            # 6. Valor de troquel
            if datos.incluye_troquel and reporte_desperdicio.get("mejor_opcion"):
                mejor_opcion = reporte_desperdicio["mejor_opcion"]
                calculo_troquel = self.calcular_valor_troquel(
                    datos=datos,
                    repeticiones=mejor_opcion.get("repeticiones"),
                    troquel_existe=datos.troquel_existe,
                    es_manga=es_manga
                )
                debug_info["calculos_intermedios"]["valor_troquel"] = {
                    "valor": calculo_troquel.get("valor"),
                    "detalles": calculo_troquel.get("detalles")
                }
            
            # 7. Comparación directa con valores del Excel
            debug_info["comparacion_excel"] = {
                "ancho": datos.ancho,
                "avance": datos.avance,
                "pistas": datos.pistas,
                "tintas": num_tintas,
                "area_etiqueta": area_etiqueta,
                "valor_plancha": calculo_plancha.get("precio"),
                "valor_plancha_por_tinta": calculo_plancha.get("precio") / num_tintas if num_tintas > 0 else 0,
                "desperdicio_mm": mejor_opcion.get("desperdicio") if reporte_desperdicio.get("mejor_opcion") else None,
                "dientes": mejor_opcion.get("dientes") if reporte_desperdicio.get("mejor_opcion") else None
            }
            
            return debug_info
            
        except Exception as e:
            debug_info["error"] = str(e)
            return debug_info

    def calcular_desperdicio_por_escala(self, datos: DatosLitografia, num_tintas: int, valor_material_mm2: float, escala: int, es_manga: bool = False) -> Dict:
        """
        Calcula el desperdicio por escala.
        """
        try:
            # 1. Obtener S3 del cálculo de planchas
            calculo_plancha = self.calcular_precio_plancha(datos, num_tintas, es_manga)
            
            # Verificar si calculo_plancha tiene la estructura esperada
            if isinstance(calculo_plancha, dict) and ('error' in calculo_plancha or 'detalles' not in calculo_plancha):
                return {
                    'error': 'No se pudo calcular el precio de plancha correctamente',
                    'valor': 0,
                    'detalles': {
                        's3': 0,
                        's7': 0,
                        'o7': 0,
                        'desperdicio_total': 0,
                        'es_manga': es_manga
                    }
                }
            
            s3 = calculo_plancha['detalles']['s3']
            
            # 2. Calcular S7 (mm por color)
            s7 = 30000 * num_tintas if num_tintas > 0 else 0
            
            # 3. O7 es el precio por mm² del material
            o7 = valor_material_mm2 / 1000000  # Convertir a millones
            
            if es_manga:
                # Para mangas, el desperdicio es simplemente S7 * S3 * O7
                desperdicio_total = s7 * s3 * o7
            else:
                # 4. Primera parte: (s3 * s7 * o7)
                primera_parte = s3 * s7 * o7
                
                # 5. Calcular papel/lam directamente sin usar CalculadoraCostosEscala
                mejor_opcion = self.obtener_mejor_opcion_desperdicio(datos, es_manga)
                calculo_area = self.calcular_area_etiqueta(
                    datos, 
                    num_tintas, 
                    mejor_opcion.medida_mm, 
                    mejor_opcion.repeticiones,
                    es_manga
                )
                area_etiqueta = calculo_area['area']
                papel_lam = area_etiqueta * valor_material_mm2 * escala
                
                # 6. Segunda parte: 10% del papel/lam
                segunda_parte = 0.1 * papel_lam
                
                # 7. Desperdicio total para etiquetas
                desperdicio_total = primera_parte + segunda_parte
            
            # Debug info consolidado
            print(f"\n=== CÁLCULO DE DESPERDICIO ({('MANGA' if es_manga else 'ETIQUETA')}, Escala {escala}) ===")
            print(f"1. Fórmula: {'S7 * S3 * O7' if es_manga else '(s3 * s7 * o7) + (10% * Papel/lam)'}")
            print(f"2. Valores:")
            print(f"   - s3 (Gap + {'Q3' if es_manga else 'Ancho Total'}): {s3} mm")
            print(f"   - s7 (mm por color): {s7} mm")
            print(f"   - o7 (precio material): ${o7:.8f}/mm²")
            if es_manga:
                print(f"   - Desperdicio total (S7 * S3 * O7): ${desperdicio_total:.2f}")
            else:
                print(f"   - Primera parte (s3 * s7 * o7): ${primera_parte:.2f}")
                print(f"   - Papel/lam: ${papel_lam:.2f}")
                print(f"   - Segunda parte (10% * Papel/lam): ${segunda_parte:.2f}")
                print(f"   - Desperdicio total: ${desperdicio_total:.2f}")
            
            detalles = {
                's3': s3,
                's7': s7,
                'o7': o7,
                'desperdicio_total': desperdicio_total,
                'es_manga': es_manga
            }
            
            if not es_manga:
                detalles.update({
                    'primera_parte': primera_parte,
                    'papel_lam': papel_lam,
                    'segunda_parte': segunda_parte,
                    'area_etiqueta': area_etiqueta
                })
            
            return {
                'valor': desperdicio_total,
                'detalles': detalles
            }
        except Exception as e:
            print(f"Error al calcular desperdicio: {str(e)}")
            return {
                'error': str(e),
                'valor': 0,
                'detalles': {
                    's3': 0,
                    's7': 0,
                    'o7': 0,
                    'desperdicio_total': 0,
                    'es_manga': es_manga
                }
            }

    def calcular_desperdicio_escala_completo(self, datos: DatosLitografia, num_tintas: int, valor_material_mm2: float = 1800.0, es_manga: bool = False) -> Dict:
        """
        Calcula el desperdicio para diferentes escalas de producción
        """
        escalas = [1000, 2000, 3000, 5000]
        resultados_desperdicio = {}
        
        # Obtener S3 una sola vez para todas las escalas
        calculo_plancha = self.calcular_precio_plancha(datos, num_tintas, es_manga)
        
        # Verificar si calculo_plancha tiene la estructura esperada
        if isinstance(calculo_plancha, dict) and ('error' in calculo_plancha or 'detalles' not in calculo_plancha):
            return {'error': 'No se pudo calcular el precio de plancha correctamente'}
        
        s3 = calculo_plancha['detalles']['s3']
        
        print("\n=== RESUMEN DE DESPERDICIOS POR ESCALA ===")
        print(f"Tipo: {'MANGA' if es_manga else 'ETIQUETA'}")
        print(f"S3 (Gap + {'Q3' if es_manga else 'Ancho Total'}): {s3} mm")
        print(f"Número de tintas: {num_tintas}")
        print(f"Valor material: ${valor_material_mm2}/mm²\n")
        
        for escala in escalas:
            resultado = self.calcular_desperdicio_por_escala(datos, num_tintas, valor_material_mm2, escala, es_manga)
            resultados_desperdicio[escala] = resultado
        
        return resultados_desperdicio

    def obtener_input_numerico(self, mensaje: str, minimo: float = 0.1) -> float:
        """Obtiene un input numérico con validación"""
        while True:
            try:
                valor = float(input(mensaje))
                if valor < minimo:
                    print(f"El valor debe ser mayor a {minimo}")
                    continue
                return valor
            except ValueError:
                print("Por favor ingrese un número válido")

    def _print_info_global(self, num_tintas: int, ancho_total: float, valor_material: float):
        print("\n=== INFORMACIÓN GLOBAL ===")
        print(f"Número de tintas: {num_tintas}")
        print(f"Ancho total: {ancho_total:.2f} mm")  # Usar el ancho_total pasado como parámetro
        print(f"Gap fijo: {self.GAP_FIJO} mm")
        print(f"Valor material: ${valor_material:f}/mm²")

    def calcular_precio_troquel(self, datos: DatosLitografia) -> Dict:
        """
        Calcula el precio del troquel según la fórmula:
        Precio troquel = (ancho + avance) * 1800
        """
        try:
            precio_troquel = (datos.ancho + datos.avance) * 1800
            
            return {
                'valor': precio_troquel,
                'detalles': {
                    'ancho': datos.ancho,
                    'avance': datos.avance
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def _calcular_q3(self, num_tintas: int, ancho: float, pistas: int, es_manga: bool = False) -> Dict:
        """
        Método auxiliar para calcular Q3, C3 y D3 para cálculos de área y precio.
        Este método es un wrapper del método de la clase base para mantener compatibilidad.
        """
        return self.calcular_q3(ancho, pistas, es_manga)
