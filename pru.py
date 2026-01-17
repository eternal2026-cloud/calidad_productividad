import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os
import requests
from datetime import datetime
import locale
from io import BytesIO
import altair as alt
import unicodedata
import re
import glob

# Importar utilidades de Google Sheets
try:
    import google_sheets_utils as gs_utils
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    st.warning("⚠️ Módulo google_sheets_utils no disponible. Usando solo archivos locales.")

# --- CONFIGURACIÓN GLOBAL ---
pd.set_option("styler.render.max_elements", 1000000)

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="BI Productividad - El Pedregal", page_icon="🍇", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .main { background-color: #F8F9FA; color: #212121; }
    h1, h2, h3 { color: #000000 !important; font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    
    .kpi-card {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .kpi-title { color: #616161; font-size: 13px; text-transform: uppercase; font-weight: 600; }
    .kpi-value { color: #212121; font-size: 26px; font-weight: 800; font-family: 'Arial', sans-serif; }
    .kpi-delta { font-size: 12px; font-weight: 700; margin-top: 5px; }
    .kpi-delta.pos { color: #2E7D32; background-color: #E8F5E9; padding: 2px 6px; border-radius: 4px; display: inline-block;} 
    .kpi-delta.neg { color: #C62828; background-color: #FFEBEE; padding: 2px 6px; border-radius: 4px; display: inline-block;}
    .kpi-delta.neu { color: #757575; }

    .stPlotlyChart { background-color: #FFFFFF; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 10px; }
    div[data-testid="stDataFrame"] { background-color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIÓN KPI ---
def mostrar_kpi(titulo, valor, delta=None, color_borde="#2196F3"):
    delta_html = ""
    if delta:
        color_class = "pos" if (str(delta).startswith("+") or "OK" in str(delta)) else "neg" if str(delta).startswith("-") else "neu"
        delta_html = f"<div class='kpi-delta {color_class}'>{delta}</div>"
    
    html = f"""
    <div class="kpi-card" style="border-left: 4px solid {color_borde};">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{valor}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(show_spinner="Cargando datos de productividad...")
def cargar_datos():
    # 1. CARGAR DATA MAESTRA (desde Google Sheets o Excel local)
    try:
        # Intentar cargar desde Google Sheets primero
        if GOOGLE_SHEETS_AVAILABLE:
            try:
                df = gs_utils.load_data_maestra()
                if df.empty:
                    raise Exception("DataFrame vacío")
            except:
                df = pd.read_excel("Data_Maestra_Limpia.xlsx")
        else:
            df = pd.read_excel("Data_Maestra_Limpia.xlsx")
        # Mapeo inteligente de columnas
        col_map = {
            'Fecha': next((c for c in df.columns if 'fecha' in c.lower()), None),
            'Dni': next((c for c in df.columns if 'dni' in c.lower()), None),
            'Rendimiento_Diario': next((c for c in df.columns if c.strip() == 'Rendimiento'), None),
            'Rendimiento_Hora': next((c for c in df.columns if 'rend/hr real' in c.lower()), None),
            'Horas': next((c for c in df.columns if 'horas' in c.lower() and 'totales' in c.lower()), None), 
            'Labor': next((c for c in df.columns if 'pep' in c.lower() or 'labor' in c.lower()), None),
            'Operario': next((c for c in df.columns if 'nombre' in c.lower() or 'operario' in c.lower()), None),
            'Lote': next((c for c in df.columns if 'lote' in c.lower()), None),
            'Meta_Min': next((c for c in df.columns if 'min' in c.lower() and 'meta' in c.lower()), None),
            'Meta_Max': next((c for c in df.columns if 'max' in c.lower() and 'meta' in c.lower()), None),
            'Clasificacion': next((c for c in df.columns if 'clasifi' in c.lower()), None),
            'Turno2': next((c for c in df.columns if 'turno' in c.lower()), None),
            # NUEVAS COLUMNAS
            'Salario': next((c for c in df.columns if any(x in c.lower() for x in ['salario', 'importe', 'monto', 'pago']) and 'tipo' not in c.lower()), None),
            'Variedad': next((c for c in df.columns if 'variedad' in c.lower()), None)
        }
        
        c_fecha = col_map['Fecha']
        if c_fecha:
            # dayfirst=True le dice a Linux que 12/05 es 12 de Mayo, no Diciembre
            df[c_fecha] = pd.to_datetime(df[c_fecha], dayfirst=True, errors='coerce')
            
        if col_map['Lote']:
            df[col_map['Lote']] = df[col_map['Lote']].astype(str).str.split('.').str[0].str.zfill(3)
        
        if col_map['Labor']:
            df[col_map['Labor']] = df[col_map['Labor']].astype(str).str.strip().str.upper()
            
        if col_map['Variedad']:
            df[col_map['Variedad']] = df[col_map['Variedad']].astype(str).str.strip().str.upper()

        # Limpieza de Salario (asegurar numérico)
        if col_map['Salario']:
            df[col_map['Salario']] = pd.to_numeric(df[col_map['Salario']], errors='coerce').fillna(0)

    except Exception as e:
        st.error(f"Error cargando Data Maestra: {e}")
        return pd.DataFrame(), {}

    return df, col_map

# ==============================================================================
# FUNCIONES Y CARGA DE DATOS PARA TAB 3 (CRUCE CALIDAD)
# ==============================================================================

def normalize_text_cruce(text):
    """Elimina acentos y convierte a minúsculas para búsquedas flexibles."""
    if not isinstance(text, str): return str(text)
    n = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower()

def clean_lote_cruce(val):
    """Normaliza el formato del lote: '001' -> '1', 'L35 (1)' -> '35'"""
    if pd.isna(val): return "Desconocido"
    s = str(val).strip()
    match = re.search(r'(\d+)', s)
    if match:
        try: return str(int(match.group(1)))
        except: return s
    return s

def codigo_a_variedad(val):
    """Convierte código de variedad a nombre completo (inverso del original)."""
    mapa_inverso = {
        'TM': 'TIMPSON', 'AL': 'ALLISON', 'CC': 'COTTON CANDY',
        'SS': 'SABLE SEEDLESS', 'CH': 'CANDY HEARTS', 'RG': 'RED GLOBE',
        'S54': 'SUGRA54', 'SG': 'SWEET GLOBE', 'IV': 'IVORY', 'AC': 'AUTUMN CRISP'
    }
    val_upper = str(val).upper().strip()
    return mapa_inverso.get(val_upper, val)

def find_col_cruce(df, candidates):
    """Busca una columna en el DataFrame coincidiendo con una lista de candidatos."""
    df_cols_norm = {normalize_text_cruce(c): c for c in df.columns}
    for cand in candidates:
        cand_norm = normalize_text_cruce(cand)
        if cand_norm in df_cols_norm:
            return df_cols_norm[cand_norm]
    return None

def format_with_icon(val, is_efficiency=False, is_quality=False):
    """Formatea el valor numérico con iconos de alerta/éxito."""
    if pd.isna(val): return "-"
    icon = ""
    if is_efficiency:
        icon = "✅" if val >= 1.0 else "🚩"
    elif is_quality:
        icon = "✅" if val >= 0.95 else "🚩"
    return f"{icon} {val:.1%}"

@st.cache_data(show_spinner="Cargando datos de calidad...")
def cargar_datos_calidad():
    """Carga el archivo de calidad para el módulo de cruce (Tab 3)."""
    df_qual = pd.DataFrame()
    debug_msg = []
    
    # Intentar cargar desde Google Sheets primero
    if GOOGLE_SHEETS_AVAILABLE:
        try:
            df_qual = gs_utils.load_calidad()
            if not df_qual.empty:
                df_qual.columns = [c.strip() for c in df_qual.columns]
                debug_msg.append("Datos de Calidad cargados desde Google Sheets")
            else:
                raise Exception("DataFrame vacío")
        except Exception as e:
            debug_msg.append(f"Google Sheets no disponible: {e}. Intentando archivo local...")
    
    # Fallback a archivos locales si Google Sheets falla o no está disponible
    if df_qual.empty:
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
        except:
            base_path = os.getcwd()
        
        try:
            files = [f for f in os.listdir(base_path) if f.endswith(('.xlsx', '.xls'))]
        except:
            return pd.DataFrame(), debug_msg
        
        file_qual = None
        for f in files:
            name_norm = normalize_text_cruce(f)
            if "calidad" in name_norm and "maestra" not in name_norm:
                file_qual = os.path.join(base_path, f)
                break
        
        if file_qual:
            try:
                df_qual = pd.read_excel(file_qual, engine='openpyxl')
                df_qual.columns = [c.strip() for c in df_qual.columns]
                debug_msg.append(f"Archivo Calidad: {os.path.basename(file_qual)}")
            except Exception as e:
                debug_msg.append(f"Error cargando archivo local: {e}")
        else:
            debug_msg.append("No se encontró archivo de calidad (busca 'calidad' en nombre)")

    # PROCESAMIENTO Y NORMALIZACIÓN (Aplica a Sheets y Local)
    if not df_qual.empty:
        try:
            # Mapeo de columnas con candidatos flexibles
            c_fecha = find_col_cruce(df_qual, ['Fecha', 'Date'])
            c_lote = find_col_cruce(df_qual, ['LoteSer', 'Lote_Clean', 'Lote', 'Ubicacion'])
            c_asist = find_col_cruce(df_qual, ['Asistente_C', 'Asistente_Clean', 'Asistente', 'Nombre'])
            c_desv = find_col_cruce(df_qual, ['Desv_Tot', 'Desviacion_Total_Grupo', 'Desviacion_Total', 'Desviacion'])
            c_tasa = find_col_cruce(df_qual, ['%Calidad', 'Tasa_Valor'])
            c_variedad = find_col_cruce(df_qual, ['Variedad', 'Variedad_Cod'])
            c_defecto = find_col_cruce(df_qual, ['Tipo_Defe', 'Tipo_Defecto', 'Categoria Defecto', 'Defecto'])
            c_jabas = find_col_cruce(df_qual, ['Cantidad_J', 'Cantidad_Jabas', 'Conteo_Jabas', 'Jabas'])
            
            # UNIFORMIZACIÓN DE FECHAS
            if c_fecha:
                df_qual['Fecha_Cruce'] = pd.to_datetime(df_qual[c_fecha], dayfirst=True, errors='coerce')
                df_qual['Fecha_Cruce'] = df_qual['Fecha_Cruce'].dt.normalize()
            
            # Lotes limpios
            df_qual['Lote_Cruce'] = df_qual[c_lote].apply(clean_lote_cruce) if c_lote else "Desconocido"
            
            # Asistente unificado
            df_qual['Asistente_Cruce'] = df_qual[c_asist].astype(str).str.strip() if c_asist else "Sin Asignar"
            
            # Desviación
            if c_desv:
                df_qual['Desv_Cruce'] = pd.to_numeric(df_qual[c_desv], errors='coerce').fillna(0)
            elif c_tasa:
                # Si no hay desv pero hay calidad, desv = 1 - calidad (si calidad es 0.95 -> desv 0.05)
                # O si c_tasa ya es la desviación (algunos archivos la llaman así)
                val_tasa = pd.to_numeric(df_qual[c_tasa], errors='coerce').fillna(0)
                if val_tasa.max() > 0.5: # Probablemente es %Calidad (ej 0.98)
                    df_qual['Desv_Cruce'] = 1.0 - val_tasa
                else:
                    df_qual['Desv_Cruce'] = val_tasa
            else:
                df_qual['Desv_Cruce'] = 0
            
            # Variedad
            df_qual['Variedad_Cruce'] = df_qual[c_variedad].apply(codigo_a_variedad) if c_variedad else "ND"
            
            # Defecto
            df_qual['Defecto_Cruce'] = df_qual[c_defecto] if c_defecto else "Sin Detalle"
            
            # Jabas
            if c_jabas:
                df_qual['Jabas_Cruce'] = pd.to_numeric(df_qual[c_jabas], errors='coerce').fillna(0).astype(int)
            else:
                df_qual['Jabas_Cruce'] = 0
            
            # Semana
            if 'Fecha_Cruce' in df_qual.columns:
                df_qual['Semana_Cruce'] = df_qual['Fecha_Cruce'].dt.isocalendar().week

            debug_msg.append(f"Procesadas {len(df_qual)} filas de calidad")
            
        except Exception as e:
            debug_msg.append(f"Error procesando datos de calidad: {e}")
    
    return df_qual, debug_msg


# ==============================================================================
# FUNCIONES CACHEADAS PARA TAB3 (OPTIMIZACIÓN DE RENDIMIENTO)
# ==============================================================================

@st.cache_data(show_spinner=False)
def preparar_produccion_cruce(_df_f, c_fecha, c_lote, c_rend_hr, c_meta_min):
    """Prepara el DataFrame de producción para cruce. Cacheado para evitar recálculo."""
    df_prod = _df_f.copy()
    df_prod['Fecha_Cruce'] = pd.to_datetime(df_prod[c_fecha]).dt.normalize()
    df_prod['Semana_Cruce'] = df_prod['Fecha_Cruce'].dt.isocalendar().week
    df_prod['Lote_Cruce'] = df_prod[c_lote].apply(clean_lote_cruce)
    
    if 'Eficiencia' not in df_prod.columns:
        if c_rend_hr and c_meta_min:
            df_prod['Eficiencia'] = df_prod[c_rend_hr] / df_prod[c_meta_min].replace(0, np.nan)
        else:
            df_prod['Eficiencia'] = 0
    return df_prod

@st.cache_data(show_spinner=False)
def calcular_merged_data(_df_prod_cruce, _df_calidad, semana_cruce, ratio_calidad):
    """Calcula el merge entre producción y calidad. Cacheado por semana y ratio."""
    df_p_sem = _df_prod_cruce[_df_prod_cruce['Semana_Cruce'] == semana_cruce].copy()
    df_q_sem = _df_calidad[_df_calidad['Semana_Cruce'] == semana_cruce].copy()
    
    if df_p_sem.empty or df_q_sem.empty:
        return pd.DataFrame(), df_p_sem, df_q_sem
    
    # Agrupación de producción
    prod_agg = df_p_sem.groupby(['Lote_Cruce', 'Fecha_Cruce']).agg({'Eficiencia': 'mean'}).reset_index()
    
    # Agrupación de calidad
    qual_agg = df_q_sem.groupby(['Asistente_Cruce', 'Lote_Cruce', 'Fecha_Cruce']).agg({
        'Desv_Cruce': 'mean', 'Variedad_Cruce': 'first', 'Jabas_Cruce': 'sum'
    }).reset_index()
    qual_agg.rename(columns={
        'Asistente_Cruce': 'Asistente', 
        'Desv_Cruce': 'Desviacion_Total', 
        'Variedad_Cruce': 'Variedad',
        'Jabas_Cruce': 'Jabas'
    }, inplace=True)
    
    # Merge
    merged = pd.merge(qual_agg, prod_agg, on=['Lote_Cruce', 'Fecha_Cruce'], how='inner')
    
    if not merged.empty:
        merged['Calidad_Calc'] = 1.0 - merged['Desviacion_Total'].fillna(0)
        merged['Score'] = (merged['Calidad_Calc'] * ratio_calidad) + (merged['Eficiencia'] * (1 - ratio_calidad))
        merged['Calidad_Tabla'] = merged['Calidad_Calc']  # Alias para compatibilidad
    
    return merged, df_p_sem, df_q_sem

@st.cache_data(show_spinner=False)
def calcular_estadisticas_asistente(merged):
    """Calcula estadísticas por asistente. Cacheado."""
    if merged.empty:
        return pd.DataFrame()
    asist_stats = merged.groupby('Asistente')['Desviacion_Total'].mean().reset_index()
    asist_stats['Desviacion_Pct'] = asist_stats['Desviacion_Total'] * 100
    return asist_stats

@st.cache_data(show_spinner=False)
def calcular_correlacion_lotes(merged):
    """Calcula correlación de lotes. Cacheado."""
    if merged.empty:
        return pd.DataFrame()
    return merged.groupby('Lote_Cruce')[['Eficiencia', 'Calidad_Calc']].mean().reset_index()

@st.cache_data(show_spinner=False)
def calcular_defects_trend(df_q_sem, filtro_asistente):
    """Calcula tendencia de defectos. Cacheado por filtro de asistente."""
    if df_q_sem.empty:
        return pd.DataFrame()
    
    if filtro_asistente == '(TODOS)':
        df_filtrado = df_q_sem
    else:
        df_filtrado = df_q_sem[df_q_sem['Asistente_Cruce'] == filtro_asistente]
    
    return df_filtrado.groupby(['Fecha_Cruce', 'Defecto_Cruce'])['Desv_Cruce'].sum().reset_index()

@st.cache_data(show_spinner=False)
def calcular_ranking_lotes(merged):
    """Calcula top y bottom lotes. Cacheado."""
    if merged.empty:
        return pd.DataFrame(), pd.DataFrame()
    lote_stats = merged.groupby('Lote_Cruce')[['Eficiencia', 'Calidad_Calc']].mean().reset_index()
    top_5 = lote_stats.nlargest(5, 'Eficiencia')
    bottom_5 = lote_stats.nsmallest(5, 'Eficiencia')
    return top_5, bottom_5

@st.cache_data(show_spinner=False)
def calcular_pivot_score(merged, index_col, filtro_lote, ratio):
    """Calcula pivot de score. Cacheado por índice y filtro."""
    if merged.empty:
        return pd.DataFrame()
    
    if filtro_lote != '(TODOS)':
        df = merged[merged['Lote_Cruce'] == filtro_lote].copy()
    else:
        df = merged

    if df.empty:
        return pd.DataFrame()
    
    df['Score'] = (df['Calidad_Calc'] * ratio) + (df['Eficiencia'] * (1 - ratio))
    
    pivot = df.pivot_table(index=index_col, columns='Fecha_Cruce', values='Score', aggfunc='mean')
    if not pivot.empty:
        pivot['PROMEDIO'] = pivot.mean(axis=1)
    return pivot

@st.cache_data(show_spinner=False)
def calcular_pivot_metricas(merged, index_col, filtro_lote):
    """Calcula pivot de métricas. Cacheado por índice y filtro."""
    if merged.empty:
        return pd.DataFrame(), []
    
    if filtro_lote != '(TODOS)':
        df = merged[merged['Lote_Cruce'] == filtro_lote]
    else:
        df = merged
    
    if df.empty:
        return pd.DataFrame(), []
    
    pivot = df.pivot_table(
        index=index_col,
        columns='Fecha_Cruce',
        values=['Calidad_Calc', 'Eficiencia'],
        aggfunc='mean'
    )
    fechas = sorted(df['Fecha_Cruce'].unique())
    return pivot, fechas


# --- API CLIMA ---
@st.cache_data(ttl=3600, show_spinner=False)  # Cache 1 hora, sin spinner
def obtener_clima_ica(fecha_inicio, fecha_fin):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": -14.06, "longitude": -75.73,
            "start_date": fecha_inicio.strftime("%Y-%m-%d"),
            "end_date": fecha_fin.strftime("%Y-%m-%d"),
            "daily": "temperature_2m_max", "timezone": "America/Lima"
        }
        r = requests.get(url, params=params, timeout=3)  # Timeout 3 segundos
        data = r.json()
        if 'daily' in data:
            return pd.DataFrame({'Fecha': pd.to_datetime(data['daily']['time']), 'Temp_Max_Ica': data['daily']['temperature_2m_max']})
    except: pass
    return pd.DataFrame()

# --- PREPARACIÓN DATASET IA ---
def generar_dataset_ia(df_filtered, c_fecha, c_lote, c_labor, c_rend_hr, c_dni, df_clima):
    grouper = [c_fecha, c_lote]
    if c_labor: grouper.append(c_labor)
    df_ai = df_filtered.groupby(grouper).agg({
        c_rend_hr: 'mean', c_dni: 'nunique'}).reset_index()
    df_ai['Mes'] = df_ai[c_fecha].dt.month
    df_ai['Dia_Semana'] = df_ai[c_fecha].dt.dayofweek
    df_ai['Dia_Anio'] = df_ai[c_fecha].dt.dayofyear
    if not df_clima.empty:
        df_ai = pd.merge(df_ai, df_clima, left_on=c_fecha, right_on='Fecha', how='left')
        df_ai.drop(columns=['Fecha'], inplace=True, errors='ignore')
        df_ai['Temp_Max_Ica'] = df_ai['Temp_Max_Ica'].fillna(method='ffill').fillna(df_ai['Temp_Max_Ica'].mean())
    rename_dict = {
        c_fecha: 'Fecha', c_lote: 'Lote_ID', c_rend_hr: 'TARGET_Rendimiento_Hr',
        c_dni: 'Feature_Num_Operarios', 'Temp_Max_Ica': 'Feature_Temp_Max'
    }
    if c_labor: rename_dict[c_labor] = 'Feature_Labor'
    return df_ai.rename(columns=rename_dict)

# --- FUNCIONES PDF ---
def crear_pdf_completo(df_lotes, conclusiones, df_pareto, df_turnos, df_scatter, df_evolucion, labor_sel, insights_asistencia, df_patron_semanal, df_trend, col_map, df_financiero_resumen):
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image("logo.png", 10, 8, 30)
                except: pass
            self.set_font('Arial', 'B', 16)
            self.cell(0, 8, 'EL PEDREGAL S.A.', 0, 1, 'C')
            self.set_font('Arial', 'I', 11)
            self.cell(0, 6, 'FUNDO YAURILLA - DEPARTAMENTO DE PRODUCTIVIDAD', 0, 1, 'C')
            self.ln(10)
            self.set_font('Arial', 'B', 12)
            self.set_fill_color(240, 240, 240)
            self.cell(0, 10, f' REPORTE TÉCNICO: {labor_sel}', 0, 1, 'L', True)
            self.ln(5)
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()} | {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

    pdf = PDF(); pdf.add_page()
    
    # 1. RESUMEN
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "1. RESUMEN EJECUTIVO", 0, 1)
    pdf.set_font("Arial", size=10)
    for p in conclusiones:
        if "REPORTE TÉCNICO" in p: continue
        pdf.multi_cell(0, 5, txt=p); pdf.ln(2)
    pdf.ln(5)

    def save_plot(fig):
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(path, bbox_inches='tight', dpi=100)
        plt.close(fig)
        return path

    # GRÁFICO CUMPLIMIENTO
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    colores = ['#D32F2F' if x < 100 else '#388E3C' for x in df_lotes['Cumplimiento_Meta']]
    ax1.bar(df_lotes['Lote'], df_lotes['Cumplimiento_Meta'], color=colores)
    ax1.axhline(100, color='blue', linestyle='--', label='Meta')
    ax1.set_title('Cumplimiento por Lote (%)', fontsize=12, fontweight='bold')
    plt.xticks(rotation=90, fontsize=8); ax1.grid(axis='y', linestyle='--', alpha=0.3)
    pdf.image(save_plot(fig1), x=10, w=190); pdf.ln(5)

    # 2. EVOLUCIÓN
    pdf.add_page(); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "2. EVOLUCIÓN TEMPORAL Y CLIMA", 0, 1)
    fig_line, ax_line = plt.subplots(figsize=(10, 5))
    c_fecha = col_map['Fecha']; c_rend = col_map['Rendimiento_Hora']
    c_meta_min = col_map['Meta_Min']; c_meta_max = col_map['Meta_Max']
    fechas = df_trend[c_fecha]; rend = df_trend[c_rend]
    ax_line.plot(fechas, rend, color='#2E7D32', linewidth=2, label='Rendimiento/Hr')
    if c_meta_min and c_meta_min in df_trend.columns: ax_line.plot(fechas, df_trend[c_meta_min], color='#D32F2F', linestyle='--', label='Meta Min')
    if c_meta_max and c_meta_max in df_trend.columns: ax_line.plot(fechas, df_trend[c_meta_max], color='#FFD700', linestyle='--', label='Meta Max')
    ax_line.set_ylabel("Rendimiento / Hr", color='#2E7D32'); ax_line.tick_params(axis='y', labelcolor='#2E7D32'); ax_line.grid(True, linestyle='--', alpha=0.3)
    if 'Temp_Max_Ica' in df_trend.columns:
        ax_temp = ax_line.twinx()
        ax_temp.fill_between(fechas, df_trend['Temp_Max_Ica'], color='#F57C00', alpha=0.2, label='Temp Max')
        ax_temp.plot(fechas, df_trend['Temp_Max_Ica'], color='#F57C00', linewidth=1)
        ax_temp.set_ylabel("Temperatura (°C)", color='#E65100'); ax_temp.tick_params(axis='y', labelcolor='#E65100'); ax_temp.set_ylim(bottom=15)
    ax_line.set_title("Evolución de Rendimiento vs Temperatura", fontsize=12, fontweight='bold'); fig_line.autofmt_xdate()
    pdf.image(save_plot(fig_line), x=10, w=190); pdf.ln(5)

    # 3. PARETO
    pdf.add_page(); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "3. ANÁLISIS DE PARETO", 0, 1)
    lotes_p, prod_p, pct_p = df_pareto['Lote'].tolist(), df_pareto['Produccion_Total'].tolist(), df_pareto['Porcentaje_Acum'].tolist()
    fig2, ax2 = plt.subplots(figsize=(10, 4.5))
    ax2.bar(lotes_p, prod_p, color='#1976D2', label='Producción')
    plt.xticks(rotation=90, fontsize=8); ax3 = ax2.twinx()
    ax3.plot(lotes_p, pct_p, color='red', marker='o', markersize=3); ax3.set_ylim(0, 110)
    ax2.set_title('Pareto de Producción', fontsize=12, fontweight='bold')
    pdf.image(save_plot(fig2), x=10, w=190); pdf.ln(5)

    # 4. ASISTENCIA
    pdf.add_page(); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "4. PATRONES DE ASISTENCIA", 0, 1)
    pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, txt=f"Insight Asistencia: {insights_asistencia}"); pdf.ln(5)
    if not df_patron_semanal.empty:
        fig_hm, ax_hm = plt.subplots(figsize=(10, 3.5))
        pivot_hm = df_patron_semanal.pivot(index='Clasificacion_Calc', columns='Dia_Nom', values='Pct')
        dias_orden = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
        dias_presentes = [d for d in dias_orden if d in pivot_hm.columns]
        pivot_hm = pivot_hm[dias_presentes].fillna(0)
        im = ax_hm.imshow(pivot_hm, cmap='RdYlGn', aspect='auto')
        ax_hm.set_xticks(np.arange(len(dias_presentes))); ax_hm.set_yticks(np.arange(len(pivot_hm.index)))
        ax_hm.set_xticklabels(dias_presentes); ax_hm.set_yticklabels(pivot_hm.index)
        for i in range(len(pivot_hm.index)):
            for j in range(len(dias_presentes)): ax_hm.text(j, i, f"{pivot_hm.iloc[i, j]:.0f}%", ha="center", va="center", color="black", fontsize=8)
        ax_hm.set_title("Distribución Semanal de Calidad (%)", fontweight='bold')
        pdf.image(save_plot(fig_hm), x=10, w=190); pdf.ln(5)

    # 5. EFICIENCIA
    pdf.add_page(); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "5. EFICIENCIA OPERATIVA", 0, 1)
    fig4, ax4 = plt.subplots(figsize=(10, 5))
    ax4.scatter(df_scatter['Operarios_Unicos'], df_scatter['Produccion_Total'], c='purple', alpha=0.6, s=80)
    for i, txt in enumerate(df_scatter['Lote']):
        if i % 2 == 0: ax4.annotate(txt, (df_scatter['Operarios_Unicos'].iloc[i], df_scatter['Produccion_Total'].iloc[i]), fontsize=8)
    ax4.set_xlabel('Operarios'); ax4.set_ylabel('Producción'); ax4.set_title('Eficiencia: Producción vs Dotación', fontsize=12, fontweight='bold'); ax4.grid(True, linestyle='--', alpha=0.5)
    pdf.image(save_plot(fig4), x=10, w=190)

    # 6. ANÁLISIS FINANCIERO
    if df_financiero_resumen is not None and not df_financiero_resumen.empty:
        pdf.add_page(); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "6. ANÁLISIS FINANCIERO Y COSTOS", 0, 1)
        pdf.set_font("Arial", size=10)
        total_pago = df_financiero_resumen['Pago_Estimado_Total'].sum()
        prod_total_fin = df_financiero_resumen['Produccion_Total'].sum()
        costo_unitario_avg = total_pago / prod_total_fin if prod_total_fin > 0 else 0
        
        pdf.multi_cell(0, 5, txt=f"Gasto Total Estimado de Planilla (Periodo): S/ {total_pago:,.2f}")
        pdf.multi_cell(0, 5, txt=f"Costo Promedio por Unidad Producida: S/ {costo_unitario_avg:.4f}")
        pdf.ln(5)
        
        # Gráfico Financiero (Eficiencia Financiera por Lote)
        fig_fin, ax_fin = plt.subplots(figsize=(10, 5))
        # Scatter: X=Producción, Y=Gasto
        ax_fin.scatter(df_financiero_resumen['Produccion_Total'], df_financiero_resumen['Pago_Estimado_Total'], c='#2E7D32', alpha=0.7, s=100)
        
        # Etiquetar lotes
        for i, row in df_financiero_resumen.iterrows():
             if i % 2 == 0: # Etiquetar alternados
                ax_fin.annotate(str(row['Lote_ID']), (row['Produccion_Total'], row['Pago_Estimado_Total']), fontsize=8)
                
        ax_fin.set_title('Eficiencia Financiera: Producción vs Gasto Total por Lote', fontsize=12, fontweight='bold')
        ax_fin.set_xlabel('Producción Total (Unidades)')
        ax_fin.set_ylabel('Gasto Total Planilla (S/)')
        ax_fin.grid(True, linestyle='--', alpha=0.5)
        pdf.image(save_plot(fig_fin), x=10, w=190)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- CARGA INICIAL DE DATOS ---
df, col_map = cargar_datos()

# --- MAIN APP ---
if df.empty:
    st.warning("⚠️ Sin datos. Verifica 'Data_Maestra_Limpia.xlsx'.")
else:
    tab1, tab2, tab3 = st.tabs(["📊 Análisis Productivo", "💰 Análisis Financiero & Pagos", "🔗 Cruce Calidad"])

    with st.sidebar:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.write("## ⚙️ Filtros Globales")
        c_fecha = col_map['Fecha']
        if not df.empty and c_fecha:
            min_d, max_d = df[c_fecha].min().date(), df[c_fecha].max().date()
            date_range = st.date_input("Periodo:", [min_d, max_d])
        else:
            date_range = [datetime.now(), datetime.now()]
        
        c_labor = col_map['Labor']
        labores = ['(TODAS)'] + sorted(df[c_labor].astype(str).unique().tolist()) if c_labor else ['(TODAS)']
        sel_labor = st.selectbox("Labor:", labores)
        
        # FILTRO VARIEDAD
        c_variedad = col_map['Variedad']
        if c_variedad:
            variedades = ['(TODAS)'] + sorted(df[c_variedad].dropna().astype(str).unique().tolist())
            sel_variedad = st.selectbox("Variedad:", variedades)
        else:
            sel_variedad = '(TODAS)'

        st.divider(); st.markdown("### 🏢 El Pedregal S.A."); st.caption("Fundo Yaurilla | BI Productividad")
        
        # --- FILTROS TAB 3 (CRUCE) ---
        st.divider()
        st.markdown("### 🔗 Config. Cruce Calidad")
        
        # Cargar datos de calidad
        df_calidad, debug_calidad = cargar_datos_calidad()
        
        if not df_calidad.empty and 'Semana_Cruce' in df_calidad.columns:
            semanas_calidad = sorted(df_calidad['Semana_Cruce'].dropna().unique())
            sel_semana_cruce = st.selectbox("Semana (Cruce):", semanas_calidad, index=len(semanas_calidad)-1 if semanas_calidad else 0)
        else:
            sel_semana_cruce = None
            st.warning("⚠️ Sin datos de calidad")
        
        ratio_calidad = st.slider("Peso Calidad vs Eficiencia:", 0.0, 1.0, 0.3, 0.05)
        
        with st.expander("🛠️ Debug Calidad"):
            for msg in debug_calidad:
                if "Error" in str(msg): st.error(msg)
            st.write(f"Filas Calidad: {len(df_calidad)}")

    # Máscara de fecha robusta
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        mask = (df[c_fecha].dt.date >= date_range[0]) & (df[c_fecha].dt.date <= date_range[1])
    else:
        # Si solo se ha seleccionado una fecha, filtrar por esa única fecha
        mask = (df[c_fecha].dt.date == date_range[0])
    if sel_labor != '(TODAS)': mask = mask & (df[c_labor] == sel_labor)
    if sel_variedad != '(TODAS)' and c_variedad: mask = mask & (df[c_variedad].astype(str) == sel_variedad)
    df_f = df[mask].copy()

    c_lote = col_map['Lote']; c_meta_min = col_map['Meta_Min']; c_meta_max = col_map['Meta_Max']
    c_rend_hr = col_map['Rendimiento_Hora']; c_rend_dia = col_map['Rendimiento_Diario']
    c_dni = col_map['Dni']; c_clasif = col_map['Clasificacion']; c_turno = col_map['Turno2']
    c_operario = col_map['Operario']
    c_salario = col_map['Salario'] # Columna de Pago Directo

    if 'Cumplimiento' not in df_f.columns:
        # Asegurar que las columnas sean numéricas para evitar TypeError con Google Sheets
        rend_vals = pd.to_numeric(df_f[c_rend_hr], errors='coerce').fillna(0)
        meta_vals = pd.to_numeric(df_f[c_meta_min], errors='coerce').fillna(0)
        
        # Evitar división por cero
        df_f['Cumplimiento'] = (rend_vals / meta_vals.replace(0, np.nan)) * 100
        df_f['Cumplimiento'] = df_f['Cumplimiento'].fillna(0)
    conditions = [(df_f['Cumplimiento'] >= 100), (df_f['Cumplimiento'] >= 85), (df_f['Cumplimiento'] < 85)]
    df_f['Clasificacion_Calc'] = np.select(conditions, ['AR', 'MR', 'BR'], default='BR')

    # LÓGICA FINANCIERA (DIRECTA)
    # Ya no se cruza con export, se usa la columna Salario/Monto directa
    if not df_f.empty:
        # Si no hay columna Salario detectada, usar 62 por defecto
        if c_salario:
            df_f['Pago_Dia_Calc'] = df_f[c_salario]
        else:
            df_f['Pago_Dia_Calc'] = 62.0 # Fallback Jornal Base
        
        # DataFrame para pestaña financiera (es el mismo filtrado)
        df_fin = df_f.copy()

    # PESTAÑA 1 (PRODUCTIVO)
    with tab1:
        if df_f.empty: st.error("No hay datos.")
        else:
            st.markdown(f"<h3 style='color:black;'>Reporte Productivo: {sel_labor} ({sel_variedad})</h3>", unsafe_allow_html=True)
            agg_cols = {c_rend_hr: 'mean', c_dni: 'nunique', c_rend_dia: 'sum'}
            if c_meta_min: agg_cols[c_meta_min] = 'mean'
            if c_meta_max: agg_cols[c_meta_max] = 'mean'
            # --- PARCHE DE COMPATIBILIDAD NUBE ---
            # Convertimos a la fuerza todo lo que parece número a número real.
            cols_numericas = ['Eficiencia', 'Calidad_Tabla', 'Score', 'Jabas', 'Horas_Trabajadas', 'Precio_Jaba']
            for col in cols_numericas:
                if col in df_f.columns:
         # errors='coerce' transforma textos basura en NaN (que sí se pueden promediar)
                    df_f[col] = pd.to_numeric(df_f[col], errors='coerce')
            df_trend = df_f.groupby(c_fecha).agg(agg_cols).reset_index().sort_values(c_fecha)
            df_clima = obtener_clima_ica(df_trend[c_fecha].min(), df_trend[c_fecha].max())
            if not df_clima.empty: df_trend = pd.merge(df_trend, df_clima, left_on=c_fecha, right_on='Fecha', how='left')

            fig_main = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.5, 0.25, 0.25], specs=[[{"secondary_y": True}], [{"secondary_y": False}], [{"secondary_y": False}]], subplot_titles=("Prod. Real y Rendimiento", "Dotación Operarios", "Clima"))
            fig_main.add_trace(go.Scatter(x=df_trend[c_fecha], y=df_trend[c_rend_hr], name='Rend/Hr', line=dict(color='#2E7D32', width=3)), row=1, col=1, secondary_y=False)
            if c_meta_min: fig_main.add_trace(go.Scatter(x=df_trend[c_fecha], y=df_trend[c_meta_min], name='Meta Min', line=dict(color='#D32F2F', dash='dot')), row=1, col=1, secondary_y=False)
            if c_meta_max and c_meta_max in df_trend.columns: fig_main.add_trace(go.Scatter(x=df_trend[c_fecha], y=df_trend[c_meta_max], name='Meta Max', line=dict(color='#FFD700', dash='dot')), row=1, col=1, secondary_y=False)
            fig_main.add_trace(go.Scatter(x=df_trend[c_fecha], y=df_trend[c_rend_dia], name='Prod. Total', line=dict(color='#1565C0', width=2, dash='solid')), row=1, col=1, secondary_y=True)
            fig_main.add_trace(go.Bar(x=df_trend[c_fecha], y=df_trend[c_dni], name='Operarios', marker_color='#1976D2'), row=2, col=1)
            if 'Temp_Max_Ica' in df_trend.columns:
                t_min, t_max = df_trend['Temp_Max_Ica'].min(), df_trend['Temp_Max_Ica'].max()
                fig_main.add_trace(go.Scatter(x=df_trend[c_fecha], y=df_trend['Temp_Max_Ica'], name='Temp Max', line=dict(color='#F57C00', width=2), fill='none'), row=3, col=1)
                fig_main.add_hline(y=30, line_dash="dot", line_color="red", row=3, col=1)
                fig_main.update_yaxes(range=[t_min-0.5, t_max+0.5], row=3, col=1)
            fig_main.update_layout(height=700, template="plotly_white", hovermode="x unified", margin=dict(t=30, b=10))
            fig_main.update_annotations(font=dict(color="black")); st.plotly_chart(fig_main, use_container_width=True)

            grp = df_f.groupby(c_lote)
            df_lotes = grp.agg(Produccion_Total=(c_rend_dia, 'sum'), Operarios_Unicos=(c_dni, 'nunique'), Cumplimiento_Meta=('Cumplimiento', 'mean')).reset_index()
            k1, k2, k3, k4 = st.columns(4)
            with k1: mostrar_kpi("Producción Total", f"{df_lotes['Produccion_Total'].sum():,.0f}", color_borde="#039BE5")
            with k2: mostrar_kpi("Operarios Únicos", f"{df_f[c_dni].nunique()}", color_borde="#8E24AA")
            cumpl = df_lotes['Cumplimiento_Meta'].mean()
            with k3: mostrar_kpi("Cumplimiento Global", f"{cumpl:.1f}%", delta="OK" if cumpl >= 100 else "-BAJO", color_borde="#43A047" if cumpl >= 100 else "#E53935")
            temp_txt = f"{df_trend['Temp_Max_Ica'].max():.1f}°C" if 'Temp_Max_Ica' in df_trend.columns else "N/A"
            with k4: mostrar_kpi("Pico Temperatura", temp_txt, color_borde="#FB8C00")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📊 Cumplimiento por Lote")
                colores_bar = ['#E53935' if x < 100 else '#43A047' for x in df_lotes['Cumplimiento_Meta']]
                fig_bar = go.Figure(go.Bar(x=df_lotes[c_lote], y=df_lotes['Cumplimiento_Meta'], marker_color=colores_bar))
                fig_bar.add_hline(y=100, line_dash="dash", line_color="black", annotation_text="Meta")
                fig_bar.update_layout(template="plotly_white", height=350); st.plotly_chart(fig_bar, use_container_width=True)
            with c2:
                st.subheader("🌓 Comparativa Turnos")
                if c_turno and df_f[c_turno].nunique() > 1:
                    df_turn = df_f.groupby(c_turno)[c_rend_hr].mean().reset_index()
                    fig_turn = px.bar(df_turn, x=c_turno, y=c_rend_hr, color=c_turno, title="Rendimiento Medio", color_discrete_sequence=['#FFB300', '#3949AB'])
                    fig_turn.update_layout(template="plotly_white", height=350); st.plotly_chart(fig_turn, use_container_width=True)
                else: st.info("Data de turnos no disponible.")
            
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("🔥 Mapa de Calor Lotes")
                fig_tree = px.treemap(df_lotes, path=[c_lote], values='Produccion_Total', color='Cumplimiento_Meta', color_continuous_scale='RdYlGn', color_continuous_midpoint=100)
                fig_tree.update_layout(template="plotly_white"); st.plotly_chart(fig_tree, use_container_width=True)
            with c4:
                st.subheader("📉 Pareto")
                df_pareto = df_lotes.sort_values('Produccion_Total', ascending=False)
                df_pareto['Acum'] = df_pareto['Produccion_Total'].cumsum()
                df_pareto['Porcentaje_Acum'] = 100 * df_pareto['Acum'] / df_pareto['Produccion_Total'].sum()
                fig_par = make_subplots(specs=[[{"secondary_y": True}]])
                fig_par.add_trace(go.Bar(x=df_pareto[c_lote], y=df_pareto['Produccion_Total'], marker_color='#1976D2', name='Prod'), secondary_y=False)
                fig_par.add_trace(go.Scatter(x=df_pareto[c_lote], y=df_pareto['Porcentaje_Acum'], marker_color='#D32F2F', name='%'), secondary_y=True)
                fig_par.update_xaxes(type='category'); fig_par.update_layout(template="plotly_white"); st.plotly_chart(fig_par, use_container_width=True)

            st.markdown("---")
            col_disp, col_ev = st.columns(2)
            with col_disp:
                st.subheader("🔍 Eficiencia de Dotación")
                fig_scat = px.scatter(df_lotes, x='Operarios_Unicos', y='Produccion_Total', size='Cumplimiento_Meta', color='Cumplimiento_Meta', color_continuous_scale='RdYlGn', hover_name=c_lote, text=c_lote)
                fig_scat.update_traces(textposition='top center'); fig_scat.update_layout(template="plotly_white", height=400); st.plotly_chart(fig_scat, use_container_width=True)
            with col_ev:
                st.subheader("📊 Evolución de Calidad")
                df_ev = df_f.groupby([c_fecha, 'Clasificacion_Calc']).size().reset_index(name='Conteo')
                df_totals = df_f.groupby(c_fecha).size().reset_index(name='Total')
                df_ev = pd.merge(df_ev, df_totals, on=c_fecha)
                df_ev['Pct'] = (df_ev['Conteo'] / df_ev['Total']) * 100
                fig_ev = px.area(df_ev, x=c_fecha, y='Pct', color='Clasificacion_Calc', color_discrete_map={'AR': '#43A047', 'MR': '#FFB300', 'BR': '#E53935'})
                fig_ev.update_layout(template="plotly_white", yaxis_title="% Personal", height=400); st.plotly_chart(fig_ev, use_container_width=True)

            st.markdown("---"); st.subheader("📅 Patrones de Asistencia Semanal")
            df_f['Dia_Semana'] = df_f[c_fecha].dt.day_name(); dias_map = {0:'Lunes',1:'Martes',2:'Miércoles',3:'Jueves',4:'Viernes',5:'Sábado',6:'Domingo'}
            df_f['Dia_Num'] = df_f[c_fecha].dt.dayofweek; df_f['Dia_Nom'] = df_f['Dia_Num'].map(dias_map)
            df_patron = df_f.groupby(['Dia_Nom', 'Clasificacion_Calc']).size().reset_index(name='Cant')
            df_patron_total = df_f.groupby('Dia_Nom').size().reset_index(name='Total')
            df_patron = pd.merge(df_patron, df_patron_total, on='Dia_Nom')
            df_patron['Pct'] = (df_patron['Cant'] / df_patron['Total']) * 100
            dias_orden = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
            fig_hm = px.density_heatmap(df_patron, x='Dia_Nom', y='Clasificacion_Calc', z='Pct', title="Concentración (%) por Día", color_continuous_scale='RdYlGn', category_orders={"Dia_Nom": dias_orden, "Clasificacion_Calc": ["BR", "MR", "AR"]}, text_auto='.0f')
            fig_hm.update_layout(template="plotly_white", height=400); st.plotly_chart(fig_hm, use_container_width=True)

    # PESTAÑA 2 (FINANCIERA)
    with tab2:
        if df_fin.empty: st.warning("No hay datos financieros disponibles (Columna Salario no detectada o vacía).")
        else:
            st.markdown(f"<h3 style='color:black;'>Análisis de Costos y Pagos: {sel_labor} ({sel_variedad})</h3>", unsafe_allow_html=True)
            
            gasto_total = df_fin['Pago_Dia_Calc'].sum(); pago_promedio = df_fin['Pago_Dia_Calc'].mean()
            max_pago = df_fin['Pago_Dia_Calc'].max()
            
            f1, f2, f3 = st.columns(3)
            with f1: mostrar_kpi("Gasto Total Planilla", f"S/ {gasto_total:,.0f}", color_borde="#FF9800")
            with f2: mostrar_kpi("Pago Diario Promedio", f"S/ {pago_promedio:.2f}", color_borde="#009688")
            with f3: mostrar_kpi("Máximo Pago Reg.", f"S/ {max_pago:.2f}", color_borde="#F44336")
            
            st.markdown("---")

            # 1. GRÁFICO DISPERSIÓN POR LOTE (Financiera)
            st.subheader("🚨 Eficiencia Financiera por Lote")
            
            df_fin_lote = df_fin.groupby(c_lote).agg({
                'Pago_Dia_Calc': 'sum', 
                c_rend_dia: 'sum', 
                c_dni: 'nunique'
            }).reset_index()
            
            df_fin_lote['Costo_Unitario'] = df_fin_lote['Pago_Dia_Calc'] / df_fin_lote[c_rend_dia]

            fig_bubble_lote = px.scatter(
                df_fin_lote, 
                x=c_rend_dia, 
                y='Pago_Dia_Calc',
                size='Costo_Unitario', 
                color='Costo_Unitario',
                hover_name=c_lote,
                text=c_lote,
                color_continuous_scale='RdYlGn_r',
                title="Gasto Total vs Producción Total (Tamaño = Costo Unitario)"
            )
            fig_bubble_lote.update_traces(textposition='top center')
            fig_bubble_lote.update_layout(template="plotly_white", height=500, xaxis_title="Producción Total (Unidades)", yaxis_title="Gasto Planilla Total (S/)")
            st.plotly_chart(fig_bubble_lote, use_container_width=True)

            # 2. COMPARATIVA COSTO PROMEDIO DIARIO (AR vs BR)
            st.subheader("💸 Costo Promedio Diario por Clasificación")
            
            # --- FILTRO POR TURNO ---
            df_fin_costo = df_fin.copy()
            if c_turno and c_turno in df_fin.columns:
                turnos_disponibles = ['(TODOS)'] + sorted(df_fin[c_turno].dropna().unique().tolist())
                sel_turno_fin = st.selectbox("Filtrar por Turno (Gráfico de Costos):", turnos_disponibles, index=0)
                if sel_turno_fin != '(TODOS)':
                    df_fin_costo = df_fin[df_fin[c_turno] == sel_turno_fin]
            
            df_costo_clasif = df_fin_costo.groupby('Clasificacion_Calc')['Pago_Dia_Calc'].mean().reset_index()
            
            fig_bar_costo = px.bar(
                df_costo_clasif, 
                x='Clasificacion_Calc', 
                y='Pago_Dia_Calc',
                color='Clasificacion_Calc',
                color_discrete_map={'AR': '#43A047', 'MR': '#FFB300', 'BR': '#E53935'},
                title=f"Pago Promedio Diario ({sel_turno_fin if 'sel_turno_fin' in locals() else 'General'}) (S/)",
                text_auto='.1f'
            )
            fig_bar_costo.update_layout(template="plotly_white", height=400, yaxis_title="Pago Promedio (S/)")
            st.plotly_chart(fig_bar_costo, use_container_width=True)

            # 3. TENDENCIA DE COSTOS
            st.subheader("📉 Evolución del Gasto de Planilla")
            df_fin_trend = df_fin.groupby(c_fecha).agg({
                'Pago_Dia_Calc': 'sum',
                c_rend_dia: 'sum'
            }).reset_index().sort_values(c_fecha)

            fig_cost = make_subplots(specs=[[{"secondary_y": True}]])
            fig_cost.add_trace(go.Bar(x=df_fin_trend[c_fecha], y=df_fin_trend['Pago_Dia_Calc'], name='Gasto Total (S/)', marker_color='#FFB74D'), secondary_y=False)
            fig_cost.add_trace(go.Scatter(x=df_fin_trend[c_fecha], y=df_fin_trend[c_rend_dia], name='Producción Total', line=dict(color='#1565C0', width=2)), secondary_y=True)
            fig_cost.update_yaxes(title_text="Soles (S/)", secondary_y=False)
            fig_cost.update_yaxes(title_text="Unidades", secondary_y=True)
            fig_cost.update_layout(template="plotly_white", height=450, title="Gasto Diario vs Producción")
            st.plotly_chart(fig_cost, use_container_width=True)

            # 4. TABLA DE DESVIACIONES
            st.subheader("📋 Top Lotes con Mayor Costo Unitario")
            df_fin_lote_sorted = df_fin_lote.sort_values('Costo_Unitario', ascending=False).head(10)
            st.dataframe(df_fin_lote_sorted.style.format({
                'Pago_Dia_Calc': 'S/ {:,.2f}',
                c_rend_dia: '{:,.0f}',
                'Costo_Unitario': 'S/ {:.4f}'
            }).background_gradient(subset=['Costo_Unitario'], cmap='Reds'), use_container_width=True)

    # ==============================================================================
    # TAB 3: CRUCE CALIDAD (MÓDULO MEJORADO CON COLORIMETRÍA DINÁMICA)
    # ==============================================================================
    with tab3:
        st.header("🏆 Matriz de Desempeño: Calidad vs Productividad")
        
        # --- INICIALIZAR SESSION STATE PARA CACHÉ DE FILTROS MENORES ---
        if 'tab3_cache' not in st.session_state:
            st.session_state.tab3_cache = {
                'umbral_rojo': 0.70,
                'umbral_ambar': 0.90,
                'vista_tabla': 'Asistente',
                'filtro_asist_evol': '(TODOS)',
                'filtro_lote': '(TODOS)'
            }
        
        if df_calidad.empty or sel_semana_cruce is None:
            st.error("❌ No se encontraron datos de calidad. Verifica que exista un archivo con 'calidad' en el nombre.")
        else:
            # --- CONTROLES DE COLORIMETRÍA DINÁMICA ---
            with st.expander("🎨 Configuración de Colorimetría (Umbrales)", expanded=False):
                col_umb1, col_umb2, col_umb3 = st.columns(3)
                with col_umb1:
                    umbral_rojo = st.number_input(
                        "🔴 Umbral ROJO (menor que):", 
                        min_value=0.0, max_value=1.0, 
                        value=st.session_state.tab3_cache['umbral_rojo'], 
                        step=0.05, format="%.2f",
                        help="Valores menores a este umbral se muestran en ROJO"
                    )
                    st.session_state.tab3_cache['umbral_rojo'] = umbral_rojo
                with col_umb2:
                    umbral_ambar = st.number_input(
                        "🟡 Umbral ÁMBAR (menor que):", 
                        min_value=0.0, max_value=1.5, 
                        value=st.session_state.tab3_cache['umbral_ambar'], 
                        step=0.05, format="%.2f",
                        help="Valores >= ROJO y < ÁMBAR se muestran en AMARILLO"
                    )
                    st.session_state.tab3_cache['umbral_ambar'] = umbral_ambar
                with col_umb3:
                    st.markdown(f"""
                    **🟢 VERDE**: >= {umbral_ambar:.2f}  
                    **🟡 ÁMBAR**: >= {umbral_rojo:.2f} y < {umbral_ambar:.2f}  
                    **🔴 ROJO**: < {umbral_rojo:.2f}
                    """)
            
            # --- USAR FUNCIONES CACHEADAS PARA EVITAR RECÁLCULO ---
            # Para el cruce, ignoramos el filtro de labor del sidebar para centrarnos en 'COSECHA'
            # que es el labor que tiene data de calidad, tal como funcionaba originalmente.
            
            # Validación de rango de fechas (evita IndexError si el usuario solo selecciona una fecha)
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                mask_prod_cruce = (df[c_fecha].dt.date >= date_range[0]) & (df[c_fecha].dt.date <= date_range[1])
            else:
                mask_prod_cruce = (df[c_fecha].dt.date >= date_range[0])
                
            if sel_variedad != '(TODAS)' and c_variedad:
                mask_prod_cruce = mask_prod_cruce & (df[c_variedad].astype(str) == sel_variedad)
            
            df_f_cruce = df[mask_prod_cruce].copy()
            
            # Intentar filtrar cosecha en producción para el cruce de forma flexible
            if c_labor:
                labores_en_data = df_f_cruce[c_labor].astype(str).unique()
                # Buscamos 'COSECHA' o 'LIMPIEZA' para capturar 'COSECHA Y LIMPIEZA DE RACIMOS'
                cosecha_names = [l for l in labores_en_data if any(x in str(l).upper() for x in ['COSECHA', 'LIMPIEZA'])]
                if cosecha_names:
                    df_f_cruce = df_f_cruce[df_f_cruce[c_labor].isin(cosecha_names)]
            
            # Asegurar que las columnas sean numéricas para evitar TypeError
            for col in [c_rend_hr, c_meta_min]:
                if col and col in df_f_cruce.columns:
                    df_f_cruce[col] = pd.to_numeric(df_f_cruce[col], errors='coerce').fillna(0)
            
            df_prod_cruce = preparar_produccion_cruce(df_f_cruce, c_fecha, c_lote, c_rend_hr, c_meta_min)
            merged, df_p_sem, df_q_sem = calcular_merged_data(df_prod_cruce, df_calidad, sel_semana_cruce, ratio_calidad)
            
            st.caption(f"📅 Analizando Semana {sel_semana_cruce} | Producción: {len(df_p_sem)} registros | Calidad: {len(df_q_sem)} registros")
            
            if df_p_sem.empty or df_q_sem.empty:
                st.warning(f"⚠️ No hay datos suficientes para la Semana {sel_semana_cruce}.")
            elif merged.empty:
                st.error("❌ No se encontraron coincidencias entre Producción y Calidad (Lote + Fecha).")
                st.info("💡 Sugerencia: Verifica que los lotes tengan el mismo formato en ambas hojas y que existan registros para la misma fecha.")
            else:
                # --- 🛑 PEGAR ESTE BLOQUE AQUÍ (LÍNEA 749) ---
                # FORZAR CONVERSIÓN A NÚMEROS (Soluciona error agg function failed)
                # Convierte cualquier texto basura o guiones en NaN para que .mean() funcione
                cols_criticas = ['Eficiencia', 'Calidad_Calc', 'Score', 'Jabas', 'Desviacion_Total']
                for col in cols_criticas:
                    if col in merged.columns:
                        merged[col] = pd.to_numeric(merged[col], errors='coerce')
                # -----------------------------------------------------------
                # --- KPIs (calculados desde merged cacheado) ---
                st.markdown("""<style>div[data-testid="stMetric"] {background-color: #f0f2f6; border: 1px solid #e0e0e0; padding: 10px; border-radius: 5px;}</style>""", unsafe_allow_html=True)
                
                col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                col_kpi1.metric("Rendimiento Promedio", f"{merged['Eficiencia'].mean():.2%}")
                col_kpi2.metric("Calidad Promedio", f"{merged['Calidad_Calc'].mean():.2%}")
                col_kpi3.metric("Lotes Cruzados", merged['Lote_Cruce'].nunique())
                col_kpi4.metric("Eficiencia Global", f"{merged['Score'].mean():.2%}")
                
                st.caption(f"📊 Nota: Rendimiento = Rend.Real / Meta. Calidad = 1 - Desviación. Eficiencia = {ratio_calidad*100:.0f}% Calidad + {(1-ratio_calidad)*100:.0f}% Rendimiento")
                
                # --- FILA 1: GRÁFICOS (usando funciones cacheadas) ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 % Desviación Promedio por Asistente")
                    st.markdown("_Muestra qué asistentes tienen mayor tasa de error promedio._")
                    asist_stats = calcular_estadisticas_asistente(merged)
                    
                    if not asist_stats.empty:
                        c_asist = alt.Chart(asist_stats).mark_bar().encode(
                            x=alt.X('Asistente:N', sort='-y', title='Asistente'),
                            y=alt.Y('Desviacion_Pct:Q', title='Desviación Promedio (%)'),
                            color=alt.value('#FF6D00'),
                            tooltip=['Asistente', alt.Tooltip('Desviacion_Pct:Q', format='.1f', title='Desviación %')]
                        ).properties(height=300)
                        st.altair_chart(c_asist, use_container_width=True)
                
                with col2:
                    st.subheader("🎯 Correlación Rendimiento vs Calidad")
                    st.markdown("_Cada punto es un lote. Busca 'Lotes Estrella' en la esquina superior derecha._")
                    lote_corr = calcular_correlacion_lotes(merged)
                    
                    if not lote_corr.empty:
                        # Ajustar escala dinámicamente al máximo real de los datos
                        max_eficiencia = lote_corr['Eficiencia'].max()
                        x_max = max(max_eficiencia * 1.1, 1.5)  # Al menos 150% o 110% del máximo
                        
                        c = alt.Chart(lote_corr).mark_circle(size=80, stroke='black', strokeWidth=1).encode(
                            x=alt.X('Eficiencia:Q', title='Rendimiento', scale=alt.Scale(domain=[0, x_max])),
                            y=alt.Y('Calidad_Calc:Q', scale=alt.Scale(domain=[0.5, 1.0]), title='Calidad'),
                            color=alt.value('#2962FF'),
                            tooltip=['Lote_Cruce', alt.Tooltip('Eficiencia:Q', format='.1%', title='Rendimiento'), alt.Tooltip('Calidad_Calc:Q', format='.1%')]
                        ).properties(height=300)
                        st.altair_chart(c, use_container_width=True)
                
                # --- FILA 2: EVOLUCIÓN DE DEFECTOS CON FILTRO POR ASISTENTE ---
                st.markdown("---")
                st.subheader("📈 Evolución de Impacto por Tipo de Defecto")
                
                # Selector para filtrar por asistente o ver todos
                asist_evol_options = ['(TODOS)'] + sorted(merged['Asistente'].unique().tolist())
                col_evol1, col_evol2 = st.columns([1, 3])
                with col_evol1:
                    filtro_asist_evol = st.selectbox(
                        "🔍 Filtrar por Asistente:",
                        asist_evol_options,
                        index=asist_evol_options.index(st.session_state.tab3_cache['filtro_asist_evol']) if st.session_state.tab3_cache['filtro_asist_evol'] in asist_evol_options else 0,
                        key='filtro_asist_evol_select'
                    )
                    st.session_state.tab3_cache['filtro_asist_evol'] = filtro_asist_evol
                
                with col_evol2:
                    if filtro_asist_evol == '(TODOS)':
                        st.markdown("_¿Qué problemas están impactando más día a día? (Todos los asistentes)_")
                    else:
                        st.markdown(f"_Evolución de defectos para: **{filtro_asist_evol}**_")
                
                # Usar función cacheada para tendencia de defectos
                defects_trend = calcular_defects_trend(df_q_sem, filtro_asist_evol)
                
                if not defects_trend.empty:
                    chart_defects = alt.Chart(defects_trend).mark_area(opacity=0.6).encode(
                        x=alt.X('Fecha_Cruce:T', axis=alt.Axis(format='%Y-%m-%d', title='Fecha')),
                        y=alt.Y('Desv_Cruce:Q', title='% Desviación'),
                        color=alt.Color('Defecto_Cruce:N', legend=alt.Legend(title="Defecto")),
                        tooltip=['Fecha_Cruce', 'Defecto_Cruce', alt.Tooltip('Desv_Cruce:Q', format='.1f')]
                    ).properties(height=300)
                    st.altair_chart(chart_defects, use_container_width=True)
                else:
                    st.info("No se encontraron datos detallados de defectos.")
                
                # --- FILA 3: TOP/BOTTOM LOTES (% con 1 decimal) ---
                st.markdown("---")
                st.subheader("🏆 Ranking de Lotes: Rendimiento (Barras) vs Calidad (Línea)")
                st.markdown("Barras (Rendimiento) // Lineas de Puntos Amarillos (Calidad)")
                
                # Usar función cacheada para ranking
                top_5_eff, bottom_5_eff = calcular_ranking_lotes(merged)
                
                def create_combo_chart(df_chart, title_text, bar_color, sort_order):
                    base = alt.Chart(df_chart).encode(
                        x=alt.X('Lote_Cruce:N', sort=alt.EncodingSortField(field="Eficiencia", order=sort_order), title='Lote')
                    )
                    bars = base.mark_bar(color=bar_color).encode(
                        y=alt.Y('Eficiencia:Q', title='Rendimiento')
                    )
                    line = base.mark_line(color='blue', strokeWidth=2).encode(
                        y=alt.Y('Calidad_Calc:Q', title='Calidad', scale=alt.Scale(domain=[0.8, 1.05]))
                    )
                    points = base.mark_circle(size=100, color='yellow', stroke='black', strokeWidth=1).encode(
                        y=alt.Y('Calidad_Calc:Q'),
                        tooltip=['Lote_Cruce', 'Eficiencia', alt.Tooltip('Calidad_Calc', format='.2%')]
                    )
                    return alt.layer(bars, line + points).resolve_scale(y='independent').properties(title=title_text, height=250)
                
                col_dev1, col_dev2 = st.columns(2)
                with col_dev1:
                    st.altair_chart(create_combo_chart(top_5_eff, "🏆 Top 5 Rendimiento", '#4CAF50', "descending"), use_container_width=True)
                with col_dev2:
                    st.altair_chart(create_combo_chart(bottom_5_eff, "⚠️ Bottom 5 Rendimiento", '#F44336', "ascending"), use_container_width=True)
                
                # --- EXPLORADOR DETALLADO CON VISTA ASISTENTE/LOTE ---
                st.markdown("---")
                st.header("🔍 Explorador Detallado")
                
                # --- SELECTOR VISTA + FILTRO LOTE ---
                col_vista1, col_vista2 = st.columns(2)
                with col_vista1:
                    vista_tabla = st.radio(
                        "📋 Ver desglose por:",
                        ['Asistente', 'Lote'],
                        horizontal=True,
                        index=0 if st.session_state.tab3_cache['vista_tabla'] == 'Asistente' else 1
                    )
                    st.session_state.tab3_cache['vista_tabla'] = vista_tabla
                
                with col_vista2:
                    lotes_disponibles = ['(TODOS)'] + sorted(merged['Lote_Cruce'].unique().tolist())
                    filtro_lote = st.selectbox(
                        "🏷️ Filtrar por Lote:",
                        lotes_disponibles,
                        index=lotes_disponibles.index(st.session_state.tab3_cache['filtro_lote']) if st.session_state.tab3_cache['filtro_lote'] in lotes_disponibles else 0
                    )
                    st.session_state.tab3_cache['filtro_lote'] = filtro_lote
                
                # Filtrado de merged (ligero, solo aplica filtro)
                if filtro_lote != '(TODOS)':
                    merged_filtrado = merged[merged['Lote_Cruce'] == filtro_lote].copy()
                else:
                    merged_filtrado = merged.copy()
                
                # Función de estilo con umbrales dinámicos (solo UI, no recalcula datos)
                def style_score_dinamico(val):
                    if pd.isna(val) or val == "": return ""
                    try:
                        v = float(val)
                        if v < umbral_rojo: return 'background-color: #FFCDD2; color: black;'
                        elif v < umbral_ambar: return 'background-color: #FFF9C4; color: black;'
                        return 'background-color: #C8E6C9; color: black;'
                    except: return ""
                
                tab_score, tab_metrics = st.tabs(["🏆 Eficiencia (Score)", "📊 Desglose Rendimiento/Calidad"])
            ### aquí tambien    
                with tab_score:
                    index_col = 'Asistente' if vista_tabla == 'Asistente' else 'Lote_Cruce'
                    st.write(f"**Tabla de Puntaje Global (Eficiencia) por {vista_tabla}** | Ponderación: {ratio_calidad*100:.0f}% Calidad + {(1-ratio_calidad)*100:.0f}% Rendimiento")
                    
                    # 1. Calculamos la tabla
                    pivot_score_raw = calcular_pivot_score(merged, index_col, filtro_lote, ratio_calidad)
                    
                    if not pivot_score_raw.empty:
                        pivot_score = pivot_score_raw.copy()
                        
                        # Formatear columnas de fecha
                        new_cols = [c.strftime('%d-%m') if hasattr(c, 'strftime') else str(c) for c in pivot_score.columns]
                        pivot_score.columns = new_cols
                        
                        # 2. Variable con promedios
                        promedios_col = pivot_score.mean(axis=0)
                        promedios_col.name = 'PROMEDIO'
                        pivot_score_con_prom = pd.concat([pivot_score, promedios_col.to_frame().T])
                        
                        # ⚠️ IMPORTANTE: ELIMINAMOS .fillna('') AQUÍ
                        # pivot_score_con_prom = pivot_score_con_prom.fillna('') 
                        
                        # 3. Mostramos la tabla usando na_rep para los vacíos
                        st.dataframe(
                            pivot_score_con_prom.style
                            .format("{:.1%}", na_rep="")      # <--- AQUÍ está el arreglo: na_rep="" pone vacío visualmente sin romper el número
                            .applymap(style_score_dinamico),  # Aplica colores
                            use_container_width=True
                        )
                    else:
                        st.info("No hay datos para calcular la Eficiencia.") 

            ## aquí       

                with tab_metrics:
                    index_col = 'Asistente' if vista_tabla == 'Asistente' else 'Lote_Cruce'
                    st.write(f"**Desglose Diario de Rendimiento y Calidad por {vista_tabla} (con Iconos)**")
                    st.caption("✅ >= 1.0 (Rendimiento) / 0.95 (Calidad) | 🚩 por debajo.")
                    
                    # Usar función cacheada para pivot de métricas
                    pivot_gen_raw, fechas = calcular_pivot_metricas(merged, index_col, filtro_lote)
                    
                    if not pivot_gen_raw.empty and fechas:
                        # Hacer copia para no modificar objeto cacheado
                        pivot_gen = pivot_gen_raw.copy()
                        frames_gen = []
                        
                        for f in fechas:
                            f_str = f.strftime('%d-%m')
                            try:
                                eff_day = pivot_gen['Eficiencia'][f]
                                qual_day = pivot_gen['Calidad_Calc'][f]
                                eff_fmt = eff_day.apply(lambda x: format_with_icon(x, is_efficiency=True) if pd.notna(x) else "-")
                                qual_fmt = qual_day.apply(lambda x: format_with_icon(x, is_quality=True) if pd.notna(x) else "-")
                                frames_gen.append(eff_fmt.rename(f"{f_str} Rend"))
                                frames_gen.append(qual_fmt.rename(f"{f_str} Cal"))
                            except KeyError: continue
                        
                        if frames_gen:
                            df_general_view = pd.concat(frames_gen, axis=1).fillna("-")
                            # Agregar columna promedio
                            df_general_view['PROM Rend'] = merged_filtrado.groupby(index_col)['Eficiencia'].mean().apply(lambda x: format_with_icon(x, is_efficiency=True) if pd.notna(x) else "-")
                            df_general_view['PROM Cal'] = merged_filtrado.groupby(index_col)['Calidad_Calc'].mean().apply(lambda x: format_with_icon(x, is_quality=True) if pd.notna(x) else "-")
                            st.dataframe(df_general_view.fillna("-"), use_container_width=True)
                
                # --- SELECTOR DE ASISTENTE/LOTE PARA DETALLE ---
                st.divider()
                
                if vista_tabla == 'Asistente':
                    asistentes_list = sorted(merged_filtrado['Asistente'].unique())
                    sel_detalle = st.selectbox("👤 Seleccionar Asistente para ver detalle:", asistentes_list)
                    subset_detalle = merged_filtrado[merged_filtrado['Asistente'] == sel_detalle].copy() if sel_detalle else None
                    titulo_detalle = f"Asistente {sel_detalle}"
                else:
                    lotes_list = sorted(merged_filtrado['Lote_Cruce'].unique())
                    sel_detalle = st.selectbox("🏷️ Seleccionar Lote para ver detalle:", lotes_list)
                    subset_detalle = merged_filtrado[merged_filtrado['Lote_Cruce'] == sel_detalle].copy() if sel_detalle else None
                    titulo_detalle = f"Lote {sel_detalle}"
                
                if subset_detalle is not None and not subset_detalle.empty:
                    if vista_tabla == 'Asistente':
                        detail_table = subset_detalle.groupby(['Fecha_Cruce', 'Lote_Cruce', 'Variedad']).agg({
                            'Eficiencia': 'mean', 'Calidad_Tabla': 'mean', 'Score': 'mean', 'Jabas': 'sum'
                        }).reset_index()
                    else:
                        detail_table = subset_detalle.groupby(['Fecha_Cruce', 'Asistente', 'Variedad']).agg({
                            'Eficiencia': 'mean', 'Calidad_Tabla': 'mean', 'Score': 'mean', 'Jabas': 'sum'
                        }).reset_index()
                    
                    detail_table['Fecha'] = detail_table['Fecha_Cruce'].dt.strftime('%Y-%m-%d')
                    
                    st.write(f"**📋 Historial de Trabajos - {titulo_detalle}**")
                    st.caption("Leyenda: ✅ Meta cumplida / Calidad óptima. 🚩 Por debajo.")
                    
                    cols_mostrar = ['Fecha', 'Lote_Cruce' if vista_tabla == 'Asistente' else 'Asistente', 'Variedad', 'Jabas', 'Eficiencia', 'Calidad_Tabla', 'Score']
                    
                    # Agregar fila de PROMEDIO
                    prom_row = {
                        'Fecha': 'PROMEDIO',
                        'Lote_Cruce' if vista_tabla == 'Asistente' else 'Asistente': '-',
                        'Variedad': '-',
                        'Jabas': detail_table['Jabas'].mean(),
                        'Eficiencia': detail_table['Eficiencia'].mean(),
                        'Calidad_Tabla': detail_table['Calidad_Tabla'].mean(),
                        'Score': detail_table['Score'].mean()
                    }
                    detail_table_con_prom = pd.concat([detail_table[cols_mostrar], pd.DataFrame([prom_row])], ignore_index=True)
                    
                    st.dataframe(
                        detail_table_con_prom.style.format({
                            'Jabas': '{:,.0f}',
                            'Eficiencia': '{:.1%}',
                            'Calidad_Tabla': '{:.1%}',
                            'Score': '{:.2f}'
                        }).applymap(style_score_dinamico, subset=['Score']),
                        use_container_width=True,
                        hide_index=True
                    )

    # --- BOTÓN PDF GLOBAL ---
    st.markdown("---")
    if st.button("🖨️ Generar Reporte PDF Completo (Incluye Financiero)"):
        pivot_br = df_patron[df_patron['Clasificacion_Calc'] == 'BR']
        insight_asist = "Distribución uniforme."
        if not pivot_br.empty:
            peor_dia_row = pivot_br.loc[pivot_br['Pct'].idxmax()]
            insight_asist = f"ALERTA: El {peor_dia_row['Dia_Nom']} es crítico ({peor_dia_row['Pct']:.1f}% BR)."
        
        top_80 = df_pareto[df_pareto['Porcentaje_Acum'] <= 80]
        if top_80.empty: top_80 = df_pareto.head(3)
        lotes_80_str = ", ".join(top_80[c_lote].astype(str).tolist())
        tipo_rep = "ANÁLISIS DIARIO" if date_range[0] == date_range[1] else f"PERIODO: {date_range[0]} al {date_range[1]}"
        txt_concl = [
            f"ALCANCE: {tipo_rep} - {sel_variedad}",
            f"Producción Total: {df_lotes['Produccion_Total'].sum():,.0f} unidades.",
            f"1. PARETO (80/20): El 80% depende de {len(top_80)} lotes: {lotes_80_str}.",
            f"2. CUMPLIMIENTO: Promedio del {cumpl:.1f}%.",
            f"3. FINANCIERO: Gasto estimado S/ {gasto_total:,.0f} (Promedio S/ {pago_promedio:.1f}/día).",
        ]
        
        df_fin_lote_resumen = None
        if not df_fin.empty:
            df_fin_lote_resumen = df_fin_lote.rename(columns={c_lote: 'Lote_ID', 'Pago_Dia_Calc': 'Pago_Estimado_Total', c_rend_dia: 'Produccion_Total'})

        df_turn_pdf = df_f.groupby(c_turno)[c_rend_hr].mean().reset_index() if c_turno and df_f[c_turno].nunique() > 1 else None
        
        pdf_bytes = crear_pdf_completo(df_lotes, txt_concl, df_pareto, df_turn_pdf, df_lotes, df_ev, sel_labor, insight_asist, df_patron, df_trend, col_map, df_fin_lote_resumen)
        st.download_button("📥 Descargar PDF Inteligente", pdf_bytes, f"Reporte_{sel_labor}.pdf", "application/pdf")
        st.success("Reporte generado con Módulo Financiero.")

    with st.expander("🤖 Zona de Inteligencia Artificial & Machine Learning"):
        if st.button("📥 Generar Dataset Listo para IA (.csv)"):
            df_ai = generar_dataset_ia(df_f, c_fecha, c_lote, c_labor, c_rend_hr, c_dni, df_clima)
            csv = df_ai.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV Entrenamiento", csv, "dataset_agricola_ia.csv", "text/csv")

