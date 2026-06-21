from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class StrategyTemplate(BaseModel):
    name: str = Field(..., description="策略模板名称")
    blacklist: List[str] = Field(default_factory=list, description="黑名单应用包名列表")
    whitelist: List[str] = Field(default_factory=list, description="白名单应用包名列表")
    enable_blacklist: bool = Field(default=True, description="是否启用黑名单模式")
    enable_whitelist: bool = Field(default=False, description="是否启用白名单模式")
    hide_root: bool = Field(default=True, description="是否隐藏 root")
    hide_bootloader: bool = Field(default=True, description="是否隐藏 bootloader 状态")


class StrategyCreate(BaseModel):
    name: str
    blacklist: Optional[List[str]] = None
    whitelist: Optional[List[str]] = None
    enable_blacklist: Optional[bool] = None
    enable_whitelist: Optional[bool] = None
    hide_root: Optional[bool] = None
    hide_bootloader: Optional[bool] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    blacklist: Optional[List[str]] = None
    whitelist: Optional[List[str]] = None
    enable_blacklist: Optional[bool] = None
    enable_whitelist: Optional[bool] = None
    hide_root: Optional[bool] = None
    hide_bootloader: Optional[bool] = None


class AppListUpdate(BaseModel):
    packages: List[str]


class StrategyData(BaseModel):
    version: int = 1
    updated_at: int = 0
    templates: Dict[str, StrategyTemplate]
