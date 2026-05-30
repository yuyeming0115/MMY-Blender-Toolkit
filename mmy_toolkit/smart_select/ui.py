"""智能选择 UI 面板"""

import bpy


def add_prefs_ui(layout, prefs):
    """在偏好设置中添加智能选择配置"""
    box = layout.box()
    box.label(text="智能选择设置", icon='RESTRICT_SELECT_OFF')

    row = box.row()
    row.label(text="快捷键：", icon='INFO')
    col = box.column()
    col.label(text="• UV 编辑器：双击选中孤岛")
    col.label(text="• 3D 视图：双击选中相连元素")
    col.label(text="• 3D 视图：Shift+双击选中相同材质")
    col.label(text="• 3D 视图：Ctrl+双击选中缝合边")


def register():
    pass


def unregister():
    pass