import streamlit as st
from supabase import create_client
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import traceback # Import traceback for detailed error logging
import math
import time
from datetime import datetime

# Logging configuration
from src.config.logging_config import get_logger, configure_root_logger, DEBUG, INFO

# Configure root logger at startup
configure_root_logger(level=INFO)
logger = get_logger(__name__)

# Configuración de página - MOVER AL INICIO
st.set_page_config(
    page_title="Sistema de Cotización - Flexo Impresos",
    page_icon="🏭",
    layout="wide"
)

# Luego las importaciones del proyecto, agrupadas por funcionalidad
# Auth y DB
from src.auth.auth_manager import AuthManager
from src.data.database import DBManager
# --- NUEVO: Importar CotizacionManager ---
from src.logic.cotizacion_manager import CotizacionManager, CotizacionManagerError
# ---------------------------------------

# Models y Constants
from src.data.models import Cotizacion, Cliente, ReferenciaCliente
from src.config.constants import (
    RENTABILIDAD_MANGAS, RENTABILIDAD_ETIQUETAS,
    DESPERDICIO_MANGAS, DESPERDICIO_ETIQUETAS,
    VELOCIDAD_MAQUINA_NORMAL, VELOCIDAD_MAQUINA_MANGAS_7_TINTAS,
    GAP_AVANCE_ETIQUETAS, GAP_AVANCE_MANGAS,
    GAP_PISTAS_ETIQUETAS, GAP_PISTAS_MANGAS,
    FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS,
    ANCHO_MAXIMO_LITOGRAFIA, ANCHO_MAXIMO_MAQUINA
)

# Utils y PDF
from src.utils.session_manager import SessionManager
from src.pdf.pdf_generator import generar_bytes_pdf_cotizacion, CotizacionPDF # Importar la nueva función helper y la clase

# Calculadoras
from src.logic.calculators.calculadora_costos_escala import CalculadoraCostosEscala, DatosEscala
from src.logic.calculators.calculadora_litografia import CalculadoraLitografia
# --- NUEVO: Importar generador de informe ---
from src.logic.report_generator import generar_informe_tecnico_markdown, markdown_a_pdf
# --------------------------------------------

# UI Components - mover estas importaciones al final
from src.ui.auth_ui import handle_authentication, show_login, show_user_info, show_profile_update
from src.ui.calculator_view import show_calculator, show_quote_results # Mantener solo los usados
# MODIFICADO: Importar funciones específicas
from src.ui.calculator.product_section import (_mostrar_material, _mostrar_adhesivo, 
                                             _mostrar_grafado_altura, mostrar_secciones_internas_formulario)
# --- NUEVO: Importar vista de gestión y dashboard ---
from src.ui.manage_quotes_view import show_manage_quotes
from src.ui.manage_clients_view import show_manage_clients, show_create_client
from src.ui.dashboard_view import show_dashboard
# --- NUEVO: Importar vista de gestión de valores ---
from src.ui.manage_values_view import show_manage_values
from src.ui.manage_policies_view import show_manage_policies
from src.ui.manage_cartera_policies_view import show_manage_cartera_policies
from src.ui.manage_commercials_view import show_manage_commercials


# Cargar CSS
try:
    with open("static/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Archivo CSS no encontrado. La aplicación funcionará con estilos por defecto.")

def initialize_session_state():
    """Inicializa el estado básico de la sesión si no existe"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'calculator'  # Valores posibles: 'calculator', 'quote_results'
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'calculation_history' not in st.session_state:
        st.session_state.calculation_history = []

def initialize_services():
    """Inicializa los servicios principales (Supabase, Auth, DB) si no existen"""
    try:
        if 'supabase' not in st.session_state:
            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]
            st.session_state.supabase = create_client(supabase_url, supabase_key)
        
        if 'auth_manager' not in st.session_state:
            st.session_state.auth_manager = AuthManager(st.session_state.supabase)
            st.session_state.auth_manager.initialize_session_state()
        
        if 'db' not in st.session_state:
            st.session_state.db = DBManager(st.session_state.supabase)
            
        # --- NUEVO: Inicializar CotizacionManager ---
        if 'cotizacion_manager' not in st.session_state:
            st.session_state.cotizacion_manager = CotizacionManager(st.session_state.db)
        # ------------------------------------------
        
        # Refuerzo: asegúrate de que las claves críticas existen
        for key in ['authenticated', 'user_id', 'usuario_rol', 'perfil_usuario']:
            if key not in st.session_state:
                st.session_state[key] = None if key != 'authenticated' else False
        
    except Exception as e:
        st.error(f"Error crítico inicializando servicios: {e}")
        st.stop()

@st.cache_resource
def load_initial_data() -> Dict[str, Any]:
    """
    Carga los datos iniciales necesarios para la calculadora.
    
    Returns:
        Dict con los datos necesarios para la operación de la calculadora
    """
    try:
        db = st.session_state.db
        # Cargar datos base sujetos a RLS
        data = {
            'materiales': db.get_materiales(),
            'acabados': db.get_acabados(),
            'tipos_producto': db.get_tipos_producto(),
            # Clientes: admin ve todos; comercial solo propios
            'clientes': (
                db.get_clientes() if st.session_state.get('usuario_rol') == 'administrador'
                else db.get_clientes_by_comercial(st.session_state.get('comercial_id'))
            ),
            'tipos_grafado': db.get_tipos_grafado(),
            'adhesivos': db.get_adhesivos(),
            'estados_cotizacion': db.get_estados_cotizacion() # <-- AÑADIDO
        }
        
        # Verificar que se obtuvieron todos los datos necesarios (excluding adhesives for now as they might be optional initially)
        required_data = ['materiales', 'acabados', 'tipos_producto', 'clientes', 
                         'tipos_grafado', 'estados_cotizacion'] # <-- AÑADIDO a la verificación
        missing_data = [k for k in required_data if k not in data or not data[k]]
        if missing_data:
            st.error(f"No se pudieron cargar los siguientes datos requeridos: {', '.join(missing_data)}")
            return {}
            
        return data
        
    except Exception as e:
        st.error(f"Error cargando datos iniciales: {str(e)}")
        if st.session_state.get('usuario_rol') == 'administrador':
            st.exception(e)
        return {}

def handle_calculation(form_data: Dict[str, Any], cliente_obj: Cliente) -> Optional[Dict[str, Any]]:
    """
    Maneja el proceso de cálculo de la cotización.
    
    Args:
        form_data: Diccionario con los datos del formulario
        cliente_obj: Objeto Cliente seleccionado
        
    Returns:
        Optional[Dict[str, Any]]: Resultados del cálculo o None si hay error
    """
    try:
        # Debug inicial para rastrear flujo del cálculo
        logger.info("======= INICIO DEL PROCESO DE CÁLCULO =======")
        logger.debug("Datos recibidos: es_manga=%s, num_tintas=%s, acabado_id=%s", 
                     form_data.get('es_manga'), form_data.get('num_tintas'), form_data.get('acabado_id'))
        
        # Validar datos necesarios
        required_fields = ['ancho', 'avance', 'pistas', 'num_tintas', 'num_paquetes', 
                         'material_id', 'es_manga', 'escalas']
        missing_fields = [field for field in required_fields if field not in form_data]
        
        if missing_fields:
            st.error(f"Faltan los siguientes campos requeridos: {', '.join(missing_fields)}")
            return None
            
        if not form_data['escalas']:
            st.error("Debe seleccionar al menos una escala para cotizar")
            return None
        
        # Debug de form_data y ajustes admin
        logger.debug("=== FORM DATA ===")
        for key, value in form_data.items():
            logger.debug("%s: %s (tipo: %s)", key, value, type(value).__name__)
        
        if st.session_state.usuario_rol == 'administrador':
            logger.debug("=== AJUSTES ADMIN ===")
            logger.debug("Material: ajustar=%s, valor=%s", st.session_state.get('ajustar_material'), st.session_state.get('valor_material_ajustado'))
            logger.debug("Troquel: ajustar=%s, valor=%s", st.session_state.get('ajustar_troquel'), st.session_state.get('precio_troquel'))
            logger.debug("Planchas: ajustar=%s, valor=%s", st.session_state.get('ajustar_planchas'), st.session_state.get('precio_planchas'))
            logger.debug("Rentabilidad ajustada: %s", st.session_state.get('rentabilidad_ajustada'))
        
        # Crear instancia de calculadora
        calculadora = CalculadoraCostosEscala(ancho_maximo=ANCHO_MAXIMO_MAQUINA)
        
        # Preparar datos para el cálculo
        es_manga = form_data['es_manga']
        num_tintas = form_data['num_tintas']
        material_id = form_data['material_id']
        adhesivo_id = form_data.get('adhesivo_id')
        
        # Obtener material y acabado de la base de datos
        # REMOVED: material = st.session_state.db.get_material(material_id) # No longer needed for price
        acabado = st.session_state.db.get_acabado(form_data.get('acabado_id')) if not es_manga else None
        
        # --- Determinar Valor Material --- 
        valor_material_base = 0.0
        ID_SIN_ADHESIVO = 4 # Assuming ID 4 corresponds to "Sin adhesivo"

        if not es_manga and adhesivo_id:
            # Etiqueta con adhesivo: Buscar valor combinado
            logger.debug("Buscando valor para Material ID: %s, Adhesivo ID: %s", material_id, adhesivo_id)
            valor_combinado = st.session_state.db.get_material_adhesivo_valor(material_id, adhesivo_id)
            if valor_combinado is not None:
                valor_material_base = valor_combinado
                logger.debug("Valor combinado encontrado: %s", valor_material_base)
            else:
                st.error(f"No se encontró precio para la combinación de Material ID {material_id} y Adhesivo ID {adhesivo_id}. Por favor, verifique la configuración.")
                return None
        elif not es_manga and not adhesivo_id:
            st.error("Para Etiquetas, debe seleccionar un Adhesivo.")
            return None
        elif es_manga:
            # Manga: Buscar valor usando el ID del material y el ID de "Sin adhesivo"
            logger.debug("Buscando valor para Material ID (Manga): %s, Adhesivo ID: %s", material_id, ID_SIN_ADHESIVO)
            valor_manga = st.session_state.db.get_material_adhesivo_valor(material_id, ID_SIN_ADHESIVO)
            if valor_manga is not None:
                valor_material_base = valor_manga
                logger.debug("Valor encontrado para manga: %s", valor_material_base)
            else:
                st.error(f"No se encontró precio base para el Material de Manga ID {material_id}. Verifique la tabla material_adhesivo.")
                return None

        # === Aplicar Ajustes Admin (si existen y están activos) ===
        valor_material = valor_material_base # Start with the fetched value
        if st.session_state.get('ajustar_material'):
            valor_material = st.session_state.get('valor_material_ajustado', valor_material)
            logger.debug("ADMIN: Usando valor material ajustado: %s", valor_material)

        # --- Troquel Cost Logic --- 
        valor_troquel_a_pasar = None # Default to None (signal internal calculation)
        if st.session_state.get('ajustar_troquel'):
            valor_troquel_a_pasar = st.session_state.get('precio_troquel', 0.0)
            logger.debug("ADMIN: Usando valor troquel ajustado: %s", valor_troquel_a_pasar)
        
        # --- Plate cost Logic ---
        valor_plancha_a_pasar = None # Default to None (signal internal calculation)
        if st.session_state.get('ajustar_planchas'):
            valor_plancha_a_pasar = st.session_state.get('precio_planchas', 0.0)
            logger.debug("ADMIN: Usando valor TOTAL de planchas ajustado: %s", valor_plancha_a_pasar)

        rentabilidad = RENTABILIDAD_MANGAS if es_manga else RENTABILIDAD_ETIQUETAS
        rentabilidad_ajustada = st.session_state.get('rentabilidad_ajustada')
        if rentabilidad_ajustada is not None and rentabilidad_ajustada > 0:
            rentabilidad = rentabilidad_ajustada / 100.0
            logger.debug("ADMIN: Usando rentabilidad ajustada: %s", rentabilidad)
        else:
            logger.debug("Usando rentabilidad por defecto: %s", rentabilidad)

        # Procesar troquel_existe explícitamente
        troquel_existe = form_data.get('tiene_troquel')
        logger.debug("TROQUEL - Valor original: %s (tipo: %s)", troquel_existe, type(troquel_existe).__name__)
        
        # Conversión a booleano
        if isinstance(troquel_existe, str):
            troquel_existe_lower = troquel_existe.lower()
            if troquel_existe == "Sí":
                troquel_existe = True
            elif troquel_existe == "No":
                troquel_existe = False
            else:
                troquel_existe = troquel_existe_lower in ('true', 'yes', '1')
        elif isinstance(troquel_existe, (int, float)):
            troquel_existe = troquel_existe > 0
        else:
            troquel_existe = bool(troquel_existe)
            
        logger.debug("TROQUEL - Valor procesado: %s", troquel_existe)
        
        # Ajustar el ancho si es manga
        ancho_base = form_data['ancho']
        if es_manga:
            if form_data.get('num_tintas', 0) == 0:
                ancho_ajustado = (ancho_base * 2) + 6
                logger.debug("MANGA FUNDA TRANSPARENTE - Ancho: %s -> %s", ancho_base, ancho_ajustado)
                if ancho_ajustado > 415:
                    st.error(f"El ancho efectivo ({ancho_ajustado:.2f} mm) excede el máximo permitido (415 mm).")
                    return None
                if ancho_ajustado > 325:
                    try:
                        if form_data.get('tipo_grafado_id') not in (None, 1):
                            logger.debug("Grafado no permitido (>325mm). Forzando 'Sin grafado'.")
                            form_data['tipo_grafado_id'] = 1
                            form_data['tipo_grafado_nombre'] = 'Sin grafado'
                    except Exception:
                        pass
            else:
                ancho_ajustado = (ancho_base * FACTOR_ANCHO_MANGAS) + INCREMENTO_ANCHO_MANGAS
                logger.debug("MANGA - Ancho: %s * %s + %s = %s", ancho_base, FACTOR_ANCHO_MANGAS, INCREMENTO_ANCHO_MANGAS, ancho_ajustado)
        else:
            ancho_ajustado = ancho_base
        
        # Crear datos de escala
        logger.debug("Creando DatosEscala con troquel_existe=%s", troquel_existe)
        
        datos_escala = DatosEscala(
            escalas=form_data['escalas'],
            pistas=form_data['pistas'],
            ancho=ancho_ajustado,
            avance=form_data['avance'],
            avance_total=form_data['avance'] + (GAP_AVANCE_MANGAS if es_manga else GAP_AVANCE_ETIQUETAS),
            desperdicio=0,
            velocidad_maquina=VELOCIDAD_MAQUINA_MANGAS_7_TINTAS if (es_manga and num_tintas >= 7) 
                            else VELOCIDAD_MAQUINA_NORMAL,
            rentabilidad=rentabilidad,
            porcentaje_desperdicio=DESPERDICIO_MANGAS if es_manga else DESPERDICIO_ETIQUETAS,
            valor_metro=valor_material,
            troquel_existe=troquel_existe,
            planchas_por_separado=form_data.get('planchas_separadas', False),
            unidad_montaje_dientes=form_data.get('unidad_montaje_dientes')
        )
        
        logger.debug("DatosEscala creado - troquel_existe=%s", datos_escala.troquel_existe)
        
        # --- Calcular Mejor Opción de Desperdicio UNA VEZ ---
        calc_lito = CalculadoraLitografia()
        try:
            if form_data.get('unidad_montaje_dientes') is not None:
                logger.debug("Usando unidad específica del usuario: %s dientes", form_data.get('unidad_montaje_dientes'))
                
                from src.logic.calculators.calculadora_desperdicios import CalculadoraDesperdicio
                calc_desp = CalculadoraDesperdicio(es_manga=es_manga)
                mejor_opcion = calc_desp.obtener_mejor_opcion_para_unidad(
                    datos_escala.avance, 
                    form_data.get('unidad_montaje_dientes')
                )
                if mejor_opcion is None:
                    st.error(f"No se encontró configuración válida para {form_data.get('unidad_montaje_dientes')} dientes.")
                    return None
                logger.debug("Mejor opción (unidad específica): Dientes=%s, Reps=%s, Desp=%.4f", 
                            mejor_opcion.dientes, mejor_opcion.repeticiones, mejor_opcion.desperdicio)
            else:
                logger.debug("Usando mejor opción global")
                mejor_opcion = calc_lito.obtener_mejor_opcion_desperdicio(datos_escala, es_manga)
                if mejor_opcion is None:
                    st.error("No se encontró configuración de cilindro/repetición válida.")
                    return None
                logger.debug("Mejor opción (global): Dientes=%s, Reps=%s, Desp=%.4f", 
                            mejor_opcion.dientes, mejor_opcion.repeticiones, mejor_opcion.desperdicio)
        except ValueError as e_desp:
            st.error(f"Error determinando la mejor opción de desperdicio: {e_desp}")
            return None
        # -----------------------------------------------------

        # Calcular área de etiqueta usando la calculadora (¿Se necesita antes de calcular_costos_por_escala?)
        # area_result = calculadora.calcular_area_etiqueta(datos_escala, num_tintas, es_manga) # Parece que no se usa directamente ahora
        # if 'error' in area_result:
        #     st.error(f"Error calculando área: {area_result['error']}")
        #     return None
        # datos_escala.set_area_etiqueta(area_result['area'])

        # ---- AJUSTAR NÚMERO DE TINTAS SI EL ACABADO LO REQUIERE ----
        num_tintas = form_data['num_tintas']  # Número original seleccionado por el usuario
        acabado_id = form_data.get('acabado_id')
        es_manga = form_data['es_manga']
        
        # Ajustar tintas para acabados especiales
        num_tintas_ajustado = num_tintas
        if not es_manga and acabado_id in [3, 4, 5, 6]:
            num_tintas_ajustado = num_tintas + 1
            logger.debug("Acabado especial: tintas %s -> %s (+1)", num_tintas, num_tintas_ajustado)
            
            if num_tintas_ajustado > 7:
                st.error(f"El acabado requiere 1 tinta adicional. Con {num_tintas} tintas, se excede el máximo de 7.")
                return None
        else:
            logger.debug("Tintas sin ajuste: %s", num_tintas)
            
        # A partir de este punto, usamos num_tintas_ajustado para todos los cálculos internos
        
        # --- GUARDAR DATOS DE CALCULO PARA GUARDADO POSTERIOR --- 
        # Guardamos los valores finales que se usaron en el cálculo
        # para pasarlos luego a guardar_calculos_escala
        
        # Calcular valor_troquel por defecto (si no ajustado), respetando selección de unidad
        valor_troquel_defecto = 0.0
        if not st.session_state.get('ajustar_troquel'):
            # Siempre calcular el valor del troquel, incluso si el usuario eligió una unidad específica
            # Esto asegura que tengamos un valor para el informe técnico
            troquel_result = calc_lito.calcular_valor_troquel(
                datos_escala, 
                mejor_opcion.repeticiones,
                troquel_existe=datos_escala.troquel_existe,
                tipo_grafado_id=form_data.get('tipo_grafado_id'),
                es_manga=es_manga
            )
            if 'error' in troquel_result:
                 st.warning(f"Advertencia: No se pudo calcular el valor del troquel por defecto: {troquel_result['error']}")
            else:
                 valor_troquel_defecto = troquel_result.get('valor', 0.0)
            
            logger.debug("Troquel calculado: valor=%s, troquel_existe=%s", valor_troquel_defecto, datos_escala.troquel_existe)

        # Calcular valor_plancha por defecto (si no ajustado)
        valor_plancha_defecto = 0.0
        precio_sin_constante = None # Inicializar para guardar el valor separado
        if not st.session_state.get('ajustar_planchas'):
             # Si el usuario eligió unidad, dejar a la calculadora interna computar plancha (None)
             if form_data.get('unidad_montaje_dientes') is not None:
                 valor_plancha_defecto = None
             else:
                 # Usar el número de tintas ajustado para calcular la plancha con Litografía
                 plancha_result = calc_lito.calcular_precio_plancha(datos_escala, num_tintas_ajustado, es_manga)
                 if 'error' in plancha_result:
                     st.warning(f"Advertencia: No se pudo calcular el valor de plancha por defecto: {plancha_result['error']}")
                 else:
                     # Usar el precio que incluye la división por constante si planchas_por_separado=False
                     valor_plancha_defecto = plancha_result.get('precio', 0.0)
                     # Guardar el precio ANTES de aplicar la constante (si existe)
                     if plancha_result.get('detalles'):
                        precio_sin_constante = plancha_result['detalles'].get('precio_sin_constante')

        # Debug: verificar valores de troquel
        logger.debug("Troquel check - datos_escala: %s, form_data: %s, procesado: %s", 
                     datos_escala.troquel_existe, form_data.get('tiene_troquel'), troquel_existe)
        
        datos_calculo_persistir = {
            'valor_material': valor_material, # Valor final usado
            'valor_plancha': st.session_state.get('precio_planchas', valor_plancha_defecto) if st.session_state.get('ajustar_planchas') else valor_plancha_defecto,
            'valor_acabado': acabado.valor if acabado else 0,
            'valor_troquel': st.session_state.get('precio_troquel', valor_troquel_defecto) if st.session_state.get('ajustar_troquel') else valor_troquel_defecto,
            'rentabilidad': datos_escala.rentabilidad, # Guardar el valor decimal directamente
            'avance': datos_escala.avance,
            'ancho': form_data['ancho'], # Guardar ancho original sin ajuste de manga
            'unidad_z_dientes': form_data.get('unidad_montaje_dientes') or (mejor_opcion.dientes if mejor_opcion else 0),
            'existe_troquel': datos_escala.troquel_existe, # Usar valor procesado
            'planchas_x_separado': datos_escala.planchas_por_separado,
            'num_tintas': num_tintas, # Número de tintas original
            'num_tintas_ajustado': num_tintas_ajustado, # Número de tintas ajustado (con tinta adicional por acabado si aplica)
            'numero_pistas': datos_escala.pistas,
            'num_paquetes_rollos': form_data['num_paquetes'],
            'tipo_producto_id': form_data['tipo_producto_id'],
            'tipo_grafado_id': form_data.get('tipo_grafado_id'), # Usar ID guardado
            'altura_grafado': form_data.get('altura_grafado'),
            'valor_plancha_separado': None, # Inicializar para aplicar la lógica de redondeo
            'acabado_id': form_data.get('acabado_id'), # Añadir ID de acabado
            # --- NUEVO: parámetros especiales opcionales ---
            'parametros_especiales': {
                # Ejemplos de parámetros especiales que queremos persistir y precargar
                # Estos se poblarán desde session_state si existen
                'ajustar_material': bool(st.session_state.get('ajustar_material', False)),
                'valor_material_ajustado': st.session_state.get('valor_material_ajustado'),
                'ajustar_troquel': bool(st.session_state.get('ajustar_troquel', False)),
                'precio_troquel': st.session_state.get('precio_troquel'),
                'ajustar_planchas': bool(st.session_state.get('ajustar_planchas', False)),
                'precio_planchas': st.session_state.get('precio_planchas'),
                'ajustar_rentabilidad': bool(st.session_state.get('ajustar_rentabilidad', False)),
                'rentabilidad_ajustada': st.session_state.get('rentabilidad_ajustada')
            }
        }
        
        logger.debug("datos_calculo_persistir - existe_troquel: %s", datos_calculo_persistir['existe_troquel'])
        
        # --- Aplicar Fórmula de Redondeo a valor_plancha_separado --- 
        valor_plancha_separado_base = None
        if datos_calculo_persistir['planchas_x_separado']: # Solo aplica si las planchas son separadas
            if st.session_state.get('ajustar_planchas'):
                valor_plancha_separado_base = st.session_state.get('precio_planchas')
            elif precio_sin_constante is not None:
                valor_plancha_separado_base = precio_sin_constante
        
        # Establecer valor_plancha_separado basado en planchas_x_separado
        if datos_calculo_persistir['planchas_x_separado'] and valor_plancha_separado_base is not None and valor_plancha_separado_base > 0:
            try:
                valor_dividido = valor_plancha_separado_base / 0.7
                valor_redondeado = math.ceil(valor_dividido / 10000) * 10000
                datos_calculo_persistir['valor_plancha_separado'] = float(valor_redondeado)
                logger.debug("Plancha separado: Base=%.2f, Dividido=%.2f, Redondeado=%.2f", 
                            valor_plancha_separado_base, valor_dividido, valor_redondeado)
            except Exception as e_round:
                logger.error("Error redondeo plancha_separado: %s", e_round)
                datos_calculo_persistir['valor_plancha_separado'] = None
        else:
            datos_calculo_persistir['valor_plancha_separado'] = None

        # Realizar cálculos principales por escala
        logger.info("Calculando costos por escala: tintas=%s->%s, es_manga=%s, acabado=%s", 
                    num_tintas, num_tintas_ajustado, es_manga, acabado_id)

        resultados = calculadora.calcular_costos_por_escala(
            datos=datos_escala,
            num_tintas=num_tintas_ajustado,  # IMPORTANTE: Usar el valor AJUSTADO que incluye +1 para acabados especiales
            valor_plancha=datos_calculo_persistir['valor_plancha'], 
            valor_troquel=datos_calculo_persistir['valor_troquel'], 
            valor_material=datos_calculo_persistir['valor_material'], 
            valor_acabado=datos_calculo_persistir['valor_acabado'],
            es_manga=es_manga,
            tipo_grafado_id=datos_calculo_persistir['tipo_grafado_id'], 
            acabado_id=acabado_id,
            repeticiones=mejor_opcion.repeticiones  # Pasar las repeticiones calculadas
        )
        
        if resultados:
            # Preparar modelo Cotizacion usando CotizacionManager
            logger.info("Cálculo exitoso. Preparando modelo de cotización...")
            try:
                manager = st.session_state.cotizacion_manager
                # Construir kwargs para el manager
                kwargs_modelo = {
                    'material_adhesivo_id': form_data['material_adhesivo_id'], # Usar la clave correcta
                    'acabado_id': form_data.get('acabado_id') if not es_manga else 10, # ID 10 = Sin acabado
                    'num_tintas': num_tintas, # Usar tintas originales (no ajustadas) para mostrar al usuario
                    'num_paquetes_rollos': form_data['num_paquetes'],
                    'es_manga': es_manga,
                    'tipo_grafado': form_data.get('tipo_grafado_nombre'), # Pasar nombre si existe
                    'valor_troquel': datos_calculo_persistir['valor_troquel'], # Usar valor final persistido
                    'valor_plancha_separado': datos_calculo_persistir.get('valor_plancha_separado'), # Valor ya calculado/ajustado
                    'planchas_x_separado': datos_escala.planchas_por_separado,
                    'existe_troquel': form_data.get('tiene_troquel', False), # Usar valor del formulario en lugar del calculado
                    'numero_pistas': datos_escala.pistas,
                    'avance': datos_escala.avance, # Usar avance de datos_escala
                    'ancho': form_data['ancho'], # Ancho original
                    'tipo_producto_id': form_data['tipo_producto_id'],
        
                    'altura_grafado': form_data.get('altura_grafado'),
                    'tipo_foil_id': st.session_state.get("tipo_foil_id"), # <--- LÍNEA AÑADIDA
                    'escalas_resultados': resultados # Pasar la lista de dicts
                }
                
                # Asegurarse de pasar el tipo_grafado_id si es manga
                if es_manga:
                    kwargs_modelo['tipo_grafado_id'] = form_data.get('tipo_grafado_id')

                # --- NUEVO: Lógica para modo edición vs nueva cotización ---
                is_edit_mode = st.session_state.get('modo_edicion', False)
                if is_edit_mode:
                    # En modo edición, actualizar el modelo existente
                    cotizacion_existente = st.session_state.get('cotizacion_model')
                    if cotizacion_existente and cotizacion_existente.id:
                        st.session_state.cotizacion_model = manager.actualizar_cotizacion_model(cotizacion_existente, **kwargs_modelo)
                        logger.debug("Modelo Cotizacion actualizado para edición.")
                    else:
                        st.error("Error: No se encontró el modelo de cotización existente para actualizar.")
                        return None
                else:
                    st.session_state.cotizacion_model = manager.preparar_nueva_cotizacion_model(**kwargs_modelo)
                    logger.debug("Modelo Cotizacion preparado para nueva cotización.")
                # --- FIN: Lógica para modo edición vs nueva cotización ---
                st.session_state.cotizacion_calculada = True # Indicar que hay un cálculo listo

            except CotizacionManagerError as cme:
                st.error(f"Error preparando el modelo de cotización: {cme}")
                return None # Falló la preparación, no continuar
            except Exception as e_prep:
                st.error(f"Error inesperado preparando el modelo: {e_prep}")
                traceback.print_exc()
                return None
            # ----------------------------------------------------------------
            
            # --- NUEVO: Determinar si ajustes admin estaban activos ---
            admin_ajustes_activos_calculo = False
            if st.session_state.get('usuario_rol') == 'administrador':
                if (st.session_state.get('ajustar_material') or 
                    st.session_state.get('ajustar_troquel') or 
                    st.session_state.get('ajustar_planchas') or
                    (st.session_state.get('rentabilidad_ajustada') is not None and st.session_state.get('rentabilidad_ajustada') > 0)):
                    admin_ajustes_activos_calculo = True
            # ------------------------------------------------------

            # Guardar resultados y cambiar vista
            st.session_state.current_calculation = {
                'form_data': form_data,
                'cliente': cliente_obj,
                'results': resultados,
                'is_manga': es_manga,
                'timestamp': datetime.now().isoformat(),
                'calculos_para_guardar': datos_calculo_persistir, 
                # --- AÑADIR EL NUEVO FLAG AQUÍ ---
                'admin_ajustes_activos': admin_ajustes_activos_calculo, 
                # ----------------------------------
                'admin_adjustments_applied': { # Mantener esto también si se usa en otro lado
                    'material': st.session_state.get('ajustar_material', False),
                    'troquel': st.session_state.get('ajustar_troquel', False),
                    'planchas': st.session_state.get('ajustar_planchas', False),
                    'rentabilidad': rentabilidad_ajustada is not None and rentabilidad_ajustada > 0
                }
            }
            st.session_state.current_view = 'quote_results'
            st.rerun() 
            
        return resultados
        
    except Exception as e:
        st.error(f"Error en el cálculo: {str(e)}")
        if st.session_state.get('usuario_rol') == 'administrador':
            st.exception(e)
        return None

def show_navigation():
    """Muestra la barra de navegación con las diferentes opciones"""
    st.sidebar.markdown("### Navegación")

    # Define las claves y los nombres para mostrar
    options = {
        'calculator': "📝 Cotizador",
        'manage_quotes': "📂 Gestionar Cotizaciones",
        'manage_clients': "👥 Gestionar Clientes",
        'dashboard': "📊 Dashboard", # Nueva opción
    }
    
    # Solo mostrar la opción de gestión de valores a administradores
    if st.session_state.get('usuario_rol') == 'administrador':
        options['manage_values'] = "💰 Administrar Valores"
        options['manage_policies'] = "📋 Políticas de Entrega"
        options['manage_cartera'] = "💰 Políticas de Cartera"
        options['manage_commercials'] = "👔 Gestionar Comerciales"

    # Obtener la vista actual o default a 'calculator'
    current_view_key = st.session_state.get('current_view', 'calculator')
    
    # Asegurarse de que la vista actual sea válida para la navegación
    # Si la vista actual no es una de las opciones del radio (p.ej. 'quote_results'),
    # mantenemos esa vista pero seleccionamos 'calculator' en el radio visualmente.
    if current_view_key not in options:
        nav_display_key = 'calculator' # Clave para mostrar en el radio
    else:
        nav_display_key = current_view_key # La vista actual es una opción del radio

    # Encontrar el índice de la opción a mostrar en el radio
    try:
        current_index = list(options.keys()).index(nav_display_key)
    except ValueError:
        current_index = 0 # Default seguro al primer índice

    # Mostrar el radio button
    selected_display_name = st.sidebar.radio(
        "Ir a:",
        list(options.values()),
        index=current_index, 
        key="navigation_radio"
    )

    # Obtener la clave de la vista que CORRESPONDE al radio seleccionado
    selected_key_from_radio = next((k for k, v in options.items() if v == selected_display_name), 'calculator')

    # Cambiar la vista SOLO si la selección del radio es DIFERENTE a la 
    # clave que usamos para mostrar la selección inicial (nav_display_key).
    # Esto significa que el usuario hizo clic activamente en una opción diferente.
    if selected_key_from_radio != nav_display_key:
        st.session_state.current_view = selected_key_from_radio
        # Limpiar estado específico de cálculo/resultados al navegar manualmente
        if 'current_calculation' in st.session_state: del st.session_state['current_calculation']
        if 'cotizacion_model' in st.session_state: del st.session_state['cotizacion_model']
        if 'cotizacion_guardada' in st.session_state: del st.session_state['cotizacion_guardada']
        
        # IMPORTANTE: NO limpiar modo_edicion si estamos navegando A la calculadora
        # (podría ser una edición iniciada desde manage_quotes)
        if selected_key_from_radio != 'calculator':
            # Solo limpiar si NO vamos a la calculadora
            if 'modo_edicion' in st.session_state: 
                 st.session_state.modo_edicion = False
                 st.session_state.cotizacion_id_editar = None
                 st.session_state.datos_cotizacion_editar = None
            if 'recotizacion_info' in st.session_state: 
                 del st.session_state['recotizacion_info']
            SessionManager.reset_calculator_widgets()
        
        st.rerun() 

def initialize_session():
    """Inicializa el estado de la sesión después del login"""
    if 'user' not in st.session_state:
        return False
        
    user_id = st.session_state.user_id
    db = st.session_state.db
    
    # Cargar perfil y permisos
    perfil = db.get_perfil(user_id)
    if not perfil:
        return False
        
    # Guardar información crítica en session_state
    st.session_state.usuario_rol = perfil.get('rol_nombre')
    st.session_state.comercial_id = user_id
    st.session_state.perfil_usuario = perfil
    
    return True

def get_filtered_clients():
    """Obtiene todos los clientes sin filtrar. Los comerciales pueden ver todos los clientes,
    aunque solo pueden trabajar con las referencias que les corresponden."""
    # Siempre mostrar todos los clientes independientemente del rol
    return st.session_state.db.get_clientes()

def _mostrar_ajustes_admin(datos_cargados: Optional[Dict] = None):
    """Muestra la sección de ajustes avanzados para administradores (fuera del form)."""
    if st.session_state.usuario_rol == 'administrador':
        with st.expander("⚙️ Ajustes Avanzados (Admin)"):
            st.markdown("##### Sobrescribir Valores Calculados")
            st.caption("Marque la casilla para activar el ajuste e ingrese el nuevo valor.")
            
            # Rentabilidad
            st.divider()
            
            # Determinar si hay ajustes de rentabilidad activos
            # Usar el valor que ya está cargado en session_state
            rentabilidad_ajustada_existe = st.session_state.get('ajustar_rentabilidad', False)
            
            ajustar_rentabilidad_checked = st.checkbox("Ajustar Rentabilidad", key='ajustar_rentabilidad')
            if ajustar_rentabilidad_checked:
                # Obtener valor inicial desde session_state o usar valor por defecto
                # Verificar si datos_cargados no es None antes de acceder a sus propiedades
                if datos_cargados is not None:
                    valor_por_defecto = RENTABILIDAD_ETIQUETAS if not datos_cargados.get('es_manga', False) else RENTABILIDAD_MANGAS
                else:
                    # Si no hay datos cargados, usar el valor por defecto según el tipo de producto actual
                    es_manga_actual = st.session_state.get('es_manga', False)
                    valor_por_defecto = RENTABILIDAD_MANGAS if es_manga_actual else RENTABILIDAD_ETIQUETAS
                valor_inicial_rentabilidad = str(st.session_state.get('rentabilidad_ajustada', valor_por_defecto))
                
                rentabilidad_text = st.text_input(
                    "Nueva Rentabilidad (%)",
                    value=valor_inicial_rentabilidad,
                    key='rentabilidad_ajustada_input',
                    help="Ingrese el porcentaje de rentabilidad (ej: 45.5)"
                )
                
                # Validar y convertir el valor del input
                try:
                    if rentabilidad_text and rentabilidad_text.strip():
                        valor_rentabilidad = float(rentabilidad_text)
                        if valor_rentabilidad < 0.1 or valor_rentabilidad > 100.0:
                            st.error("La rentabilidad debe estar entre 0.1% y 100.0%")
                            # Determinar valor por defecto
                            if datos_cargados is not None:
                                valor_por_defecto = RENTABILIDAD_ETIQUETAS if not datos_cargados.get('es_manga', False) else RENTABILIDAD_MANGAS
                            else:
                                es_manga_actual = st.session_state.get('es_manga', False)
                                valor_por_defecto = RENTABILIDAD_MANGAS if es_manga_actual else RENTABILIDAD_ETIQUETAS
                            valor_rentabilidad = valor_por_defecto
                        st.session_state['rentabilidad_ajustada'] = valor_rentabilidad
                    else:
                        # Determinar valor por defecto
                        if datos_cargados is not None:
                            valor_por_defecto = RENTABILIDAD_ETIQUETAS if not datos_cargados.get('es_manga', False) else RENTABILIDAD_MANGAS
                        else:
                            es_manga_actual = st.session_state.get('es_manga', False)
                            valor_por_defecto = RENTABILIDAD_MANGAS if es_manga_actual else RENTABILIDAD_ETIQUETAS
                        st.session_state['rentabilidad_ajustada'] = valor_por_defecto
                except ValueError:
                    st.error("Por favor ingrese un valor numérico válido para la rentabilidad")
                    # Determinar valor por defecto
                    if datos_cargados is not None:
                        valor_por_defecto = RENTABILIDAD_ETIQUETAS if not datos_cargados.get('es_manga', False) else RENTABILIDAD_MANGAS
                    else:
                        es_manga_actual = st.session_state.get('es_manga', False)
                        valor_por_defecto = RENTABILIDAD_MANGAS if es_manga_actual else RENTABILIDAD_ETIQUETAS
                    st.session_state['rentabilidad_ajustada'] = valor_por_defecto
                
                # Determinar valor por defecto para el caption
                if datos_cargados is not None:
                    valor_por_defecto = RENTABILIDAD_ETIQUETAS if not datos_cargados.get('es_manga', False) else RENTABILIDAD_MANGAS
                else:
                    es_manga_actual = st.session_state.get('es_manga', False)
                    valor_por_defecto = RENTABILIDAD_MANGAS if es_manga_actual else RENTABILIDAD_ETIQUETAS
                st.caption(f"Valor configurado: {st.session_state.get('rentabilidad_ajustada', valor_por_defecto)}%")
            else: 
                if 'rentabilidad_ajustada' in st.session_state:
                    st.session_state.rentabilidad_ajustada = None
            
            # Material
            st.divider()
            
            # Determinar si hay ajustes de material activos
            # Usar el valor que ya está cargado en session_state
            material_ajustado_existe = st.session_state.get('ajustar_material', False)
            
            ajustar_material_checked = st.checkbox("Ajustar Material", key='ajustar_material')
            if ajustar_material_checked:
                # Obtener valor inicial desde session_state o usar valor por defecto
                valor_inicial_material = str(st.session_state.get('valor_material_ajustado', 0.0))
                
                material_text = st.text_input(
                    "Nuevo Valor Material ($/m²)",
                    value=valor_inicial_material,
                    key='valor_material_ajustado_input',
                    help="Ingrese el valor del material por metro cuadrado (ej: 1500.50)"
                )
                
                # Validar y convertir el valor del input
                try:
                    if material_text and material_text.strip():
                        valor_material = float(material_text)
                        if valor_material < 0.0:
                            st.error("El valor del material debe ser mayor o igual a 0")
                            valor_material = 0.0
                        st.session_state['valor_material_ajustado'] = valor_material
                    else:
                        st.session_state['valor_material_ajustado'] = 0.0
                except ValueError:
                    st.error("Por favor ingrese un valor numérico válido para el material")
                    st.session_state['valor_material_ajustado'] = 0.0
                
                st.caption(f"Valor configurado: ${st.session_state.get('valor_material_ajustado', 0.0):.2f}/m²")
            else: 
                if 'valor_material_ajustado' in st.session_state:
                    st.session_state.valor_material_ajustado = 0.0
            
            # Troquel
            st.divider()
            
            # Determinar si hay ajustes de troquel activos
            # Usar el valor que ya está cargado en session_state
            troquel_ajustado_existe = st.session_state.get('ajustar_troquel', False)
            
            ajustar_troquel_checked = st.checkbox("Ajustar Troquel", key='ajustar_troquel')
            if ajustar_troquel_checked:
                # Obtener valor inicial desde session_state o usar valor por defecto
                valor_inicial_troquel = str(st.session_state.get('precio_troquel', 0.0))
                
                troquel_text = st.text_input(
                    "Nuevo Precio Troquel ($)",
                    value=valor_inicial_troquel,
                    key='precio_troquel_input',
                    help="Ingrese el precio del troquel (ej: 2500.00)"
                )
                
                # Validar y convertir el valor del input
                try:
                    if troquel_text and troquel_text.strip():
                        valor_troquel = float(troquel_text)
                        if valor_troquel < 0.0:
                            st.error("El precio del troquel debe ser mayor o igual a 0")
                            valor_troquel = 0.0
                        st.session_state['precio_troquel'] = valor_troquel
                    else:
                        st.session_state['precio_troquel'] = 0.0
                except ValueError:
                    st.error("Por favor ingrese un valor numérico válido para el troquel")
                    st.session_state['precio_troquel'] = 0.0
                
                st.caption(f"Valor configurado: ${st.session_state.get('precio_troquel', 0.0):.2f}")
            else: 
                if 'precio_troquel' in st.session_state:
                    st.session_state.precio_troquel = 0.0
            
            # Planchas
            st.divider()
            
            # Determinar si hay ajustes de planchas activos
            # Usar el valor que ya está cargado en session_state
            planchas_ajustadas_existe = st.session_state.get('ajustar_planchas', False)
            
            ajustar_planchas_checked = st.checkbox("Ajustar Planchas", key='ajustar_planchas')
            if ajustar_planchas_checked:
                # Obtener valor inicial desde session_state o usar valor por defecto
                valor_inicial_planchas = str(st.session_state.get('precio_planchas', 0.0))
                
                planchas_text = st.text_input(
                    "Nuevo Precio Total Planchas ($)",
                    value=valor_inicial_planchas,
                    key='precio_planchas_input',
                    help="Ingrese el precio total de las planchas (ej: 1800.00)"
                )
                
                # Validar y convertir el valor del input
                try:
                    if planchas_text and planchas_text.strip():
                        valor_planchas = float(planchas_text)
                        if valor_planchas < 0.0:
                            st.error("El precio de las planchas debe ser mayor o igual a 0")
                            valor_planchas = 0.0
                        st.session_state['precio_planchas'] = valor_planchas
                    else:
                        st.session_state['precio_planchas'] = 0.0
                except ValueError:
                    st.error("Por favor ingrese un valor numérico válido para las planchas")
                    st.session_state['precio_planchas'] = 0.0
                
                st.caption(f"Valor configurado: ${st.session_state.get('precio_planchas', 0.0):.2f}")
            else: 
                if 'precio_planchas' in st.session_state:
                    st.session_state.precio_planchas = 0.0
# --- Fin _mostrar_ajustes_admin ---

def mostrar_calculadora():
    """Vista principal de la calculadora"""
    if not initialize_session():
        st.error("Error de inicialización")
        return

    # --- Lógica de Carga para Modo Edición ---
    datos_cargados = None
    is_edit_mode = st.session_state.get('modo_edicion', False)
    if is_edit_mode:
        cotizacion_id_editar = st.session_state.get('cotizacion_id_editar')
        
        if cotizacion_id_editar:
            # Solo cargar si no tenemos ya los datos cargados en sesión 
            # (evita recargar en cada rerun dentro del modo edición)
            if 'datos_cotizacion_editar' not in st.session_state or st.session_state.datos_cotizacion_editar is None:
                with st.spinner("Cargando datos para edición..."):
                    db = st.session_state.db
                    datos_cargados = db.get_full_cotizacion_details(cotizacion_id_editar)
                    
                    if datos_cargados:
                        st.session_state.datos_cotizacion_editar = datos_cargados
                        
                        # Forzar tipo producto ANTES de mostrar selector
                        tipo_producto_id_cargado = datos_cargados.get('tipo_producto_id')
                        if tipo_producto_id_cargado:
                            tipos_producto_list = st.session_state.initial_data.get('tipos_producto', [])
                            tipo_producto_obj_cargado = next((tp for tp in tipos_producto_list if tp.id == tipo_producto_id_cargado), None)
                            if tipo_producto_obj_cargado:
                                st.session_state['tipo_producto_seleccionado'] = tipo_producto_id_cargado
                                st.session_state['tipo_producto_objeto'] = tipo_producto_obj_cargado
                            else:
                                st.error(f"Error crítico: Tipo de producto ID {tipo_producto_id_cargado} de la cotización no se encontró en los datos iniciales. No se puede editar.")
                                # Limpiar estado para evitar inconsistencias
                                if 'tipo_producto_objeto' in st.session_state: del st.session_state['tipo_producto_objeto']
                        
                        # --- NUEVO: Precargar parámetros especiales almacenados (si existen) ---
                        try:
                            calculos_raw = db.get_calculos_escala_cotizacion(cotizacion_id_editar)
                            if calculos_raw and isinstance(calculos_raw, dict):
                                # --- NUEVO: Cargar unidad de montaje persistida ---
                                unidad_z = calculos_raw.get('unidad_z_dientes')
                                if unidad_z is not None:
                                    st.session_state['unidad_montaje_dientes'] = int(unidad_z)
                                    print(f"DEBUG: Unidad de montaje cargada de BD: {unidad_z}")

                                params_esp = calculos_raw.get('parametros_especiales')
                                if isinstance(params_esp, dict):
                                    st.session_state['ajustar_material'] = bool(params_esp.get('ajustar_material', False))
                                    if params_esp.get('valor_material_ajustado') is not None:
                                        st.session_state['valor_material_ajustado'] = params_esp.get('valor_material_ajustado')
                                    st.session_state['ajustar_troquel'] = bool(params_esp.get('ajustar_troquel', False))
                                    if params_esp.get('precio_troquel') is not None:
                                        st.session_state['precio_troquel'] = params_esp.get('precio_troquel')
                                    st.session_state['ajustar_planchas'] = bool(params_esp.get('ajustar_planchas', False))
                                    if params_esp.get('precio_planchas') is not None:
                                        st.session_state['precio_planchas'] = params_esp.get('precio_planchas')
                                    st.session_state['ajustar_rentabilidad'] = bool(params_esp.get('ajustar_rentabilidad', False))
                                    if params_esp.get('rentabilidad_ajustada') is not None:
                                        st.session_state['rentabilidad_ajustada'] = params_esp.get('rentabilidad_ajustada')
                        except Exception as e_precarga:
                            print(f"ADVERTENCIA: No se pudieron precargar parametros_especiales: {e_precarga}")
                        
                        # --- NUEVO: Establecer existe_troquel en session_state.tiene_troquel ---
                        try:
                            # Obtener el valor de existe_troquel de los datos cargados
                            existe_troquel_cargado = datos_cargados.get('existe_troquel', False)
                            print(f"DEBUG: Valor de existe_troquel cargado de BD: {existe_troquel_cargado} (tipo: {type(existe_troquel_cargado)})")
                            
                            # Convertir a booleano explícitamente
                            existe_troquel_bool = bool(existe_troquel_cargado)
                            print(f"DEBUG: Valor convertido a booleano: {existe_troquel_bool}")
                            
                            # Establecer en session_state.tiene_troquel
                            st.session_state['tiene_troquel'] = "Sí" if existe_troquel_bool else "No"
                            print(f"DEBUG: Establecido session_state.tiene_troquel = '{st.session_state['tiene_troquel']}'")
                            
                        except Exception as e_troquel:
                            print(f"ERROR: No se pudo establecer existe_troquel en session_state: {e_troquel}")
                            # Establecer valor por defecto
                            st.session_state['tiene_troquel'] = "No"
                        # --- FIN: Establecer existe_troquel ---
                        
                        # --- NUEVO: Establecer todos los valores necesarios en session_state ---
                        try:
                            # Dimensiones y tintas
                            st.session_state['ancho'] = float(datos_cargados.get('ancho', 50.0))
                            st.session_state['avance'] = float(datos_cargados.get('avance', 50.0))
                            st.session_state['numero_pistas'] = int(datos_cargados.get('numero_pistas', 1))
                            st.session_state['num_tintas'] = int(datos_cargados.get('num_tintas', 0))
                            
                            # Empaque
                            st.session_state['num_paquetes'] = int(datos_cargados.get('num_paquetes_rollos', 1))
                            
                            # Opciones adicionales
                            st.session_state['planchas_separadas'] = bool(datos_cargados.get('planchas_x_separado', False))
                            
                            # Valores de troquel y planchas
                            valor_troquel = datos_cargados.get('valor_troquel')
                            if valor_troquel is not None:
                                st.session_state['valor_troquel'] = float(valor_troquel)
                            else:
                                st.session_state['valor_troquel'] = 0.0
                                
                            valor_plancha_separado = datos_cargados.get('valor_plancha_separado')
                            if valor_plancha_separado is not None:
                                st.session_state['valor_plancha_separado'] = float(valor_plancha_separado)
                            else:
                                st.session_state['valor_plancha_separado'] = 0.0
                            
                            # Material y acabado
                            st.session_state['material_adhesivo_id'] = datos_cargados.get('material_adhesivo_id')
                            st.session_state['acabado_id'] = datos_cargados.get('acabado_id')
                            
                            # Grafado (solo para mangas)
                            if datos_cargados.get('es_manga', False):
                                st.session_state['altura_grafado'] = float(datos_cargados.get('altura_grafado', 0.0)) if datos_cargados.get('altura_grafado') is not None else 0.0
                                st.session_state['tipo_grafado_id'] = datos_cargados.get('tipo_grafado_id')
                            
                            # Escalas (convertir a string formateado)
                            escalas = datos_cargados.get('escalas', [])
                            if escalas:
                                escalas_str = ", ".join([str(esc.get('escala', '')) for esc in escalas if esc.get('escala')])
                                st.session_state['escalas'] = escalas_str
                            else:
                                st.session_state['escalas'] = ""
                                
                            print(f"DEBUG: Valores establecidos en session_state:")
                            print(f"  ancho: {st.session_state.get('ancho')}")
                            print(f"  avance: {st.session_state.get('avance')}")
                            print(f"  numero_pistas: {st.session_state.get('numero_pistas')}")
                            print(f"  num_tintas: {st.session_state.get('num_tintas')}")
                            print(f"  num_paquetes: {st.session_state.get('num_paquetes')}")
                            print(f"  planchas_separadas: {st.session_state.get('planchas_separadas')}")
                            print(f"  valor_troquel: {st.session_state.get('valor_troquel')}")
                            print(f"  valor_plancha_separado: {st.session_state.get('valor_plancha_separado')}")
                            print(f"  material_adhesivo_id: {st.session_state.get('material_adhesivo_id')}")
                            print(f"  acabado_id: {st.session_state.get('acabado_id')}")
                            print(f"  escalas: {st.session_state.get('escalas')}")
                            
                        except Exception as e_valores:
                            print(f"ERROR: No se pudieron establecer valores en session_state: {e_valores}")
                        # --- FIN: Establecer todos los valores ---
                        
                        # --- NUEVO: Cargar modelo de cotización existente ---
                        try:
                            from src.data.models import Cotizacion
                            # Crear modelo de cotización existente para edición
                            cotizacion_existente = Cotizacion()
                            cotizacion_existente.id = cotizacion_id_editar
                            cotizacion_existente.material_adhesivo_id = datos_cargados.get('material_adhesivo_id')
                            cotizacion_existente.acabado_id = datos_cargados.get('acabado_id')
                            cotizacion_existente.num_tintas = int(datos_cargados.get('num_tintas', 0))
                            cotizacion_existente.num_paquetes_rollos = int(datos_cargados.get('num_paquetes_rollos', 1))
                            cotizacion_existente.es_manga = bool(datos_cargados.get('es_manga', False))
                            cotizacion_existente.valor_troquel = float(datos_cargados.get('valor_troquel', 0.0)) if datos_cargados.get('valor_troquel') is not None else None
                            cotizacion_existente.valor_plancha_separado = float(datos_cargados.get('valor_plancha_separado', 0.0)) if datos_cargados.get('valor_plancha_separado') is not None else None
                            cotizacion_existente.planchas_x_separado = bool(datos_cargados.get('planchas_x_separado', False))
                            cotizacion_existente.existe_troquel = bool(datos_cargados.get('existe_troquel', False))
                            cotizacion_existente.numero_pistas = int(datos_cargados.get('numero_pistas', 1))
                            cotizacion_existente.tipo_producto_id = datos_cargados.get('tipo_producto_id')
                            cotizacion_existente.ancho = float(datos_cargados.get('ancho', 0.0))
                            cotizacion_existente.avance = float(datos_cargados.get('avance', 0.0))
                            cotizacion_existente.altura_grafado = float(datos_cargados.get('altura_grafado', 0.0)) if datos_cargados.get('altura_grafado') is not None else None
                            cotizacion_existente.tipo_grafado_id = datos_cargados.get('tipo_grafado_id')
                            
                            # Establecer en session_state
                            st.session_state['cotizacion_model'] = cotizacion_existente
                            print(f"DEBUG: Modelo de cotización existente cargado con ID: {cotizacion_existente.id}")
                            
                        except Exception as e_modelo:
                            print(f"ERROR: No se pudo cargar el modelo de cotización existente: {e_modelo}")
                        # --- FIN: Cargar modelo de cotización existente ---
                    else:
                        st.error(f"No se pudieron cargar detalles para Cotización ID {cotizacion_id_editar}.")
                        st.session_state.modo_edicion = False
                        st.session_state.cotizacion_a_editar_id = None
                        st.rerun()
            else:
                 # Ya tenemos los datos cargados, usarlos
                 datos_cargados = st.session_state.datos_cotizacion_editar 
        else:
             st.warning("Modo edición activado pero no se encontró ID.")
             st.session_state.modo_edicion = False
             # Limpiar por si acaso
             if 'datos_cotizacion_editar' in st.session_state: del st.session_state['datos_cotizacion_editar']
             st.rerun()

    # --- Barra de Edición (si aplica) --- 
    if is_edit_mode:
        # Mostrar información de la cotización que se está editando
        cotizacion_info = ""
        if datos_cargados:
            num_cot = datos_cargados.get('numero_cotizacion', 'N/A')
            cliente_nom = datos_cargados.get('cliente_nombre', 'N/A')
            ref_desc = datos_cargados.get('referencia_descripcion', 'N/A')
            cotizacion_info = f" - Cotización #{num_cot} | Cliente: {cliente_nom} | Ref: {ref_desc}"
        
        edit_cols = st.columns([0.8, 0.2])
        with edit_cols[0]:
            st.warning(f"**✏️ Modo Edición{cotizacion_info}**")
            st.caption("Los cambios sobrescribirán la versión anterior. Se usarán los precios actuales de materiales/acabados.")
        with edit_cols[1]:
            if st.button("❌ Cancelar Edición", key="cancel_edit_button", width="stretch"):
                st.session_state.modo_edicion = False
                st.session_state.cotizacion_a_editar_id = None
                st.session_state.datos_cotizacion_editar = None
                SessionManager.reset_calculator_widgets()
                st.session_state.current_view = 'manage_quotes' # Volver a la lista
                st.rerun()
        st.divider()
        st.title("📝 Editar Cotización") 
    else:
        st.title("📊 Cotizador Flexo Impresos")
    # --- Fin Barra Edición ---
    
    st.write(f"Selecciona un cliente y un tipo de producto para comenzar a cotizar.")
    
    clientes = get_filtered_clients()
    default_cliente_index = 0
    if is_edit_mode and datos_cargados:
        cliente_id_cargado = datos_cargados.get('cliente_id')
        if cliente_id_cargado:
            try:
                default_cliente_index = next(i for i, c in enumerate(clientes) if c.id == cliente_id_cargado)
            except StopIteration:
                 st.warning(f"Cliente ID {cliente_id_cargado} no encontrado.")
                 default_cliente_index = 0 
                 
    cliente_seleccionado = st.selectbox(
        "Cliente",
        options=clientes,
        format_func=lambda x: x.nombre,
        index=default_cliente_index, 
        key="cliente_selector",
        disabled=is_edit_mode # Deshabilitar en modo edición
    )
    
    if cliente_seleccionado:
        st.session_state.cliente_seleccionado = cliente_seleccionado 
        
        # === INICIO SECCIÓN FUERA DEL FORMULARIO ===
        
        # -- Tipo de Producto (Fuera del form) --
        tipo_producto_seleccionado_id = None
        tipo_producto_objeto = None
        if not is_edit_mode:
            # Permitir seleccionar si no estamos editando
            if 'tipo_producto_seleccionado' not in st.session_state:
                tipos_producto = st.session_state.initial_data.get('tipos_producto', [])
                tipo_producto = st.selectbox(
                    "Tipo de Producto",
                    options=tipos_producto,
                    format_func=lambda x: x.nombre,
                    key="tipo_producto_select",
                    help="Seleccione si es manga o etiqueta"
                )
                if st.button("Seleccionar producto"):
                    st.session_state['tipo_producto_seleccionado'] = tipo_producto.id
                    st.session_state['tipo_producto_objeto'] = tipo_producto
                    # Limpiar material/adhesivo si cambia tipo producto
                    st.session_state['material_id'] = None
                    st.session_state['adhesivo_id'] = None
                    st.rerun()
            else:
                # Mostrar tipo ya seleccionado y botón para cambiar
                tipo_producto_seleccionado_id = st.session_state['tipo_producto_seleccionado']
                
                # --- VERIFICACIÓN ADICIONAL: Si el ID es None, manejar como si no existiera la clave ---
                if tipo_producto_seleccionado_id is None:
                    st.warning("Debe seleccionar un tipo de producto para continuar.")
                    # Limpiar la clave del estado para forzar el flujo correcto
                    del st.session_state['tipo_producto_seleccionado']
                    if 'tipo_producto_objeto' in st.session_state: 
                        del st.session_state['tipo_producto_objeto']
                    # Forzar rerun para mostrar el selector de tipo
                    st.rerun()
                # --- FIN VERIFICACIÓN ADICIONAL ---
                
                # --- REFUERZO: Volver a buscar el objeto desde el ID --- 
                tipos_producto_list = st.session_state.initial_data.get('tipos_producto', [])
                tipo_producto_objeto = next((tp for tp in tipos_producto_list if tp.id == tipo_producto_seleccionado_id), None)
                
                # Guardar el objeto recuperado (o None si no se encontró) de nuevo en el estado
                st.session_state['tipo_producto_objeto'] = tipo_producto_objeto 
                # -----------------------------------------------------
                
                # --- Verificación (ya existente y ahora más robusta) --- 
                if tipo_producto_objeto is not None:
                    st.success(f"Tipo producto: {tipo_producto_objeto.nombre}")
                else:
                    # Ahora este error indica que el ID guardado no corresponde a ningún tipo válido
                    st.error(f"Error crítico: ID de tipo de producto ({tipo_producto_seleccionado_id}) inválido en sesión.")
                    if st.button("Reintentar selección de producto"):
                         del st.session_state['tipo_producto_seleccionado']
                         if 'tipo_producto_objeto' in st.session_state: del st.session_state['tipo_producto_objeto']
                         st.rerun()
                    return # Detener ejecución si el objeto es None aquí
                    
                if st.button("Cambiar tipo de producto"):
                    del st.session_state['tipo_producto_seleccionado']
                    del st.session_state['tipo_producto_objeto']
                    # Limpiar también material/adhesivo
                    st.session_state['material_id'] = None
                    st.session_state['adhesivo_id'] = None
                    st.rerun()
        else: 
            # Modo edición: solo mostrar, obtener ID y objeto del estado
            tipo_producto_seleccionado_id = st.session_state.get('tipo_producto_seleccionado')
            tipo_producto_objeto = st.session_state.get('tipo_producto_objeto')
            if tipo_producto_objeto is not None: # <-- CORRECCIÓN: Check explícito para None
                 st.success(f"Tipo producto: {tipo_producto_objeto.nombre} (No editable)")
            else:
                 st.error("Error: Tipo de producto no definido en modo edición.")
                 return # No continuar si falta en modo edición
        
        # Determinar es_manga basado en la selección (necesario para _mostrar_material)
        es_manga = (tipo_producto_seleccionado_id == 2) if tipo_producto_seleccionado_id else False
        st.session_state['es_manga'] = es_manga
        
        # -- Material (Fuera del form, si ya se seleccionó Tipo Producto) --
        material_obj_actual = None
        if tipo_producto_seleccionado_id:
            materiales = st.session_state.initial_data.get('materiales', [])
            _mostrar_material(es_manga, materiales, datos_cargados)
            st.divider()
            # Obtener el objeto material actual DESPUÉS de llamar a _mostrar_material
            material_obj_actual = st.session_state.get('material_select')
        
        # -- Adhesivo (Fuera del form, si aplica y hay material) --
        if not es_manga and material_obj_actual:
            material_id_actual = material_obj_actual.id
            adhesivos_filtrados = []
            db = st.session_state.db
            try:
                print(f"APP: Llamando a get_adhesivos_for_material para ID: {material_id_actual}") # DEBUG
                adhesivos_filtrados = db.get_adhesivos_for_material(material_id_actual)
                print(f"APP: Resultado get_adhesivos_for_material: {len(adhesivos_filtrados)} items") # DEBUG
            except Exception as e:
                st.error(f"APP: Error al obtener adhesivos: {e}")
                
            # Llamar a _mostrar_adhesivo fuera del form
            _mostrar_adhesivo(adhesivos_filtrados, material_obj_actual, datos_cargados)
            st.divider()
            

            
        # -- Ajustes Admin (Fuera del form) --> SE MOVERÁ AL FINAL <--
        # _mostrar_ajustes_admin() 
        # st.divider()

        # === FIN SECCIÓN FUERA DEL FORMULARIO (INICIAL) ===
        
        # --- INICIO FORMULARIO (SOLO WIDGETS INTERNOS) --- 
        # Mostrar el formulario SOLO si ya se seleccionó el tipo de producto
        if tipo_producto_seleccionado_id:
            # Ya no usamos st.form aquí, los widgets se leen directamente de session_state
            # Eliminamos with st.form(...) y st.form_submit_button
            
            # === MOVER LÓGICA DE ESCALAS AQUÍ ===
            # --- INICIO: Lógica para obtener valor inicial de escalas en modo edición --- 
            default_escalas_str = "" 
            if is_edit_mode and datos_cargados:
                escalas_guardadas = datos_cargados.get('escalas_guardadas') 
                if escalas_guardadas and isinstance(escalas_guardadas, list):
                    default_escalas_str = ", ".join(map(str, escalas_guardadas))
                    print(f"-- DEBUG (Modo Edición): Escalas cargadas: {escalas_guardadas} -> String: '{default_escalas_str}'")
                else:
                    print(f"-- DEBUG (Modo Edición): No se encontraron 'escalas_guardadas' válidas.")
            # --- FIN: Lógica para obtener valor inicial --- 
            # ====================================
            
            # Llamar a la función refactorizada para mostrar secciones internas
            # PASAR default_escalas_str A LA FUNCIÓN
            mostrar_secciones_internas_formulario(
                es_manga=es_manga, 
                initial_data=st.session_state.initial_data, 
                datos_cargados=datos_cargados, 
                default_escalas=default_escalas_str # <-- NUEVO ARGUMENTO
            )
            
            # -- EL CÓDIGO AÑADIDO ERRÓNEAMENTE POR EL PASO ANTERIOR SE ELIMINA DE AQUÍ --
            
            # --- Ajustes Admin YA NO ESTÁ AQUÍ --- 

            # --- El botón Calcular/Actualizar se mueve abajo --- 
                
            # --- MOVER AJUSTES ADMIN AQUÍ (SOLO DESPUÉS DE SELECCIONAR TIPO PRODUCTO) --- 
        st.divider() # Añadir un divisor antes de los ajustes
        _mostrar_ajustes_admin(datos_cargados) # Llamar a la función de ajustes aquí
        # --- NO MOSTRAR AJUSTES ADMIN AQUÍ SI NO SE HA SELECCIONADO TIPO PRODUCTO --- 
        # st.divider()
        # _mostrar_ajustes_admin()
        # st.divider()

        # --- MOVER BOTÓN CALCULAR/ACTUALIZAR AQUÍ --- 
        if tipo_producto_seleccionado_id: # Solo mostrar si hay tipo producto
            # Mostrar ajustes Admin también solo después de seleccionar tipo producto
            st.divider()

            button_label = "Actualizar Cálculo" if is_edit_mode else "Calcular"
            if st.button(button_label, key="calculate_button_main"):
                # === RECOLECTAR DATOS ===
                datos_formulario_enviado = {}
                validation_errors = []
                try:
                    # ** Obtener valores de FUERA del form (desde session_state) **
                    datos_formulario_enviado['material_id'] = st.session_state.get('material_id')
                    datos_formulario_enviado['adhesivo_id'] = st.session_state.get('adhesivo_id') # Será None si es manga o no se seleccionó
                    datos_formulario_enviado['tipo_producto_id'] = st.session_state.get('tipo_producto_seleccionado')
                    datos_formulario_enviado['es_manga'] = st.session_state.get('es_manga')
                    
                    # Validar que los IDs necesarios (fuera del form) existan
                    if not datos_formulario_enviado['material_id']:
                         validation_errors.append("Material no definido en sesión.")
                    if not datos_formulario_enviado['es_manga'] and not datos_formulario_enviado['adhesivo_id']:
                         validation_errors.append("Adhesivo no definido en sesión para etiquetas.")
                    if not datos_formulario_enviado['tipo_producto_id']:
                        validation_errors.append("Tipo de producto no definido en sesión.")

                    # ** Obtener valores de DENTRO del form (desde session_state via keys) **
                    # Escalas 
                    escalas_texto = st.session_state.get('escalas_texto_input', '')
                    escalas_usuario = [int(e.strip()) for e in escalas_texto.split(",") if e.strip()]
                    if not escalas_usuario or any(e < 100 for e in escalas_usuario):
                        raise ValueError("Ingrese al menos una escala válida (>= 100).")
                    datos_formulario_enviado['escalas'] = sorted(list(set(escalas_usuario)))
                    
                    # Dimensiones y Tintas
                    datos_formulario_enviado['ancho'] = float(st.session_state.get('ancho', 0.0))
                    datos_formulario_enviado['avance'] = float(st.session_state.get('avance', 0.0))
                    datos_formulario_enviado['num_tintas'] = int(st.session_state.get('num_tintas', 0))
                    # Pistas 
                    if datos_formulario_enviado['es_manga']:
                         if st.session_state.get('usuario_rol') == 'comercial': datos_formulario_enviado['pistas'] = 1
                         else: datos_formulario_enviado['pistas'] = int(st.session_state.get('num_pistas_manga', 1))
                    else:
                        datos_formulario_enviado['pistas'] = int(st.session_state.get('num_pistas_otro', 1))

                    # Acabado/Grafado
                    if datos_formulario_enviado['es_manga']:
                        grafado_obj = st.session_state.get('tipo_grafado_select')
                        if grafado_obj:
                            datos_formulario_enviado['tipo_grafado_id'] = grafado_obj.id
                            datos_formulario_enviado['tipo_grafado_nombre'] = grafado_obj.nombre

                            # --- Validación de altura_grafado ---
                            if grafado_obj.id in [3, 4]: # IDs que requieren altura
                                altura_grafado_value = st.session_state.get('altura_grafado')
                                if altura_grafado_value is not None:
                                    try:
                                        # Intentar convertir a float solo si no es None
                                        datos_formulario_enviado['altura_grafado'] = float(altura_grafado_value)
                                    except (ValueError, TypeError):
                                        validation_errors.append("Altura de grafado debe ser un número válido.")
                                        datos_formulario_enviado['altura_grafado'] = None
                                else:
                                    # Es requerido, así que si es None, es un error
                                    validation_errors.append("Altura de grafado es requerida para este tipo de grafado.")
                                    datos_formulario_enviado['altura_grafado'] = None
                            # --- Fin Validación ---
                            else: # Si el tipo de grafado no requiere altura
                                datos_formulario_enviado['altura_grafado'] = None
                        else:
                            validation_errors.append("Tipo de grafado no seleccionado.")
                        datos_formulario_enviado['acabado_id'] = None
                    else: # Etiqueta
                        acabado_obj = st.session_state.get('acabado_select')
                        if acabado_obj:
                            datos_formulario_enviado['acabado_id'] = acabado_obj.id
                        else:
                            validation_errors.append("Acabado no seleccionado.")
                        datos_formulario_enviado['tipo_grafado_id'] = None
                        datos_formulario_enviado['altura_grafado'] = None

                    # Empaque
                    datos_formulario_enviado['num_paquetes'] = int(st.session_state.get('num_paquetes', 0))
                    # Opciones Adicionales
                    # CORRECCIÓN: Convertir correctamente el valor de tiene_troquel
                    tiene_troquel_value = st.session_state.get('tiene_troquel', 'No')
                    print(f"\n=== DEBUG CONVERSIÓN TROQUEL ===")
                    print(f"Valor original en session_state: {tiene_troquel_value} (tipo: {type(tiene_troquel_value)})")
                    
                    if isinstance(tiene_troquel_value, str):
                        datos_formulario_enviado['tiene_troquel'] = tiene_troquel_value == 'Sí'
                        print(f"Es string, comparando con 'Sí': {datos_formulario_enviado['tiene_troquel']}")
                    else:
                        datos_formulario_enviado['tiene_troquel'] = bool(tiene_troquel_value)
                        print(f"No es string, convirtiendo a bool: {datos_formulario_enviado['tiene_troquel']}")
                    
                    print(f"Valor final en datos_formulario_enviado: {datos_formulario_enviado['tiene_troquel']}")
                    
                    datos_formulario_enviado['planchas_separadas'] = bool(st.session_state.get('planchas_separadas', False))
                    # Unidad de montaje elegida por el usuario (si marcó troquel existente)
                    if datos_formulario_enviado['tiene_troquel']:
                        um_dientes = st.session_state.get('unidad_montaje_dientes')
                        try:
                            datos_formulario_enviado['unidad_montaje_dientes'] = float(um_dientes) if um_dientes is not None else None
                        except Exception:
                            datos_formulario_enviado['unidad_montaje_dientes'] = None

                         
                    # Calcular ID Combinado (como antes)
                    mat_id = datos_formulario_enviado.get('material_id')
                    adh_id = datos_formulario_enviado.get('adhesivo_id')
                    id_combinado = None
                    if mat_id:
                        db = st.session_state.db
                        if datos_formulario_enviado['es_manga']:
                            ID_SIN_ADHESIVO = 4 # Asumiendo ID 4
                            ma_entry = db.get_material_adhesivo_entry(mat_id, ID_SIN_ADHESIVO)
                            if ma_entry: id_combinado = ma_entry['id']
                        elif adh_id:
                            ma_entry = db.get_material_adhesivo_entry(mat_id, adh_id)
                            if ma_entry: id_combinado = ma_entry['id']
                    if id_combinado: datos_formulario_enviado['material_adhesivo_id'] = id_combinado
                    else: validation_errors.append("No se encontró ID combinado Material/Adhesivo. Verifique config.")
                         
                except ValueError as ve: validation_errors.append(f"Error en valor numérico: {ve}")
                except KeyError as ke: validation_errors.append(f"Falta un campo esperado en session_state: {ke}")
                except Exception as e: validation_errors.append(f"Error inesperado recolectando datos: {e}")
                # === FIN RECOLECCIÓN ===
                
                # --- Validación y Ejecución --- 
                if not validation_errors:
                    # Necesitamos el objeto cliente seleccionado, asegurarnos que está en sesión
                    cliente_seleccionado = st.session_state.get('cliente_seleccionado')
                    if cliente_seleccionado:
                        resultados = handle_calculation(datos_formulario_enviado, cliente_seleccionado)
                    else:
                        st.error("Error interno: Cliente no encontrado en sesión.")
                else:
                    for error in validation_errors: st.error(error)
                    st.warning("No se pudo calcular debido a errores en los datos ingresados.")
        # --- FIN MOVIMIENTO BOTÓN ---

# NOTA: Las funciones show_manage_clients() y show_create_client() 
# se importan desde src.ui.manage_clients_view (línea 56)
# No definir aquí para evitar duplicación

def main():
    """Función principal que orquesta el flujo de la aplicación"""
    # Inicializar servicios primero
    initialize_services()

    # Inicializar el estado de la sesión
    SessionManager.init_session()

    # Si el usuario está autenticado pero faltan datos críticos, restaurar
    if st.session_state.get('authenticated', False):
        if not st.session_state.get('user_id') or not st.session_state.get('usuario_rol') or not st.session_state.get('perfil_usuario'):
            db = st.session_state.db
            user_id = st.session_state.get('user_id')
            perfil = db.get_perfil(user_id) if user_id else None
            usuario_rol = perfil.get('rol_nombre') if perfil else None
            SessionManager.full_init(user_id=user_id, usuario_rol=usuario_rol, perfil_usuario=perfil)

    # Verificar autenticación
    if not st.session_state.authenticated:
        show_login()
        return

    # Mostrar info de usuario y opciones (actualizar perfil / logout) en el sidebar
    show_user_info()
    # Renderizar formulario de actualización de perfil si el usuario lo activó
    show_profile_update()

    # Mostrar mensajes pendientes
    if st.session_state.messages:
        for msg_type, message in st.session_state.messages:
            if msg_type == 'success':
                st.success(message)
            elif msg_type == 'error':
                st.error(message)
            else:
                st.info(message)
        SessionManager.clear_messages()
        
    # --- Mostrar Navegación --- 
    show_navigation()
    # ------------------------

    # --- Cargar datos iniciales si no están ---
    # Asegurar que la clave exista, aunque sea como None inicialmente
    if 'initial_data' not in st.session_state:
        st.session_state.initial_data = None 

    # Intentar cargar solo si aún no tenemos datos válidos
    if st.session_state.initial_data is None: 
        with st.spinner("Cargando datos iniciales (materiales, acabados, etc.)..."):
            try:
                # Llamar a la función cacheada
                data = load_initial_data() 
                if data:
                    st.session_state.initial_data = data
                else:
                    # Si load_initial_data devuelve None o {}, marcamos que no se cargó
                    st.session_state.initial_data = None 
                    SessionManager.add_message('error', "Error crítico: No se pudieron cargar los datos iniciales necesarios (empty data returned).")
            except Exception as e_load:
                 st.session_state.initial_data = None # Marcar como no cargado en excepción
                 SessionManager.add_message('error', f"Excepción al cargar datos iniciales: {e_load}")
                 if st.session_state.get('usuario_rol') == 'administrador':
                     st.exception(e_load)

    # Verificar si los datos se cargaron correctamente ANTES de continuar
    if not st.session_state.get('initial_data'):
        st.error("No se pudieron cargar los datos iniciales. La aplicación no puede continuar.")
        # Mostrar mensajes de error acumulados
        if st.session_state.messages:
            for msg_type, message in st.session_state.messages:
                if msg_type == 'error': st.error(message)
                else: st.info(message)
            SessionManager.clear_messages()
        st.stop() # Detener ejecución si los datos no están
    # --------------------------------------------

    # SOLUCIÓN STREAMLIT CLOUD: Detectar triggers de navegación
    # Método 1: Trigger directo
    if st.session_state.get('trigger_editar_cotizacion', False):
        print("DEBUG ROUTER: Detectado trigger de edición")
        st.session_state.current_view = 'calculator'
        st.session_state.trigger_editar_cotizacion = False
    
    # Método 2: Query params (más confiable en Cloud)
    try:
        query_params = st.query_params
        if "edit" in query_params:
            cotizacion_id = query_params["edit"]
            print(f"DEBUG ROUTER: Detectado edit en query params: {cotizacion_id}")
            
            # Configurar modo edición
            st.session_state.modo_edicion = True
            st.session_state.cotizacion_id_editar = int(cotizacion_id)
            st.session_state.datos_cotizacion_editar = None
            st.session_state.current_view = 'calculator'
            
            # Limpiar query param
            st.query_params.clear()
    except:
        try:
            # Fallback a método antiguo
            query_params = st.experimental_get_query_params()
            if "edit" in query_params:
                cotizacion_id = query_params["edit"][0]
                print(f"DEBUG ROUTER: Detectado edit en query params (método antiguo): {cotizacion_id}")
                
                st.session_state.modo_edicion = True
                st.session_state.cotizacion_id_editar = int(cotizacion_id)
                st.session_state.datos_cotizacion_editar = None
                st.session_state.current_view = 'calculator'
                
                st.experimental_set_query_params()
        except:
            pass
    
    # Mostrar la vista actual
    current_view = st.session_state.get('current_view', 'calculator')

    if current_view == 'calculator':
        mostrar_calculadora()
    elif current_view == 'quote_results':
        show_quote_results()
    elif current_view == 'manage_quotes':
        show_manage_quotes()
    elif current_view == 'manage_clients':
        show_manage_clients()
    elif current_view == 'crear_cliente':
        show_create_client()
    elif current_view == 'dashboard':
        show_dashboard()
    elif current_view == 'manage_values':
        show_manage_values()
    elif current_view == 'manage_policies':
        show_manage_policies()
    elif current_view == 'manage_cartera':
        show_manage_cartera_policies()
    elif current_view == 'manage_commercials':
        show_manage_commercials()
    else:
        # Si la vista no coincide con ninguna opción, volver a la calculadora
        st.warning(f"Vista desconocida: {current_view}. Volviendo a la calculadora.")
        st.session_state.current_view = 'calculator'
        st.rerun()

def show_quote_results():
    """Muestra los resultados de la cotización calculada."""
    # --- MOSTRAR INFORME SI YA ESTÁ GUARDADA ---
    if st.session_state.get('cotizacion_guardada', False) and st.session_state.get('cotizacion_id') is not None:
        # Obtener el número de cotización de los datos completos
        numero_cotizacion = None
        if 'datos_completos_cot' in st.session_state and st.session_state.datos_completos_cot:
            numero_cotizacion = st.session_state.datos_completos_cot.get('numero_cotizacion', None)
            
        # Mostrar mensaje con el número de cotización si está disponible
        if numero_cotizacion:
            st.success(f"Cotización #{numero_cotizacion} guardada ✓")
        else:
            st.success(f"Cotización #{st.session_state.cotizacion_id} guardada ✓")
        
        # --- Botones de PDF y Nueva Cotización ---
        col_pdf, col_new = st.columns(2)
        with col_pdf:
             # --- Lógica para botón Generar PDF --- 
             if st.button("📄 Generar PDF", key="pdf_button_saved"):
                  with st.spinner("Generando PDF..."):
                      try:
                          # Obtener datos completos usando el ID guardado
                        cotizacion_id = st.session_state.cotizacion_id
                        datos_pdf = st.session_state.db.get_datos_completos_cotizacion(cotizacion_id)
                        if datos_pdf:
                              print(f"DEBUG PDF COTIZACION: datos_pdf contiene: {datos_pdf}") # <-- LÍNEA DE DEBUG AÑADIDA
                              pdf_gen = CotizacionPDF()
                              pdf_bytes = pdf_gen.generar_pdf(datos_pdf)
                              # Ofrecer descarga
                              st.download_button(
                                  label="Descargar PDF Ahora",
                                  data=pdf_bytes,
                                  file_name=f"{datos_pdf.get('identificador') or 'Cotizacion_' + str(datos_pdf.get('consecutivo', 'N'))}.pdf", # Usar identificador, con fallback y sin reemplazo de espacios
                                  mime="application/pdf"
                              )
                        else:
                              st.error("No se pudieron obtener los datos completos para generar el PDF.")
                      except Exception as e_pdf:
                          st.error(f"Error generando PDF: {e_pdf}")
                          traceback.print_exc()
        
        with col_new:
            if st.button("Nueva Cotización", key="new_quote_button_saved"):
                # Resetear todo para una nueva cotización
                st.session_state.current_view = 'calculator'
                st.session_state.cotizacion_guardada = False
                st.session_state.referencia_guardar = ""
                st.session_state.cotizacion_model = None
                st.session_state.current_calculation = None
                st.session_state.modo_edicion = False
                st.session_state.cotizacion_id_editar = None
                st.session_state.datos_cotizacion_editar = None
                if 'recotizacion_info' in st.session_state:
                    del st.session_state['recotizacion_info']
                if 'informe_tecnico_md' in st.session_state: # Limpiar informe anterior
                    del st.session_state['informe_tecnico_md']
                SessionManager.reset_calculator_widgets()
                st.rerun()
                
        # --- MOSTRAR INFORME TÉCNICO (SI EXISTE) ---
        st.divider() # Separador visual
        st.subheader("Informe Técnico para Impresión")
        informe_md = st.session_state.get("informe_tecnico_md", "*El informe técnico se genera al guardar la cotización.*")
        st.markdown(informe_md)
        
        # Botón para descargar el informe en PDF
        if 'cotizacion_guardada' in st.session_state and st.session_state.cotizacion_guardada and informe_md and informe_md != "*El informe técnico se genera al guardar la cotización.*":
            try:
                # Generar nombre de archivo usando número de cotización o identificador
                id_para_archivo = 'informe'  # Valor predeterminado
                nombre_cliente = ''
                if 'datos_completos_cot' in st.session_state and st.session_state.datos_completos_cot:
                    nombre_cliente = st.session_state.datos_completos_cot.get('cliente_nombre', '').replace(' ', '_')
                    numero_cotizacion = st.session_state.datos_completos_cot.get('numero_cotizacion', '')
                    if numero_cotizacion:
                        id_para_archivo = f"{numero_cotizacion}_{nombre_cliente}"
                
                nombre_archivo = f"Informe_Tecnico_{id_para_archivo}"
                
                # Generar enlace de descarga
                pdf_download_link = markdown_a_pdf(informe_md, nombre_archivo)
                if pdf_download_link:
                    st.markdown(pdf_download_link, unsafe_allow_html=True)
                else:
                    st.error("No se pudo generar el PDF para descarga.")
            except Exception as e_pdf:
                st.error(f"Error al preparar PDF para descarga: {e_pdf}")
        # -----------------------------------------
        return # Terminar aquí si ya está guardada

    # --- Lógica si la cotización AÚN NO está guardada ---
    if 'current_calculation' not in st.session_state or not st.session_state.current_calculation:
        st.error("No hay resultados para mostrar. Por favor, realice un cálculo primero.")
        if st.button("Volver a Calcular", key="back_to_calc_no_results"):
            st.session_state.current_view = 'calculator'
            st.rerun()
        return
    if 'cotizacion_model' not in st.session_state or st.session_state.cotizacion_model is None:
        st.error("Error interno: Modelo de cotización no preparado. Por favor, recalcule.")
        if st.button("Volver a Calcular", key="back_to_calc_no_model"):
            st.session_state.current_view = 'calculator'
            st.rerun()
        return
    calc = st.session_state.current_calculation
    if 'calculos_para_guardar' not in calc or not calc['calculos_para_guardar']:
        st.error("Error interno: Datos de cálculo para guardar no encontrados. Por favor, recalcule.")
        if st.button("Volver a Calcular", key="back_to_calc_no_save_data"):
            st.session_state.current_view = 'calculator'
            st.rerun()
        return
    
    cotizacion_preparada = st.session_state.cotizacion_model # Modelo listo para guardar
    datos_calculo_persistir = calc['calculos_para_guardar']
    
    st.markdown("## Resultados de la Cotización")
    

    # Mostrar resultados para cada escala
    st.markdown("### Resultados por Escala")
    resultados_df = pd.DataFrame(calc['results'])
    
    # Si existe el campo num_tintas_mostrar, usar ese para mostrar en lugar de num_tintas
    if 'num_tintas_mostrar' in resultados_df.columns:
        # Hacemos una copia para no modificar los datos originales guardados en session_state
        df_mostrar = resultados_df.copy()
        # Renombrar la columna para mayor claridad en el dataframe
        df_mostrar = df_mostrar.rename(columns={'num_tintas_mostrar': 'Tintas'})
        # Quitar columnas internas/técnicas que no son necesarias para el usuario
        columnas_a_quitar = ['num_tintas_original', 'num_tintas_interno', 'num_tintas']
        columnas_mostrar = [col for col in df_mostrar.columns if col not in columnas_a_quitar]
        st.dataframe(df_mostrar[columnas_mostrar])
    else:
        # Si no existe, mostrar el dataframe original
        st.dataframe(resultados_df)
    
    st.divider()
    
    # --- Formulario y Lógica de Guardado --- 
    is_edit_mode = st.session_state.get('modo_edicion', False)
    section_title = "Actualizar Cotización" if is_edit_mode else "Guardar Cotización"
    button_label = "💾 Actualizar" if is_edit_mode else "💾 Guardar Cotización"
    st.markdown(f"#### {section_title}")
    
    default_referencia = ""
    if is_edit_mode and 'datos_cotizacion_editar' in st.session_state and st.session_state.datos_cotizacion_editar:
        default_referencia = st.session_state.datos_cotizacion_editar.get('referencia_descripcion', "")
    elif 'referencia_guardar' in st.session_state:
        default_referencia = st.session_state.referencia_guardar
    
    with st.form("guardar_cotizacion_form"):
        referencia_desc = st.text_input(
            "Descripción de la referencia *",
            value=default_referencia,
            key="referencia_guardar_input", 
            help="Ingrese un nombre o descripción única para esta cotización (Ej: Etiqueta XYZ V1)"
        )
        
        # Selección de Comercial (Solo Admin)
        selected_comercial_id = None 
        if st.session_state.get('usuario_rol') == 'administrador':
            try:
                comerciales = st.session_state.db.get_perfiles_by_role('comercial')
                if comerciales:
                    opciones_comercial = [(c['id'], c['nombre']) for c in comerciales] 
                    opciones_display = [(None, "-- Seleccione Comercial --")] + opciones_comercial
                    default_comercial_index = 0
                    comercial_id_cargado = None
                    if is_edit_mode and 'datos_cotizacion_editar' in st.session_state and st.session_state.datos_cotizacion_editar:
                        comercial_id_cargado = st.session_state.datos_cotizacion_editar.get('comercial_id') 
                        if comercial_id_cargado:
                            try:
                                default_comercial_index = next(i for i, (id, _) in enumerate(opciones_display) if id == comercial_id_cargado)
                            except StopIteration:
                                default_comercial_index = 0 
                    selected_option = st.selectbox(
                        "Asignar a Comercial *", 
                        options=opciones_display, 
                        format_func=lambda x: x[1], 
                        key="comercial_selector_admin", 
                        index=default_comercial_index,
                        help="Seleccione el comercial al que pertenece esta cotización."
                    )
                else:
                    st.warning("No se encontraron comerciales para asignar.")
            except Exception as e_comm:
                st.error(f"Error al cargar lista de comerciales: {e_comm}")

        guardar = st.form_submit_button(button_label, type="primary")
        
        if guardar:
            # --- INICIO DEBUG ---
            print("--- DEBUG: Botón Guardar presionado ---")
            # --- FIN DEBUG ---
            error_guardado = False
            # Validaciones
            if not referencia_desc.strip():
                st.error("Debe ingresar una Referencia / Descripción para guardar la cotización.")
                error_guardado = True
            comercial_id_para_guardar = None
            if st.session_state.get('usuario_rol') == 'administrador':
                selected_comercial_tuple = st.session_state.get("comercial_selector_admin")
                selected_comercial_id = selected_comercial_tuple[0] if selected_comercial_tuple else None
                if selected_comercial_id is None:
                    st.error("Como administrador, debe seleccionar un comercial.")
                    error_guardado = True
                else:
                    comercial_id_para_guardar = selected_comercial_id
            else:
                comercial_id_para_guardar = st.session_state.user_id 
            
            # --- INICIO DEBUG ---
            print(f"--- DEBUG: Validaciones pasadas: {not error_guardado} ---")
            # --- FIN DEBUG ---

            # Proceso de Guardado/Actualización
            if not error_guardado:
                st.session_state.referencia_guardar = referencia_desc 
                spinner_text = "Actualizando cotización..." if is_edit_mode else "Guardando cotización..."
                # --- INICIO DEBUG ---
                print(f"--- DEBUG: Intentando guardar/actualizar. Modo edición: {is_edit_mode} ---")
                # --- FIN DEBUG ---
                with st.spinner(spinner_text):
                    try:
                        cliente_id = calc['cliente'].id 
                        if not comercial_id_para_guardar or not cliente_id or not datos_calculo_persistir:
                             st.error("Error interno: Faltan datos (cliente, comercial o cálculos).")
                             # --- INICIO DEBUG ---
                             print(f"--- DEBUG: Faltan datos! Comercial: {comercial_id_para_guardar}, Cliente: {cliente_id}, Datos Calculo: {'Sí' if datos_calculo_persistir else 'No'} ---")
                             # --- FIN DEBUG ---
                        else:
                            manager = st.session_state.cotizacion_manager
                            success = False
                            message = ""
                            cotizacion_id_final = None

                            # --- INICIO DEBUG ---
                            print(f"--- DEBUG: Llamando al manager. Modo edición: {is_edit_mode} ---")
                            # --- FIN DEBUG ---
                            if is_edit_mode:
                                cotizacion_id_a_actualizar = st.session_state.get('cotizacion_id_editar')
                                if not cotizacion_id_a_actualizar:
                                     st.error("Error: ID de cotización a editar no encontrado.")
                                else:
                                    es_recotizacion = False
                                    recotizacion_info_actual = st.session_state.get('recotizacion_info')
                                    if recotizacion_info_actual and recotizacion_info_actual['id'] == cotizacion_id_a_actualizar:
                                        es_recotizacion = True
                                    
                                    # --- DETECCIÓN DE AJUSTES ADMIN --- 
                                    admin_ajustes_activos = False
                                    if st.session_state.get('usuario_rol') == 'administrador':
                                        # Verificar todas las posibles formas de ajuste
                                        rentabilidad_ajustada = st.session_state.get('rentabilidad_ajustada')
                                        
                                        # --- DIAGNÓSTICO ESPECÍFICO DE RENTABILIDAD ---
                                        rentabilidad_modificada = st.session_state.get('ajustar_rentabilidad') or (rentabilidad_ajustada is not None and rentabilidad_ajustada > 0)
                                        # --- INICIO DEBUG: Diagnóstico Rentabilidad ---
                                        if rentabilidad_modificada:
                                            print(f"⚠️ DEBUG: Admin modificó rentabilidad. ajustar_rentabilidad={st.session_state.get('ajustar_rentabilidad')}, rentabilidad_ajustada={rentabilidad_ajustada}")
                                        # --- FIN DEBUG ---
                                        # --- FIN DIAGNÓSTICO ESPECÍFICO ---
                                        
                                        if (st.session_state.get('ajustar_rentabilidad') or 
                                            st.session_state.get('ajustar_material') or 
                                            st.session_state.get('ajustar_troquel') or 
                                            st.session_state.get('ajustar_planchas') or
                                            (rentabilidad_ajustada is not None and rentabilidad_ajustada > 0)):
                                            admin_ajustes_activos = True
                                            # --- INICIO DEBUG: Ajustes Admin ---
                                            print(f"--- DEBUG: AJUSTES ADMIN DETECTADOS ---")
                                            print(f"  ajustar_rentabilidad: {st.session_state.get('ajustar_rentabilidad')}")
                                            print(f"  rentabilidad_ajustada: {rentabilidad_ajustada}")
                                            print(f"  ajustar_material: {st.session_state.get('ajustar_material')}")
                                            print(f"  ajustar_troquel: {st.session_state.get('ajustar_troquel')}")
                                            print(f"  ajustar_planchas: {st.session_state.get('ajustar_planchas')}")
                                            # --- FIN DEBUG ---
                                    # --- FIN DETECCIÓN --- 
                                    
                                    # --- INICIO DEBUG: Antes de llamar actualizar ---
                                    print(f"--- DEBUG: Llamando manager.actualizar_cotizacion_existente(cotizacion_id={cotizacion_id_a_actualizar}, ...) ---")
                                    # --- FIN DEBUG ---
                                    success, message = manager.actualizar_cotizacion_existente(
                                        cotizacion_id=cotizacion_id_a_actualizar,
                                        cotizacion_model=cotizacion_preparada, 
                                        cliente_id=cliente_id,
                                        referencia_descripcion=referencia_desc,
                                        comercial_id=comercial_id_para_guardar,
                                        datos_calculo=datos_calculo_persistir,
                                        modificado_por=st.session_state.user_id,
                                        es_recotizacion=es_recotizacion,
                                        admin_ajustes_activos=admin_ajustes_activos  # Pasar el nuevo parámetro
                                    )
                                    # --- INICIO DEBUG: Después de llamar actualizar ---
                                    print(f"--- DEBUG: Resultado manager.actualizar: success={success}, message='{message}' ---")
                                    # --- FIN DEBUG ---
                                    if success: 
                                        cotizacion_id_final = cotizacion_id_a_actualizar
                                        # --- INICIO DEBUG ---
                                        print(f"--- DEBUG: Después de actualizar, cotizacion_id_final={cotizacion_id_final}")
                                        # --- FIN DEBUG ---
                            else:
                                # --- INICIO DEBUG: Antes de llamar guardar nueva ---
                                print(f"--- DEBUG: Llamando manager.guardar_nueva_cotizacion(...) ---")
                                # --- FIN DEBUG ---
                                admin_ajustes_activos = calc.get('admin_ajustes_activos', False)
                                success, message, cotizacion_id = manager.guardar_nueva_cotizacion(
                                    cotizacion_preparada, 
                                    cliente_id,
                                    referencia_desc,
                                    comercial_id_para_guardar,
                                    datos_calculo_persistir, 
                                    admin_ajustes_activos 
                                )
                                # --- INICIO DEBUG: Después de llamar guardar nueva ---
                                print(f"--- DEBUG: Resultado manager.guardar_nueva: success={success}, message='{message}', cotizacion_id={cotizacion_id} ---")
                                # --- FIN DEBUG ---
                                if success: 
                                    cotizacion_id_final = cotizacion_id
                                    # --- INICIO DEBUG ---
                                    print(f"--- DEBUG: Después de guardar nueva, cotizacion_id_final={cotizacion_id_final}")
                                    # --- FIN DEBUG ---

                            # --- SI EL GUARDADO/ACTUALIZACIÓN FUE EXITOSO (código para ambos casos) --- 
                            if success and cotizacion_id_final:
                                # --- INICIO DEBUG ---
                                print(f"--- DEBUG: Guardado/Actualización exitoso (ID: {cotizacion_id_final}). Generando informe y limpiando... ---")
                                # --- FIN DEBUG ---
                                st.success(message)
                                st.session_state.cotizacion_guardada = True
                                st.session_state.cotizacion_id = cotizacion_id_final
                                
                                # --- GENERAR INFORME TÉCNICO AQUÍ --- 
                                try:
                                    # --- INICIO DEBUG ---
                                    print(f"--- DEBUG: Intentando generar informe para Cotización ID: {cotizacion_id_final}")
                                    # --- FIN DEBUG ---
                                    # Obtener datos completos y frescos de la cotización recién guardada/actualizada
                                    datos_completos_cot = st.session_state.db.get_full_cotizacion_details(cotizacion_id_final)
                                    if datos_completos_cot:
                                        st.session_state.datos_completos_cot = datos_completos_cot
                                        # Generar el markdown usando la función importada
                                        informe_md = generar_informe_tecnico_markdown(
                                            cotizacion_data=datos_completos_cot,
                                            calculos_guardados=datos_calculo_persistir # Usar los datos que se guardaron
                                        )
                                        st.session_state.informe_tecnico_md = informe_md
                                        # --- INICIO DEBUG ---
                                        print("--- DEBUG: Informe técnico generado y guardado en session_state. ---")
                                        # --- FIN DEBUG ---
                                    else:
                                        st.warning("Cotización guardada, pero no se pudieron obtener datos completos para generar el informe técnico.")
                                        st.session_state.informe_tecnico_md = "Error al obtener datos completos para el informe."
                                        # --- INICIO DEBUG ---
                                        print("--- DEBUG: Error al obtener datos completos para informe. ---")
                                        # --- FIN DEBUG ---
                                except Exception as e_report:
                                    st.warning(f"Cotización guardada, pero ocurrió un error al generar el informe técnico: {e_report}")
                                    traceback.print_exc()
                                    st.session_state.informe_tecnico_md = f"Error generando informe: {e_report}"
                                    # --- INICIO DEBUG ---
                                    print(f"--- DEBUG: Excepción generando informe: {e_report} ---")
                                    # --- FIN DEBUG ---
                                
                                # --- Limpieza post-éxito ---
                                st.session_state.modo_edicion = False 
                                st.session_state.cotizacion_id_editar = None 
                                st.session_state.datos_cotizacion_editar = None 
                                st.session_state.cotizacion_model = None # Limpiar modelo
                                st.session_state.current_calculation = None
                                if 'recotizacion_info' in st.session_state:
                                    del st.session_state['recotizacion_info']
                                SessionManager.reset_calculator_widgets()
                                # --- INICIO DEBUG ---
                                print(f"--- DEBUG: Rerun después de éxito. ---")
                                # --- FIN DEBUG ---
                                st.rerun() # Rerun para mostrar estado guardado y informe
                            elif not success:
                                st.error(f"Error al guardar/actualizar: {message}")
                                # --- INICIO DEBUG ---
                                print(f"--- DEBUG: Error reportado por el manager: {message} ---")
                                # --- FIN DEBUG ---
                    except CotizacionManagerError as cme:
                        st.error(f"Error en guardado/actualización: {cme}")
                        # --- INICIO DEBUG ---
                        print(f"--- DEBUG: CotizacionManagerError: {cme} ---")
                        # --- FIN DEBUG ---
                    except Exception as e_save:
                        st.error(f"Error inesperado: {e_save}")
                        traceback.print_exc()
                        # --- INICIO DEBUG ---
                        print(f"--- DEBUG: Excepción inesperada en guardado: {e_save} ---")
                        # --- FIN DEBUG ---
                                
    # Botón Nueva Cotización 
    st.divider()
    if st.button("Nueva Cotización", key="new_quote_button_results"):
        # Resetear todo para una nueva cotización
        st.session_state.current_view = 'calculator'
        st.session_state.cotizacion_guardada = False
        st.session_state.referencia_guardar = ""
        st.session_state.cotizacion_model = None
        st.session_state.current_calculation = None
        st.session_state.modo_edicion = False
        st.session_state.cotizacion_id_editar = None 
        st.session_state.datos_cotizacion_editar = None 
        if 'recotizacion_info' in st.session_state:
            del st.session_state['recotizacion_info']
        if 'informe_tecnico_md' in st.session_state: # Limpiar informe anterior
            del st.session_state['informe_tecnico_md']
        SessionManager.reset_calculator_widgets()
        st.rerun()

# La implementación de show_manage_quotes se ha movido a src/ui/manage_quotes_view.py
# y se importa al inicio del archivo como: from src.ui.manage_quotes_view import show_manage_quotes

def show_reports():
    """Muestra la vista de reportes."""
    st.title("Reportes")
    st.write("Funcionalidad de reportes en desarrollo.")
    # Aquí se implementará la lógica para mostrar reportes

if __name__ == "__main__":
    main()

