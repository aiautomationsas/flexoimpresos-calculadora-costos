"""
Servicio de cálculo de cotizaciones.

Este módulo encapsula la lógica de negocio para el cálculo de cotizaciones,
separándola de la lógica de UI/Streamlit.
"""

import math
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

from src.logic.calculators.calculadora_costos_escala import CalculadoraCostosEscala, DatosEscala
from src.logic.calculators.calculadora_litografia import CalculadoraLitografia
from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio, OpcionDesperdicio
from src.config.constants import (
    ANCHO_MAXIMO_MAQUINA, VELOCIDAD_MAQUINA_NORMAL, VELOCIDAD_MAQUINA_MANGAS_7_TINTAS,
    GAP_AVANCE_ETIQUETAS, GAP_AVANCE_MANGAS,
    DESPERDICIO_ETIQUETAS, DESPERDICIO_MANGAS,
    RENTABILIDAD_ETIQUETAS, RENTABILIDAD_MANGAS,
    FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS
)

logger = logging.getLogger(__name__)


@dataclass
class CalculationInput:
    """Datos de entrada para el cálculo de cotización."""
    # Datos básicos del producto
    es_manga: bool
    ancho: float
    avance: float
    pistas: int
    escalas: List[int]
    num_tintas: int
    
    # IDs de referencias
    material_id: int
    adhesivo_id: Optional[int]
    acabado_id: Optional[int]
    tipo_grafado_id: Optional[int] = None
    tipo_producto_id: Optional[int] = None
    
    # Valores obtenidos de la BD
    valor_material_base: float = 0.0
    valor_acabado: float = 0.0
    
    # Configuración de cálculo
    troquel_existe: bool = False
    planchas_separadas: bool = False
    unidad_montaje_dientes: Optional[float] = None
    altura_grafado: Optional[float] = None
    num_paquetes: int = 1
    
    # Ajustes administrativos (opcionales)
    rentabilidad_ajustada: Optional[float] = None
    valor_material_ajustado: Optional[float] = None
    valor_troquel_ajustado: Optional[float] = None
    valor_plancha_ajustado: Optional[float] = None


@dataclass
class CalculationResult:
    """Resultado del cálculo de cotización."""
    success: bool
    resultados: Optional[List[Dict[str, Any]]] = None
    datos_persistir: Optional[Dict[str, Any]] = None
    mejor_opcion: Optional[OpcionDesperdicio] = None
    error_message: Optional[str] = None
    ancho_ajustado: float = 0.0
    num_tintas_ajustado: int = 0


class CalculationService:
    """
    Servicio para calcular cotizaciones de etiquetas y mangas.
    
    Encapsula la lógica de negocio separándola de la UI.
    """
    
    ID_SIN_ADHESIVO = 4  # ID correspondiente a "Sin adhesivo"
    ACABADOS_ESPECIALES = [3, 4, 5, 6]  # IDs que requieren +1 tinta
    
    def __init__(self):
        self.calculadora = CalculadoraCostosEscala(ancho_maximo=ANCHO_MAXIMO_MAQUINA)
        self.calc_lito = CalculadoraLitografia()
        
    def validar_input(self, input_data: CalculationInput) -> Tuple[bool, Optional[str]]:
        """
        Valida los datos de entrada para el cálculo.
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not input_data.escalas:
            return False, "Debe seleccionar al menos una escala para cotizar"
            
        if input_data.ancho <= 0:
            return False, "El ancho debe ser mayor a 0"
            
        if input_data.avance <= 0:
            return False, "El avance debe ser mayor a 0"
            
        if input_data.pistas <= 0:
            return False, "El número de pistas debe ser mayor a 0"
            
        if input_data.num_tintas < 0 or input_data.num_tintas > 7:
            return False, "El número de tintas debe estar entre 0 y 7"
            
        # Validación específica para etiquetas
        if not input_data.es_manga and not input_data.adhesivo_id:
            return False, "Para Etiquetas, debe seleccionar un Adhesivo"
            
        return True, None
    
    def ajustar_ancho_manga(self, ancho_base: float, num_tintas: int) -> Tuple[float, Optional[str]]:
        """
        Ajusta el ancho para mangas según la fórmula correspondiente.
        
        Returns:
            Tuple[float, Optional[str]]: (ancho_ajustado, mensaje_error)
        """
        if num_tintas == 0:
            # Funda transparente: ancho = (ancho_cerrado * 2) + 6
            ancho_ajustado = (ancho_base * 2) + 6
            logger.debug("MANGA FUNDA TRANSPARENTE - Ancho: %s -> %s", ancho_base, ancho_ajustado)
            
            if ancho_ajustado > 415:
                return ancho_ajustado, f"El ancho efectivo ({ancho_ajustado:.2f} mm) excede el máximo permitido (415 mm)"
        else:
            # Manga con tintas: ancho = (ancho * factor) + incremento
            ancho_ajustado = (ancho_base * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
            logger.debug("MANGA - Ancho: %s * %s + %s = %s", 
                        ancho_base, FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS, ancho_ajustado)
            
        return ancho_ajustado, None
    
    def procesar_troquel_existe(self, valor: Any) -> bool:
        """
        Convierte cualquier representación de 'troquel_existe' a booleano.
        """
        if isinstance(valor, str):
            if valor == "Sí":
                return True
            elif valor == "No":
                return False
            else:
                return valor.lower() in ('true', 'yes', '1')
        elif isinstance(valor, (int, float)):
            return valor > 0
        else:
            return bool(valor)
    
    def ajustar_tintas_por_acabado(self, num_tintas: int, acabado_id: Optional[int], 
                                   es_manga: bool) -> Tuple[int, Optional[str]]:
        """
        Ajusta el número de tintas si el acabado lo requiere.
        
        Returns:
            Tuple[int, Optional[str]]: (tintas_ajustadas, mensaje_error)
        """
        if es_manga or acabado_id not in self.ACABADOS_ESPECIALES:
            return num_tintas, None
            
        num_tintas_ajustado = num_tintas + 1
        logger.debug("Acabado especial: tintas %s -> %s (+1)", num_tintas, num_tintas_ajustado)
        
        if num_tintas_ajustado > 7:
            return num_tintas, f"El acabado requiere 1 tinta adicional. Con {num_tintas} tintas, se excede el máximo de 7."
            
        return num_tintas_ajustado, None
    
    def obtener_mejor_opcion_desperdicio(
        self, 
        datos_escala: DatosEscala, 
        es_manga: bool,
        unidad_montaje_dientes: Optional[float] = None
    ) -> Tuple[Optional[OpcionDesperdicio], Optional[str]]:
        """
        Calcula la mejor opción de desperdicio.
        
        Returns:
            Tuple[Optional[OpcionDesperdicio], Optional[str]]: (mejor_opcion, mensaje_error)
        """
        try:
            if unidad_montaje_dientes is not None:
                logger.debug("Usando unidad específica del usuario: %s dientes", unidad_montaje_dientes)
                calc_desp = CalculadoraDesperdicio(es_manga=es_manga)
                mejor_opcion = calc_desp.obtener_mejor_opcion_para_unidad(
                    datos_escala.avance, 
                    unidad_montaje_dientes
                )
                if mejor_opcion is None:
                    return None, f"No se encontró configuración válida para {unidad_montaje_dientes} dientes"
            else:
                logger.debug("Usando mejor opción global")
                mejor_opcion = self.calc_lito.obtener_mejor_opcion_desperdicio(datos_escala, es_manga)
                if mejor_opcion is None:
                    return None, "No se encontró configuración de cilindro/repetición válida"
                    
            logger.debug("Mejor opción: Dientes=%s, Reps=%s, Desp=%.4f", 
                        mejor_opcion.dientes, mejor_opcion.repeticiones, mejor_opcion.desperdicio)
            return mejor_opcion, None
            
        except ValueError as e:
            return None, f"Error determinando la mejor opción de desperdicio: {e}"
    
    def calcular_valor_plancha_separado(self, valor_base: Optional[float]) -> Optional[float]:
        """
        Aplica la fórmula de redondeo para planchas separadas.
        
        Fórmula: CEILING(valor_base / 0.7, 10000)
        """
        if valor_base is None or valor_base <= 0:
            return None
            
        try:
            valor_dividido = valor_base / 0.7
            valor_redondeado = math.ceil(valor_dividido / 10000) * 10000
            logger.debug("Plancha separado: Base=%.2f, Dividido=%.2f, Redondeado=%.2f", 
                        valor_base, valor_dividido, valor_redondeado)
            return float(valor_redondeado)
        except Exception as e:
            logger.error("Error redondeo plancha_separado: %s", e)
            return None
    
    def crear_datos_escala(self, input_data: CalculationInput, ancho_ajustado: float) -> DatosEscala:
        """
        Crea el objeto DatosEscala con todos los parámetros calculados.
        """
        es_manga = input_data.es_manga
        num_tintas = input_data.num_tintas
        
        # Determinar velocidad de máquina
        velocidad = VELOCIDAD_MAQUINA_MANGAS_7_TINTAS if (es_manga and num_tintas >= 7) else VELOCIDAD_MAQUINA_NORMAL
        
        # Determinar rentabilidad
        if input_data.rentabilidad_ajustada and input_data.rentabilidad_ajustada > 0:
            rentabilidad = input_data.rentabilidad_ajustada / 100.0
        else:
            rentabilidad = RENTABILIDAD_MANGAS if es_manga else RENTABILIDAD_ETIQUETAS
            
        # Determinar valor de material (usar ajustado si existe)
        valor_material = input_data.valor_material_ajustado if input_data.valor_material_ajustado else input_data.valor_material_base
        
        # Determinar GAP de avance
        gap_avance = GAP_AVANCE_MANGAS if es_manga else GAP_AVANCE_ETIQUETAS
        
        return DatosEscala(
            escalas=input_data.escalas,
            pistas=input_data.pistas,
            ancho=ancho_ajustado,
            avance=input_data.avance,
            avance_total=input_data.avance + gap_avance,
            desperdicio=0,
            velocidad_maquina=velocidad,
            rentabilidad=rentabilidad,
            porcentaje_desperdicio=DESPERDICIO_MANGAS if es_manga else DESPERDICIO_ETIQUETAS,
            valor_metro=valor_material,
            troquel_existe=input_data.troquel_existe,
            planchas_por_separado=input_data.planchas_separadas,
            unidad_montaje_dientes=input_data.unidad_montaje_dientes
        )
    
    def calcular(self, input_data: CalculationInput) -> CalculationResult:
        """
        Ejecuta el cálculo completo de cotización.
        
        Args:
            input_data: Datos de entrada validados
            
        Returns:
            CalculationResult con resultados o error
        """
        # 1. Validar input
        es_valido, error = self.validar_input(input_data)
        if not es_valido:
            return CalculationResult(success=False, error_message=error)
        
        # 2. Ajustar ancho si es manga
        if input_data.es_manga:
            ancho_ajustado, error = self.ajustar_ancho_manga(input_data.ancho, input_data.num_tintas)
            if error:
                return CalculationResult(success=False, error_message=error)
        else:
            ancho_ajustado = input_data.ancho
            
        # 3. Procesar troquel_existe
        input_data.troquel_existe = self.procesar_troquel_existe(input_data.troquel_existe)
        logger.debug("TROQUEL procesado: %s", input_data.troquel_existe)
        
        # 4. Ajustar tintas por acabado
        num_tintas_ajustado, error = self.ajustar_tintas_por_acabado(
            input_data.num_tintas, 
            input_data.acabado_id,
            input_data.es_manga
        )
        if error:
            return CalculationResult(success=False, error_message=error)
            
        # 5. Crear DatosEscala
        datos_escala = self.crear_datos_escala(input_data, ancho_ajustado)
        
        # 6. Obtener mejor opción de desperdicio
        mejor_opcion, error = self.obtener_mejor_opcion_desperdicio(
            datos_escala, 
            input_data.es_manga,
            input_data.unidad_montaje_dientes
        )
        if error:
            return CalculationResult(success=False, error_message=error)
            
        # 7. Calcular valores por defecto (troquel y plancha) si no están ajustados
        valor_troquel = input_data.valor_troquel_ajustado
        valor_plancha = input_data.valor_plancha_ajustado
        precio_sin_constante = None
        
        if valor_troquel is None:
            troquel_result = self.calc_lito.calcular_valor_troquel(
                datos_escala, 
                mejor_opcion.repeticiones,
                troquel_existe=datos_escala.troquel_existe,
                tipo_grafado_id=input_data.tipo_grafado_id,
                es_manga=input_data.es_manga
            )
            if 'error' not in troquel_result:
                valor_troquel = troquel_result.get('valor', 0.0)
            else:
                valor_troquel = 0.0
                
        if valor_plancha is None:
            if input_data.unidad_montaje_dientes is None:
                plancha_result = self.calc_lito.calcular_precio_plancha(
                    datos_escala, 
                    num_tintas_ajustado, 
                    input_data.es_manga
                )
                if 'error' not in plancha_result:
                    valor_plancha = plancha_result.get('precio', 0.0)
                    if plancha_result.get('detalles'):
                        precio_sin_constante = plancha_result['detalles'].get('precio_sin_constante')
                else:
                    valor_plancha = 0.0
                    
        # 8. Calcular valor_plancha_separado si aplica
        valor_plancha_separado = None
        if input_data.planchas_separadas:
            base_para_separado = input_data.valor_plancha_ajustado if input_data.valor_plancha_ajustado else precio_sin_constante
            valor_plancha_separado = self.calcular_valor_plancha_separado(base_para_separado)
            
        # 9. Determinar valor de material final
        valor_material = input_data.valor_material_ajustado if input_data.valor_material_ajustado else input_data.valor_material_base
        
        # 10. Ejecutar cálculo principal
        logger.info("Calculando costos por escala: tintas=%s->%s, es_manga=%s", 
                    input_data.num_tintas, num_tintas_ajustado, input_data.es_manga)
                    
        resultados = self.calculadora.calcular_costos_por_escala(
            datos=datos_escala,
            num_tintas=num_tintas_ajustado,
            valor_plancha=valor_plancha,
            valor_troquel=valor_troquel,
            valor_material=valor_material,
            valor_acabado=input_data.valor_acabado,
            es_manga=input_data.es_manga,
            tipo_grafado_id=input_data.tipo_grafado_id,
            acabado_id=input_data.acabado_id,
            repeticiones=mejor_opcion.repeticiones
        )
        
        if not resultados:
            return CalculationResult(success=False, error_message="No se obtuvieron resultados del cálculo")
            
        # 11. Preparar datos para persistencia
        datos_persistir = {
            'valor_material': valor_material,
            'valor_plancha': valor_plancha,
            'valor_acabado': input_data.valor_acabado,
            'valor_troquel': valor_troquel,
            'rentabilidad': datos_escala.rentabilidad,
            'avance': datos_escala.avance,
            'ancho': input_data.ancho,  # Ancho original sin ajuste
            'unidad_z_dientes': input_data.unidad_montaje_dientes or (mejor_opcion.dientes if mejor_opcion else 0),
            'existe_troquel': datos_escala.troquel_existe,
            'planchas_x_separado': datos_escala.planchas_por_separado,
            'num_tintas': input_data.num_tintas,
            'num_tintas_ajustado': num_tintas_ajustado,
            'numero_pistas': datos_escala.pistas,
            'num_paquetes_rollos': input_data.num_paquetes,
            'tipo_producto_id': input_data.tipo_producto_id,
            'tipo_grafado_id': input_data.tipo_grafado_id,
            'altura_grafado': input_data.altura_grafado,
            'valor_plancha_separado': valor_plancha_separado,
            'acabado_id': input_data.acabado_id,
        }
        
        return CalculationResult(
            success=True,
            resultados=resultados,
            datos_persistir=datos_persistir,
            mejor_opcion=mejor_opcion,
            ancho_ajustado=ancho_ajustado,
            num_tintas_ajustado=num_tintas_ajustado
        )
