import json
import time
import threading
from pathlib import Path
from typing import Dict, Optional

from app.config import STRATEGY_FILE, DEFAULT_TEMPLATE
from app.models.strategy import StrategyTemplate, StrategyData, StrategyUpdate


class StrategyStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._lock = threading.Lock()
        self._data: Optional[StrategyData] = None
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_TEMPLATE, f, indent=2, ensure_ascii=False)

    def _load(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._data = StrategyData(**data)

    def _save(self):
        self._data.updated_at = int(time.time())
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._data.model_dump(), f, indent=2, ensure_ascii=False)

    def get_all(self) -> StrategyData:
        with self._lock:
            return self._data.model_copy(deep=True)

    def list_templates(self) -> Dict[str, StrategyTemplate]:
        with self._lock:
            return {k: v.model_copy(deep=True) for k, v in self._data.templates.items()}

    def get_template(self, template_id: str) -> Optional[StrategyTemplate]:
        with self._lock:
            tpl = self._data.templates.get(template_id)
            return tpl.model_copy(deep=True) if tpl else None

    def create_template(self, template_id: str, template: StrategyTemplate) -> StrategyTemplate:
        with self._lock:
            if template_id in self._data.templates:
                raise ValueError(f"Template '{template_id}' already exists")
            self._data.templates[template_id] = template.model_copy(deep=True)
            self._save()
            return self._data.templates[template_id].model_copy(deep=True)

    def update_template(self, template_id: str, update: StrategyUpdate) -> Optional[StrategyTemplate]:
        with self._lock:
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
            if template_id not in self._data.templates:
                return False
            del self._data.templates[template_id]
            self._save()
            return True

    def add_to_blacklist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
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
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            tpl.blacklist = [p for p in tpl.blacklist if p not in packages]
            self._save()
            return list(tpl.blacklist)

    def add_to_whitelist(self, template_id: str, packages: list[str]) -> Optional[list[str]]:
        with self._lock:
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
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            tpl.whitelist = [p for p in tpl.whitelist if p not in packages]
            self._save()
            return list(tpl.whitelist)

    def get_sync_package(self, template_id: str = "default") -> Optional[dict]:
        with self._lock:
            tpl = self._data.templates.get(template_id)
            if not tpl:
                return None
            return {
                "template_id": template_id,
                "version": self._data.version,
                "updated_at": self._data.updated_at,
                "config": tpl.model_dump()
            }


strategy_store = StrategyStore(STRATEGY_FILE)
