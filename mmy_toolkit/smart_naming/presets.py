"""智能命名预设管理"""

import os
import json
import bpy


# 预设文件路径
PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")
NAMING_PRESETS_FILE = os.path.join(PRESETS_DIR, "naming_presets.json")

# 默认预设
DEFAULT_NAMING_PRESETS = {
    "separator": "_",
    "digits": 2,
    "prefix_presets": ["Model", "Char", "Prop", "Set", "Asset"],
    "suffix_presets": ["_01", "_LOD", "_A", "_B", "_High", "_Low"],
}


def ensure_presets_dir():
    """确保预设目录存在"""
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)


def load_naming_presets():
    """加载命名预设"""
    ensure_presets_dir()
    if os.path.exists(NAMING_PRESETS_FILE):
        try:
            with open(NAMING_PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # 返回默认预设并保存
    save_naming_presets(DEFAULT_NAMING_PRESETS)
    return DEFAULT_NAMING_PRESETS.copy()


def save_naming_presets(data):
    """保存命名预设"""
    ensure_presets_dir()
    with open(NAMING_PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_separator():
    """获取当前分隔符配置"""
    data = load_naming_presets()
    return data.get("separator", "_")


def set_separator(separator):
    """设置分隔符"""
    data = load_naming_presets()
    data["separator"] = separator
    save_naming_presets(data)


def get_digits():
    """获取数字位数"""
    data = load_naming_presets()
    return data.get("digits", 2)


def set_digits(digits):
    """设置数字位数"""
    data = load_naming_presets()
    data["digits"] = digits
    save_naming_presets(data)


def get_prefix_presets():
    """获取前缀预设列表"""
    data = load_naming_presets()
    return data.get("prefix_presets", DEFAULT_NAMING_PRESETS["prefix_presets"])


def add_prefix_preset(prefix):
    """添加前缀预设"""
    data = load_naming_presets()
    presets = data.get("prefix_presets", [])
    if prefix not in presets:
        presets.append(prefix)
        data["prefix_presets"] = presets
        save_naming_presets(data)
        return True
    return False


def remove_prefix_preset(prefix):
    """删除前缀预设"""
    data = load_naming_presets()
    presets = data.get("prefix_presets", [])
    if prefix in presets:
        presets.remove(prefix)
        data["prefix_presets"] = presets
        save_naming_presets(data)
        return True
    return False


def get_suffix_presets():
    """获取后缀预设列表"""
    data = load_naming_presets()
    return data.get("suffix_presets", DEFAULT_NAMING_PRESETS["suffix_presets"])


def add_suffix_preset(suffix):
    """添加后缀预设"""
    data = load_naming_presets()
    presets = data.get("suffix_presets", [])
    if suffix not in presets:
        presets.append(suffix)
        data["suffix_presets"] = presets
        save_naming_presets(data)
        return True
    return False


def remove_suffix_preset(suffix):
    """删除后缀预设"""
    data = load_naming_presets()
    presets = data.get("suffix_presets", [])
    if suffix in presets:
        presets.remove(suffix)
        data["suffix_presets"] = presets
        save_naming_presets(data)
        return True
    return False


def update_naming_setting(key, value):
    """更新命名设置"""
    data = load_naming_presets()
    data[key] = value
    save_naming_presets(data)