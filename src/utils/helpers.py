"""
Funciones de utilidad para la aplicación de cotizaciones.

Este módulo contiene helpers para reducir código duplicado en la interfaz
de ajustes administrativos y otras partes de la aplicación.
"""

from typing import Optional, Dict, Tuple
import streamlit as st

from src.config.constants import (
    RENTABILIDAD_ETIQUETAS, RENTABILIDAD_MANGAS
)


def get_rentabilidad_default(datos_cargados: Optional[Dict] = None) -> float:
    """
    Obtiene el valor por defecto de rentabilidad según el tipo de producto.
    
    Args:
        datos_cargados: Diccionario con datos cargados de cotización existente.
                        Si es None, se usa el valor de session_state.
                        
    Returns:
        float: Valor de rentabilidad por defecto (RENTABILIDAD_MANGAS o RENTABILIDAD_ETIQUETAS)
    """
    if datos_cargados is not None:
        es_manga = datos_cargados.get('es_manga', False)
    else:
        es_manga = st.session_state.get('es_manga', False)
    
    return RENTABILIDAD_MANGAS if es_manga else RENTABILIDAD_ETIQUETAS


def parse_numeric_input(
    text_value: str,
    default_value: float = 0.0,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> Tuple[float, Optional[str]]:
    """
    Parsea y valida un input numérico de texto.
    
    Args:
        text_value: Valor de texto a parsear
        default_value: Valor por defecto si el parsing falla o está vacío
        min_value: Valor mínimo permitido (opcional)
        max_value: Valor máximo permitido (opcional)
        
    Returns:
        Tuple[float, Optional[str]]: (valor_parseado, mensaje_error o None)
    """
    if not text_value or not text_value.strip():
        return default_value, None
        
    try:
        valor = float(text_value)
        
        if min_value is not None and valor < min_value:
            return default_value, f"El valor debe ser mayor o igual a {min_value}"
            
        if max_value is not None and valor > max_value:
            return default_value, f"El valor debe ser menor o igual a {max_value}"
            
        return valor, None
        
    except ValueError:
        return default_value, "Por favor ingrese un valor numérico válido"


def render_admin_numeric_field(
    checkbox_label: str,
    checkbox_key: str,
    value_key: str,
    input_key: str,
    input_label: str,
    input_help: str,
    default_value: float = 0.0,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    caption_format: str = "Valor configurado: ${:.2f}"
) -> bool:
    """
    Renderiza un campo de ajuste numérico con checkbox, input y validación.
    
    Args:
        checkbox_label: Etiqueta para el checkbox
        checkbox_key: Key de session_state para el checkbox
        value_key: Key de session_state para almacenar el valor
        input_key: Key del widget de input
        input_label: Etiqueta del campo de entrada
        input_help: Texto de ayuda del campo
        default_value: Valor por defecto
        min_value: Valor mínimo permitido
        max_value: Valor máximo permitido  
        caption_format: Formato para el caption del valor configurado
        
    Returns:
        bool: True si el checkbox está activado
    """
    st.divider()
    
    checked = st.checkbox(checkbox_label, key=checkbox_key)
    
    if checked:
        valor_inicial = str(st.session_state.get(value_key, default_value))
        
        text_value = st.text_input(
            input_label,
            value=valor_inicial,
            key=input_key,
            help=input_help
        )
        
        valor, error = parse_numeric_input(text_value, default_value, min_value, max_value)
        
        if error:
            st.error(error)
            
        st.session_state[value_key] = valor
        st.caption(caption_format.format(st.session_state.get(value_key, default_value)))
    else:
        if value_key in st.session_state:
            st.session_state[value_key] = None
            
    return checked
