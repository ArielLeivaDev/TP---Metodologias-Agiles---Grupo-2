"""Configuración del local para el catálogo público (HU-13).

El nombre del kiosco y el WhatsApp de contacto son datos del comercio, no
constantes del código: se leen de variables de entorno (`.env`) y tienen un
default razonable para que el proyecto arranque sin configurar nada.
"""
import os


def _limpiar_telefono(valor):
    """Deja solo dígitos: WhatsApp quiere el número pelado (549...).

    Acepta lo que uno escribiría a mano: "+54 9 11 5555-4444", "(011)
    5555-4444", etc.
    """
    return "".join(c for c in (valor or "") if c.isdigit())


NOMBRE_KIOSCO = os.environ.get("KIOSCO_NOMBRE", "Kiosco de Barrio")

# Número de WhatsApp del local en formato internacional sin "+" ni espacios.
# Ejemplo: 5491155554444 (Argentina, celular de Buenos Aires).
WHATSAPP_KIOSCO = _limpiar_telefono(
    os.environ.get("KIOSCO_WHATSAPP", "5491155554444")
)


def whatsapp_configurado():
    """True si hay un número cargado (distinto del placeholder por defecto).

    El catálogo público lo usa para avisar que falta configurar el WhatsApp
    en vez de abrir un chat a un número de mentira.
    """
    return bool(WHATSAPP_KIOSCO) and WHATSAPP_KIOSCO != "5491155554444"


def url_whatsapp(texto):
    """Link `wa.me` al WhatsApp del kiosco con el mensaje ya codificado."""
    from urllib.parse import quote

    return f"https://wa.me/{WHATSAPP_KIOSCO}?text={quote(texto)}"
