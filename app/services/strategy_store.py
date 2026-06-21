import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Optional

from fastapi import HTTPException

from app.config import STRATEGY_FILE, DEFAULT_TEMPLATE
from app.models.strategy import StrategyTemplate, StrategyData, StrategyUpdate

logger = logging.getLogger(__name__)


class StrategyStoreError(Exception):
    pass


class StrategyStore:
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path).expanduser().resolve()
        self._lock = threading.Lock()
        self._data: Optional[StrategyData] = None
        self._initialized = False
        self._init_storage()

    def _init_storage(self):
        try:
            self._ensure_file()
            self._load()
            self._initialized = True
            logger.info("策略存储初始化成功: file=%s, templates=%s",
                        self.file_path, list(self._data.templates.keys()))
        except Exception as e:
            logger.error("策略存储初始化失败: file=%s, error=%s", self.file_path, e, exc_info=True)
            raise StrategyStoreError(
                f"策略文件加载失败: {self.file_path}。"
                f"请确认文件存在且为合法 JSON。当前目录 CWD={Path.cwd()}。"
                f"详细错误: {e}"
            ) from e

    def _ensure_file(self):
        parent = self.file_path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StrategyStoreError(
                f"无法创建数据目录 {parent}: {e}。"
                f"请检查该路径的写入权限。"
            ) from e

        if not self.file_path.exists():
            logger.warning("策略文件不存在，将创建默认文件: %s", self.file_path)
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_TEMPLATE, f, indent=2, ensure_ascii=False)
            except OSError as e:
                raise StrategyStoreError(
                    f"无法写入默认策略文件 {self.file_path}: {e}。"
                    f"请检查权限或通过 HMA_STRATEGY_FILE 环境变量指定其他路径。"
                ) from e

    def _load(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise StrategyStoreError(
                f"策略文件不存在: {self.file_path} (已解析的绝对路径)。"
                f"CWD={Path.cwd()}"
            ) from e
        except json.JSONDecodeError as e:
            raise StrategyStoreError(
                f"策略文件 JSON 解析失败: {self.file_path}，行={e.lineno}，位置={e.pos}。"
                f"错误信息: {e.msg}"
            ) from e
        except OSError as e:
            raise StrategyStoreError(
                f"读取策略文件失败 (权限/IO错误): {self.file_path}。错误: {e}"
            ) from e

        try:
            self._data = StrategyData(**data)
        except (TypeError, ValueError) as e:
            raise StrategyStoreError(
                f"策略文件结构不正确: {self.file_path}。{e}"
            ) from e

    def _save(self):
        if self._data is None:
            raise StrategyStoreError("存储未初始化，无法写入")
        self._data.updated_at = int(time.time())
        tmp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data.model_dump(), f, indent=2, ensure_ascii=False)
            tmp_path.replace(self.file_path)
        except OSError as e:
            logger.error("写入策略文件失败: %s, error=%s", self.file_path, e, exc_info=True)
            raise StrategyStoreError(
                f"写入策略文件失败 {self.file_path}: {e}"
            ) from e

    def _check_init(self):
        if not self._initialized or self._data is None:
            raise HTTPException(
                status_code=500,
                detail=f"策略存储未正确初始化。请检查配置文件: {self.file_path}"
            )

    def get_all(self) -> StrategyData:
        with self._lock:
            self._check_init()
            return self._data.model_copy(deep=True)

    def list_templates(self) -> Dict[str, StrategyTemplate]:
        with self._lock:
            self._check_init()
            return {k: v.model_copy(deep=True) for k, v in self._data.templates.items()}

    def get_template(self, template_id: str) -> Optional[StrategyTemplate]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            return tpl.model_copy(deep=True) if tpl else None

    def create_template(self, template_id: str, template: StrategyTemplate) -> StrategyTemplate:
        with self._lock:
            self._check_init()
            if template_id in self._data.templates:
                raise ValueError(f"Template '{template_id}' already exists")
            self._data.templates[template_id] = template.model_copy(deep=True)
            self._save()
            return self._data.templates[template_id].model_copy(deep=True)

    def update_template(self, template_id: str, update: StrategyUpdate) -> Optional[StrategyTemplate]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            update_data = update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(tpl, key, value)
            self._save()
            return tpl.model_copy(deep=True)

    def delete_template(self, template_id: str) -> bool:
        with self._lock:
            self._check_init()
            if template_id not in self._data.templates:
                return False
            del self._data.templates[template_id]
            self._save()
            return True

    def add_to_blacklist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            for pkg in packages:
                if pkg not in tpl.blacklist:
                    tpl.blacklist.append(pkg)
            self._save()
            return list(tpl.blacklist)

    def remove_from_blacklist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            tpl.blacklist = [p for p in tpl.blacklist if p not in packages]
            self._save()
            return list(tpl.blacklist)

    def add_to_whitelist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            for pkg in packages:
                if pkg not in tpl.whitelist:
                    tpl.whitelist.append(pkg)
            self._save()
            return list(tpl.whitelist)

    def remove_from_whitelist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            tpl.whitelist = [p for p in tpl.whitelist if p not in packages]
            self._save()
            return list(tpl.whitelist)

    def get_sync_package(self, template_id: str = "default") -> Optional[dict]:
        with self._lock:
            self._check_init()
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            return {
                "template_id": template_id,
                "version": self._data.version,
                "updated_at": self._data.updated_at,
                "config": tpl.model_dump()
            }


try:
    strategy_store = StrategyStore(STRATEGY_FILE)
except StrategyStoreError as init_err:
    logger.critical("=" * 60)
    logger.critical("策略存储初始化失败，服务将以降级模式启动")
    logger.critical("错误: %s", init_err)
    logger.critical("=" * 60)
    strategy_store = None
