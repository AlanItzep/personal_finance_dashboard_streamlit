import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px # Asegúrate de tener esta importación

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide")
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
    st.subheader("Control de Datos")
    
    if st.button('🔄 Actualizar Datos (Recargar CSV)'):
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
    categorias_consumo = ['FACTURA', 'SUSCRIPCIONES', 'GASTO', 'DEUDAS']
    gastos_consumo = df_filtrado[
        df_filtrado['main_category'].isin(categorias_consumo)
    ]['amount'].sum()

    # 3. Ahorros Netos Destinados (Solo Traspasos de Ahorro)
    ahorros_periodo = df_filtrado[
        (df_filtrado['main_category'] == 'AHORRO') &
        (df_filtrado['sub_category'] == 'Traspaso')
    ]['amount'].sum()
    
    # 4. Resultado Neto
    resultado_neto = ingresos_netos - gastos_consumo - ahorros_periodo

    return ingresos_netos, gastos_consumo, ahorros_periodo, resultado_neto

# --- CÁLCULO DE AHORRO HISTÓRICO ---
def calcular_ahorro_historico(df_completo):
    """Calcula el ahorro total acumulado sobre toda la historia de los datos."""
    
    # CORRECCIÓN DE COLUMNAS: Usar 'main_category' y 'sub_category' que ya usaste arriba
    df_ahorro = df_completo[
        (df_completo['main_category'] == 'AHORRO') & 
        (df_completo['sub_category'] == 'Traspaso')
    ].copy()
    
    ahorro_total_historico = df_ahorro['amount'].sum()
    
    return ahorro_total_historico

# Llama a la función una vez sobre el DF COMPLETO (sin filtros de mes)
ahorro_historico = calcular_ahorro_historico(df) 

# --- CREACIÓN DE FILTROS ---
st.sidebar.header('Filtros')

# Slicer de Year/month
meses_disponibles = sorted(df['YearMonth'].unique(), reverse=True)
meses_seleccionados = st.sidebar.multiselect(
    'Selecciona Mes(es):',
    options=meses_disponibles,
    default=meses_disponibles[:3] # Muestra los últimos tres meses por defecto
)
# Filtra el DataFrame 
df_seleccionado = df[df['YearMonth'].isin(meses_seleccionados)]

# Calcula las métricas con los datos filtrados
ingresos, gastos, ahorros, balance = calcular_metricas(df_seleccionado)

# --- CREACIÓN DE TARJETAS (KPIs) ---
# Función simple para formatear las tarjetas
def format_card(col, value, label, description):
    col.metric(
        label=label,
        value=f"{value:,.2f} €",
        delta=None,
        help=description
    )

# 1. KPIs Principales (4 columnas)
col1, col2, col3, col4 = st.columns(4)

with col1:
    format_card(col1, ingresos, "Ingresos Totales", "Dinero nuevo que entró (Nóminas, Ventas, etc.).")

with col2:
    format_card(col2, gastos, "Gastos de Consumo", "Dinero que gastaste para vivir (Facturas, Gastos Variables, etc.).")

with col3:
    format_card(col3, ahorros, "Ahorros del Período", "Dinero apartado activamente a la cuenta de ahorro (Traspasos).")

with col4:
    # CORRECCIÓN: Usar balance en el valor para que se muestre.
    color_balance = 'green' if balance >= 0 else 'red'
    st.markdown(f"<p style='color:{color_balance}; font-size:16px;'>Balance Neto</p>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{color_balance};'>{balance:,.2f} €</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:12px;'>Capacidad de Ahorro después de gastos y ahorro activo.</p>", unsafe_allow_html=True)


# 2. KPI de Ahorro Histórico (Sección extra de 2 columnas)
col5, _, _ = st.columns([1, 1, 2]) # Solo necesitamos una columna para este KPI extra, las otras quedan vacías para alinear

with col5:
    format_card(col5, ahorro_historico, "Ahorro Histórico (Total)", "Suma total de dinero apartado desde el inicio de los registros.")

st.markdown("---")

# --- GRÁFICO DE DONA (GASTOS POR SUBCATEGORÍA) ---
st.header("📊 Distribución de Gastos de Consumo")
st.markdown("---")

# 1. Filtrar solo los gastos de consumo
categorias_consumo = ['FACTURA', 'SUSCRIPCIONES', 'GASTO', 'DEUDAS'] # Usa los nombres de categorías que definiste en calcular_metricas
df_gastos = df_seleccionado[
    df_seleccionado['main_category'].isin(categorias_consumo) # CORRECCIÓN: Usar 'main_category'
].copy()

# 2. Agrupar por la columna de subcategoría
# ASUMIMOS que la subcategoría es 'sub_category'
df_gastos_agrupados = df_gastos.groupby('sub_category')['amount'].sum().reset_index()
df_gastos_agrupados.columns = ['Subcategoría', 'Monto']


if not df_gastos_agrupados.empty:
    fig = px.pie(
        df_gastos_agrupados, 
        values='Monto', 
        names='Subcategoría', 
        title='Detalle de Gastos por Subcategoría',
        hole=0.4
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(legend_title_text='Subcategorías', showlegend=True)
    
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.info("No hay gastos de consumo en el período seleccionado para visualizar.")

# --- CREACIÓN DE TABLA INTERACTIVA ---
st.header("Detalle de Movimientos")
st.dataframe(
    df_seleccionado, 
    use_container_width=True,
    # ASUNCIÓN: value_date, main_category, description, y amount son los nombres de tus columnas
    column_order=('value_date', 'main_category', 'description', 'amount'), 
    hide_index=True
)