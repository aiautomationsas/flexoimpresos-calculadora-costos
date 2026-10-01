import streamlit as st
import traceback

from src.data.database import DBManager
from src.utils.session_manager import SessionManager

def show_manage_config_mangas():
    """Vista de administración de rentabilidad y costo de troquel para
    fundas/mangas termoencogibles. Solo administradores pueden editar."""

    if not SessionManager.verify_role(['administrador']):
        st.error("❌ Acceso denegado. Solo los administradores pueden editar esta configuración.")
        return

    st.subheader("Configuración Fundas/Mangas Termoencogibles")
    st.markdown(
        "Rentabilidad y costo de troquel base que se aplican por defecto a todas las "
        "cotizaciones de fundas/mangas termoencogibles."
    )

    if 'db' not in st.session_state:
        st.error("Error: La conexión a la base de datos no está inicializada.")
        return

    db: DBManager = st.session_state.db

    try:
        config = db.get_config_mangas()

        if config is None:
            st.error(
                "❌ No se encontró la configuración en la base de datos. "
                "Debe ejecutarse primero la migración que crea la tabla "
                "config_mangas_termoencogibles."
            )
            return

        with st.form("edit_config_mangas_form"):
            rentabilidad = st.number_input(
                "Rentabilidad (%)",
                min_value=0.1,
                max_value=99.9,
                value=float(config.rentabilidad),
                step=0.5,
                help="Porcentaje de rentabilidad aplicado por defecto a fundas/mangas termoencogibles."
            )

            costo_troquel_base = st.number_input(
                "Costo de troquel ($)",
                min_value=1.0,
                value=max(float(config.costo_troquel_base), 1.0),
                step=10000.0,
                help=(
                    "Valor fijo del troquel que se cobra en toda cotización de fundas/mangas, "
                    "sin importar el tamaño ni el tipo de grafado."
                )
            )

            submitted = st.form_submit_button("Guardar Cambios", type="primary")

            if submitted:
                success = db.actualizar_config_mangas(rentabilidad, costo_troquel_base)
                if success:
                    st.success("✅ Configuración actualizada exitosamente.")
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar la configuración.")

        if config.actualizado_en:
            st.caption(f"Última actualización: {config.actualizado_en.strftime('%d/%m/%Y %H:%M')}")

    except Exception as e:
        st.error(f"Error al cargar la configuración: {str(e)}")
        traceback.print_exc()
