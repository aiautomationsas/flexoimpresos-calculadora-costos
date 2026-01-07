"""
Configuración centralizada de logging para la aplicación Flexo Impresos.

Este módulo proporciona una configuración de logging consistente que reemplaza
los print statements para mejor control y mantenibilidad.

Uso:
    from src.config.logging_config import get_logger
    logger = get_logger(__name__)
    
    logger.debug("Mensaje de debug detallado")
    logger.info("Información general")
    logger.warning("Advertencia")
    logger.error("Error")
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Obtiene o crea un logger configurado para el módulo especificado.
    
    Args:
        name: Nombre del módulo (típicamente __name__)
        level: Nivel de logging opcional. Si no se especifica, usa el nivel
               del logger raíz o DEBUG si no está configurado.
    
    Returns:
        Logger configurado para el módulo.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Valor calculado: %s", resultado)
    """
    logger = logging.getLogger(name)
    
    # Solo configurar si no tiene handlers (evitar duplicación)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    if level is not None:
        logger.setLevel(level)
    elif logger.level == logging.NOTSET:
        # Default a DEBUG para desarrollo
        logger.setLevel(logging.DEBUG)
    
    return logger


def configure_root_logger(level: int = logging.INFO, 
                          format_string: Optional[str] = None) -> None:
    """
    Configura el logger raíz de la aplicación.
    
    Llamar esta función al inicio de la aplicación para establecer
    la configuración global de logging.
    
    Args:
        level: Nivel mínimo de logging (default: INFO)
        format_string: Formato personalizado opcional
    
    Example:
        >>> configure_root_logger(level=logging.DEBUG)
    """
    if format_string is None:
        format_string = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt='%H:%M:%S',
        stream=sys.stdout,
        force=True  # Sobrescribir config existente
    )


# Niveles de logging exportados para conveniencia
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
