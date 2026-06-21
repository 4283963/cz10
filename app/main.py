import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.strategy import router as strategy_router
from app.api.sync import router as sync_router
from app.config import API_HOST, API_PORT, dump_paths
from app.services.strategy_store import strategy_store, StrategyStoreError


def _setup_logging():
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)


_setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths = dump_paths()
    banner = [
        "",
        "=" * 60,
        "  HMA 策略管理服务启动",
        "=" * 60,
        f"  项目根目录    : {paths['project_root']}",
        f"  数据目录      : {paths['data_dir']}",
        f"  策略文件路径  : {paths['strategy_file']}",
        f"  策略文件存在  : {paths['strategy_file_exists']}",
        f"  监听地址      : {API_HOST}:{API_PORT}",
        f"  策略存储状态  : {'✅ 已初始化' if strategy_store is not None else '❌ 初始化失败'}",
        "=" * 60,
    ]
    for line in banner:
        logger.info(line)

    if strategy_store is None:
        logger.error(
            "策略存储未初始化，所有策略接口将返回 500。"
            "请检查上方打印的路径，或通过环境变量指定: "
            "HMA_PROJECT_ROOT / HMA_DATA_DIR / HMA_STRATEGY_FILE"
        )
    yield


app = FastAPI(
    title="HMA 策略管理后端",
    description="Hide My Applist 策略配置与同步服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(StrategyStoreError)
async def strategy_store_error_handler(request: Request, exc: StrategyStoreError):
    logger.error("StrategyStoreError: %s | path=%s", exc, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "strategy_store_error",
            "detail": str(exc),
            "hint": "访问 /diagnose 查看当前路径诊断信息",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: path=%s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc),
            "hint": "访问 /diagnose 查看当前路径诊断信息",
        },
    )


app.include_router(strategy_router)
app.include_router(sync_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {
        "status": "ok" if strategy_store is not None else "degraded",
        "service": "hma-strategy-server",
        "store_initialized": strategy_store is not None,
    }


@app.get("/diagnose")
async def diagnose():
    info = dump_paths()
    info["cwd"] = str(__import__("pathlib").Path.cwd())
    info["store_initialized"] = strategy_store is not None
    if strategy_store is not None:
        try:
            info["templates"] = list(strategy_store.list_templates().keys())
        except Exception as e:
            info["templates_error"] = str(e)
    return info


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )
