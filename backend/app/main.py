from fastapi import FastAPI

from app.api.stocks import router as stocks_router
from app.api.watchlist import router as watchlist_router


def create_app() -> FastAPI:
    app = FastAPI(title="Investment Board Backend")
    app.include_router(watchlist_router, prefix="/api/watchlist")
    app.include_router(stocks_router, prefix="/api/stocks")
    return app


app = create_app()
