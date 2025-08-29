import streamlit as st
import pandas as pd
import traceback
import time
from src.utils.session_manager import SessionManager

def show_manage_values():
    """Vista para administradores que permite modificar valores de materiales-adhesivos y acabados."""
    # Verificar que el usuario sea administrador
    if st.session_state.get('usuario_rol') != 'administrador':
        st.error("Solo los administradores pueden acceder a esta sección.")
        return
    
    st.title("🛠️ Administración de Valores")
    st.markdown("Esta sección permite modificar los valores (precios) de los materiales-adhesivos y acabados.")
    
    # Obtener el DB Manager
    db = st.session_state.db
    
    # Crear pestañas para separar materiales-adhesivos y acabados
    tab1, tab2 = st.tabs(["Materiales-Adhesivos", "Acabados"])
    
    # --- Pestaña de Materiales-Adhesivos ---
    with tab1:
        st.subheader("Valores de Materiales-Adhesivos")
        st.markdown("""
        Aquí puede visualizar y modificar los valores para cada combinación de material y adhesivo.
        Para modificar un valor, seleccione la combinación y establezca el nuevo precio.
        
        **💡 Nota:** Los valores se pueden ingresar como números enteros (ej: 1500) y automáticamente se formatearán con dos decimales (ej: 1500.00).
        """)
        
        # Cargar datos
        with st.spinner("Cargando datos de materiales-adhesivos..."):
            try:
                materiales_adhesivos = db.get_materiales_adhesivos_table()
                if not materiales_adhesivos:
                    st.warning("No se encontraron combinaciones de materiales-adhesivos.")
                    return
                
                # Crear DataFrame para mostrar los datos
                df_mat_adh = pd.DataFrame(materiales_adhesivos)
                df_mat_adh = df_mat_adh.rename(columns={
                    'id': 'ID',
                    'material_nombre': 'Material',
                    'adhesivo_tipo': 'Adhesivo',
                    'valor': 'Valor ($/m²)',
                    'code': 'Código'
                })
                
                # Mostrar DataFrame
                st.dataframe(
                    df_mat_adh[['ID', 'Material', 'Adhesivo', 'Valor ($/m²)', 'Código']],
                    hide_index=True,
                    use_container_width=True
                )
                
                # Selector para elegir combinación a modificar
                opciones_mat_adh = {row['ID']: f"{row['Material']} + {row['Adhesivo']} (${row['Valor ($/m²)']:.2f})" 
                                for _, row in df_mat_adh.iterrows()}
                
                st.markdown("### Modificar Valor")
                selected_mat_adh_id = st.selectbox(
                    "Seleccione combinación Material-Adhesivo:",
                    options=list(opciones_mat_adh.keys()),
                    format_func=lambda x: opciones_mat_adh[x],
                    key="select_mat_adh"
                )
                
                # Si se seleccionó una combinación
                if selected_mat_adh_id:
                    # Obtener el valor actual
                    valor_actual = float(df_mat_adh[df_mat_adh['ID'] == selected_mat_adh_id]['Valor ($/m²)'].values[0])
                    
                    # Input para nuevo valor
                    st.write("**Nuevo valor ($/m²):**")
                    nuevo_valor_input = st.text_input(
                        "Nuevo valor",
                        value=str(int(valor_actual)),
                        key="new_value_mat_adh_input",
                        help="Ingrese el nuevo valor en pesos por metro cuadrado"
                    )
                    
                    # Convertir y validar el valor ingresado
                    try:
                        if nuevo_valor_input:
                            nuevo_valor = float(nuevo_valor_input)
                            # Formatear el valor con 2 decimales si es entero
                            if nuevo_valor.is_integer():
                                nuevo_valor = round(nuevo_valor, 2)
                        else:
                            nuevo_valor = float(valor_actual)
                    except ValueError:
                        st.error("Por favor ingrese un valor numérico válido")
                        nuevo_valor = float(valor_actual)
                    
                    # Botón para actualizar
                    if st.button("Actualizar valor", key="update_mat_adh_btn"):
                        with st.spinner("Actualizando valor..."):
                            try:
                                success = db.actualizar_material_adhesivo_valor(selected_mat_adh_id, nuevo_valor)
                                if success:
                                    st.success(f"Valor actualizado correctamente a ${nuevo_valor:.2f}")
                                    time.sleep(1)  # Pequeña pausa para que el usuario vea el mensaje
                                    st.rerun()  # Recargar para mostrar los datos actualizados
                                else:
                                    st.error("No se pudo actualizar el valor. Intente nuevamente.")
                            except Exception as e:
                                st.error(f"Error al actualizar: {str(e)}")
                                traceback.print_exc()
            
            except Exception as e:
                st.error(f"Error cargando datos de materiales-adhesivos: {str(e)}")
                traceback.print_exc()
    
    # --- Pestaña de Acabados ---
    with tab2:
        st.subheader("Valores de Acabados")
        st.markdown("""
        Aquí puede visualizar y modificar los valores para cada tipo de acabado.
        Para modificar un valor, seleccione el acabado y establezca el nuevo precio.
        
        **💡 Nota:** Los valores se pueden ingresar como números enteros (ej: 1500) y automáticamente se formatearán con dos decimales (ej: 1500.00).
        """)
        
        # Cargar datos
        with st.spinner("Cargando datos de acabados..."):
            try:
                acabados = db.get_acabados()
                if not acabados:
                    st.warning("No se encontraron acabados registrados.")
                    return
                
                # Crear DataFrame para mostrar los datos
                df_acabados = pd.DataFrame([{
                    'ID': a.id,
                    'Nombre': a.nombre,
                    'Valor ($/m²)': float(a.valor),  # Asegurar que sea float
                    'Código': a.code
                } for a in acabados])
                
                # Mostrar DataFrame
                st.dataframe(
                    df_acabados,
                    hide_index=True,
                    use_container_width=True
                )
                
                # Selector para elegir acabado a modificar
                opciones_acabados = {a.id: f"{a.nombre} (${float(a.valor):.2f})" for a in acabados}  # Asegurar que valor sea float
                
                st.markdown("### Modificar Valor")
                selected_acabado_id = st.selectbox(
                    "Seleccione acabado:",
                    options=list(opciones_acabados.keys()),
                    format_func=lambda x: opciones_acabados[x],
                    key="select_acabado"
                )
                
                # Si se seleccionó un acabado
                if selected_acabado_id:
                    # Obtener el acabado seleccionado
                    acabado = next((a for a in acabados if a.id == selected_acabado_id), None)
                    if acabado:
                        # Input para nuevo valor
                        st.write("**Nuevo valor ($/m²):**")
                        nuevo_valor_input = st.text_input(
                            "Nuevo valor",
                            value=str(int(acabado.valor)),
                            key="new_value_acabado_input",
                            help="Ingrese el nuevo valor en pesos por metro cuadrado"
                        )
                        
                        # Convertir y validar el valor ingresado
                        try:
                            if nuevo_valor_input:
                                nuevo_valor = float(nuevo_valor_input)
                                # Formatear el valor con 2 decimales si es entero
                                if nuevo_valor.is_integer():
                                    nuevo_valor = round(nuevo_valor, 2)
                            else:
                                nuevo_valor = float(acabado.valor)
                        except ValueError:
                            st.error("Por favor ingrese un valor numérico válido")
                            nuevo_valor = float(acabado.valor)
                        
                        # Botón para actualizar
                        if st.button("Actualizar valor", key="update_acabado_btn"):
                            with st.spinner("Actualizando valor..."):
                                try:
                                    success = db.actualizar_acabado_valor(selected_acabado_id, nuevo_valor)
                                    if success:
                                        st.success(f"Valor de acabado actualizado correctamente a ${nuevo_valor:.2f}")
                                        time.sleep(1)  # Pequeña pausa para que el usuario vea el mensaje
                                        st.rerun()  # Recargar para mostrar los datos actualizados
                                    else:
                                        st.error("No se pudo actualizar el valor del acabado. Intente nuevamente.")
                                except Exception as e:
                                    st.error(f"Error al actualizar acabado: {str(e)}")
                                    traceback.print_exc()
                    else:
                        st.error("No se encontró el acabado seleccionado. Intente nuevamente.")
            
            except Exception as e:
                st.error(f"Error cargando datos de acabados: {str(e)}")
                traceback.print_exc() 