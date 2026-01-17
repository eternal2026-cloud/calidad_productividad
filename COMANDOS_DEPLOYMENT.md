# 🚀 COMANDOS DE DEPLOYMENT - EL PEDREGAL S.A.

## ⚠️ IMPORTANTE: Git no está instalado o configurado

Git no se detectó en tu sistema. Tienes dos opciones:

### Opción 1: Instalar Git (Recomendado)

1. **Descargar Git para Windows:**
   - Ve a: https://git-scm.com/download/win
   - Descarga e instala la versión más reciente
   - Durante la instalación, acepta las opciones por defecto

2. **Verificar instalación:**
   - Abre una nueva terminal PowerShell
   - Ejecuta: `git --version`
   - Deberías ver algo como: `git version 2.x.x`

3. **Ejecutar los comandos de deployment** (ver más abajo)

### Opción 2: Usar GitHub Desktop (Interfaz gráfica)

1. **Descargar GitHub Desktop:**
   - Ve a: https://desktop.github.com/
   - Descarga e instala

2. **Configurar el repositorio:**
   - Abre GitHub Desktop
   - File → Add Local Repository
   - Selecciona la carpeta: `c:\Users\Elsa\Downloads\Nueva carpeta (10)`
   - Publish repository → `eternal2026-cloud/productividad_calidad`

---

## 📋 COMANDOS DE DEPLOYMENT (después de instalar Git)

### Paso 1: Abrir PowerShell en la carpeta del proyecto

```powershell
cd "c:\Users\Elsa\Downloads\Nueva carpeta (10)"
```

### Paso 2: Inicializar repositorio Git

```powershell
git init
```

### Paso 3: Configurar usuario

```powershell
git config user.name "eternal2026-cloud"
git config user.email "eternal2026-cloud@users.noreply.github.com"
```

### Paso 4: Hacer commits organizados

**Commit 1: Configuración del proyecto**
```powershell
git add requirements.txt .gitignore .streamlit/config.toml .streamlit/secrets.toml.example
git commit -m "chore: configuración inicial del proyecto (requirements, gitignore, streamlit config)"
```

**Commit 2: Documentación**
```powershell
git add README.md DEPLOYMENT_GUIDE.md
git commit -m "docs: agregar documentación completa (README y guía de deployment)"
```

**Commit 3: Módulo de Google Sheets**
```powershell
git add google_sheets_utils.py
git commit -m "feat: módulo de integración con Google Sheets (carga de datos desde la nube)"
```

**Commit 4: Aplicación principal**
```powershell
git add pru.py
git commit -m "feat: integrar Google Sheets en dashboard BI Productividad (con fallback a Excel local)"
```

**Commit 5: Script de deployment**
```powershell
git add deploy_to_github.bat
git commit -m "chore: script de deployment automatizado para Windows"
```

### Paso 5: Conectar con GitHub y subir

```powershell
git remote add origin https://github.com/eternal2026-cloud/productividad_calidad.git
git branch -M main
git push -u origin main
```

**Si te pide autenticación:**
- Usuario: `eternal2026-cloud`
- Contraseña: Usa un **Personal Access Token** (no tu contraseña de GitHub)
  - Crear token en: https://github.com/settings/tokens
  - Permisos necesarios: `repo` (full control)

---

## 🔄 ALTERNATIVA: Un solo commit (más rápido)

Si prefieres hacer un solo commit con todo:

```powershell
cd "c:\Users\Elsa\Downloads\Nueva carpeta (10)"
git init
git config user.name "eternal2026-cloud"
git config user.email "eternal2026-cloud@users.noreply.github.com"
git add .
git commit -m "feat: Dashboard BI Productividad El Pedregal con integración Google Sheets"
git remote add origin https://github.com/eternal2026-cloud/productividad_calidad.git
git branch -M main
git push -u origin main
```

---

## ✅ Verificar que todo se subió correctamente

1. Ve a: https://github.com/eternal2026-cloud/productividad_calidad
2. Verifica que veas estos archivos:
   - ✅ pru.py
   - ✅ google_sheets_utils.py
   - ✅ requirements.txt
   - ✅ README.md
   - ✅ DEPLOYMENT_GUIDE.md
   - ✅ deploy_to_github.bat
   - ✅ .gitignore
   - ✅ .streamlit/config.toml
   - ✅ .streamlit/secrets.toml.example
   - ❌ .streamlit/secrets.toml (NO debe estar)

---

## 🛠️ Troubleshooting

### Error: "fatal: repository 'https://github.com/eternal2026-cloud/productividad_calidad.git' not found"

**Solución:** El repositorio no existe en GitHub. Créalo primero:
1. Ve a: https://github.com/new
2. Repository name: `productividad_calidad`
3. Owner: `eternal2026-cloud`
4. Public o Private (tu elección)
5. **NO** marques "Initialize with README"
6. Create repository
7. Ejecuta los comandos de nuevo

### Error: "fatal: refusing to merge unrelated histories"

**Solución:** Si el repositorio ya existe con contenido:
```powershell
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Error: "Support for password authentication was removed"

**Solución:** Necesitas un Personal Access Token:
1. Ve a: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Selecciona: `repo` (todos los checks)
4. Copia el token generado
5. Úsalo como contraseña cuando Git te lo pida

---

## 📝 Resumen de lo que se va a subir:

```
productividad_calidad/
├── pru.py (69 KB)                          ✅ Dashboard principal
├── google_sheets_utils.py (6 KB)          ✅ Integración Google Sheets
├── requirements.txt (243 bytes)            ✅ Dependencias
├── README.md (4.5 KB)                      ✅ Documentación
├── DEPLOYMENT_GUIDE.md (5.2 KB)           ✅ Guía de deployment
├── deploy_to_github.bat (1.4 KB)          ✅ Script automatización
├── .gitignore (521 bytes)                 ✅ Protección archivos
└── .streamlit/
    ├── config.toml                         ✅ Configuración Streamlit
    └── secrets.toml.example                ✅ Plantilla credenciales
```

**Total:** ~87 KB de código y documentación

---

**¿Necesitas ayuda?** Consulta el DEPLOYMENT_GUIDE.md para más detalles.

**🎉 ¡Éxito!** Una vez subido, tu dashboard estará listo para desplegarse en Streamlit Cloud.
