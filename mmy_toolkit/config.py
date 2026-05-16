import bpy
import json
import os

# 预设文件路径
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")
PRESET_FILE = os.path.join(PRESETS_DIR, "suffix_presets.json")

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