# Cuida Tu Techo — MASCATE

Plataforma de registro y seguimiento comunitario (FastAPI + SQLite).

Instalación, usuarios de prueba, configuración y despliegue: ver **[README_Backend.md](README_Backend.md)**.

Inicio rápido:

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Mac/Linux: source venv/bin/activate)
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8080
```

Luego abre [http://127.0.0.1:8080/login](http://127.0.0.1:8080/login) — usuario `techotivasite@gmail.com`, clave `Test1234!`.
