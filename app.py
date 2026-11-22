import streamlit as st
import pandas as pd

from app_functions import (
    TEXT_OPERATORS,
    NUMBER_OPERATORS,
    apply_single_filter,
    show_cool_loading_screen, 
    login
)


@st.cache_data
def load_data():
    
    return pd.read_excel(
        r"listado_streamlit.xlsx"
    )


TEXT_FIELDS = ["Nombre", "Dirección", "Descripción", "Tipo combustible"]
NUMBER_FIELDS = ["Precio", "Precio final", "Kilómetros", "Año", "CV"]


def initialize_dataframe():
    """Carga una copia original y otra que se irá filtrando acumulativamente."""
    if "df_original" not in st.session_state:
        original = load_data()
        st.session_state.df_original = original.copy()
        st.session_state.df_actual = original.copy()
        st.session_state.historial_filtros = []


@st.dialog("Autofiltro personalizado")
def filter_dialog(column: str, kind: str):
    st.write(f"Configura un nuevo filtro para **{column}**")
    st.caption(
        "Este filtro se aplicará sobre el resultado actual, no sobre el Excel original."
    )

    operators = NUMBER_OPERATORS if kind == "number" else TEXT_OPERATORS

    with st.form(f"filter_form_{column}"):
        operator = st.selectbox("Condición", operators, key=f"op_{column}")

        if kind == "number":
            step = 1.0 if column in ["Kilómetros", "Año", "CV"] else 0.01
            value = st.number_input(
                "Valor",
                value=0.0,
                step=step,
                key=f"value_num_{column}",
            )
        else:
            value = st.text_input("Valor", key=f"value_text_{column}")

        submitted = st.form_submit_button(
            "Aplicar filtro",
            type="primary",
            use_container_width=True,
        )

    col_clear, col_cancel = st.columns(2)
    with col_clear:
        clear = st.button("Restablecer dataframe", use_container_width=True)
    with col_cancel:
        cancel = st.button("Cancelar", use_container_width=True)

    if submitted:
        if kind == "text" and not value.strip():
            st.warning("Introduce un valor para aplicar el filtro.")
        else:
            condition = {
                "kind": kind,
                "operator": operator,
                "value": value,
            }
            # CLAVE: el filtro nuevo se aplica al dataframe ya filtrado.
            st.session_state.df_actual = apply_single_filter(
                st.session_state.df_actual,
                column,
                condition,
            )
            st.session_state.historial_filtros.append(
                {"column": column, **condition}
            )
            st.rerun()

    if clear:
        st.session_state.df_actual = st.session_state.df_original.copy()
        st.session_state.historial_filtros = []
        st.rerun()

    if cancel:
        st.rerun()


def main():
    login()
    
    
    
    st.set_page_config(layout="wide")
    initialize_dataframe()

    # st.sidebar.selectbox("Opciones", ["Inicio", "Ayuda"])
    st.title("Base de datos de camiones")
    st.header("Filtros acumulativos")

    st.info(
        "Cada filtro se aplica sobre el resultado del filtro anterior. "
        "Puedes volver a filtrar la misma columna tantas veces como quieras."
    )

    st.subheader("Filtros de texto")
    text_cols = st.columns(4)
    for col, field in zip(text_cols, TEXT_FIELDS):
        with col:
            if st.button(f"⚙ {field}", key=f"open_{field}", use_container_width=True):
                filter_dialog(field, "text")

    st.subheader("Filtros numéricos")
    number_cols = st.columns(5)
    for col, field in zip(number_cols, NUMBER_FIELDS):
        with col:
            if st.button(f"⚙ {field}", key=f"open_{field}", use_container_width=True):
                filter_dialog(field, "number")

    # st.subheader("Rango de fechas")
    # date_col1, date_col2 = st.columns(2)
    # with date_col1:
    #     date_start = st.date_input("Fecha inicio", value=None, key="fecha_inicio")
    # with date_col2:
    #     date_end = st.date_input("Fecha final", value=None, key="fecha_final")

    if st.session_state.historial_filtros:
        with st.expander("Historial de filtros aplicados", expanded=True):
            for i, item in enumerate(st.session_state.historial_filtros, start=1):
                st.write(
                    f"{i}. **{item['column']}** — "
                    f"{item['operator']} — `{item['value']}`"
                )

    if st.button("Limpiar todos los filtros y recuperar el Excel original"):
        st.session_state.df_actual = st.session_state.df_original.copy()
        st.session_state.historial_filtros = []
        st.rerun()

    # La tabla siempre parte del dataframe acumulativamente filtrado.
    display_df = st.session_state.df_actual.copy()

    if "Fecha" in display_df.columns:
        dates = pd.to_datetime(display_df["Fecha"], errors="coerce")
        if date_start is not None:
            display_df = display_df.loc[dates >= pd.Timestamp(date_start)]
            dates = dates.loc[display_df.index]
        if date_end is not None:
            display_df = display_df.loc[
                dates < pd.Timestamp(date_end) + pd.Timedelta(days=1)
            ]

    st.subheader("Resultado")
    st.write(
        f"**{len(display_df):,} registros** "
        f"(de {len(st.session_state.df_original):,} originales)"
    )

    column_config = {}
    for column in display_df.columns:
        values = display_df[column].dropna().astype(str).str.strip()
        contains_url = values.str.match(r"^https?://", case=False).any()

        if contains_url:
            display_df[column] = display_df[column].fillna("").astype(str).str.strip()
            column_config[column] = st.column_config.LinkColumn(
                label=str(column),
                help="Pulsa para abrir este enlace en el navegador",
                validate=r"^https?://.+",
            )

    st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("""
            <style>
            /* Ocultar barra de herramientas de las tablas */
            [data-testid="stElementToolbar"] {
                display: none !important;
            }
    
            /* Ocultar menú contextual de descarga */
            [data-testid="stDataFrame"] button {
                display: none !important;
            }
            </style>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
