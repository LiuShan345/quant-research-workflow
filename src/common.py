"""通用工具：路径、配置加载与文件哈希。"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts: str) -> str:
    return os.path.join(ROOT, *parts)


def load_json(rel: str) -> dict:
    with open(path(rel), "r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    """合并全局配置与限额。"""
    cfg = load_json(os.path.join("config", "config.json"))
    cfg["limits"] = load_json(os.path.join("config", "limits.json"))
    return cfg


def sha256_file(rel_or_abs: str) -> str:
    p = rel_or_abs if os.path.isabs(rel_or_abs) else path(rel_or_abs)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(rel_or_abs: str) -> str:
    p = rel_or_abs if os.path.isabs(rel_or_abs) else path(rel_or_abs)
    os.makedirs(p, exist_ok=True)
    return p


def write_json(rel_or_abs: str, obj) -> str:
    p = rel_or_abs if os.path.isabs(rel_or_abs) else path(rel_or_abs)
    ensure_dir(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return p
