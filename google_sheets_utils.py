"""
Módulo de utilidades para cargar datos desde Google Sheets
Autor: El Pedregal S.A. - Departamento de BI
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re

@st.cache_resource
def get_gspread_client():
    """
    Crea y cachea el cliente de gspread usando las credenciales de Streamlit secrets.
    
    Returns:
        gspread.Client: Cliente autenticado de gspread
    """
    try:
        # Cargar credenciales desde secrets
        credentials_dict = dict(st.secrets["gcp_service_account"])
        
        # Scopes necesarios para Google Sheets
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error al autenticar con Google: {e}")
        return None

def extract_sheet_id(url):
    """
    Extrae el ID de la hoja de cálculo de una URL de Google Sheets.
    
    Args:
        url (str): URL completa de Google Sheets
        
    Returns:
        str: ID de la hoja de cálculo
    """
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

@st.cache_data(ttl=600, show_spinner="Cargando datos desde Google Sheets...")
def load_sheet_as_dataframe(_client, sheet_url, sheet_name=None):
    """
    Carga una hoja de Google Sheets como DataFrame de pandas.
    
    Args:
        _client: Cliente de gspread (prefijado con _ para no cachear)
        sheet_url (str): URL de Google Sheets
        sheet_name (str, optional): Nombre de la pestaña específica. Si es None, usa la primera.
        
    Returns:
        pd.DataFrame: Datos de la hoja
    """
    try:
        if _client is None:
            st.error("Cliente de Google Sheets no disponible")
            return pd.DataFrame()
        
        # Extraer ID de la URL
        sheet_id = extract_sheet_id(sheet_url)
        if not sheet_id:
            st.error(f"No se pudo extraer el ID de la URL: {sheet_url}")
            return pd.DataFrame()
        
        # Abrir la hoja
        spreadsheet = _client.open_by_key(sheet_id)
        
        # Seleccionar pestaña
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.get_worksheet(0)  # Primera pestaña
        
        # Obtener todos los datos
        data = worksheet.get_all_records()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        return df
    
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ No se encontró la hoja de cálculo. Verifica que el ID sea correcto y que la Service Account tenga acceso.")
        return pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ No se encontró la pestaña '{sheet_name}'. Verifica el nombre.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

def load_data_maestra():
    """
    Carga la hoja de Data_Maestra_Limpia desde Google Sheets.
    
    Returns:
        pd.DataFrame: Datos de productividad
    """
    client = get_gspread_client()
    
    if client is None:
        st.warning("⚠️ Usando modo sin conexión. Configura las credenciales de Google Sheets.")
        return pd.DataFrame()
    
    try:
        url = st.secrets["google_sheets"]["data_maestra_url"]
        df = load_sheet_as_dataframe(client, url)
        
        if df.empty:
            st.warning("La hoja Data_Maestra_Limpia está vacía o no se pudo cargar.")
        
        return df
    except KeyError:
        st.error("❌ No se encontró 'data_maestra_url' en secrets. Verifica tu configuración.")
        return pd.DataFrame()

def load_calidad():
    """
    Carga la hoja de Calidad desde Google Sheets.
    
    Returns:
        pd.DataFrame: Datos de calidad
    """
    client = get_gspread_client()
    
    if client is None:
        st.warning("⚠️ Usando modo sin conexión. Configura las credenciales de Google Sheets.")
        return pd.DataFrame()
    
    try:
        url = st.secrets["google_sheets"]["calidad_url"]
        df = load_sheet_as_dataframe(client, url)
        
        if df.empty:
            st.warning("La hoja de Calidad está vacía o no se pudo cargar.")
        
        return df
    except KeyError:
        st.error("❌ No se encontró 'calidad_url' en secrets. Verifica tu configuración.")
        return pd.DataFrame()

# Función de compatibilidad para desarrollo local con archivos Excel
def load_data_with_fallback(use_google_sheets=True):
    """
    Carga datos con fallback: primero intenta Google Sheets, luego archivos locales.
    
    Args:
        use_google_sheets (bool): Si True, intenta cargar desde Google Sheets primero
        
    Returns:
        tuple: (df_maestra, df_calidad)
    """
    df_maestra = pd.DataFrame()
    df_calidad = pd.DataFrame()
    
    if use_google_sheets:
        df_maestra = load_data_maestra()
        df_calidad = load_calidad()
    
    # Fallback a archivos locales si Google Sheets falla
    if df_maestra.empty:
        try:
            st.warning("⚠️ Intentando cargar desde archivo local...")
            df_maestra = pd.read_excel("Data_Maestra_Limpia.xlsx")
            st.success("✅ Data Maestra cargada desde archivo local")
        except Exception as e:
            st.error(f"No se pudo cargar Data Maestra: {e}")
    
    if df_calidad.empty:
        try:
            # Buscar archivo de calidad
            import os
            import glob
            files = glob.glob("*calidad*.xlsx") + glob.glob("*calidad*.xls")
            if files:
                df_calidad = pd.read_excel(files[0])
                st.success(f"✅ Calidad cargada desde {files[0]}")
        except Exception as e:
            st.info(f"Calidad no disponible localmente: {e}")
    
    return df_maestra, df_calidad
