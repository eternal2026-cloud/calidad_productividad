import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import unicodedata
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BI Productividad - El Pedregal", page_icon="🍇", layout="wide")

# --- IMPORTACIÓN ROBUSTA DE TU MÓDULO DE GOOGLE SHEETS ---
try:
    import google_sheets_utils as gs_utils
    SHEETS_AVAILABLE = True
except ImportError:
    st.error("⚠️ Error Crítico: No se encontró el archivo 'google_sheets_utils.py'. Asegúrate de que esté subido en la misma carpeta.")
    SHEETS_AVAILABLE = False

# --- ESTILOS VISUALES MEJORADOS ---
st.markdown("""
<style>
    .kpi-container {
        background-color: #FFFFFF; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 5px solid #2E7D32;
    }
    .kpi-label { font-size: 14px; color: #555; font-weight: 600; text-transform: uppercase; }
    .kpi-val { font-size: 28px; font-weight: 800; color: #212121; margin-top: 5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #F0F2F6; border-radius: 5px 5px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-top: 3px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- 1. FUNCIONES DE LIMPIEZA Y NORMALIZACIÓN (EL CORAZÓN DE LA ROBUSTEZ) ---
# Estas funciones evitan que el código se rompa si Google Sheets envía basura.

def normalize_text(text):
    """Elimina tildes y convierte a mayúsculas para comparaciones seguras."""
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def safe_float(val):
    """Convierte a float forzosamente, devolviendo 0.0 si falla (ej. celda vacía)."""
    try:
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '').replace('S/', '').strip())
    except:
        return 0.0

def clean_lote_id(val):
    """Estandariza los IDs de Lote (ej. '001' -> '1', 'Lote 1' -> '1')."""
    s = str(val).strip().upper()
    # Extraer solo números si es posible
    match = re.search(r'(\d+)', s)
    if match:
        try:
            return str(int(match.group(1))) # "05" -> "5"
        except:
            return s
    return s

def clean_labor(val):
    """Estandariza nombres de labores."""
    if pd.isna(val): return "DESCONOCIDO"
    return normalize_text(str(val))

# --- 2. CARGA DE DATOS (CON BLINDAJE DE TIPOS) ---

@st.cache_data(ttl=600, show_spinner="Procesando Data Maestra...")
def get_data_maestra_clean():
    """Carga y limpia la Data Maestra para evitar errores matemáticos."""
    if not SHEETS_AVAILABLE: return pd.DataFrame(), {}
    
    # 1. Cargar desde Utils
    df_raw = gs_utils.load_data_maestra()
    if df_raw.empty: return pd.DataFrame(), {}
    
    # 2. Mapa de Columnas Inteligente (Busca nombres parecidos)
    cols = [str(c).strip() for c in df_raw.columns]
    df_raw.columns = cols # Asignar nombres limpios
    
    def find_col(candidates):
        for c in cols:
            if any(cand.lower() == c.lower() for cand in candidates): return c
            if any(cand.lower() in c.lower() for cand in candidates): return c
        return None

    # Definir mapa
    col_map = {
        'Fecha': find_col(['fecha', 'date']),
        'Lote': find_col(['lote', 'ubicacion', 'sector']),
        'Labor': find_col(['labor', 'actividad', 'pep']),
        'Rend_Hr': find_col(['rendimiento_hora', 'rend/hr', 'unidades/hr']),
        'Meta': find_col(['meta', 'meta_min']),
        'Salario': find_col(['salario', 'pago', 'monto']),
        'Dni': find_col(['dni', 'codigo', 'id']),
        'Asistente': find_col(['asistente', 'evaluador', 'supervisor']) # A veces está aquí
    }
    
    # 3. Conversiones Fuertes
    df = df_raw.copy()
    
    if col_map['Fecha']:
        df[col_map['Fecha']] = pd.to_datetime(df[col_map['Fecha']], dayfirst=True, errors='coerce').dt.normalize()
        # Eliminar fechas inválidas
        df = df.dropna(subset=[col_map['Fecha']])
    
    if col_map['Rend_Hr']: df[col_map['Rend_Hr']] = df[col_map['Rend_Hr']].apply(safe_float)
    if col_map['Meta']: df[col_map['Meta']] = df[col_map['Meta']].apply(safe_float)
    if col_map['Salario']: df[col_map['Salario']] = df[col_map['Salario']].apply(safe_float)
    
    if col_map['Lote']:
        df['Lote_Clean'] = df[col_map['Lote']].apply(clean_lote_id)
    else:
        df['Lote_Clean'] = "GENERICO"
        
    if col_map['Labor']:
        df['Labor_Clean'] = df[col_map['Labor']].apply(clean_labor)
        
    return df, col_map

@st.cache_data(ttl=600, show_spinner="Procesando Calidad...")
def get_data_calidad_clean():
    """Carga y limpia Calidad para el Cruce."""
    if not SHEETS_AVAILABLE: return pd.DataFrame()
    
    # 1. Cargar
    df_raw = gs_utils.load_calidad()
    if df_raw.empty: return pd.DataFrame()
    
    # 2. Buscar columnas críticas
    cols = [str(c).strip() for c in df_raw.columns]
    df_raw.columns = cols
    
    def find_col(candidates):
        return next((c for c in cols if any(x in c.lower() for x in candidates)), None)

    c_fecha = find_col(['fecha', 'date'])
    c_lote = find_col(['lote', 'ubicacion'])
    c_asist = find_col(['asistente', 'evaluador', 'nombre'])
    c_desv = find_col(['desviacion', 'desv', '% mala', '% defecto'])
    c_nota = find_col(['nota', 'calificacion', 'score'])
    
    # 3. Limpieza para Cruce
    df = df_raw.copy()
    
    # Fecha y Semana
    if c_fecha:
        df['Fecha_Cruce'] = pd.to_datetime(df[c_fecha], dayfirst=True, errors='coerce').dt.normalize()
        df = df.dropna(subset=['Fecha_Cruce'])
        # Cálculo de Semana (%U es estándar, ajusta si usas ISO)
        df['Semana_Cruce'] = df['Fecha_Cruce'].dt.strftime('%U').astype(int)
    else:
        return pd.DataFrame() # Sin fecha no hay cruce
        
    # Lote
    if c_lote:
        df['Lote_Cruce'] = df[c_lote].apply(clean_lote_id)
    else:
        df['Lote_Cruce'] = "DESCONOCIDO"
        
    # Asistente
    df['Asistente_Cruce'] = df[c_asist].astype(str).str.strip().str.upper() if c_asist else "SIN ASIGNAR"
    
    # Métrica de Calidad (Normalizada a 0.0 - 1.0 donde 1.0 es perfecto)
    # Prioridad: 1. Columna Nota, 2. 1 - Desviación
    df['Calidad_Score'] = 0.0
    
    if c_nota:
        # Asumiendo nota sobre 20 o sobre 100
        vals = df[c_nota].apply(safe_float)
        max_val = vals.max()
        if max_val > 20: # Escala 100
            df['Calidad_Score'] = vals / 100.0
        elif max_val > 1: # Escala 20
            df['Calidad_Score'] = vals / 20.0
        else: # Escala 0-1
            df['Calidad_Score'] = vals
    elif c_desv:
        # Asumimos que es % de defecto (ej. 0.05 o 5)
        vals = df[c_desv].apply(safe_float)
        if vals.max() > 1.0: vals = vals / 100.0 # Convertir 5% a 0.05
        df['Calidad_Score'] = 1.0 - vals
    else:
        df['Calidad_Score'] = 1.0 # Asumir perfecto si no hay datos (o 0 según prefieras)
        
    # Clamp (Asegurar que esté entre 0 y 1)
    df['Calidad_Score'] = df['Calidad_Score'].clip(0, 1)
    
    return df

# --- 3. LOGICA DE NEGOCIO DEL CRUCE (OPTIMIZADA) ---

def calcular_matriz_cruce(df_prod, df_calidad, col_map_prod, semana_selected, ratio):
    """
    Realiza el cruce 'Lote + Fecha' de manera segura.
    """
    # 1. Preparar Producción para el Cruce
    # Filtrar solo la semana relevante en Producción para optimizar
    c_fecha = col_map_prod['Fecha']
    df_p = df_prod.copy()
    df_p['Semana'] = df_p[c_fecha].dt.strftime('%U').astype(int)
    df_p = df_p[df_p['Semana'] == semana_selected]
    
    if df_p.empty: return pd.DataFrame()
    
    # Calcular Eficiencia Diaria por Lote
    # Eficiencia = Promedio(Real / Meta)
    c_rend = col_map_prod['Rend_Hr']
    c_meta = col_map_prod['Meta']
    
    # Evitar división por cero
    df_p['Meta_Safe'] = df_p[c_meta].replace(0, np.nan)
    df_p['Eficiencia_Row'] = df_p[c_rend] / df_p['Meta_Safe']
    
    # Agrupar Producción por [Fecha, Lote]
    prod_agg = df_p.groupby([c_fecha, 'Lote_Clean'])['Eficiencia_Row'].mean().reset_index()
    prod_agg.rename(columns={c_fecha: 'Fecha_Comun', 'Lote_Clean': 'Lote_Comun', 'Eficiencia_Row': 'Eficiencia_Prom'}, inplace=True)
    
    # 2. Preparar Calidad
    q_sem = df_calidad[df_calidad['Semana_Cruce'] == semana_selected].copy()
    if q_sem.empty: return pd.DataFrame()
    
    # Agrupar Calidad por [Fecha, Lote, Asistente]
    qual_agg = q_sem.groupby(['Fecha_Cruce', 'Lote_Cruce', 'Asistente_Cruce'])['Calidad_Score'].mean().reset_index()
    qual_agg.rename(columns={'Fecha_Cruce': 'Fecha_Comun', 'Lote_Cruce': 'Lote_Comun'}, inplace=True)
    
    # 3. MERGE (El Cruce)
    # Inner Join: Solo registros que tengan Producción Y Calidad ese día en ese lote
    merged = pd.merge(qual_agg, prod_agg, on=['Fecha_Comun', 'Lote_Comun'], how='inner')
    
    # 4. Cálculo Final
    # Score = (Calidad * Ratio) + (Eficiencia * (1 - Ratio))
    merged['Score_Final'] = (merged['Calidad_Score'] * ratio) + (merged['Eficiencia_Prom'] * (1 - ratio))
    
    return merged

# --- MAIN APP ---

def main():
    st.sidebar.title("BI Productividad")
    
    # Cargar Datos
    df_maestra, cols_maestra = get_data_maestra_clean()
    df_calidad = get_data_calidad_clean()
    
    if df_maestra.empty:
        st.error("❌ No se pudo cargar la Data Maestra. Verifica la conexión a Google Sheets.")
        st.stop()
        
    # --- SIDEBAR FILTROS GENERALES ---
    st.sidebar.divider()
    
    # Filtro Fecha Global (Afecta a Tab Producción y Financiero)
    c_fecha_m = cols_maestra['Fecha']
    min_d, max_d = df_maestra[c_fecha_m].min(), df_maestra[c_fecha_m].max()
    fechas_sel = st.sidebar.date_input("Rango Fechas:", [min_d, max_d])
    
    # Filtro Labor
    if 'Labor_Clean' in df_maestra.columns:
        labores = sorted(df_maestra['Labor_Clean'].unique())
        labor_sel = st.sidebar.selectbox("Labor:", ["(TODAS)"] + labores)
    
    # Filtrado Maestro
    df_filtrada = df_maestra.copy()
    if isinstance(fechas_sel, (list, tuple)) and len(fechas_sel) == 2:
        df_filtrada = df_filtrada[(df_filtrada[c_fecha_m].dt.date >= fechas_sel[0]) & (df_filtrada[c_fecha_m].dt.date <= fechas_sel[1])]
    if labor_sel != "(TODAS)":
        df_filtrada = df_filtrada[df_filtrada['Labor_Clean'] == labor_sel]

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Producción General", "💰 Resumen Financiero", "⭐ CRUCE CALIDAD (ADVANCED)"])
    
    # TAB 1: Producción (Simplificada pero funcional)
    with tab1:
        st.subheader("Resumen Operativo")
        c1, c2, c3 = st.columns(3)
        
        c_rend = cols_maestra['Rend_Hr']
        prom_rend = df_filtrada[c_rend].mean()
        total_regs = len(df_filtrada)
        
        c1.metric("Rendimiento Promedio", f"{prom_rend:.2f}")
        c2.metric("Registros Procesados", f"{total_regs:,}")
        
        # Gráfico Serie Tiempo
        daily = df_filtrada.groupby(c_fecha_m)[c_rend].mean().reset_index()
        st.line_chart(daily, x=c_fecha_m, y=c_rend)

    # TAB 2: Financiero (Simplificada)
    with tab2:
        st.subheader("Estimación de Costos")
        c_sal = cols_maestra['Salario']
        if c_sal:
            total_gasto = df_filtrada[c_sal].sum()
            st.metric("Gasto Total Planilla (Est.)", f"S/ {total_gasto:,.2f}")
            
            # Top Costos por Lote
            by_lote = df_filtrada.groupby('Lote_Clean')[c_sal].sum().sort_values(ascending=False).head(10)
            st.bar_chart(by_lote)
        else:
            st.warning("No se detectó columna de salario.")

    # TAB 3: CRUCE CON CALIDAD (FOCO PRINCIPAL - ROBUSTO)
    with tab3:
        st.markdown("### 🧬 Matriz de Desempeño: Calidad vs Productividad")
        st.info("Este módulo cruza la información de los Asistentes de Calidad con la Eficiencia de los operarios en el mismo Lote y Día.")
        
        if df_calidad.empty:
            st.warning("⚠️ No hay datos de Calidad disponibles para realizar el cruce.")
        else:
            # Selectores Específicos del Cruce
            col_sel1, col_sel2 = st.columns(2)
            
            semanas_disp = sorted(df_calidad['Semana_Cruce'].unique())
            
            with col_sel1:
                sem_cruce = st.selectbox("📅 Seleccionar Semana a Analizar:", semanas_disp, index=len(semanas_disp)-1)
            
            with col_sel2:
                ratio = st.slider("⚖️ Peso de la Calidad (vs Eficiencia):", 0.0, 1.0, 0.6, help="1.0 = Solo importa la Calidad. 0.0 = Solo Eficiencia.")

            # --- EJECUCIÓN DEL ALGORITMO DE CRUCE ---
            resultado_cruce = calcular_matriz_cruce(df_maestra, df_calidad, cols_maestra, sem_cruce, ratio)
            
            if resultado_cruce.empty:
                st.warning(f"⚠️ No se encontraron coincidencias para la Semana {sem_cruce}.")
                st.markdown("""
                **Posibles Causas:**
                1. No hay producción registrada en los mismos Lotes que Calidad evaluó esa semana.
                2. Las fechas no coinciden exactamente.
                3. Los nombres de los Lotes son muy diferentes (ej. 'Lote 1' vs 'Sector 1').
                """)
                
                # Debugger
                with st.expander("🔍 Ver Datos Crudos para Debug"):
                    st.write("Muestra Calidad (Semana Sel):", df_calidad[df_calidad['Semana_Cruce'] == sem_cruce].head())
                    st.write("Muestra Producción (Semana Sel):", df_maestra.head())
            else:
                st.success(f"✅ Análisis Generado: {len(resultado_cruce)} cruces exitosos.")
                
                # --- VISUALIZACIÓN AVANZADA ---
                
                # 1. Gráfico de Dispersión (Scatter Plot)
                # Eje X: Eficiencia, Eje Y: Calidad, Color: Asistente
                chart = alt.Chart(resultado_cruce).mark_circle(size=100).encode(
                    x=alt.X('Eficiencia_Prom', title='Eficiencia (Prod/Meta)', scale=alt.Scale(zero=False)),
                    y=alt.Y('Calidad_Score', title='Calidad (Score 0-1)', scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color('Asistente_Cruce', legend=alt.Legend(title="Asistente")),
                    tooltip=['Fecha_Comun', 'Lote_Comun', 'Asistente_Cruce', 
                             alt.Tooltip('Eficiencia_Prom', format='.2f'), 
                             alt.Tooltip('Calidad_Score', format='.2%'),
                             alt.Tooltip('Score_Final', format='.2f')]
                ).properties(
                    title=f"Mapa de Desempeño - Semana {sem_cruce}",
                    height=400
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
                
                # 2. Ranking de Mejores Lotes/Asistentes
                col_rank1, col_rank2 = st.columns(2)
                
                with col_rank1:
                    st.markdown("#### 🏆 Top Lotes (Score Global)")
                    top_lotes = resultado_cruce.groupby('Lote_Comun')[['Score_Final', 'Calidad_Score', 'Eficiencia_Prom']].mean().sort_values('Score_Final', ascending=False).head(10)
                    st.dataframe(top_lotes.style.format("{:.2f}").background_gradient(cmap='Greens'), use_container_width=True)
                
                with col_rank2:
                    st.markdown("#### 👤 Desempeño por Asistente")
                    perf_asist = resultado_cruce.groupby('Asistente_Cruce')[['Score_Final', 'Calidad_Score']].mean().sort_values('Score_Final', ascending=False)
                    st.dataframe(perf_asist.style.format("{:.2%}"), use_container_width=True)

                # 3. Descarga de Datos
                st.download_button(
                    label="📥 Descargar Data Cruce (Excel)",
                    data=resultado_cruce.to_csv(index=False).encode('utf-8'),
                    file_name=f"Reporte_Cruce_Semana_{sem_cruce}.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
