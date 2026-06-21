from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.strategy import router as strategy_router
from app.api.sync import router as sync_router
from app.config import API_HOST, API_PORT

app = FastAPI(
    title="HMA 策略管理后端",
    description="Hide My Applist 策略配置与同步服务",
    version="1.0.0",
)

app.include_router(strategy_router)
app.include_router(sync_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hma-strategy-server"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
