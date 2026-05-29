"""智能选择 UI 面板"""

import bpy


def add_prefs_ui(layout, prefs):
    """在偏好设置中添加智能选择配置"""
    box = layout.box()
    box.label(text="智能选择设置", icon='RESTRICT_SELECT_OFF')

    row = box.row()
    row.prop(prefs, "smart_select_double_click_interval", text="双击间隔（秒）")

    row = box.row()
    row.prop(prefs, "smart_select_mode", text="选择模式")

    row = box.row()
    row.label(text="快捷键：Shift + 双击", icon='INFO')


def register():
    # UI 注册在 __init__.py 中统一处理
    pass


def unregister():
    pass