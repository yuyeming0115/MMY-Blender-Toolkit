"""自动备份模块 - 属性定义"""

import bpy
from bpy.props import FloatProperty


def register_backup_prefs():
    """注册运行时状态属性（场景属性）"""
    bpy.types.Scene.mmy_backup_last_minor = FloatProperty(default=0.0)
    bpy.types.Scene.mmy_backup_last_major = FloatProperty(default=0.0)


def unregister_backup_prefs():
    """注销运行时状态属性"""
    try:
        del bpy.types.Scene.mmy_backup_last_minor
    except:
        pass
    try:
        del bpy.types.Scene.mmy_backup_last_major
    except:
        pass


def get_backup_prefs():
    """获取备份偏好设置"""
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if addon and addon.preferences:
        return addon.preferences
    return None