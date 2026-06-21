from __future__ import annotations

import json
import time
import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, Header, status
from pydantic import BaseModel, Field

from app.services.strategy_store import strategy_store

router = APIRouter(prefix="/api/sync", tags=["客户端同步"])


class SyncResponse(BaseModel):
    template_id: str
    version: int
    updated_at: int
    config: dict


class SyncUpToDateResponse(BaseModel):
    status: str = Field("up_to_date", description="固定值 up_to_date，表示已是最新")
    message: str = Field("不用动，就是最新的", description="人类可读提示")
    template_id: str
    version: int
    updated_at: int


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


def _build_etag(template_id: str, version: int, updated_at: int) -> str:
    raw = f"{template_id}|{version}|{updated_at}"
    return '"' + hashlib.md5(raw.encode()).hexdigest() + '"'


def _common_headers(template_id: str, version: int, updated_at: int) -> dict:
    return {
        "X-Template-ID": template_id,
        "X-Version": str(version),
        "X-Updated-At": str(updated_at),
        "ETag": _build_etag(template_id, version, updated_at),
        "Cache-Control": "no-store",
    }


@router.get("/version", response_model=VersionCheckResponse)
def check_version(
    template_id: str = Query("default", description="策略模板 ID"),
    client_version: int = Query(0, description="客户端当前版本号"),
):
    data = strategy_store.get_all()
    tpl = data.templates.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    need = data.version > client_version
    resp = VersionCheckResponse(
        template_id=template_id,
        version=data.version,
        updated_at=data.updated_at,
        need_update=need,
    )
    headers = _common_headers(template_id, data.version, data.updated_at)
    return Response(
        content=resp.model_dump_json(),
        media_type="application/json",
        headers=headers,
    )


@router.get(
    "/pull",
    response_model=None,
    responses={
        200: {"model": SyncResponse},
        304: {"description": "无需更新，内容与客户端版本一致"},
    },
)
def pull_strategy(
    response: Response,
    template_id: str = Query("default", description="策略模板 ID"),
    format: str = Query("json", description="返回格式: json 或 hma"),
    client_version: int = Query(
        0,
        description="客户端当前版本号（相同则不发送完整配置，省流量）",
        ge=0,
    ),
    if_none_match: Optional[str] = Header(
        default=None,
        description="HTTP 标准 If-None-Match，传之前返回的 ETag 也可判断",
    ),
):
    pkg = strategy_store.get_sync_package(template_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")

    server_version = pkg["version"]
    server_updated_at = pkg["updated_at"]
    headers = _common_headers(template_id, server_version, server_updated_at)

    etag_match = if_none_match is not None and (
        if_none_match == headers["ETag"]
        or if_none_match.strip() == headers["ETag"]
        or if_none_match.strip() == headers["ETag"].strip('"')
    )
    version_match = client_version > 0 and server_version <= client_version

    if version_match or etag_match:
        body = SyncUpToDateResponse(
            template_id=template_id,
            version=server_version,
            updated_at=server_updated_at,
        )
        if etag_match:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
        return Response(
            content=body.model_dump_json(),
            media_type="application/json",
            headers=headers,
        )

    if format == "hma":
        hma_config = _convert_to_hma_format(pkg["config"])
        return Response(
            content=json.dumps(hma_config, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers=headers,
        )

    payload = SyncResponse(**pkg)
    return Response(
        content=payload.model_dump_json(),
        media_type="application/json",
        headers=headers,
    )


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
