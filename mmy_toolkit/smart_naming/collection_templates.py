"""集合架构模板管理"""

import json
import os
from bpy.app import version

# 模板文件路径
PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")
TEMPLATE_FILE = os.path.join(PRESETS_DIR, "collection_templates.json")

# 内置模板
BUILTIN_TEMPLATES = {
    "烘焙工作流": {
        "root_name": "Assets",
        "children": ["Char", "Prop", "Set"],
        "auto_lod": True,
        "lod_suffixes": ["_high", "_low"],
    },
    "动画流程": {
        "root_name": "Project",
        "children": ["Mesh", "Rig", "Ani", "Render"],
        "auto_lod": False,
    },
    "资产库": {
        "root_name": "AssetLibrary",
        "children": ["Characters", "Props", "Environments", "Materials"],
        "auto_lod": False,
    },
    "简单分组": {
        "root_name": "Groups",
        "children": [],
        "auto_lod": False,
    },
}


def ensure_presets_dir():
    """确保预设目录存在"""
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)


def load_templates() -> dict:
    """加载模板配置"""
    ensure_presets_dir()
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # 创建默认配置
    data = {
        "default_template": "烘焙工作流",
        "recent_template": "烘焙工作流",
        "templates": BUILTIN_TEMPLATES.copy(),
    }
    save_templates(data)
    return data


def save_templates(data: dict):
    """保存模板配置"""
    ensure_presets_dir()
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_template_names() -> list:
    """获取所有模板名称列表"""
    data = load_templates()
    return list(data.get("templates", BUILTIN_TEMPLATES).keys())


def get_template(name: str) -> dict:
    """获取指定模板的配置"""
    data = load_templates()
    templates = data.get("templates", BUILTIN_TEMPLATES)
    return templates.get(name, BUILTIN_TEMPLATES["烘焙工作流"])


def get_default_template_name() -> str:
    """获取默认模板名称"""
    data = load_templates()
    return data.get("default_template", "烘焙工作流")


def set_default_template(name: str):
    """设置默认模板"""
    data = load_templates()
    if name in data.get("templates", {}):
        data["default_template"] = name
        save_templates(data)


def get_recent_template_name() -> str:
    """获取最近使用的模板名称"""
    data = load_templates()
    return data.get("recent_template", "烘焙工作流")


def set_recent_template(name: str):
    """设置最近使用的模板"""
    data = load_templates()
    if name in data.get("templates", {}):
        data["recent_template"] = name
        save_templates(data)


def add_custom_template(name: str, config: dict) -> bool:
    """添加自定义模板"""
    if not name:
        return False

    data = load_templates()
    templates = data.get("templates", {})

    # 不允许覆盖内置模板
    if name in BUILTIN_TEMPLATES:
        return False

    templates[name] = config
    data["templates"] = templates
    save_templates(data)
    return True


def remove_custom_template(name: str) -> bool:
    """删除自定义模板（不能删除内置模板）"""
    if name in BUILTIN_TEMPLATES:
        return False

    data = load_templates()
    templates = data.get("templates", {})

    if name in templates:
        del templates[name]
        data["templates"] = templates
        save_templates(data)
        return True
    return False


def update_custom_template(name: str, config: dict) -> bool:
    """更新自定义模板"""
    if name in BUILTIN_TEMPLATES:
        return False

    data = load_templates()
    templates = data.get("templates", {})

    if name in templates:
        templates[name] = config
        data["templates"] = templates
        save_templates(data)
        return True
    return False