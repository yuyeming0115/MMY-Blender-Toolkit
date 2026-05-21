"""Transform 质检模块 - 入口"""

import bpy
from . import operators
from . import properties


def register():
    properties.register()
    operators.register()


def unregister():
    operators.unregister()
    properties.unregister()


def draw_header(self, context):
    """顶栏按钮绘制（供主模块调用）"""
    operators._draw_tqa_header_button(self, context)