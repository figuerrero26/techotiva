"""
Limitador de intentos en memoria (login, código 2FA, recuperar contraseña).

Cuenta fallos por clave (correo, IP…) dentro de una ventana de tiempo. Al
superar el máximo, la clave queda bloqueada hasta que pase la ventana.
Vive en memoria del proceso: se reinicia al reiniciar el servidor, suficiente
para frenar ataques de fuerza bruta con un solo proceso de uvicorn.
"""

import threading
import time

from fastapi import HTTPException, Request


class Limitador:
    def __init__(self, maximo: int, ventana_seg: int):
        self.maximo = maximo
        self.ventana = ventana_seg
        self._fallos: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _vigentes(self, clave: str, ahora: float) -> list[float]:
        lista = [t for t in self._fallos.get(clave, []) if ahora - t < self.ventana]
        if lista:
            self._fallos[clave] = lista
        else:
            self._fallos.pop(clave, None)
        return lista

    def verificar(self, *claves: str) -> None:
        """Lanza 429 si alguna clave superó el máximo de fallos."""
        ahora = time.time()
        with self._lock:
            for clave in claves:
                lista = self._vigentes(clave, ahora)
                if len(lista) >= self.maximo:
                    espera = int(self.ventana - (ahora - lista[0])) + 1
                    minutos = max(1, round(espera / 60))
                    raise HTTPException(
                        status_code=429,
                        detail=f"Demasiados intentos. Intenta de nuevo en {minutos} minuto(s).",
                    )

    def fallo(self, *claves: str) -> None:
        ahora = time.time()
        with self._lock:
            for clave in claves:
                self._fallos.setdefault(clave, []).append(ahora)

    def limpiar(self, *claves: str) -> None:
        with self._lock:
            for clave in claves:
                self._fallos.pop(clave, None)


def ip_cliente(request: Request) -> str:
    """
    IP del cliente. X-Forwarded-For solo se acepta si la conexión viene de un
    proxy local (nginx en el mismo servidor); si no, cualquiera podría falsearlo.
    Se toma la última IP de la lista, que es la que agregó nuestro proxy.
    """
    directa = request.client.host if request.client else "desconocida"
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada and (directa.startswith("127.") or directa == "::1"):
        return reenviada.split(",")[-1].strip()
    return directa


# 5 contraseñas erradas por correo (o 20 por IP) → 15 minutos de bloqueo
limite_login = Limitador(maximo=5, ventana_seg=15 * 60)
limite_login_ip = Limitador(maximo=20, ventana_seg=15 * 60)
# Códigos 2FA erróneos por IP
limite_2fa_ip = Limitador(maximo=10, ventana_seg=15 * 60)
# Solicitudes de recuperación de contraseña por IP
limite_recuperar_ip = Limitador(maximo=5, ventana_seg=15 * 60)
