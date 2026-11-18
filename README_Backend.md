# 🌿 Cuida Tu Techo — MASCATE

**Mesa Autónoma de SPA y Cannábica Techotiva**

Plataforma de registro y seguimiento comunitario. Backend en **Python + FastAPI**, base de datos **SQLite** con **SQLAlchemy**, e interfaz en HTML/CSS/JavaScript que sirve el mismo servidor.

---

## ✅ Requisitos

- **Python 3.10 o superior** (el código usa sintaxis que no funciona en versiones anteriores).
  - Descárgalo en [python.org](https://python.org).
  - ⚠️ En Windows, durante la instalación marca **"Add Python to PATH"**.
- **Git**, para clonar el repositorio.

---

## 🚀 Ejecutar en local

### 1. Clonar el repositorio

```bash
git clone https://github.com/figuerrero26/techotiva.git
cd techotiva
```

### 2. Crear y activar un entorno virtual

```bash
python -m venv venv
```

**Windows:**
```cmd
venv\Scripts\activate
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

> ✅ Funcionó si aparece `(venv)` al inicio de la línea de la terminal.

### 3. Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

### 4. Arrancar el servidor

```bash
python -m uvicorn main:app --reload --port 8080
```

> ⚠️ Usa `python -m uvicorn` y no solo `uvicorn`. Si hay varias versiones de Python instaladas, `uvicorn` a secas puede usar una que no tiene las dependencias y fallar con `ModuleNotFoundError: No module named 'fastapi'`.

### 5. Abrir la plataforma

| Qué | Dirección |
|---|---|
| **Plataforma** (inicio de sesión) | [http://127.0.0.1:8080/login](http://127.0.0.1:8080/login) |
| Documentación de la API (Swagger) | [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) |
| Estado del servidor | [http://127.0.0.1:8080/health](http://127.0.0.1:8080/health) |

La interfaz la sirve el propio servidor: **no abras los archivos HTML con doble clic**, entra siempre por la dirección de arriba.

---

## 👥 Usuarios de prueba

Al arrancar, el servidor crea automáticamente la base de datos y estos usuarios. **Todos usan la clave `Test1234!`.**

| Rol | Email | Nombre |
|---|---|---|
| Administrador | techotivasite@gmail.com | — |
| Dispositivo | artevivo.fontibon@ctt.org | Arte Vivo Fontibón |
| Dispositivo | clubdeportivo.engativa@ctt.org | Club Deportivo Engativá |
| Prescriptor | frankin.guerrero@ctt.org | Frankin Ivan Guerrero |
| Prescriptor | ana.martinez@ctt.org | Ana Sofia Martinez |
| Beneficiario | laura.omana@correo.com | Laura Isabela Omaña |
| Beneficiario | karol.cotame@correo.com | Karol Marcela Cotame |
| Beneficiario | yeimy.poveda@correo.com | Yeimy Poveda |

> La clave del administrador sale de `ADMIN_PASSWORD` en el `.env` y se vuelve a aplicar **cada vez que arranca el servidor**. Si se cambia desde la plataforma, al reiniciar vuelve a la del `.env`.

### Datos ficticios (opcional)

Para ver el panel central con información, puedes cargar 40 beneficiarios ficticios con su primer contacto (SPA, emociones, situaciones, etc.):

```bash
python scripts/seed_demo.py           # crear
python scripts/seed_demo.py --borrar  # eliminar
```

Todos usan correos `@demo.ctt`, así que se borran sin tocar datos reales. **No los cargues en el servidor de producción.**

---

## ⚙️ Archivo `.env`

El repositorio **ya incluye** un `.env` listo para usar en local. Estas son sus variables:

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` | Base de datos. Por defecto `sqlite:///./mascate.db` |
| `SECRET_KEY` | Clave para firmar las sesiones (JWT) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Cuenta de administrador que se crea y sincroniza al arrancar |
| `APP_ENV` | `development` o `production` |
| `APP_BASE_URL` | Dirección pública de la plataforma. Se usa en los enlaces de los correos (activar cuenta, recuperar contraseña) |
| `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_FROM` | Cuenta de Gmail que envía los correos |

> - `MAIL_PASSWORD` **no** es la clave normal de Gmail: es una **contraseña de aplicación** (Cuenta Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones).
> - En el servidor, `APP_BASE_URL` debe ser el **dominio publicado**, o los correos llevarán enlaces a `127.0.0.1`.
> - Después de editar el `.env` hay que **reiniciar el servidor**; los cambios no se leen en caliente.

---

## 🖥️ Despliegue en Ubuntu

Primera vez:

```bash
git clone https://github.com/figuerrero26/techotiva.git
cd techotiva
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

Para actualizar cuando hay cambios nuevos (con la plataforma corriendo como servicio de systemd):

```bash
cd techotiva
git pull
source venv/bin/activate
python -m pip install -r requirements.txt   # por si hay dependencias nuevas
sudo systemctl restart <nombre-del-servicio>
```

> Los cambios en la base de datos (columnas nuevas) se aplican solos al reiniciar; no hace falta borrar `mascate.db`.

---

## 📁 Estructura del proyecto

```
techotiva/
├── main.py                 # Punto de entrada: arranque, datos iniciales y rutas de las páginas
├── database.py             # Conexión a la base de datos y migraciones automáticas
├── requirements.txt        # Dependencias
├── .env                    # Configuración
├── app/
│   ├── core/               # Configuración (.env) y seguridad (JWT, contraseñas)
│   ├── models/             # Tablas de la base de datos
│   ├── schemas/            # Formato de los datos que entran y salen de la API
│   ├── routers/            # Endpoints: auth, admin, dispositivos, prescriptores,
│   │                       #   beneficiarios, actividades, primer_contacto
│   ├── services/           # Envío de correos y cambios de estado
│   └── repositories/       # Acceso al historial de estados
├── templates/
│   ├── *.html              # Páginas de la plataforma
│   └── static/             # CSS, JavaScript, logo y favicon
├── scripts/
│   └── seed_demo.py        # Datos ficticios (opcional)
└── mascate.db              # Base de datos (se crea sola; no está en el repositorio)
```

---

## 🧩 Qué hace cada rol

| Rol | Puede |
|---|---|
| **Administrador** | Ver el panel central con indicadores (beneficiarios, usuarios de SPA, balance emocional, cobertura por DBC); gestionar dispositivos, usuarios y roles; ver quién está conectado y exportar toda la información a Excel desde Configuración |
| **Dispositivo** | Gestionar sus actividades, beneficiarios y prescriptores; diligenciar la Hoja de Primer Contacto |
| **Prescriptor** | Registrar seguimientos y primeros contactos de los beneficiarios de su dispositivo |
| **Beneficiario** | Buscar actividades e inscribirse, ver el mapa de dispositivos y su perfil |

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.10+ | Lenguaje |
| FastAPI + Uvicorn | API y servidor web |
| SQLAlchemy + SQLite | Base de datos (también compatible con PostgreSQL) |
| pydantic / pydantic-settings | Validación de datos y lectura del `.env` |
| python-jose | Sesiones con JWT |
| passlib + bcrypt | Encriptación de contraseñas |
| fastapi-mail | Envío de correos |
| openpyxl | Exportación a Excel |

---

## 📝 Notas

- `mascate.db` **no** está en el repositorio: se crea al primer arranque.
- Para empezar desde cero en local, detén el servidor, borra `mascate.db` y vuelve a arrancar.
- Si después de actualizar ves una versión vieja de una página, recarga con **Ctrl + F5**.
