"""
Servicio de correo electrónico para verificación de usuarios.
"""
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


def generar_token() -> str:
    return secrets.token_urlsafe(32)


async def enviar_correo_verificacion(email: str, token: str, base_url: str):
    link = f"{base_url}/auth/verificar-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1D9E75">Verifica tu correo en MASCATE</h2>
      <p>Haz clic en el botón para verificar tu correo y continuar con tu solicitud de registro.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:#1D9E75;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
        Verificar correo
      </a>
      <p style="color:#888;font-size:0.85rem;margin-top:1rem">
        Si no solicitaste esto, ignora este mensaje.<br>
        El enlace expira en 24 horas.
      </p>
    </div>
    """
    message = MessageSchema(
        subject="Verifica tu correo - MASCATE",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)