"""Single Django Ninja API; each app contributes a router.

Interactive docs are served at /api/docs (OpenAPI schema at /api/openapi.json).
"""
from ninja import NinjaAPI

api = NinjaAPI(
    title="Church Platform API",
    version="1.0.0",
    description="History, branches, community, media, giving and real-time.",
    urls_namespace="api",
)

api.add_router("/auth", "apps.accounts.api.router", tags=["auth"])
api.add_router("/branches", "apps.churches.api.router", tags=["branches"])
api.add_router("/history", "apps.history.api.router", tags=["history"])
api.add_router("/community", "apps.community.api.router", tags=["community"])
api.add_router("/media", "apps.media_library.api.router", tags=["media"])
api.add_router("/giving", "apps.giving.api.router", tags=["giving"])
api.add_router("/realtime", "apps.realtime.api.router", tags=["realtime"])
