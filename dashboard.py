import pandas as pd
import streamlit as st
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout = "wide")
st.title("💸 Dashboard de Finanzas Personales")

# Carga de datos (Ajusta la ruta y el nombre del archivo )
@st.cache_data
def load_data():
    df = pd.read_csv(
        'registro_operaciones_personales_csv.csv',
        sep=';',  # Asumiendo que has confirmado que el separador de columnas es el punto y coma (;)
        encoding='latin1' # Añadimos encoding por si hay caracteres especiales en el CSV
    )
    
    # 1. Limpieza y Conversión Explícita de 'amount'
    # Primero, se convierte a String.
    # Luego, se eliminan los puntos de miles (si existen).
    # Finalmente, se reemplazan las comas decimales por puntos decimales.
    df['amount'] = (
        df['amount'].astype(str)
        .str.replace('.', '', regex=False)  # Eliminar puntos de miles
        .str.replace(',', '.', regex=False)  # Sustituir coma por punto decimal
    )
    
    # Aplicar pd.to_numeric para asegurar que sea float, forzando errores a NaN
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce') 
    
    # 2. Conversión de Fecha
    df['value_date'] = pd.to_datetime(df['value_date'], dayfirst=True)
    
    # 3. Creación de la columna 'YearMonth'
    df['YearMonth'] = df['value_date'].dt.to_period('M').astype(str)
    
    return df

# Colocamos el botón en la barra lateral para que no ocupe espacio en el dashboard principal
with st.sidebar:
    st.markdown("---")
    # Título para la sección de control
    st.subheader("Control de Datos")
    
    # El botón de recarga
    if st.button('🔄 Actualizar Datos (Recargar CSV)'):
        # 1. Limpia la memoria caché de la función load_data
        st.cache_data.clear()
        # 2. Forzar la re-ejecución de todo el script
        st.rerun()
    st.markdown("---")

df = load_data()

# --- FUNCIÓN PARA CALCULAR MÉTRICAS ---
def calcular_metricas(df_filtrado):

    # 1. Ingresos Totales (Excluyendo Traspasos)
    ingresos_netos = df_filtrado[
        (df_filtrado['main_category'] == 'INGRESO') &
        (df_filtrado['sub_category'] != 'Reintegro')
    ]['amount'].sum()

    # 2. Gastos de consumo (Costo de Vida, sin ahorro ni ingresos)
    categorias_consumo = ['FACTURA','SUSCRIPCIONES','GASTO','DEUDAS']
    gastos_consumo = df_filtrado[
        df_filtrado['main_category'].isin(categorias_consumo)
    ]['amount'].sum()

    # 3. Ahorros Netos Destinados (Solo Traspasos de Ahorro)
    ahorros_destinados = df_filtrado[
        (df_filtrado['main_category'] == 'AHORRO') &
        (df_filtrado['sub_category'] == 'Traspaso')
    ]['amount'].sum()
    
    # 4. Resultado Neto (Capacidad de Ahorro)
    # Se utiliza la medida de Gastos de consumo porque el ahorro se cuenta aparte
    resultado_neto = ingresos_netos - gastos_consumo - ahorros_destinados

    return ingresos_netos, gastos_consumo, ahorros_destinados, resultado_neto


# --- CREACIÓN DE FILTROS ---
st.sidebar.header('Filtros')

# Slicer de Year/month (similar al segmentador de datos)
meses_disponibles = sorted(df['YearMonth'].unique(), reverse = True)
meses_seleccionados = st.sidebar.multiselect(
    'Selecciona Mes(es):',
    options=meses_disponibles,
    default=meses_disponibles[:3] # Muestralos últimos tres meses por defecto
)
# Filtra el DataFrame 
df_seleccionado = df[df['YearMonth'].isin(meses_seleccionados)]

# Calcula las métricas con los datos filtrados
ingresos, gastos, ahorros, balance = calcular_metricas(df_seleccionado)

# --- CREACIÓN DE TARJETAS(KPIS) ---
col1, col2, col3, col4 = st.columns(4)

# Función simple para formatear las tarjetas
def format_card(col,value,label,description):
    col.metric(
        label=label,
        value=f"{value:,.2f} €",
        delta=None,
        help=description #El 'help' actua como Tooltip/Description
    )

with col1:
    format_card(col1,ingresos,"Ingresos Totales", "Dinero nuevo que entró (Nóminas, Ventas, etc.).")

with col2:
    format_card(col2,gastos,"Gastos de Consumo","Dinero que gastaste para vivir (Facturas, Gastos Variables, etc.).")

with col3:
    format_card(col3,ahorros,"Ahorros Destinados", "Dinero apartado activamente a la cuenta de ahorro (Traspasos). ")

with col4:
    color_balance = 'green' if balance >= 0 else 'red'
    st.markdown(f"<p style='color:{color_balance}; font-size:16px;'>Balance Neto</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:12px;'>Capacidad de Ahorro después de gastos y ahorro activo.</p>", unsafe_allow_html=True)


st.markdown("---")


# --- CREACIÓN DE TABLA INTERACTIVA ---
st.header("Detalle de Movimientos")
st.dataframe(
    df_seleccionado, 
    use_container_width=True,
    column_order=('value_date', 'main_category', 'description', 'amount'),
    hide_index=True
)