# 📊 BI Productividad - El Pedregal S.A.

Dashboard interactivo de Business Intelligence para análisis de productividad y calidad en Fundo Yaurilla.

## 🚀 Características

- **Análisis Productivo**: Visualización de rendimiento, cumplimiento de metas, y eficiencia operativa
- **Análisis Financiero**: Seguimiento de costos, pagos y eficiencia financiera por lote
- **Cruce Calidad**: Correlación entre productividad y calidad con matrices dinámicas
- **Reportes PDF**: Generación automática de reportes técnicos completos
- **Integración con Google Sheets**: Carga de datos en tiempo real desde la nube

## 📋 Prerrequisitos

- Python 3.8 o superior
- Cuenta de Google con acceso a Google Sheets
- Credenciales de Google Cloud (Service Account)

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/eternal2026-cloud/productividad_calidad.git
cd productividad_calidad
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar credenciales de Google Sheets**

   a. Crear un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Habilitar Google Sheets API
   
   c. Crear una Service Account y descargar el archivo JSON de credenciales
   
   d. Compartir tus Google Sheets con el email de la Service Account (permiso de lectura)
   
   e. Crear el archivo `.streamlit/secrets.toml` con el siguiente contenido:

```toml
[gcp_service_account]
type = "service_account"
project_id = "tu-project-id"
private_key_id = "tu-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nTU_PRIVATE_KEY_AQUI\n-----END PRIVATE KEY-----\n"
client_email = "tu-service-account@project.iam.gserviceaccount.com"
client_id = "tu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/tu-service-account%40project.iam.gserviceaccount.com"

[google_sheets]
data_maestra_url = "https://docs.google.com/spreadsheets/d/1A_DslqrRZSIguP9OMaThS9zjl0vASRWe/edit?usp=drive_link&ouid=114520033838807346715&rtpof=true&sd=true"
calidad_url = "https://docs.google.com/spreadsheets/d/19g6bd0QnY_q0IMgISoa4L5bqVyZvRC8q/edit?usp=drive_link&ouid=114520033838807346715&rtpof=true&sd=true"
```

## ▶️ Ejecutar la aplicación

```bash
streamlit run pru.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📊 Configuración de Google Sheets

Los datos se obtienen de dos hojas de cálculo:

1. **Data_Maestra_Limpia**: Datos de productividad
   - URL: [Tu hoja de datos maestros](https://docs.google.com/spreadsheets/d/1A_DslqrRZSIguP9OMaThS9zjl0vASRWe/)

2. **Calidad**: Datos de control de calidad
   - URL: [Tu hoja de calidad](https://docs.google.com/spreadsheets/d/19g6bd0QnY_q0IMgISoa4L5bqVyZvRC8q/)

### Estructura esperada de las hojas

**Data_Maestra_Limpia** debe contener:
- Fecha
- DNI
- Operario
- Lote
- Labor
- Rendimiento
- Horas Totales
- Meta Min/Max
- Salario/Monto
- Variedad

**Calidad** debe contener:
- Fecha
- Lote
- Asistente
- Desviación Total
- Tipo de Defecto
- Variedad
- Cantidad de Jabas

## 🌐 Deploy en Streamlit Cloud

1. Sube tu código a GitHub:
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. Ve a [share.streamlit.io](https://share.streamlit.io)

3. Conecta tu repositorio de GitHub

4. En la configuración de Secrets, pega el contenido de tu `.streamlit/secrets.toml`

5. ¡Despliega!

## 📂 Estructura del Proyecto

```
productividad_calidad/
├── pru.py                 # Aplicación principal
├── requirements.txt       # Dependencias Python
├── .gitignore            # Archivos a ignorar en Git
├── README.md             # Este archivo
├── .streamlit/
│   ├── config.toml       # Configuración de Streamlit
│   └── secrets.toml      # Credenciales (NO subir a Git)
└── logo.png              # Logo (opcional)
```

## 🔒 Seguridad

⚠️ **IMPORTANTE**: Nunca subas el archivo `secrets.toml` a Git. Está incluido en `.gitignore` para proteger tus credenciales.

## 👤 Autor

**El Pedregal S.A.**  
Departamento de Productividad - Fundo Yaurilla

## 📝 Licencia

Uso interno - El Pedregal S.A.

---

Para soporte o preguntas, contacta al Departamento de TI.
