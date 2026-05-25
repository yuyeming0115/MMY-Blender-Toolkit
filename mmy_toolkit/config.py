import bpy
import json
import os

# 预设文件路径
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")
PRESET_FILE = os.path.join(PRESETS_DIR, "suffix_presets.json")
ASSET_PRESET_FILE = os.path.join(PRESETS_DIR, "asset_presets.json")
LENS_PRESET_FILE = os.path.join(PRESETS_DIR, "lens_presets.json")
PROJECT_PRESET_FILE = os.path.join(PRESETS_DIR, "project_presets.json")

# 默认预设数据
DEFAULT_PRESETS = {
    "完整流程": ["_Mesh", "_Mat", "_Rig", "_Ani", "_Render"],
    "动画流程": ["_Mesh", "_Rig", "_Ani"],
    "渲染流程": ["_Mat", "_Light", "_Render"],
}

# 默认后缀（兼容旧版本）
DEFAULT_SUFFIXES = ["_Mesh", "_Mat", "_Rig", "_Ani", "_Render"]


def ensure_presets_dir():
    """确保预设目录存在"""
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)


def load_presets() -> dict:
    """加载预设文件，如果不存在则创建默认预设"""
    ensure_presets_dir()
    if os.path.exists(PRESET_FILE):
        try:
            with open(PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # 创建默认预设文件
    data = {
        "current_preset": "完整流程",
        "presets": DEFAULT_PRESETS,
    }
    save_presets(data)
    return data


def save_presets(data: dict):
    """保存预设到文件"""
    ensure_presets_dir()
    with open(PRESET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_suffixes() -> list:
    """获取当前激活的后缀列表"""
    data = load_presets()
    current_name = data.get("current_preset", "完整流程")
    presets = data.get("presets", DEFAULT_PRESETS)
    return presets.get(current_name, DEFAULT_SUFFIXES)


def get_current_preset_name() -> str:
    """获取当前预设名称"""
    data = load_presets()
    return data.get("current_preset", "完整流程")


def set_current_preset(name: str):
    """设置当前预设"""
    data = load_presets()
    if name in data.get("presets", {}):
        data["current_preset"] = name
        save_presets(data)


def get_all_preset_names() -> list:
    """获取所有预设名称列表"""
    data = load_presets()
    return list(data.get("presets", DEFAULT_PRESETS).keys())


def update_preset(name: str, suffixes: list):
    """更新或添加预设"""
    data = load_presets()
    data["presets"][name] = suffixes
    save_presets(data)


def delete_preset(name: str):
    """删除预设（保留默认预设）"""
    if name in DEFAULT_PRESETS:
        return False
    data = load_presets()
    if name in data.get("presets", {}):
        del data["presets"][name]
        save_presets(data)
        return True
    return False


# 兼容旧版本的函数
def get_suffixes() -> list[str]:
    return get_current_suffixes()


# ============ 资产预设配置 ============

DEFAULT_ASSET_PRESETS = {
    "recent_paths": [],
    "favorite_paths": [],
    "last_used_path": "",
}


def load_asset_presets() -> dict:
    """加载资产预设配置"""
    ensure_presets_dir()
    if os.path.exists(ASSET_PRESET_FILE):
        try:
            with open(ASSET_PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    save_asset_presets(DEFAULT_ASSET_PRESETS)
    return DEFAULT_ASSET_PRESETS.copy()


def save_asset_presets(data: dict):
    """保存资产预设配置"""
    ensure_presets_dir()
    with open(ASSET_PRESET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_recent_asset_path(path: str, max_count: int = 10):
    """添加最近使用路径"""
    if not path:
        return

    data = load_asset_presets()
    recent = data.get("recent_paths", [])

    # 移除已存在的相同路径
    if path in recent:
        recent.remove(path)

    # 添加到开头
    recent.insert(0, path)

    # 限制数量
    data["recent_paths"] = recent[:max_count]
    data["last_used_path"] = path

    save_asset_presets(data)


def get_recent_asset_paths() -> list:
    """获取最近使用路径列表"""
    data = load_asset_presets()
    return data.get("recent_paths", [])


def get_last_used_asset_path() -> str:
    """获取最后使用的路径"""
    data = load_asset_presets()
    return data.get("last_used_path", "")


def add_favorite_path(path: str, alias: str = ""):
    """添加收藏路径"""
    if not path:
        return False

    data = load_asset_presets()
    favorites = data.get("favorite_paths", [])

    # 检查是否已存在
    for fav in favorites:
        if fav.get("path") == path:
            return False

    favorites.append({
        "path": path,
        "alias": alias or os.path.basename(path) or path
    })
    data["favorite_paths"] = favorites
    save_asset_presets(data)
    return True


def remove_favorite_path(path: str):
    """移除收藏路径"""
    data = load_asset_presets()
    favorites = data.get("favorite_paths", [])
    data["favorite_paths"] = [f for f in favorites if f.get("path") != path]
    save_asset_presets(data)


def get_favorite_paths() -> list:
    """获取收藏路径列表"""
    data = load_asset_presets()
    return data.get("favorite_paths", [])


# ============ 焦距预设配置 ============

DEFAULT_LENS_PRESETS = {
    "presets": {
        "24mm": 24.0,
        "35mm": 35.0,
        "50mm": 50.0,
        "85mm": 85.0,
        "135mm": 135.0,
    }
}


def load_lens_presets() -> dict:
    """加载焦距预设配置"""
    ensure_presets_dir()
    if os.path.exists(LENS_PRESET_FILE):
        try:
            with open(LENS_PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    save_lens_presets(DEFAULT_LENS_PRESETS)
    return DEFAULT_LENS_PRESETS.copy()


def save_lens_presets(data: dict):
    """保存焦距预设配置"""
    ensure_presets_dir()
    with open(LENS_PRESET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_lens_presets() -> dict:
    """获取所有焦距预设"""
    data = load_lens_presets()
    return data.get("presets", DEFAULT_LENS_PRESETS["presets"])


def get_lens_preset_value(name: str) -> float:
    """获取指定预设的焦距值"""
    presets = get_lens_presets()
    return presets.get(name, 50.0)


def add_lens_preset(name: str, value: float):
    """添加或更新焦距预设"""
    data = load_lens_presets()
    data["presets"][name] = value
    save_lens_presets(data)


def delete_lens_preset(name: str) -> bool:
    """删除焦距预设（保留默认预设）"""
    if name in DEFAULT_LENS_PRESETS["presets"]:
        return False
    data = load_lens_presets()
    if name in data.get("presets", {}):
        del data["presets"][name]
        save_lens_presets(data)
        return True
    return False


def get_all_lens_preset_names() -> list:
    """获取所有焦距预设名称列表"""
    presets = get_lens_presets()
    return list(presets.keys())


# ============ 项目路径预设配置 ============

DEFAULT_PROJECT_PRESETS = {
    "recent_project_paths": [],      # 最近打开的项目路径（完整文件路径）
    "favorite_project_paths": [],    # 收藏的项目书签（包含 path 和 alias）
    "max_recent": 10,                 # 最大历史记录数
}


def load_project_presets() -> dict:
    """加载项目路径预设配置"""
    ensure_presets_dir()
    if os.path.exists(PROJECT_PRESET_FILE):
        try:
            with open(PROJECT_PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    save_project_presets(DEFAULT_PROJECT_PRESETS)
    return DEFAULT_PROJECT_PRESETS.copy()


def save_project_presets(data: dict):
    """保存项目路径预设配置"""
    ensure_presets_dir()
    with open(PROJECT_PRESET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_recent_project_path(filepath: str, max_count: int = 10):
    """添加最近打开的项目路径"""
    if not filepath:
        return

    data = load_project_presets()
    recent = data.get("recent_project_paths", [])

    # 移除已存在的相同路径
    if filepath in recent:
        recent.remove(filepath)

    # 添加到开头
    recent.insert(0, filepath)

    # 限制数量
    max_count = data.get("max_recent", max_count)
    data["recent_project_paths"] = recent[:max_count]

    save_project_presets(data)


def get_recent_project_paths() -> list:
    """获取最近打开的项目路径列表"""
    data = load_project_presets()
    return data.get("recent_project_paths", [])


def clear_recent_project_paths():
    """清空最近打开的项目路径"""
    data = load_project_presets()
    data["recent_project_paths"] = []
    save_project_presets(data)


def add_project_bookmark(path: str, alias: str = ""):
    """添加项目书签"""
    if not path:
        return False

    data = load_project_presets()
    bookmarks = data.get("favorite_project_paths", [])

    # 检查是否已存在
    for bookmark in bookmarks:
        if bookmark.get("path") == path:
            return False

    # 使用路径名作为默认别名
    display_alias = alias or os.path.basename(path) or path
    bookmarks.append({
        "path": path,
        "alias": display_alias
    })
    data["favorite_project_paths"] = bookmarks
    save_project_presets(data)
    return True


def remove_project_bookmark(path: str):
    """移除项目书签"""
    data = load_project_presets()
    bookmarks = data.get("favorite_project_paths", [])
    data["favorite_project_paths"] = [b for b in bookmarks if b.get("path") != path]
    save_project_presets(data)


def get_project_bookmarks() -> list:
    """获取项目书签列表"""
    data = load_project_presets()
    return data.get("favorite_project_paths", [])