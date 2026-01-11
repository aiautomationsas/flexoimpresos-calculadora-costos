"""
Clase base para cálculos comunes entre CalculadoraLitografia y CalculadoraCostosEscala.
"""
from typing import Dict, Optional
import math
from src.config.constants import (
    GAP_PISTAS_ETIQUETAS, GAP_PISTAS_MANGAS, GAP_FIJO, 
    AVANCE_FIJO, MM_COLOR
)

class CalculadoraBase:
    """
    Clase base que contiene los cálculos comunes para Q3, S3 y variables relacionadas,
    así como lógica compartida para planchas, troqueles y áreas.
    """
    
    # Constantes compartidas, ahora importadas desde constants.py
    GAP = GAP_PISTAS_ETIQUETAS  # GAP entre pistas
    GAP_FIJO = GAP_FIJO  # R3 es 50 tanto para mangas como etiquetas
    AVANCE_FIJO = AVANCE_FIJO  # Avance fijo para cálculos
    MM_COLOR = MM_COLOR  # MM de color para cálculo de desperdicio
    VALOR_MM_PLANCHA = 1.5  # Valor por mm de plancha
    VALOR_MM_TROQUEL = 100.0 # Valor por mm para troquel
    
    def calcular_q3(self, ancho: float, pistas: int, es_manga: bool = False) -> Dict:
        """
        Calcula Q3, C3 y D3 para cálculos de área y precio.
        
        Este método centraliza el cálculo de Q3 (ancho total ajustado) que se utiliza
        en múltiples cálculos. Implementa la fórmula: Q3 = D3 * pistas + C3
        
        Args:
            ancho: Ancho en mm
            pistas: Número de pistas
            es_manga: True si es manga, False si es etiqueta
            
        Returns:
            Dict con los valores calculados:
                - c3: Valor de C3 (gap)
                - d3: Valor de D3 (ancho + gap)
                - e3: Número de pistas
                - q3: Valor de Q3 (ancho total ajustado)
        """
        # Determinar C3 según tipo y pistas
        c3 = GAP_PISTAS_MANGAS if es_manga or pistas <= 1 else self.GAP
        
        # Calcular D3 = ancho + C3
        d3 = ancho + c3
        
        # Calcular Q3 = D3 * pistas + C3
        q3 = (d3 * pistas) + c3
        
        return {
            'c3': c3,
            'd3': d3,
            'e3': pistas,
            'q3': q3
        }
    
    def calcular_s3(self, ancho: float, pistas: int, es_manga: bool = False) -> Dict:
        """
        Calcula S3 basado en Q3 y el GAP_FIJO.
        
        Args:
            ancho: Ancho en mm
            pistas: Número de pistas
            es_manga: True si es manga, False si es etiqueta
            
        Returns:
            Dict con los valores calculados incluyendo s3 y los valores intermedios
        """
        # Calcular Q3 y valores relacionados
        resultado_q3 = self.calcular_q3(ancho, pistas, es_manga)
        
        # Calcular S3 = GAP_FIJO + Q3
        s3 = self.GAP_FIJO + resultado_q3['q3']
        
        # Agregar S3 al resultado
        resultado_q3['s3'] = s3
        resultado_q3['gap_fijo'] = self.GAP_FIJO
        
        return resultado_q3

    def calcular_precio_plancha_base(
        self,
        s3: float,
        mm_unidad_montaje: float,
        num_tintas: int,
        planchas_por_separado: bool
    ) -> Dict:
        """
        Lógica base para calcular el precio de la plancha.
        Fórmula: (VALOR_MM_PLANCHA * S3 * S4 * num_tintas) / constante
        Donde S4 = mm_unidad_montaje + AVANCE_FIJO
        Constante = 10000000 si planchas_por_separado else 1
        """
        # Calcular S4
        s4 = mm_unidad_montaje + self.AVANCE_FIJO

        # Calcular precio sin constante
        precio_sin_constante = self.VALOR_MM_PLANCHA * s3 * s4 * num_tintas

        # Determinar constante
        constante = 10000000 if planchas_por_separado else 1

        # Calcular precio final
        precio = precio_sin_constante / constante

        return {
            'precio': precio,
            'detalles': {
                's3': s3,
                's4': s4,
                'mm_unidad_montaje': mm_unidad_montaje,
                'avance_fijo': self.AVANCE_FIJO,
                'num_tintas': num_tintas,
                'planchas_por_separado': planchas_por_separado,
                'constante': constante,
                'precio_sin_constante': precio_sin_constante,
                'valor_mm_plancha': self.VALOR_MM_PLANCHA
            }
        }

    def calcular_valor_troquel_base(
        self,
        ancho: float,
        avance: float,
        pistas: int,
        repeticiones: int,
        es_manga: bool,
        troquel_existe: bool,
        tipo_grafado_id: Optional[int] = None
    ) -> Dict:
        """
        Lógica base para calcular el valor del troquel.
        """
        # Constantes
        FACTOR_BASE = 125000.0  # 25 * 5000
        VALOR_MINIMO = 700000.0

        # Calcular valor base
        perimetro = (ancho + avance) * 2
        valor_base = perimetro * pistas * repeticiones * self.VALOR_MM_TROQUEL
        valor_calculado = max(VALOR_MINIMO, valor_base)

        # Determinar factor de división
        factor_division = 1
        if es_manga:
            # Para mangas: división 1 si es tipo_grafado_id 4, sino 2
            factor_division = 1 if tipo_grafado_id == 4 else 2
        else:
            # Para etiquetas: división 2 si troquel_existe, sino 1
            factor_division = 2 if troquel_existe else 1

        # Calcular valor final
        # Asegurarse de que no sea 0 si el valor_calculado es válido
        if valor_calculado <= 0:
             valor_calculado = VALOR_MINIMO

        valor_final = (FACTOR_BASE + valor_calculado) / factor_division

        return {
            'valor': valor_final,
            'detalles': {
                'perimetro': perimetro,
                'valor_base': valor_base,
                'valor_minimo': VALOR_MINIMO,
                'valor_calculado': valor_calculado,
                'factor_base': FACTOR_BASE,
                'factor_division': factor_division,
                'es_manga': es_manga,
                'tipo_grafado_id': tipo_grafado_id,
                'troquel_existe': troquel_existe,
                'suma_antes_division': FACTOR_BASE + valor_calculado
            }
        }

    def calcular_area_etiqueta_base(
        self,
        q3: float,
        s3: float,
        pistas: int, # E3
        medida_montaje: float, # Q4
        repeticiones: int, # E4
        num_tintas: int
    ) -> Dict:
        """
        Lógica base para calcular área de etiqueta.
        """
        if pistas <= 0 or repeticiones <= 0:
             return {'area': 0.0, 'detalles': {'error': 'Pistas o repeticiones no pueden ser 0'}}

        if num_tintas == 0:
            area_ancho = q3 / pistas
            formula_usada = 'Q3/E3 * Q4/E4'
        else:
            area_ancho = s3 / pistas
            formula_usada = 'S3/E3 * Q4/E4'

        area_largo = medida_montaje / repeticiones
        area = area_ancho * area_largo

        return {
            'area': area,
            'detalles': {
                'q3': q3,
                's3': s3,
                'pistas': pistas,
                'medida_montaje': medida_montaje,
                'repeticiones': repeticiones,
                'area_ancho': area_ancho,
                'area_largo': area_largo,
                'formula_usada': formula_usada
            }
        }
