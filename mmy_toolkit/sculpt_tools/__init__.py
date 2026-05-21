"""雕刻工具模块 - 面组右键菜单"""

import bpy


def _append_sculpt_context_menu(self, context):
    """在雕刻模式右键菜单中添加面组功能"""
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'SCULPT':
        return

    layout = self.layout
    layout.separator()
    layout.label(text="面组")

    # 创建面组（基于选择/遮罩）
    layout.operator("sculpt.face_sets_create", text="从遮罩创建", icon='GROUP_VERTEX').mode = 'MASK'

    # 可见性控制
    row = layout.row(align=True)
    row.operator("sculpt.face_set_change_visibility", text="切换显示", icon='HIDE_OFF')
    row.operator("sculpt.face_set_invert_visibility", text="反转", icon='ARROW_LEFTRIGHT')

    # 全局控制
    row = layout.row(align=True)
    row.operator("sculpt.face_set_hide_all", text="隐藏全部", icon='HIDE_ON')
    row.operator("sculpt.face_set_show_all", text="显示全部", icon='HIDE_OFF')

    # 编辑功能
    layout.separator()
    layout.operator("sculpt.face_set_edit", text="填充", icon='FILL').mode = 'GROW'
    layout.operator("sculpt.face_set_edit", text="收缩", icon='SHRINK').mode = 'SHRINK'


def register():
    """注册模块"""
    try:
        bpy.types.VIEW3D_MT_sculpt_context_menu.append(_append_sculpt_context_menu)
    except Exception as e:
        print(f"[MMY Sculpt] 注册右键菜单失败: {e}")


def unregister():
    """注销模块"""
    try:
        bpy.types.VIEW3D_MT_sculpt_context_menu.remove(_append_sculpt_context_menu)
    except:
        pass