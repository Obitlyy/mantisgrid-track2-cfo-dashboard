from __future__ import annotations

from contextlib import asynccontextmanager

from api.main import app
from decision.bootstrap import decision_lifespan
from decision.routes import router

if not getattr(app.state, "decision_router_installed", False):
    app.include_router(router, prefix="/v1/decision", tags=["Decision API"])
    app.state.decision_router_installed = True

if not getattr(app.state, "decision_lifespan_installed", False):
    official_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def combined_lifespan(application):
        async with official_lifespan(application):
            async with decision_lifespan(application):
                yield

    app.router.lifespan_context = combined_lifespan
    app.state.decision_lifespan_installed = True
