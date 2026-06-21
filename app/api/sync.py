import json
import time
from fastapi import APIRouter, HTTPException, Query, Response, Header
from pydantic import BaseModel

from app.services.strategy_store import strategy_store

router = APIRouter(prefix="/api/sync", tags=["客户端同步"])


class SyncResponse(BaseModel):
    template_id: str
    version: int
    updated_at: int
    config: dict


class VersionCheckResponse(BaseModel):
    template_id: str
    version: int
    updated_at: int
    need_update: bool


class SyncReportRequest(BaseModel):
    device_id: str
    template_id: str
    local_version: int
    sync_success: bool
    message: str = ""


@router.get("/version", response_model=VersionCheckResponse)
def check_version(
    template_id: str = Query("default", description="策略模板 ID"),
    client_version: int = Query(0, description="客户端当前版本号"),
):
    data = strategy_store.get_all()
    tpl = data.templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return VersionCheckResponse(
        template_id=template_id,
        version=data.version,
        updated_at=data.updated_at,
        need_update=data.version > client_version,
    )


@router.get("/pull", response_model=SyncResponse)
def pull_strategy(
    template_id: str = Query("default", description="策略模板 ID"),
    format: str = Query("json", description="返回格式: json 或 hma"),
):
    pkg = strategy_store.get_sync_package(template_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")

    if format == "hma":
        hma_config = _convert_to_hma_format(pkg["config"])
        return Response(
            content=json.dumps(hma_config, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={
                "X-Template-ID": template_id,
                "X-Version": str(pkg["version"]),
                "X-Updated-At": str(pkg["updated_at"]),
            },
        )

    return SyncResponse(**pkg)


@router.get("/export/{template_id}")
def export_strategy(template_id: str):
    pkg = strategy_store.get_sync_package(template_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")

    hma_config = _convert_to_hma_format(pkg["config"])
    content = json.dumps(hma_config, ensure_ascii=False, indent=2)

    filename = f"hma_config_{template_id}_v{pkg['version']}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/report")
def report_sync(payload: SyncReportRequest):
    tpl = strategy_store.get_template(payload.template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板 '{payload.template_id}' 不存在")
    return {
        "status": "received",
        "server_time": int(time.time()),
        "device_id": payload.device_id,
        "sync_success": payload.sync_success,
    }


def _convert_to_hma_format(config: dict) -> dict:
    return {
        "hide_my_applist": {
            "version": "2.0",
            "config": {
                "enable_blacklist": config.get("enable_blacklist", True),
                "enable_whitelist": config.get("enable_whitelist", False),
                "blacklist": config.get("blacklist", []),
                "whitelist": config.get("whitelist", []),
                "hide_root": config.get("hide_root", True),
                "hide_bootloader": config.get("hide_bootloader", True),
            }
        }
    }
