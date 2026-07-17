from app.channels.zalo.client import get_zalo_client
from app.channels.zalo.webhook import router as zalo_router

__all__ = ["get_zalo_client", "zalo_router"]
