"""FBX 规范化导出模块

提供针对 Unity 的 FBX 规范化导出功能：
- 批量导出选中物体为单独 FBX
- 变换重置/归零处理
- 贴图导出并重命名（随物体名）
- NLA 动画轨道选择导出
"""

import bpy
from . import operators
from . import properties
from . import ui


def register():
    """注册模块"""
    properties.register()
    operators.register()
    ui.register()


def unregister():
    """注销模块"""
    ui.unregister()
    operators.unregister()
    properties.unregister()