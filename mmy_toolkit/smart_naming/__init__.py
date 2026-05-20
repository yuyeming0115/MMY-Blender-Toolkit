"""智能命名模块

提供智能复制、批量重命名功能，解决 Blender 原生 .001 后缀问题。
"""

import bpy
from . import operators
from . import ui


def register():
    """注册模块"""
    operators.register()
    ui.register()


def unregister():
    """注销模块"""
    ui.unregister()
    operators.unregister()