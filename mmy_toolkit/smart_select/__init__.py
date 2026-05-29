"""智能选择模块

提供双击智能选择功能：UV孤岛、材质、缝合边。
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