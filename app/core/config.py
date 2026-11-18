from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql://postgres:postgres@localhost:5432/mascate_db"

    # JWT
    secret_key: str = "cambia_esto_en_produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Admin por defecto
    admin_email: str = "admin@mascate.com"
    admin_password: str = "Test1234!"

    # Verificación en dos pasos para el administrador (código por correo).
    # Solo poner en false si el correo no funciona y hay que entrar de emergencia.
    admin_2fa: bool = True

    # App
    app_env: str = "development"

    class Config:
        # .env.local (no se sube a GitHub) sobrescribe a .env: ahí van los secretos reales
        env_file = (".env", ".env.local")
        env_file_encoding = "utf-8"
        
    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    app_base_url: str = "http://127.0.0.1:8080"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()