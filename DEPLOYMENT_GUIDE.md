# Guía de Deployment a GitHub

Este documento proporciona instrucciones paso a paso para subir el proyecto al repositorio de GitHub.

## Prerrequisitos

- Git instalado en tu sistema
- Cuenta de GitHub activa
- Repositorio `productividad_calidad` creado en GitHub (https://github.com/eternal2026-cloud/productividad_calidad)

## Configuración Inicial

### 1. Configurar Git (si es primera vez)

```bash
git config --global user.name "eternal2026-cloud"
git config --global user.email "tu-email@ejemplo.com"
```

### 2. Verificar archivos del proyecto

Asegúrate de tener estos archivos:
- ✅ `pru.py` - Aplicación principal
- ✅ `google_sheets_utils.py` - Módulo de Google Sheets
- ✅ `requirements.txt` - Dependencias
- ✅ `README.md` - Documentación
- ✅ `.gitignore` - Archivos a ignorar
- ✅ `.streamlit/config.toml` - Configuración de Streamlit
- ✅ `.streamlit/secrets.toml.example` - Ejemplo de credenciales
- ⚠️ `logo.png` (opcional) - Logo de la empresa

## Comandos para Deployment

### Opción A: Nuevo Repositorio Local

Si es la primera vez que subes el proyecto:

```bash
# 1. Navegar a la carpeta del proyecto
cd "c:\Users\Elsa\Downloads\Nueva carpeta (10)"

# 2. Inicializar repositorio Git
git init

# 3. Agregar todos los archivos
git add .

# 4. Verificar qué archivos se van a subir (secrets.toml NO debe aparecer)
git status

# 5. Crear el primer commit
git commit -m "Initial commit: BI Productividad El Pedregal con integración Google Sheets"

# 6. Conectar con GitHub
git remote add origin https://github.com/eternal2026-cloud/productividad_calidad.git

# 7. Renombrar rama principal a 'main'
git branch -M main

# 8. Subir los archivos a GitHub
git push -u origin main
```

### Opción B: Actualizar Repositorio Existente

Si el repositorio ya existe y quieres actualizarlo:

```bash
# 1. Navegar a la carpeta del proyecto
cd "c:\Users\Elsa\Downloads\Nueva carpeta (10)"

# 2. Agregar cambios
git add .

# 3. Crear commit
git commit -m "Feat: Integración con Google Sheets y mejoras en documentación"

# 4. Subir cambios
git push
```

## Verificación en GitHub

1. Ve a https://github.com/eternal2026-cloud/productividad_calidad
2. Verifica que todos los archivos estén presentes
3. **IMPORTANTE**: Verifica que `secrets.toml` NO esté en el repositorio (solo debe estar `secrets.toml.example`)
4. Verifica que el README.md se visualice correctamente

## Configurar Secrets en GitHub (opcional para GitHub Actions)

Si planeas usar GitHub Actions o similar:

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Agrega los secrets de Google Cloud si es necesario

## Deploy en Streamlit Cloud

Para que la aplicación funcione en la nube:

1. Ve a https://share.streamlit.io
2. Inicia sesión con GitHub
3. Click en "New app"
4. Selecciona el repositorio: `eternal2026-cloud/productividad_calidad`
5. Branch: `main`
6. Main file path: `pru.py`
7. En **Advanced settings** → **Secrets**, pega el contenido de tu `.streamlit/secrets.toml`:

```toml
[gcp_service_account]
type = "service_account"
project_id = "TU_PROJECT_ID"
private_key_id = "TU_PRIVATE_KEY_ID"
private_key = "TU_PRIVATE_KEY"
client_email = "TU_SERVICE_ACCOUNT@...iam.gserviceaccount.com"
client_id = "TU_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[google_sheets]
data_maestra_url = "https://docs.google.com/spreadsheets/d/1A_DslqrRZSIguP9OMaThS9zjl0vASRWe/edit..."
calidad_url = "https://docs.google.com/spreadsheets/d/19g6bd0QnY_q0IMgISoa4L5bqVyZvRC8q/edit..."
```

8. Click "Deploy!"

## Troubleshooting

### Error: "Permission denied (publickey)"

Necesitas configurar SSH o usar HTTPS con token:

```bash
# Usar HTTPS en lugar de SSH
git remote set-url origin https://github.com/eternal2026-cloud/productividad_calidad.git
```

### Error: "Repository not found"

Verifica que el repositorio exista y que tengas permisos:
- https://github.com/eternal2026-cloud/productividad_calidad

### Archivo secrets.toml aparece en Git

Si accidentalmente agregaste secrets.toml:

```bash
# Removerlo del índice de Git
git rm --cached .streamlit/secrets.toml
git commit -m "Remove secrets.toml from repository"
git push
```

## Próximos Pasos

1. ✅ Proyecto subido a GitHub
2. 📝 Compartir Google Sheets con la Service Account
3. 🚀 Desplegar en Streamlit Cloud
4. 🔧 Configurar secrets en Streamlit Cloud
5. ✨ Compartir URL de la aplicación con el equipo

## Comandos Útiles

```bash
# Ver estado del repositorio
git status

# Ver historial de commits
git log --oneline

# Ver archivos ignorados por .gitignore
git status --ignored

# Crear una rama nueva para desarrollo
git checkout -b desarrollo

# Volver a la rama principal
git checkout main
```

---

**🎉 ¡Listo!** Tu proyecto ahora está en GitHub y listo para ser compartido con el equipo.
