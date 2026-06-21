from fastapi import APIRouter, HTTPException, status

from app.models.strategy import (
    StrategyTemplate,
    StrategyCreate,
    StrategyUpdate,
    AppListUpdate,
)
from app.services.strategy_store import strategy_store

router = APIRouter(prefix="/api/strategy", tags=["策略配置"])


@router.get("/", response_model=dict)
def get_all_strategies():
    data = strategy_store.get_all()
    return data.model_dump()


@router.get("/templates", response_model=dict)
def list_templates():
    return strategy_store.list_templates()


@router.get("/templates/{template_id}", response_model=StrategyTemplate)
def get_template(template_id: str):
    tpl = strategy_store.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return tpl


@router.post("/templates/{template_id}", response_model=StrategyTemplate, status_code=status.HTTP_201_CREATED)
def create_template(template_id: str, payload: StrategyCreate):
    template = StrategyTemplate(
        name=payload.name,
        blacklist=payload.blacklist or [],
        whitelist=payload.whitelist or [],
        enable_blacklist=payload.enable_blacklist if payload.enable_blacklist is not None else True,
        enable_whitelist=payload.enable_whitelist if payload.enable_whitelist is not None else False,
        hide_root=payload.hide_root if payload.hide_root is not None else True,
        hide_bootloader=payload.hide_bootloader if payload.hide_bootloader is not None else True,
    )
    try:
        return strategy_store.create_template(template_id, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/templates/{template_id}", response_model=StrategyTemplate)
def update_template(template_id: str, payload: StrategyUpdate):
    tpl = strategy_store.update_template(template_id, payload)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return tpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str):
    success = strategy_store.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return None


@router.post("/templates/{template_id}/blacklist/add", response_model=list[str])
def add_to_blacklist(template_id: str, payload: AppListUpdate):
    result = strategy_store.add_to_blacklist(template_id, payload.packages)
    if result is None:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return result


@router.post("/templates/{template_id}/blacklist/remove", response_model=list[str])
def remove_from_blacklist(template_id: str, payload: AppListUpdate):
    result = strategy_store.remove_from_blacklist(template_id, payload.packages)
    if result is None:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return result


@router.post("/templates/{template_id}/whitelist/add", response_model=list[str])
def add_to_whitelist(template_id: str, payload: AppListUpdate):
    result = strategy_store.add_to_whitelist(template_id, payload.packages)
    if result is None:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return result


@router.post("/templates/{template_id}/whitelist/remove", response_model=list[str])
def remove_from_whitelist(template_id: str, payload: AppListUpdate):
    result = strategy_store.remove_from_whitelist(template_id, payload.packages)
    if result is None:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")
    return result
