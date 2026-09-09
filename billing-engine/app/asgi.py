"""Production ASGI entrypoint that adds optional payment-specific routers to the canonical app."""

from app.main import app
from app.moneybag_routes import router as moneybag_router

# Keep app.main as the canonical application so existing billing routes and
# operational control-plane behavior remain unchanged. The Moneybag boundary
# is mounted here as a separate reviewed router.
app.include_router(moneybag_router)
