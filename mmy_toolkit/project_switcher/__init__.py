"""项目文件快速切换模块"""

import bpy
from . import operators


def register():
    operators.register()


def unregister():
    operators.unregister()


def draw_header(self, context):
    """Header绘制函数（供主模块调用）"""
    operators._draw_project_switcher(self, context)