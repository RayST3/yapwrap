"""Prebuilt FastAPI app that answers WhatsApp Business voice calls with YapWrap."""

from yapwrap.whatsapp.app import whatsapp_app

__all__ = ["whatsapp_app"]
