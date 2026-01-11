from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional # Added Optional here
import math
import pandas as pd
from src.logic.calculators.calculadora_base import CalculadoraBase
from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio
from src.config.constants import (
    VELOCIDAD_MAQUINA_NORMAL, MO_MONTAJE, MO_IMPRESION, MO_TROQUELADO,
    VALOR_GR_TINTA, RENTABILIDAD_ETIQUETAS, DESPERDICIO_ETIQUETAS,
    ANCHO_MAXIMO_MAQUINA, GAP_PISTAS_ETIQUETAS, MM_COLOR, GAP_FIJO,
    INCREMENTO_ANCHO_SIN_TINTAS, INCREMENTO_ANCHO_TINTAS, 
    GAP_AVANCE_ETIQUETAS, GAP_AVANCE_MANGAS, MO_SELLADO, MO_CORTE,
    FACTOR_TINTA_AREA, CANTIDAD_TINTA_ESTANDAR, INCREMENTO_ANCHO_MANGAS
)

@dataclass
class DatosEscala:
    """
    Clase para almacenar los datos necesarios para los cálculos por escala.
    
    Esta clase encapsula todos los parámetros requeridos para realizar cálculos
    de costos por escala, incluyendo dimensiones, configuración de producción,
    y valores fijos para cálculos.
    """
    escalas: List[int]
    pistas: int
    ancho: float  # Ancho base para calcular ancho_total
    avance: float  # Avance en mm
    avance_total: Optional[float] = None  # Ahora es opcional y por defecto None
    desperdicio: float = 0.0 # Añadido valor por defecto
    velocidad_maquina: float = VELOCIDAD_MAQUINA_NORMAL  # Valor fijo desde constants.py
    mo_montaje: float = MO_MONTAJE  # Valor fijo desde constants.py
    mo_impresion: float = MO_IMPRESION  # Valor fijo desde constants.py
    mo_troquelado: float = MO_TROQUELADO  # Valor fijo desde constants.py
    valor_gr_tinta: float = VALOR_GR_TINTA  # Valor fijo desde constants.py
    rentabilidad: float = RENTABILIDAD_ETIQUETAS  # Valor por defecto para etiquetas desde constants.py
    area_etiqueta: float = 0.0  # Se calcula o se recibe
    porcentaje_desperdicio: float = DESPERDICIO_ETIQUETAS  # Porcentaje de desperdicio por defecto desde constants.py
    valor_metro: float = 0.0  # Valor del metro de material
    troquel_existe: bool = False  # Si ya existe el troquel
    planchas_por_separado: bool = False  # Si las planchas se cobran por separado
    unidad_montaje_dientes: Optional[float] = None  # Unidad de montaje elegida (opcional)
    
    def __post_init__(self):
        """Asegurar que troquel_existe sea siempre un booleano"""
        # Convertir explícitamente a booleano para evitar problemas con tipos
        if not isinstance(self.troquel_existe, bool):
            print(f"ADVERTENCIA: troquel_existe no es booleano, es {type(self.troquel_existe)}. Valor: {self.troquel_existe}")
            if isinstance(self.troquel_existe, str):
                if self.troquel_existe == "Sí":
                    self.troquel_existe = True
                elif self.troquel_existe == "No":
                    self.troquel_existe = False
                else:
                    self.troquel_existe = self.troquel_existe.lower() in ('true', 'yes', '1')
            else:
                self.troquel_existe = bool(self.troquel_existe)
        
        print(f"RESULTADO FINAL __post_init__: troquel_existe = {self.troquel_existe} (tipo: {type(self.troquel_existe)})")

    def set_area_etiqueta(self, area: float):
        """Set the area of the label."""
        self.area_etiqueta = area

class CalculadoraCostosEscala(CalculadoraBase):
    """
    Clase para calcular los costos por escala.
    
    Esta clase proporciona métodos para calcular costos de producción
    basados en diferentes escalas, incluyendo costos de materiales,
    mano de obra, desperdicios, y otros factores relevantes.
    """
    
    def __init__(self, ancho_maximo: float = ANCHO_MAXIMO_MAQUINA):
        """
        Inicializa la calculadora de costos por escala.
        
        Args:
            ancho_maximo: Ancho máximo de la máquina en mm
        """
        super().__init__()
        self.ANCHO_MAXIMO = ancho_maximo
        self.GAP = GAP_PISTAS_ETIQUETAS  # GAP entre pistas desde constants.py
        
        # Constantes para cálculos
        self.C3 = self.GAP  # GAP fijo para cálculos
        self.MM_COLOR = MM_COLOR  # MM de color para cálculo de desperdicio desde constants.py
        self.GAP_FIJO = GAP_FIJO  # R3 es 50 tanto para mangas como etiquetas desde constants.py
        self.VALOR_MM_PLANCHA = 1.5  # Valor por mm de plancha
        self.GAP_AVANCE_ETIQUETAS = GAP_AVANCE_ETIQUETAS # Añadido
        self.GAP_AVANCE_MANGA = GAP_AVANCE_MANGAS # Añadido

    def _get_calculadora_desperdicios(self, es_manga: bool = False) -> CalculadoraDesperdicio:
        """
        Obtiene una instancia de CalculadoraDesperdicio configurada según el tipo
        """
        return CalculadoraDesperdicio(
            ancho_maquina=self.ANCHO_MAXIMO,
            gap_mm=self.GAP,
            es_manga=es_manga
        )

    def _debug_datos_entrada(
        self,
        datos: DatosEscala,
        num_tintas: int,
        valor_plancha: float,
        valor_troquel: float,
        valor_material: float,
        valor_acabado: float,
        es_manga: bool
    ) -> None:
        """Imprime información de debug sobre los datos de entrada"""
        print("\n=== DATOS DE ENTRADA PARA CÁLCULO DE COSTOS ===")
        print(f"Número de tintas: {num_tintas}")
        # Handle None for valor_plancha
        valor_plancha_str = f"${valor_plancha:.2f}" if valor_plancha is not None else "N/A (Calculado)"
        print(f"Valor plancha: {valor_plancha_str}")
        print(f"Valor troquel: ${valor_troquel:.2f}")
        print(f"Valor material: ${valor_material:.2f}")
        print(f"Valor acabado: ${valor_acabado:.2f}")
        print(f"Es manga: {es_manga}")
        print(f"Área etiqueta: {datos.area_etiqueta:.2f} mm²")
        print(f"Ancho: {datos.ancho:.2f} mm")
        print(f"Avance: {datos.avance:.2f} mm")
        print(f"Pistas: {datos.pistas}")
        print(f"Troquel existe: {datos.troquel_existe}")
        print(f"Planchas por separado: {datos.planchas_por_separado}")
        print("="*50 + "\n")

    def _calcular_s3(self, avance: float, es_manga: bool = False) -> Dict:
        """
        Calcula S3 (avance total) basado en el avance y tipo de trabajo.
        Retorna un diccionario con el valor de S3 y detalles del cálculo.
        """
        try:
            # Validaciones iniciales
            if avance <= 0:
                raise ValueError("El avance debe ser mayor que 0")
            
            # Cálculo base de S3
            s3_base = avance
            
            # Ajustes según tipo de trabajo
            if es_manga:
                s3_final = s3_base + self.GAP_AVANCE_MANGA
            else:
                s3_final = s3_base + self.GAP_AVANCE_ETIQUETAS
            
            # Validación final
            if s3_final > self.ANCHO_MAXIMO:
                raise ValueError(f"El avance total ({s3_final:.2f} mm) excede el máximo permitido ({self.ANCHO_MAXIMO} mm)")
            
            print(f"\n=== CÁLCULO DE S3 ===")
            print(f"Avance base: {s3_base:.2f} mm")
            print(f"Gap de avance: {self.GAP_AVANCE_MANGA if es_manga else self.GAP_AVANCE_ETIQUETAS} mm")
            print(f"S3 final: {s3_final:.2f} mm")
            
            return {
                's3': s3_final,
                'detalles': {
                    's3_base': s3_base,
                    'gap_avance': self.GAP_AVANCE_MANGA if es_manga else self.GAP_AVANCE_ETIQUETAS,
                    'es_manga': es_manga
                }
            }
            
        except Exception as e:
            print(f"Error en cálculo de S3: {str(e)}")
            return {
                'error': str(e),
                's3': 0,
                'detalles': None
            }
        
    def calcular_ancho_total(self, num_tintas: int, pistas: int, ancho: float) -> Tuple[float, str]:
        """
        Calcula el ancho total según la fórmula:
        ROUNDUP(IF(B2=0, ((E3*D3-C3)+10), ((E3*D3-C3)+20)), -1)
        """
        d3 = ancho + self.C3
        base = pistas * d3 - self.C3
        incremento = INCREMENTO_ANCHO_SIN_TINTAS if num_tintas == 0 else INCREMENTO_ANCHO_TINTAS
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
            ancho_con_gap = ancho + self.C3
            pistas_recomendadas = math.floor((self.ANCHO_MAXIMO - incremento + self.C3) / ancho_con_gap)
            
            if ancho > self.ANCHO_MAXIMO:
                mensaje = f"ERROR: El ancho base ({ancho}mm) excede el máximo permitido ({self.ANCHO_MAXIMO}mm)"
            else:
                mensaje = f"ADVERTENCIA: El ancho total calculado ({ancho_redondeado}mm) excede el máximo permitido ({self.ANCHO_MAXIMO}mm). Se recomienda usar {pistas_recomendadas} pistas o menos."
            
        return ancho_redondeado, mensaje
        
    def calcular_metros(self, escala: int, datos: DatosEscala, es_manga: bool = False) -> float:
        """
        Calcula los metros según la fórmula: (Escala / Pistas) * ((Avance_total + Desperdicio_unidad) / 1000)
        """
        try:
            # 1. Obtener la opción de desperdicio según la unidad de montaje elegida (si existe)
            calculadora = self._get_calculadora_desperdicios(es_manga)
            mejor_opcion = None
            
            # Si el usuario ha seleccionado una unidad específica, calcular las repeticiones óptimas para esa unidad
            if getattr(datos, 'unidad_montaje_dientes', None) is not None:
                # Usar el nuevo método para obtener la mejor opción para esta unidad específica
                opcion_unidad = calculadora.obtener_mejor_opcion_para_unidad(datos.avance, datos.unidad_montaje_dientes)
                if opcion_unidad:
                    mejor_opcion = opcion_unidad
                    
            # Si no se ha seleccionado unidad o no se encontró una opción válida, usar la mejor opción global
            if mejor_opcion is None:
                mejor_opcion = calculadora.obtener_mejor_opcion(datos.avance)
            if not mejor_opcion:
                raise ValueError("No se pudo determinar la unidad de montaje")
            
            # 2. Obtener el desperdicio por dientes
            desperdicio_unidad = mejor_opcion.desperdicio
            
            # 3. Usar el avance_total que ya incluye el GAP correspondiente
            avance_total = datos.avance_total
            
            # 4. Cálculo de metros
            metros = (escala / datos.pistas) * ((avance_total + desperdicio_unidad) / 1000)
            
            print(f"\n=== CÁLCULO DE METROS ===")
            print(f"Escala: {escala}")
            print(f"Pistas: {datos.pistas}")
            print(f"Avance base: {datos.avance} mm")
            print(f"Avance total (con GAP): {avance_total} mm")
            print(f"Desperdicio unidad: {desperdicio_unidad} mm")
            print(f"Fórmula: ({escala} / {datos.pistas}) * (({avance_total} + {desperdicio_unidad}) / 1000)")
            print(f"Metros calculados: {metros:.2f}")
            
            return metros
            
        except Exception as e:
            print(f"Error en cálculo de metros: {str(e)}")
            return 0
        
    def calcular_tiempo_horas(self, metros: float, datos: DatosEscala) -> float:
        """Calcula el tiempo en horas según la fórmula: metros / velocidad_maquina / 60"""
        tiempo = metros / datos.velocidad_maquina / 60
        return tiempo
        
    def calcular_montaje(self, num_tintas: int, datos: DatosEscala) -> float:
        """Calcula el montaje según la fórmula: Tintas * MO Montaje"""
        return num_tintas * datos.mo_montaje
        
    def calcular_mo_y_maq(self, tiempo_horas: float, num_tintas: int, datos: DatosEscala, es_manga: bool = False) -> float:
        """
        Calcula MO y Maq según la fórmula.
        """
        # Debug adicional para rastrear parámetros
        print(f"\n=== DEBUG CÁLCULO MO_Y_MAQ ===")
        print(f"Tiempo horas: {tiempo_horas:.2f}")
        print(f"Número tintas: {num_tintas}")
        print(f"Es manga: {es_manga}")
        
        if not es_manga:
            # Cálculo para etiquetas
            if num_tintas > 0:
                # Si hay tintas, usar MO_Impresion
                base_mo = datos.mo_impresion
                resultado = base_mo if tiempo_horas < 1 else base_mo * tiempo_horas
                print(f"Etiqueta con tintas > 0: base_mo={base_mo:.2f}, resultado={resultado:.2f}")
            else:
                # Si no hay tintas (tintas = 0), usar MO_Troquelado
                base_mo = datos.mo_troquelado
                resultado = base_mo if tiempo_horas < 1 else base_mo * tiempo_horas
                print(f"Etiqueta con tintas = 0: base_mo={base_mo:.2f}, resultado={resultado:.2f}")
            return resultado
        else:
            # Cálculo para mangas
            # Se requiere agregar MO_SELLADO y MO_CORTE
            base_mo = datos.mo_impresion if num_tintas > 0 else datos.mo_troquelado
            total_mo = base_mo + MO_SELLADO + MO_CORTE
            resultado = total_mo if tiempo_horas < 1 else total_mo * tiempo_horas
            print(f"Manga: base_mo={base_mo:.2f}, + sellado/corte -> total_mo={total_mo:.2f}, resultado={resultado:.2f}")
            return resultado

    def calcular_tintas(self, escala: int, num_tintas: int, area_etiqueta: float, datos: DatosEscala) -> float:
        if area_etiqueta <= 0 or num_tintas <= 0:
            return 0
        
        # Costo variable por área y escala
        costo_variable = FACTOR_TINTA_AREA * num_tintas * area_etiqueta * escala
        
        # Costo fijo por número de tintas
        costo_fijo = CANTIDAD_TINTA_ESTANDAR * num_tintas * datos.valor_gr_tinta
        
        total_tintas = costo_variable + costo_fijo
        
        return total_tintas
        
    def calcular_papel_lam(self, escala: int, area_etiqueta: float, 
                          valor_material: float, valor_acabado: float) -> float:
        if area_etiqueta <= 0:
            return 0
        
        costo_por_unidad = area_etiqueta * ((valor_material + valor_acabado) / 1000000)
        papel_lam = costo_por_unidad * escala
        
        return papel_lam
        
    def _validar_inputs(self, datos: DatosEscala, num_tintas: int, es_manga: bool = False):
        if datos.ancho <= 0:
            raise ValueError("El ancho debe ser mayor que 0")
        if datos.ancho > self.ANCHO_MAXIMO:
            # Excepción para mangas: Fundas Transparentes (0 Tintas) permiten hasta 415 mm de ancho efectivo
            if not (es_manga and num_tintas == 0 and datos.ancho <= 415):
                raise ValueError(f"El ancho ({datos.ancho}) no puede ser mayor que el máximo permitido ({self.ANCHO_MAXIMO})")
        if datos.pistas <= 0:
            raise ValueError("El número de pistas debe ser mayor que 0")
        if not (0 <= num_tintas <= 7):
            raise ValueError("El número de tintas debe estar entre 0 y 7")
        if datos.avance <= 0:
            raise ValueError("El avance debe ser mayor que 0")
        # Modificado: Solo validar avance_total si no es None
        if datos.avance_total is not None and datos.avance_total <= 0:
            raise ValueError("El avance total debe ser mayor que 0 (si se proporciona)")
        # Validar ancho total solo para etiquetas (la fórmula de ancho total es específica de etiquetas aquí)
        if not es_manga:
            ancho_total, _ = self.calcular_ancho_total(num_tintas, datos.pistas, datos.ancho)
            if ancho_total > self.ANCHO_MAXIMO:
                # Excepción solicitada: permitir etiquetas 50mm con 6 pistas sin bloquear
                es_caso_excepcion = (abs(datos.ancho - 50.0) < 0.01 and int(datos.pistas) == 6)
                if not es_caso_excepcion:
                    raise ValueError(f"El ancho total calculado ({ancho_total} mm) excede el máximo permitido ({self.ANCHO_MAXIMO} mm) para la máquina.")

    def calcular_desperdicio(self, num_tintas: int, ancho: float, papel_lam: float,
                            valor_material: float, datos: DatosEscala,
                            porcentaje_desperdicio: float = 0.10,
                            es_manga: bool = False, s3_val: float = None) -> float:
        """
        Calcula el desperdicio total (tintas + material).
        """
        self._validar_inputs(datos, num_tintas, es_manga)
        # 1. Desperdicio por tintas
        if num_tintas > 0:
            mm_totales = self.MM_COLOR * num_tintas
            if s3_val is None:
                s3 = self.GAP_FIJO + self.calcular_q3(ancho, datos.pistas, es_manga)['q3']
            else:
                s3 = s3_val
            desperdicio_tintas = mm_totales * s3 * (valor_material / 1000000)
        else:
            desperdicio_tintas = 0
        
        # 2. Desperdicio por material
        desperdicio_material = papel_lam * porcentaje_desperdicio
        
        desperdicio_total = desperdicio_tintas + desperdicio_material
        
        return desperdicio_total
        
    def calcular_valor_plancha(self, datos: DatosEscala, num_tintas: int, es_manga: bool = False, q3_val: float = None, s3_val: float = None) -> float:
        """
        Calcula el valor de la plancha utilizando el método base en CalculadoraBase.
        """
        self._validar_inputs(datos, num_tintas, es_manga)
        try:
            # 1. Calcular Q3 (ancho total ajustado) solo si no se pasa
            if q3_val is None or s3_val is None:
                q3_result = self.calcular_q3(datos.ancho, datos.pistas, es_manga)
                s3 = self.GAP_FIJO + q3_result['q3']
            else:
                s3 = s3_val
            
            # 3. Obtener medida de montaje respetando la unidad elegida
            calculadora = self._get_calculadora_desperdicios(es_manga)
            mejor_opcion = None
            
            # Si el usuario ha seleccionado una unidad específica, calcular las repeticiones óptimas para esa unidad
            if getattr(datos, 'unidad_montaje_dientes', None) is not None:
                # Usar el nuevo método para obtener la mejor opción para esta unidad específica
                opcion_unidad = calculadora.obtener_mejor_opcion_para_unidad(datos.avance, datos.unidad_montaje_dientes)
                if opcion_unidad:
                    mejor_opcion = opcion_unidad
                    
            # Si no se ha seleccionado unidad o no se encontró una opción válida, usar la mejor opción global
            if mejor_opcion is None:
                mejor_opcion = calculadora.obtener_mejor_opcion(datos.avance)
            if not mejor_opcion:
                raise ValueError("No se pudo determinar la unidad de montaje")
            mm_unidad_montaje = mejor_opcion.medida_mm
            
            print("\n=== CÁLCULO DE PLANCHA (Refactorizado) ===")
            
            # 4. Llamar al método base
            resultado_base = self.calcular_precio_plancha_base(
                s3=s3,
                mm_unidad_montaje=mm_unidad_montaje,
                num_tintas=num_tintas,
                planchas_por_separado=datos.planchas_por_separado
            )
            
            return resultado_base['precio']
            
        except Exception as e:
            print(f"Error en cálculo de plancha: {str(e)}")
            return 0

    def calcular_valor_troquel(self, datos: DatosEscala, es_manga: bool = False, tipo_grafado_id: Optional[int] = None, repeticiones: Optional[int] = None) -> float:
        """
        Calcula el valor del troquel utilizando el método base en CalculadoraBase.
        """
        try:
            print("\n=== CÁLCULO TROQUEL (Refactorizado) ===")
            # Si no se proporcionan repeticiones, calcularlas automáticamente
            repeticiones_final = repeticiones
            if repeticiones_final is None:
                calculadora = self._get_calculadora_desperdicios(es_manga)
                # (Lógica para determinar repeticiones igual que antes)
                if getattr(datos, 'unidad_montaje_dientes', None) is not None:
                    mejor_opcion = calculadora.obtener_mejor_opcion_para_unidad(datos.avance, datos.unidad_montaje_dientes)
                    if mejor_opcion:
                        repeticiones_final = mejor_opcion.repeticiones
                if repeticiones_final is None:
                    repeticiones_final = calculadora.obtener_mejor_opcion(datos.avance).repeticiones

            resultado = self.calcular_valor_troquel_base(
                ancho=datos.ancho,
                avance=datos.avance,
                pistas=datos.pistas,
                repeticiones=repeticiones_final,
                es_manga=es_manga,
                troquel_existe=datos.troquel_existe,
                tipo_grafado_id=tipo_grafado_id
            )

            # Imprimir detalles para debug (opcional, ya que el test los usa)
            print(f"Valor final: ${resultado['valor']:,.2f}")

            return resultado['valor']

        except Exception as e:
            print(f"Error en cálculo de troquel (costos_escala): {str(e)}")
            return 0

    def calcular_valor_unidad_full(self, suma_costos: float, datos: DatosEscala, 
                                 escala: int, valor_plancha: float, valor_troquel: float) -> float:
        """
        Calcula el valor por unidad basado en costos, rentabilidad y escala.
        """
        try:
            # 1. Validar y convertir valores de entrada
            valor_plancha = float(valor_plancha) if valor_plancha is not None else 0
            valor_troquel = float(valor_troquel) if valor_troquel is not None else 0
            suma_costos = float(suma_costos) if suma_costos is not None else 0
            
            # 2. Validar escala
            if escala <= 0:
                print("Error: Escala es cero o negativa, retornando 0")
                return 0
            
            # 3. Calcular factor de rentabilidad CORRECTO
            if datos.rentabilidad >= 1:
                rentabilidad_decimal = datos.rentabilidad / 100.0
            else:
                rentabilidad_decimal = datos.rentabilidad
            
            if rentabilidad_decimal >= 1:
                 return 0
            factor_rentabilidad = 1 - rentabilidad_decimal
            
            # 4. Calcular costos indirectos (ajustados por rentabilidad)
            if factor_rentabilidad <= 0:
                costos_indirectos = float('inf')
            else:
                costos_indirectos = suma_costos / factor_rentabilidad
            
            # 5. Usar el valor del troquel directamente sin recalcular
            costos_fijos = valor_plancha + valor_troquel
            
            # 6. Calcular costos totales
            costos_totales = costos_indirectos + costos_fijos
            
            # 7. Calcular valor por unidad
            valor_unidad = costos_totales / escala
            
            # 8. Verificar resultado
            if not isinstance(valor_unidad, (int, float)) or valor_unidad < 0:
                print("Error: Valor unidad inválido, retornando 0")
                return 0
            
            return valor_unidad
        
        except Exception as e:
            print(f"Error en cálculo de valor unidad: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
        
    def calcular_desperdicio_tintas(self, dados: DatosEscala, num_tintas: int, valor_material: float, es_manga: bool = False) -> Dict:
        # Validaciones iniciales
        if num_tintas <= 0 or valor_material <= 0:
            return {
                'desperdicio_tintas': 0,
                'detalles': {}
            }

        # Constantes
        MM_COLOR = 30000  # mm por color
        GAP_FIJO = 50  # R3 es 50 tanto para mangas como etiquetas

        # Calcular mm totales
        mm_totales = MM_COLOR * num_tintas

        # Usar el ancho que ya viene ajustado
        B3 = dados.ancho  # El ancho ya viene ajustado desde el cálculo anterior
        
        # Para mangas: no hay gap entre pistas
        # Para etiquetas: gap = 0 si pistas = 1, gap = GAP_PISTAS_ETIQUETAS si pistas > 1
        C3 = 0 if (es_manga or dados.pistas == 1) else GAP_PISTAS_ETIQUETAS

        # Calcular D3 (ancho + GAP)
        D3 = B3 + C3
        
        # Calcular E3 (pistas)
        E3 = dados.pistas

        # Calcular Q3
        Q3 = (D3 * E3) + C3

        # Calcular S3
        S3 = GAP_FIJO + Q3

        # Calcular factor de conversión
        factor = valor_material / 1000000

        # Calcular desperdicio de tintas
        desperdicio_tintas = mm_totales * S3 * factor

        # Retornar diccionario con más detalles
        return {
            'desperdicio_tintas': desperdicio_tintas,
            'detalles': {
                'mm_totales': mm_totales,
                'q3': Q3,
                'c3': C3,
                'd3': D3,
                's3': S3,
                'factor': factor,
                'formula': 'desperdicio_tintas = mm_totales * s3 * factor',
                'ancho': B3,
                'pistas': E3,
                'es_manga': es_manga
            }
        }
        
    def calcular_area_etiqueta(self, datos: DatosEscala, num_tintas: int, es_manga: bool = False, q3_val: float = None, s3_val: float = None) -> Dict:
        """
        Calcula el área de la etiqueta utilizando el método base.
        """
        self._validar_inputs(datos, num_tintas, es_manga)
        try:
            # 1. Obtener Q3/S3
            if q3_val is None or s3_val is None:
                q3_result = self.calcular_q3(datos.ancho, datos.pistas, es_manga)
                q3 = q3_result['q3']
                s3 = self.GAP_FIJO + q3
            else:
                q3 = q3_val
                s3 = s3_val
            
            # 3. Obtener mejor opción de desperdicio respetando unidad elegida (si existe)
            calculadora = self._get_calculadora_desperdicios(es_manga)
            mejor_opcion = None
            
            # (Lógica de unidad igual que antes)
            if getattr(datos, 'unidad_montaje_dientes', None) is not None:
                opcion_unidad = calculadora.obtener_mejor_opcion_para_unidad(datos.avance, datos.unidad_montaje_dientes)
                if opcion_unidad:
                    mejor_opcion = opcion_unidad
                    
            if mejor_opcion is None:
                mejor_opcion = calculadora.obtener_mejor_opcion(datos.avance)
            if not mejor_opcion:
                raise ValueError("No se pudo determinar la unidad de montaje")
            
            print("\n=== CÁLCULO DE ÁREA DE ETIQUETA (Refactorizado) ===")
            
            # 4. Llamar al método base
            resultado = self.calcular_area_etiqueta_base(
                q3=q3,
                s3=s3,
                pistas=datos.pistas,
                medida_montaje=mejor_opcion.medida_mm,
                repeticiones=mejor_opcion.repeticiones,
                num_tintas=num_tintas
            )
            
            return resultado
            
        except Exception as e:
            print(f"Error en cálculo de área de etiqueta: {str(e)}")
            return {
                'error': str(e),
                'area': 0,
                'detalles': None
            }

    def calcular_costos_por_escala(
        self, 
        datos: DatosEscala, 
        num_tintas: int,
        valor_plancha: float,
        valor_troquel: float,
        valor_material: float,
        valor_acabado: float,
        es_manga: bool = False,
        tipo_grafado_id: Optional[int] = None, # Added tipo_grafado_id here
        acabado_id: Optional[int] = None, # Añadido acabado_id
        repeticiones: Optional[int] = None # Añadido repeticiones
    ) -> List[Dict]:
        """
        Calcula los costos por escala para un producto.
        """
        try:
            # Simplemente mantenemos el valor de tintas que viene desde afuera
            # IMPORTANTE: Asumimos que el ajuste por acabados especiales YA FUE REALIZADO
            # en app_calculadora_costos.py
            num_tintas_original = num_tintas  # Para registro y debugging
            num_tintas_interno = num_tintas   # Usar el valor que ya viene ajustado si era necesario
            
            print(f"\n=== INFORMACIÓN DE TINTAS ===")
            print(f"- Tintas recibidas: {num_tintas}")
            print(f"- Acabado ID: {acabado_id}")
            print(f"- Es manga: {es_manga}")
            print(f"- NO se realiza ajuste interno de tintas (debe venir ya ajustado desde app_calculadora_costos.py)")
            
            # Calcular y asignar avance_total a datos antes de validar
            s3_result = self._calcular_s3(datos.avance, es_manga)
            if 'error' in s3_result:
                raise ValueError(f"Error calculando avance total (S3): {s3_result['error']}")
            datos.avance_total = s3_result['s3']

            # Validar entradas con el número de tintas recibido
            self._validar_inputs(datos, num_tintas_interno, es_manga)
            
            # Calcular Q3/S3 una sola vez
            q3_result = self.calcular_q3(datos.ancho, datos.pistas, es_manga)
            q3 = q3_result['q3']
            s3 = self.GAP_FIJO + q3

            # Calcular valor de plancha y troquel si no se proporcionan
            if valor_plancha is None:
                valor_plancha = self.calcular_valor_plancha(datos, num_tintas_interno, es_manga, q3, s3)
            if valor_troquel is None:
                # Pass tipo_grafado_id and repeticiones to the internal method call
                valor_troquel = self.calcular_valor_troquel(datos, es_manga, tipo_grafado_id, repeticiones) # Pass the ID and repeticiones
            # Ensure they are floats after potential calculation or if passed as 0 initially
           
            valor_troquel = float(valor_troquel) if valor_troquel is not None else 0.0

            # Calcular área de etiqueta si no está establecida
            if datos.area_etiqueta <= 0:
                calculo_area = self.calcular_area_etiqueta(datos, num_tintas_interno, es_manga, q3, s3)
                if 'error' in calculo_area:
                    raise ValueError(f"Error calculando área: {calculo_area['error']}")
                datos.set_area_etiqueta(calculo_area['area'])

            # Debug detallado de datos de entrada
            self._debug_datos_entrada(
                datos, num_tintas_interno, valor_plancha, valor_troquel, valor_material, valor_acabado, es_manga
            )
            
            resultados = []
            porcentaje_desperdicio = datos.porcentaje_desperdicio / 100
            print("\n=== INICIO CÁLCULO DE COSTOS POR ESCALA ===")
            print(f"Datos de entrada:")
            print(f"- Número de tintas: {num_tintas_interno} (ya incluye ajustes si los había)")
            print(f"- Acabado ID: {acabado_id}")
            print(f"- Valor plancha: ${valor_plancha:.2f}")
            print(f"- Valor troquel: ${valor_troquel:.2f}")
            print(f"- Valor material: ${valor_material:.6f}/mm²")
            print(f"- Valor acabado: ${valor_acabado:.6f}/mm²")
            print(f"- Es manga: {es_manga}")
            print(f"- Porcentaje desperdicio: {porcentaje_desperdicio * 100}%")
            print(f"- Área etiqueta: {datos.area_etiqueta:.2f} mm²")
            if datos.area_etiqueta <= 0:
                print("ADVERTENCIA: El área de etiqueta es cero o negativa. Esto afectará los cálculos.")
            for escala in datos.escalas:
                print(f"\n=== CÁLCULO PARA ESCALA: {escala:,} ===")
                metros = self.calcular_metros(escala, datos, es_manga)
                print(f"Metros lineales: {metros:.2f}")
                tiempo_horas = self.calcular_tiempo_horas(metros, datos)
                print(f"Tiempo en horas: {tiempo_horas:.2f}")
                montaje = self.calcular_montaje(num_tintas_interno, datos)
                print(f"Montaje: ${montaje:.2f}")
                mo_y_maq = self.calcular_mo_y_maq(tiempo_horas, num_tintas_interno, datos, es_manga)
                print(f"MO y Maq: ${mo_y_maq:.2f}")
                print(f"Área etiqueta para cálculo de tintas: {datos.area_etiqueta:.2f} mm²")
                tintas = self.calcular_tintas(escala, num_tintas_interno, datos.area_etiqueta, datos)
                print(f"Tintas: ${tintas:.2f}")
                print(f"Área etiqueta para cálculo de papel_lam: {datos.area_etiqueta:.2f} mm²")
                papel_lam = self.calcular_papel_lam(escala, datos.area_etiqueta, valor_material, valor_acabado)
                print(f"Papel/lam: ${papel_lam:.2f}")
                desperdicio_porcentaje = papel_lam * porcentaje_desperdicio
                print(f"Desperdicio porcentaje ({porcentaje_desperdicio * 100}%): ${desperdicio_porcentaje:.2f}")
                if num_tintas_interno > 0:
                    resultado_desperdicio = self.calcular_desperdicio_tintas(
                        dados=datos,
                        num_tintas=num_tintas_interno,
                        valor_material=valor_material,
                        es_manga=es_manga
                    )
                    desperdicio_tintas = resultado_desperdicio['desperdicio_tintas']
                    desperdicio_tintas_detalles = resultado_desperdicio['detalles']
                else:
                    desperdicio_tintas = 0
                    desperdicio_tintas_detalles = {}
                desperdicio_total = desperdicio_porcentaje + desperdicio_tintas
                print(f"Desperdicio total: ${desperdicio_total:.2f} = ${desperdicio_porcentaje:.2f} + ${desperdicio_tintas:.2f}")
                suma_costos = montaje + mo_y_maq + tintas + papel_lam + desperdicio_total
                print(f"Suma de costos variables: ${suma_costos:.2f}")
                valor_unidad = self.calcular_valor_unidad_full(
                    suma_costos, datos, escala, valor_plancha, valor_troquel
                )
                print(f"Valor por unidad: ${valor_unidad:.6f}")
                resultados.append({
                    'escala': escala,
                    'valor_unidad': valor_unidad,
                    'metros': metros,
                    'tiempo_horas': tiempo_horas,
                    'montaje': montaje,
                    'mo_y_maq': mo_y_maq,
                    'tintas': tintas,
                    'papel_lam': papel_lam,
                    'desperdicio': desperdicio_total,
                    'desperdicio_tintas': desperdicio_tintas,
                    'desperdicio_porcentaje': desperdicio_porcentaje,
                    'desperdicio_total': desperdicio_total,
                    'num_tintas': num_tintas_original,  # Guardar número original de tintas
                    'num_tintas_interno': num_tintas_interno,  # Guardar número ajustado de tintas
                    'ancho': datos.ancho,
                    'avance': datos.avance,
                    'porcentaje_desperdicio': porcentaje_desperdicio
                })
            return resultados
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error en cálculo de costos: {str(e)}")
