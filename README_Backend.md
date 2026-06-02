# 🌿 MASCATE — Backend

**Mesa Autónoma de SPA y Cannábica Techotiva**

Backend desarrollado en **Python** con **FastAPI**, base de datos local **SQLite** (`mascate.db`) gestionada con **SQLAlchemy**. Incluye datos de prueba (seeds) y autenticación configurada.

---

## ✅ Requisitos Previos

El computador donde se vaya a ejecutar debe tener instalado **Python 3.8 o superior**.

- Descárgalo desde: [https://python.org](https://python.org)
- ⚠️ **En Windows:** durante la instalación, marca la casilla **"Add Python to PATH"**.

---

## 🚀 Pasos para Ejecutar el Proyecto

Abre una terminal (Símbolo del sistema o PowerShell en Windows, Terminal en Mac/Linux) y sigue este orden:

### Paso 1 — Navegar a la carpeta del proyecto

```bash
cd "ruta/hacia/Backend informatica social/mascate"
```

### Paso 2 — Crear un entorno virtual

Crea una burbuja aislada para instalar las dependencias sin afectar el resto del sistema:

```bash
python -m venv venv
```

### Paso 3 — Activar el entorno virtual

**En Windows:**
```cmd
venv\Scripts\activate
```

**En Mac / Linux:**
```bash
source venv/bin/activate
```

> ✅ Sabrás que funcionó porque aparecerá `(venv)` al inicio de la línea en tu terminal.

### Paso 4 — Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

> ⚠️ Usa siempre `python -m pip` en vez de solo `pip` para garantizar que las dependencias se instalan dentro del entorno virtual activo.

### Paso 5 — Arrancar el servidor

```bash
python -m uvicorn main:app --reload --port 8080
```

> ⚠️ **Importante:** usa `python -m uvicorn` y **no** simplemente `uvicorn`. En sistemas donde hay múltiples versiones de Python instaladas, escribir solo `uvicorn` puede ejecutar una versión del sistema que no tiene acceso a las dependencias del entorno virtual, causando errores como `ModuleNotFoundError: No module named 'fastapi'`.

---

## 🌐 Verificar que está funcionando

Una vez que el servidor esté corriendo, abre cualquier navegador y visita:

| Recurso | URL |
|---|---|
| Documentación interactiva (Swagger) | [http://localhost:8080/docs](http://localhost:8080/docs) |
| Documentación alternativa (ReDoc) | [http://localhost:8080/redoc](http://localhost:8080/redoc) |

---

## 🖥️ Usar la Interfaz

Para usar la interfaz gráfica, simplemente abre cualquiera de estos archivos HTML con **doble clic**. Se conectarán automáticamente al backend que acabas de encender:

- `mascate-auth-final.html` — Pantalla de autenticación
- `mascate-dashboards-final.html` — Panel principal / Dashboards

> ⚠️ El servidor debe estar corriendo para que la interfaz funcione correctamente.

---

## 📁 Estructura del Proyecto

```
Backend informatica social/
└── mascate/
    ├── main.py                       # Punto de entrada de la aplicación
    ├── database.py                   # Configuración de la base de datos
    ├── mascate.db                    # Base de datos SQLite local
    ├── requirements.txt              # Dependencias del proyecto
    ├── mascate-auth-final.html       # Interfaz de autenticación
    ├── mascate-dashboards-final.html # Interfaz de dashboards
    ├── app/                          # Módulos de la aplicación
    └── venv/                         # Entorno virtual (no incluir al comprimir)
```

> 💡 Al comprimir el proyecto para enviarlo, puedes omitir las carpetas `venv/` y `__pycache__/`.

---

## 🛠️ Tecnologías Usadas

| Tecnología | Uso |
|---|---|
| Python 3.8+ | Lenguaje base |
| FastAPI | Framework web / API REST |
| Uvicorn | Servidor ASGI |
| SQLAlchemy | ORM para base de datos |
| SQLite | Base de datos local |
| python-jose | Autenticación JWT |
| passlib / bcrypt | Encriptación de contraseñas |

---

## 📝 Notas

- La base de datos `mascate.db` ya viene con datos de prueba (seeds) listos para usar.
- La autenticación ya está configurada en el proyecto.
- No se requiere configuración adicional de base de datos ni variables de entorno para arrancar.
