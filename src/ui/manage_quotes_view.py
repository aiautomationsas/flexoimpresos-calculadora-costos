import streamlit as st
import pandas as pd
import time
import traceback
from datetime import datetime # Asegurar importación

# Importaciones del proyecto
from src.data.database import DBManager
from src.utils.session_manager import SessionManager # Para resetear widgets al editar
from src.pdf.pdf_generator import generar_bytes_pdf_cotizacion # Para el botón PDF
from src.logic.report_generator import generar_informe_tecnico_markdown, markdown_a_pdf # Para el informe técnico

def show_manage_quotes_ui():
    """Muestra la vista para gestionar (ver y modificar) cotizaciones."""
    st.title("Gestión de Cotizaciones")
    
    # Limpiar estado de edición al entrar a esta vista (evita el error "Editar Cotización #None")
    if not st.session_state.get('mostrar_editor_inline', False):
        if 'modo_edicion' in st.session_state and st.session_state.get('current_view') == 'manage_quotes':
            st.session_state['modo_edicion'] = False
            st.session_state['cotizacion_id_editar'] = None
            st.session_state['datos_cotizacion_editar'] = None
            if 'recotizacion_info' in st.session_state:
                del st.session_state['recotizacion_info']
    
    # SOLUCIÓN STREAMLIT CLOUD: Tabs para edición inline
    # Verificar si hay una cotización seleccionada para editar
    if st.session_state.get('mostrar_editor_inline', False):
        _mostrar_editor_inline()
        return
    
    # Mensaje informativo
    st.info("💡 Seleccione una cotización de la tabla para ver sus acciones")

    if 'db' not in st.session_state:
        st.error("Error: La conexión a la base de datos no está inicializada.")
        return
    if 'user_id' not in st.session_state or 'usuario_rol' not in st.session_state:
         st.error("Error: Información de usuario no encontrada en la sesión.")
         return
    # Cargar initial_data si no está presente (puede ser redundante si app.py ya lo hace)
    if 'initial_data' not in st.session_state or not st.session_state.get('initial_data'):
         st.warning("Datos iniciales (estados, motivos) no encontrados. Funcionalidad limitada.")

    db_manager: DBManager = st.session_state.db
    user_role = st.session_state.usuario_rol
    user_id = st.session_state.user_id

    # --- Obtener Cotizaciones ---
    cotizaciones = []
    try:
        # --- EJECUCIÓN NORMAL DEL CÓDIGO ---
        if user_role == 'administrador':
            try:
                # Primero intentamos con la nueva función específica para el dashboard
                cotizaciones = db_manager.supabase.rpc('get_visible_cotizaciones_for_dashboard').execute().data
                print("DEBUG: Cotizaciones obtenidas usando get_visible_cotizaciones_for_dashboard")
            except Exception as e_new_func:
                print(f"DEBUG: Error con get_visible_cotizaciones_for_dashboard: {e_new_func}")
                # Si falla, intentamos con la función original
                cotizaciones = db_manager.get_all_cotizaciones_overview()
                print("DEBUG: Cotizaciones obtenidas usando get_all_cotizaciones_overview (fallback admin)")

        elif user_role == 'comercial':
            try:
                # Primero intentamos con la nueva función específica para el dashboard
                cotizaciones = db_manager.supabase.rpc('get_visible_cotizaciones_for_dashboard').execute().data
                print("DEBUG: Cotizaciones obtenidas usando get_visible_cotizaciones_for_dashboard (comercial)")
            except Exception as e_new_func_com:
                print(f"DEBUG: Error con get_visible_cotizaciones_for_dashboard (comercial): {e_new_func_com}")
                # Intentar obtener todas las cotizaciones y filtrar por comercial_id
                all_cotizaciones = db_manager.get_all_cotizaciones_overview()
                print(f"DEBUG: Filtrando cotizaciones para comercial ID {user_id}")
                cotizaciones = [c for c in all_cotizaciones if str(c.get('id_usuario')) == str(user_id) or str(c.get('comercial_id')) == str(user_id)]
                print("DEBUG: Cotizaciones obtenidas usando get_all_cotizaciones_overview (fallback comercial)")
        else:
            st.error("No tiene permisos para ver cotizaciones.")
            return

        # Verificar si las cotizaciones están vacías o son None
        if not cotizaciones:
            print("DEBUG: No se encontraron cotizaciones")
            st.info("No hay cotizaciones disponibles.")
            return
                
    except Exception as e_cotiz:
        st.error(f"Error obteniendo cotizaciones: {e_cotiz}")
        print(f"DEBUG: Error detallado al obtener cotizaciones: {e_cotiz}")
        print(traceback.format_exc())
        return

    # --- Mostrar Tabla de Cotizaciones ---
    st.subheader("Cotizaciones Guardadas")

    # Crear DataFrame desde la lista de diccionarios/objetos
    df_cotizaciones = pd.DataFrame(cotizaciones)

    # Verificar columnas esenciales para la tabla
    required_table_cols = ['id', 'numero_cotizacion', 'referencia', 'cliente_nombre', 'fecha_creacion', 'estado_id']
    missing_table_cols = [col for col in required_table_cols if col not in df_cotizaciones.columns]
    if missing_table_cols:
        st.error(f"Faltan columnas para mostrar la tabla: {', '.join(missing_table_cols)}. Verifique los métodos overview.")
        return

    # --- OBTENER MAPEO DE ESTADOS DENTRO DE LA FUNCIÓN ---
    current_estados_map = {}
    if 'initial_data' in st.session_state and st.session_state.initial_data and 'estados_cotizacion' in st.session_state.initial_data:
        try:
            # Asegurarse que estados_cotizacion es una lista de objetos/dicts con .id y .estado
            estados_list = st.session_state.initial_data['estados_cotizacion']
            if isinstance(estados_list, list):
                current_estados_map = {item.id: item.estado for item in estados_list if hasattr(item, 'id') and hasattr(item, 'estado')}
            else:
                st.warning("Formato inesperado para 'estados_cotizacion' en initial_data.")
        except Exception as e:
            st.warning(f"Error al procesar estados desde initial_data: {e}")
    
    # Usar fallback si el mapeo no se pudo crear o está vacío
    if not current_estados_map:
        st.warning("No se pudo obtener el mapeo de estados desde initial_data. Usando mapeo local de emergencia.")
        current_estados_map = {
             1: "En negociación", 2: "Aprobada", 3: "Rechazada"
        }
    # -----------------------------------------------------

    # Mapear estado_id a nombre de estado usando el mapa obtenido
    df_cotizaciones['Estado Nombre'] = df_cotizaciones['estado_id'].map(current_estados_map).fillna('Desconocido')

    # Definir columnas a mostrar y renombrar
    columnas_db = {
        'numero_cotizacion': 'Número',
        'referencia': 'Referencia',
        'cliente_nombre': 'Cliente',
        'fecha_creacion': 'Fecha Creación',
        'Estado Nombre': 'Estado'
        # Añadir 'comercial_nombre' si está disponible y se quiere mostrar
        # 'comercial_nombre': 'Comercial' # Si se renombró en _load_dashboard_data
    }

    # Filtrar y renombrar columnas existentes
    columnas_existentes_db = {k: v for k, v in columnas_db.items() if k in df_cotizaciones.columns or k == 'Estado Nombre'}
    df_display = df_cotizaciones[list(columnas_existentes_db.keys())].rename(columns=columnas_existentes_db)

    # Formatear fecha
    if 'Fecha Creación' in df_display.columns:
         df_display['Fecha Creación'] = pd.to_datetime(df_display['Fecha Creación']).dt.strftime('%Y-%m-%d %H:%M')

    st.dataframe(df_display, hide_index=True, use_container_width=True)
    st.divider()

    # --- Sección para Descargar PDF ---
    st.subheader("Descargar PDF de Cotización")

    # Crear opciones para selectbox (ID -> Texto formateado)
    # Usar nombres de columnas originales del df_cotizaciones
    opciones_cotizacion_pdf = {}
    num_col_pdf = 'numero_cotizacion'
    client_col_pdf = 'cliente_nombre'
    id_col_pdf = 'id'

    if all(col in df_cotizaciones.columns for col in [id_col_pdf, num_col_pdf, client_col_pdf]):
        opciones_cotizacion_pdf = {
            row[id_col_pdf]: f"CT{row[num_col_pdf]:0>8} - {row[client_col_pdf]}"
            for index, row in df_cotizaciones.iterrows()
        }
    else:
         st.error("Faltan columnas (ID, Número, Cliente) para generar opciones de descarga PDF.")

    if opciones_cotizacion_pdf:
        selected_quote_id_pdf = st.selectbox(
            "Seleccione la cotización para descargar su PDF:",
            options=[None] + list(opciones_cotizacion_pdf.keys()), # Añadir opción None
            format_func=lambda x: "Elija una cotización..." if x is None else opciones_cotizacion_pdf[x],
            key="selectbox_descargar_pdf_manage"
        )

        if selected_quote_id_pdf is not None:
            numero_cotizacion_seleccionada_pdf = opciones_cotizacion_pdf[selected_quote_id_pdf].split(' - ')[0] # Extraer número para nombre archivo

            # Usar una key única para el botón basada en el ID para evitar conflictos entre reruns
            button_key_pdf = f"generate_pdf_button_{selected_quote_id_pdf}"
            download_key_pdf = f"download_pdf_final_{selected_quote_id_pdf}"
            session_bytes_key = f'pdf_bytes_{selected_quote_id_pdf}'
            session_filename_key = f'pdf_filename_{selected_quote_id_pdf}'

            if st.button("📄 Generar PDF para Descargar", key=button_key_pdf):
                with st.spinner("⏳ Generando PDF, por favor espere..."):
                    try:
                        # Usar el método específico para obtener datos completos para el PDF
                        datos_pdf = db_manager.get_datos_completos_cotizacion(selected_quote_id_pdf)
                        if datos_pdf:
                            pdf_bytes = generar_bytes_pdf_cotizacion(datos_pdf) # Usar helper importado
                            if pdf_bytes:
                                st.session_state[session_bytes_key] = pdf_bytes
                                st.session_state[session_filename_key] = f"{datos_pdf.get('identificador') or 'Cotizacion ' + str(datos_pdf.get('consecutivo', 'N'))}.pdf"
                                st.success("✅ PDF generado exitosamente. Use el botón de abajo para descargar.")
                                # No usar st.rerun() aquí para que el botón de descarga aparezca
                            else:
                                st.error("❌ No se pudo generar el PDF (función devolvió None).")
                        else:
                            st.error("❌ No se encontraron los datos completos de la cotización para el PDF.")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error inesperado generando el PDF: {e}")
                        print(f"Error generando PDF para ID {selected_quote_id_pdf}: {e}")
                        traceback.print_exc()

            # Mostrar botón de descarga si los bytes están en sesión
            if session_bytes_key in st.session_state and session_filename_key in st.session_state:
                st.download_button(
                    label="⬇️ Descargar PDF Generado",
                    data=st.session_state[session_bytes_key],
                    file_name=st.session_state[session_filename_key],
                    mime="application/pdf",
                    key=download_key_pdf,
                    type="primary",
                    on_click=lambda: SessionManager.clear_pdf_data(selected_quote_id_pdf) # Limpiar datos después de click (opcional)
                )
    else:
         st.info("No hay cotizaciones disponibles para seleccionar.")

    st.divider()

    # --- Sección para Descargar Informe Técnico ---
    st.subheader("Descargar Informe Técnico")

    # Usar las mismas opciones que para el PDF
    if opciones_cotizacion_pdf:
        selected_quote_id_informe = st.selectbox(
            "Seleccione la cotización para descargar su informe técnico:",
            options=[None] + list(opciones_cotizacion_pdf.keys()), # Añadir opción None
            format_func=lambda x: "Elija una cotización..." if x is None else opciones_cotizacion_pdf[x],
            key="selectbox_descargar_informe_manage"
        )

        if selected_quote_id_informe is not None:
            # Usar una key única para el botón basada en el ID para evitar conflictos
            button_key_informe = f"generate_informe_button_{selected_quote_id_informe}"

            if st.button("📋 Generar Informe Técnico", key=button_key_informe):
                with st.spinner("⏳ Generando informe técnico, por favor espere..."):
                    try:
                        # Obtener datos completos de la cotización
                        datos_completos_cot = db_manager.get_full_cotizacion_details(selected_quote_id_informe)
                        # También necesitamos los cálculos guardados
                        try:
                            # Obtener los cálculos directamente sin depender del método get_calculos_persistidos
                            calculos_raw = db_manager.get_calculos_escala_cotizacion(selected_quote_id_informe)
                            
                            if calculos_raw:
                                # Formatear datos manualmente para el informe técnico
                                datos_calculo = {
                                    'valor_material': calculos_raw.get('valor_material', 0.0),
                                    'valor_acabado': calculos_raw.get('valor_acabado', 0.0),
                                    'valor_troquel': calculos_raw.get('valor_troquel', 0.0),
                                    'valor_plancha': calculos_raw.get('valor_plancha', 0.0),
                                    'valor_plancha_separado': calculos_raw.get('valor_plancha_separado'),
                                    'unidad_z_dientes': calculos_raw.get('unidad_z_dientes', 0),
                                    'existe_troquel': calculos_raw.get('existe_troquel', False),
                                    'planchas_x_separado': calculos_raw.get('planchas_x_separado', False),
                                    'rentabilidad': calculos_raw.get('rentabilidad', 0.0),
                                    'avance': calculos_raw.get('avance', 0.0),
                                    'ancho': calculos_raw.get('ancho', 0.0),
                                    'num_tintas': calculos_raw.get('num_tintas', 0),
                                    'numero_pistas': calculos_raw.get('numero_pistas', 1),
                                    'num_paquetes_rollos': calculos_raw.get('num_paquetes_rollos', 0),
                                    # Pasar desperdicio en mm y repeticiones si están persistidos
                                    'desperdicio_mm': calculos_raw.get('desperdicio_mm'),
                                    'repeticiones': calculos_raw.get('repeticiones')
                                }
                            else:
                                datos_calculo = None
                                st.error("❌ No se encontraron datos de cálculos para generar el informe.")
                        except Exception as e_calc:
                            st.error(f"❌ Error al obtener datos de cálculos: {e_calc}")
                            print(f"Error obteniendo cálculos: {e_calc}")
                            traceback.print_exc()
                            datos_calculo = None
                        
                        if datos_completos_cot and datos_calculo:
                            # Generar el informe técnico
                            informe_md = generar_informe_tecnico_markdown(
                                cotizacion_data=datos_completos_cot,
                                calculos_guardados=datos_calculo
                            )
                            
                            # Generar nombre de archivo
                            numero_cotizacion = datos_completos_cot.get('numero_cotizacion', 'informe')
                            cliente_nombre = datos_completos_cot.get('cliente_nombre', '').replace(' ', '_')
                            nombre_archivo = f"Informe_Tecnico_{numero_cotizacion}_{cliente_nombre}"
                            
                            # Generar enlace de descarga
                            pdf_download_link = markdown_a_pdf(informe_md, nombre_archivo)
                            if pdf_download_link:
                                st.markdown(pdf_download_link, unsafe_allow_html=True)
                                st.success("✅ Informe técnico generado exitosamente. Use el enlace para descargar.")
                            else:
                                st.error("❌ No se pudo generar el PDF del informe técnico.")
                        else:
                            st.error("❌ No se encontraron los datos completos o cálculos de la cotización para generar el informe.")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error inesperado generando el informe técnico: {e}")
                        print(f"Error generando informe técnico para ID {selected_quote_id_informe}: {e}")
                        traceback.print_exc()
    else:
         st.info("No hay cotizaciones disponibles para seleccionar.")

    st.divider()

    # --- Sección de Acciones (Editar / Cambiar Estado) ---
    st.subheader("Editar / Cambiar Estado de Cotización")

    # Crear opciones para selectbox de acciones (ID -> Texto formateado)
    opciones_accion = {}
    num_col_acc = 'numero_cotizacion'
    client_col_acc = 'cliente_nombre'
    ref_col_acc = 'referencia' # Nombre de la columna de referencia/descripción
    id_col_acc = 'id'

    if all(col in df_cotizaciones.columns for col in [id_col_acc, num_col_acc, client_col_acc, ref_col_acc]):
        opciones_accion = {
            row[id_col_acc]: f"#{row[num_col_acc]} - {row[client_col_acc]} - {row[ref_col_acc]}"
             for index, row in df_cotizaciones.iterrows()
        }
    else:
         st.error("Faltan columnas (ID, Número, Cliente, Referencia) para generar opciones de acción.")

    if opciones_accion:
        selected_cotizacion_id_accion = st.selectbox(
            "Seleccione Cotización para Editar / Cambiar Estado:",
            options=[None] + list(opciones_accion.keys()), # Añadir opción None
            format_func=lambda x: "-- Elija una cotización --" if x is None else opciones_accion[x],
            key="selectbox_accion_cotizacion_manage"
        )

        # --- Mostrar acciones si se selecciona una cotización ---
        if selected_cotizacion_id_accion is not None:
            try:
                # Obtener datos de la cotización seleccionada del DataFrame
                selected_quote_data = df_cotizaciones.loc[df_cotizaciones[id_col_acc] == selected_cotizacion_id_accion].iloc[0]

                # --- INICIO: DIAGNÓSTICO DETALLADO DE AJUSTES_MODIFICADOS_ADMIN ---
                # Obtener el valor directamente de la base de datos para confirmar
                ajustes_admin_flag_df = selected_quote_data.get('ajustes_modificados_admin', False)
                
                ajustes_admin_flag_db = False
                try:
                    # Consulta directa a la base de datos para verificar el valor real
                    response_flag = db_manager.supabase.from_('cotizaciones').select('ajustes_modificados_admin').eq('id', selected_cotizacion_id_accion).execute()
                    if response_flag and response_flag.data and len(response_flag.data) > 0:
                        ajustes_admin_flag_db = response_flag.data[0].get('ajustes_modificados_admin', False)
                        print(f"DEBUG: Valor de ajustes_modificados_admin directo de DB para cotización {selected_cotizacion_id_accion}: {ajustes_admin_flag_db}")
                        
                        # Si hay discrepancia entre el valor del DataFrame y el de la BD
                        if ajustes_admin_flag_df != ajustes_admin_flag_db:
                            print(f"ADVERTENCIA: Discrepancia en ajustes_modificados_admin entre DataFrame ({ajustes_admin_flag_df}) y BD ({ajustes_admin_flag_db})")
                            # Usar el valor de la BD como fuente principal de verdad
                            ajustes_admin_flag = ajustes_admin_flag_db
                        else:
                            ajustes_admin_flag = ajustes_admin_flag_df
                    else:
                        print(f"Error: No se pudo obtener ajustes_modificados_admin de la BD para cotización {selected_cotizacion_id_accion}")
                        ajustes_admin_flag = ajustes_admin_flag_df  # Usar el valor del DataFrame como respaldo
                except Exception as e_flag:
                    print(f"Error consultando flag directamente: {e_flag}")
                    ajustes_admin_flag = ajustes_admin_flag_df  # Usar el valor del DataFrame como respaldo
                
                print(f"DEBUG: Valor FINAL de ajustes_modificados_admin para cotización {selected_cotizacion_id_accion}: {ajustes_admin_flag}")
                # --- FIN: DIAGNÓSTICO DETALLADO DE AJUSTES_MODIFICADOS_ADMIN ---

                estado_actual_id = selected_quote_data['estado_id']
                ID_ESTADO_APROBADO = 2 # Asumiendo ID 2 = Aprobado

                disable_edit_button = False
                disable_edit_reason = ""
                disable_status_change = False
                disable_status_reason = ""

                if user_role == 'comercial':
                    # Verificar si hay restricción por ajustes_modificados_admin
                    if ajustes_admin_flag:
                        disable_edit_button = True
                        disable_edit_reason = "🔒 Edición deshabilitada: Ajustes modificados por administrador."
                    
                    # Verificar INDEPENDIENTEMENTE si hay restricción por estado Aprobado
                    if estado_actual_id == ID_ESTADO_APROBADO:
                        disable_edit_button = True
                        disable_edit_reason = "🔒 Edición deshabilitada: Cotización ya aprobada."
                        disable_status_change = True # También deshabilitar cambio de estado
                        disable_status_reason = "🔒 Estado Aprobado no modificable por comercial."

                cols_accion_display = st.columns(2)

                # --- SOLUCIÓN FINAL: Expandir directamente inline ---
                with cols_accion_display[0]:
                    st.write("**Editar Cotización:**")
                    
                    label_text = f"Editar #{selected_quote_data[num_col_acc]}"
                    if user_role == 'administrador' and estado_actual_id == ID_ESTADO_APROBADO:
                         label_text = f"Recotizar #{selected_quote_data[num_col_acc]}"
                    
                    # SOLUCIÓN INLINE: Activar modo editor
                    if not disable_edit_button:
                        if st.button(
                            f"✏️ {label_text}",
                            key=f"edit_inline_{selected_cotizacion_id_accion}",
                            use_container_width=True,
                            type="primary"
                        ):
                            # Activar editor inline
                            st.session_state['mostrar_editor_inline'] = True
                            st.session_state['cotizacion_id_editar'] = selected_cotizacion_id_accion
                            st.session_state['es_recotizacion'] = (user_role == 'administrador' and estado_actual_id == ID_ESTADO_APROBADO)
                            st.rerun()
                    else:
                        st.button(
                            f"✏️ {label_text}",
                            key=f"edit_disabled_{selected_cotizacion_id_accion}",
                            use_container_width=True,
                            disabled=True
                        )
                        if user_role == 'comercial':
                            if ajustes_admin_flag:
                                st.caption("🔒 Modificada por administrador")
                            elif estado_actual_id == ID_ESTADO_APROBADO:
                                st.caption("🔒 Ya aprobada")
                    
                    if False:  # Código viejo deshabilitado
                        edit_submitted = False
                    
                    if False:  # edit_submitted (deshabilitado)
                        print(f"DEBUG: Edit/Recotizar button clicked for Cotizacion ID: {selected_cotizacion_id_accion}")
                        
                        # --- INICIO: Verificación adicional antes de permitir editar ---
                        if user_role == 'comercial':
                            # Verificar nuevamente las restricciones como doble capa de seguridad
                            if ajustes_admin_flag:
                                st.error("🚫 No se puede editar esta cotización porque ha sido modificada por un administrador.")
                                print(f"BLOQUEO: Intento de edición bloqueado para comercial en cotización con ajustes_modificados_admin=True")
                                time.sleep(2)
                                st.rerun()
                                return
                            
                            if estado_actual_id == ID_ESTADO_APROBADO:
                                st.error("🚫 No se puede editar esta cotización porque ya está aprobada.")
                                print(f"BLOQUEO: Intento de edición bloqueado para comercial en cotización aprobada (ID: {estado_actual_id})")
                                time.sleep(2)
                                st.rerun()
                                return
                        # --- FIN: Verificación adicional ---

                        # Marcar si es recotización (Admin editando Aprobada)
                        if user_role == 'administrador' and estado_actual_id == ID_ESTADO_APROBADO:
                            st.session_state.recotizacion_info = {'id': selected_cotizacion_id_accion}
                            print(f"DEBUG: Marcando inicio de recotización para ID {selected_cotizacion_id_accion}")
                        else:
                            if 'recotizacion_info' in st.session_state:
                                del st.session_state['recotizacion_info']

                        # Configurar modo edición
                        st.session_state.modo_edicion = True
                        st.session_state.cotizacion_id_editar = selected_cotizacion_id_accion
                        st.session_state.datos_cotizacion_editar = None
                        
                        # SOLUCIÓN: Usar trigger en lugar de cambiar directamente
                        st.session_state.trigger_editar_cotizacion = True
                        
                        # DEBUG
                        print(f"DEBUG EDIT: Configurando edición para cotización ID {selected_cotizacion_id_accion}")
                        print(f"DEBUG EDIT: modo_edicion = {st.session_state.modo_edicion}")
                        print(f"DEBUG EDIT: trigger_editar_cotizacion = True")
                        
                        # Limpiar widgets
                        try:
                            SessionManager.reset_calculator_widgets()
                        except Exception as e:
                            print(f"Error reseteando widgets: {e}")
                        
                        # SOLUCIÓN RADICAL: Usar query params para forzar navegación
                        # Esto funciona en Streamlit Cloud cuando st.rerun() falla
                        st.success(f"⏳ Cargando cotización #{selected_cotizacion_id_accion} para edición...")
                        
                        # Método 1: Forzar con query params
                        try:
                            st.query_params.update({"edit": str(selected_cotizacion_id_accion)})
                        except:
                            try:
                                st.experimental_set_query_params(edit=str(selected_cotizacion_id_accion))
                            except:
                                pass
                        
                        time.sleep(0.5)
                        st.rerun()

                    if disable_edit_button:
                        # Mejorar la visibilidad del mensaje cuando está deshabilitado
                        if ajustes_admin_flag and user_role == 'comercial':
                            st.warning(disable_edit_reason)
                        else:
                            st.caption(disable_edit_reason)

                # --- Cambiar Estado ---
                with cols_accion_display[1]:
                    st.write("**Cambiar Estado:**")

                    # Obtener listas de estados y motivos desde la DB (o usar datos cacheados si existen)
                    estados_db = []
                    motivos_db = []
                    try:
                         # Intentar obtener de initial_data si está disponible y completo
                         if 'initial_data' in st.session_state and st.session_state.initial_data:
                             estados_db = st.session_state.initial_data.get('estados_cotizacion', [])
                             # Asumiendo que motivos también se carga en initial_data o se puede obtener
                             if 'motivos_rechazo' in st.session_state.initial_data:
                                  motivos_db = st.session_state.initial_data['motivos_rechazo']
                             elif hasattr(db_manager, 'get_motivos_rechazo'): # Fallback a DB si no está en initial_data
                                  motivos_db = db_manager.get_motivos_rechazo()

                         # Si initial_data no está o falta algo, obtener de DB
                         if not estados_db and hasattr(db_manager, 'get_estados_cotizacion'):
                              estados_db = db_manager.get_estados_cotizacion()
                         if not motivos_db and hasattr(db_manager, 'get_motivos_rechazo'):
                              motivos_db = db_manager.get_motivos_rechazo()

                    except Exception as e_load_sm:
                         st.warning(f"Error cargando estados/motivos: {e_load_sm}")

                    opciones_estado = [(e.id, e.estado) for e in estados_db] if estados_db else []
                    opciones_motivo = [(None, "-- Seleccione Motivo --")] + [(m.id, m.motivo) for m in motivos_db] if motivos_db else [(None, "-- No hay motivos --")]

                    # Encontrar índice actual solo si hay opciones
                    current_status_index = 0
                    if opciones_estado:
                        try:
                            current_status_index = next(i for i, (id, _) in enumerate(opciones_estado) if id == estado_actual_id)
                        except StopIteration:
                            st.warning(f"Estado actual ID {estado_actual_id} no encontrado en opciones.")
                            current_status_index = 0 # Default seguro

                    nuevo_estado_tupla = st.selectbox("Nuevo Estado",
                        options=opciones_estado, format_func=lambda x: x[1],
                        index=current_status_index, key=f"estado_select_manage_{selected_cotizacion_id_accion}",
                        disabled=disable_status_change or not opciones_estado, label_visibility="collapsed")

                    nuevo_estado_id = nuevo_estado_tupla[0] if nuevo_estado_tupla else None

                    motivo_rechazo_id = None
                    ID_ESTADO_RECHAZADO = 3 # Asumiendo ID 3 = Rechazado
                    show_motivo_selector = (nuevo_estado_id == ID_ESTADO_RECHAZADO)
                    disable_motivo_selector = disable_status_change or not show_motivo_selector or len(opciones_motivo) <= 1

                    if show_motivo_selector:
                        motivo_rechazo_tupla = st.selectbox("Motivo Rechazo *",
                            options=opciones_motivo, format_func=lambda x: x[1],
                            key=f"motivo_select_manage_{selected_cotizacion_id_accion}",
                            disabled=disable_motivo_selector, label_visibility="collapsed")
                        if not disable_motivo_selector and motivo_rechazo_tupla:
                            motivo_rechazo_id = motivo_rechazo_tupla[0]

                    update_button_key = f"update_status_button_{selected_cotizacion_id_accion}"
                    if st.button("🔄 Actualizar Estado", key=update_button_key, use_container_width=True, disabled=disable_status_change):
                        error_actualizacion = False
                        if nuevo_estado_id == ID_ESTADO_RECHAZADO and motivo_rechazo_id is None:
                            st.error("Debe seleccionar un motivo de rechazo.")
                            error_actualizacion = True

                        if not error_actualizacion and nuevo_estado_id is not None:
                            with st.spinner("Actualizando estado..."):
                                success = db_manager.actualizar_estado_cotizacion(
                                    selected_cotizacion_id_accion, nuevo_estado_id, motivo_rechazo_id)
                                if success:
                                    # Usar mensajes de SessionManager si está disponible
                                    msg = f"✅ Estado de cotización #{selected_quote_data[num_col_acc]} actualizado."
                                    if hasattr(SessionManager, 'add_message'):
                                        SessionManager.add_message('success', msg)
                                    else:
                                        st.success(msg) # Fallback
                                    time.sleep(0.5) # Pausa breve
                                    st.rerun()
                                else:
                                    st.error("❌ No se pudo actualizar el estado.")
                        elif not error_actualizacion:
                            st.warning("No se seleccionó un nuevo estado válido.")


                    if disable_status_change:
                        st.caption(disable_status_reason)

            except KeyError as ke:
                 st.error(f"Error interno: Falta la columna '{ke}' en los datos de la cotización seleccionada. Verifica los métodos overview.")
                 print(f"KeyError en sección acciones manage_quotes: {ke}")
            except Exception as e_acc:
                 st.error(f"Error inesperado en la sección de acciones: {e_acc}")
                 traceback.print_exc()
    else:
        st.info("No hay cotizaciones disponibles para seleccionar acciones.")

# Limpia los datos del PDF generado de la sesión (helper opcional)
def clear_pdf_data(quote_id):
    bytes_key = f'pdf_bytes_{quote_id}'
    filename_key = f'pdf_filename_{quote_id}'
    if bytes_key in st.session_state:
        del st.session_state[bytes_key]
    if filename_key in st.session_state:
        del st.session_state[filename_key]
        print(f"Limpiando datos PDF para quote_id {quote_id}") # Debug

def _mostrar_editor_inline():
    """Muestra el editor de cotización inline"""
    cotizacion_id = st.session_state.get('cotizacion_id_editar')
    es_recotizacion = st.session_state.get('es_recotizacion', False)
    
    # Obtener el número de cotización para mostrar al usuario
    numero_cotizacion = "N/A"
    cliente_nombre = "N/A"
    referencia = "N/A"
    
    if cotizacion_id:
        try:
            db_manager = st.session_state.get('db')
            if db_manager:
                # Usar el mismo RPC que se usa en la lista principal para obtener datos completos
                response = db_manager.supabase.rpc('get_visible_cotizaciones_for_dashboard').execute()
                
                if response and response.data:
                    # Buscar la cotización específica por ID
                    cotizacion_data = next((c for c in response.data if c.get('id') == cotizacion_id), None)
                    
                    if cotizacion_data:
                        numero_cotizacion = cotizacion_data.get('numero_cotizacion', 'N/A')
                        cliente_nombre = cotizacion_data.get('cliente_nombre', 'N/A')
                        referencia = cotizacion_data.get('referencia', 'N/A')
                        print(f"🔍 DEBUG: Cotización obtenida - #{numero_cotizacion}, Cliente: {cliente_nombre}")
                    else:
                        print(f"🔍 DEBUG: No se encontró la cotización ID {cotizacion_id} en los datos del RPC")
                else:
                    print(f"🔍 DEBUG: No se obtuvieron datos del RPC")
        except Exception as e:
            print(f"Error obteniendo información de cotización: {e}")
            import traceback
            traceback.print_exc()
    
    # Configurar modo edición en session_state PRIMERO
    st.session_state['modo_edicion'] = True
    st.session_state['datos_cotizacion_editar'] = None
    
    if es_recotizacion:
        st.session_state['recotizacion_info'] = {'id': cotizacion_id}
    
    try:
        SessionManager.reset_calculator_widgets()
    except:
        pass
    
    # UI
    st.title(f"{'🔁 Recotizar' if es_recotizacion else '✏️ Editar'} Cotización #{numero_cotizacion}")
    
    # Botón para cancelar
    if st.button("❌ Cancelar Edición"):
        st.session_state['mostrar_editor_inline'] = False
        st.session_state['cotizacion_id_editar'] = None
        st.session_state['modo_edicion'] = False
        st.rerun()
    
    st.divider()
    
    # Mensaje principal
    st.success("✅ Modo de Edición Activado")
    st.write("### La cotización está lista para editar")
    
    # Caja destacada con instrucción
    st.info("""
    ### 👉 Siguiente paso:
    
    **Haz click en "🧮 Cotizador" en el menú lateral izquierdo**
    
    La cotización se cargará automáticamente en la calculadora lista para editar.
    """)
    
    # Información adicional
    st.write("---")
    st.write("**Información de la cotización:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Número", f"#{numero_cotizacion}")
    with col2:
        st.metric("Cliente", cliente_nombre)
    with col3:
        st.metric("Modo", "🔁 Recotización" if es_recotizacion else "✏️ Edición")
    
    if referencia != "N/A":
        st.caption(f"**Referencia:** {referencia}")

# Definir la función original para mantener compatibilidad
def show_manage_quotes():
    """Función de compatibilidad que llama a la versión mejorada"""
    show_manage_quotes_ui()

