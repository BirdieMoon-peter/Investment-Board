import secrets

from fastapi import FastAPI

from app.api.ai_settings import protect_ai_settings, router as ai_settings_router
from app.api.holdings import router as holdings_router
from app.api.homepage import router as homepage_router
from app.api.investment_advice import router as investment_advice_router
from app.api.stocks import router as stocks_router
from app.api.watchlist import router as watchlist_router
from app.core.settings import Settings
from app.db.session import create_db_and_tables, make_engine


def create_app() -> FastAPI:
    app = FastAPI(title="Investment Board Backend")
    app.state.ai_settings_mutation_token = secrets.token_urlsafe(32)
    app.middleware("http")(protect_ai_settings)

    @app.on_event("startup")
    def startup() -> None:
        create_db_and_tables(make_engine(Settings()))

    app.include_router(watchlist_router, prefix="/api/watchlist")
    app.include_router(stocks_router, prefix="/api/stocks")
    app.include_router(homepage_router, prefix="/api/homepage")
    app.include_router(holdings_router, prefix="/api/holdings")
    app.include_router(investment_advice_router, prefix="/api/ai")
    app.include_router(ai_settings_router, prefix="/api/ai")
    return app


app = create_app()
