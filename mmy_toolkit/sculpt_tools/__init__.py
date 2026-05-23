"""雕刻工具模块 - 面组菜单（右键菜单入口）"""

import bpy


class MMY_MT_SculptFaceSets(bpy.types.Menu):
    """面组菜单"""
    bl_idname = "MMY_MT_sculpt_face_sets"
    bl_label = "面组"

    def draw(self, context):
        layout = self.layout

        # 创建面组
        layout.label(text="创建")
        layout.operator("sculpt.face_sets_create", text="从遮罩创建").mode = 'MASKED'
        layout.operator("sculpt.face_sets_create", text="从可见面创建").mode = 'VISIBLE'
        layout.operator("sculpt.face_sets_create", text="全部").mode = 'ALL'

        layout.separator()

        # 可见性控制
        layout.label(text="可见性")
        layout.operator("sculpt.face_set_change_visibility", text="切换显示")
        layout.operator("sculpt.face_set_invert_visibility", text="反转可见性")

        layout.separator()

        # 全局控制
        layout.label(text="全局")
        layout.operator("sculpt.face_set_hide_all", text="隐藏全部")
        layout.operator("sculpt.face_set_show_all", text="显示全部")

        layout.separator()

        # 编辑功能
        layout.label(text="编辑")
        layout.operator("sculpt.face_set_edit", text="填充面组").mode = 'GROW'
        layout.operator("sculpt.face_set_edit", text="收缩面组").mode = 'SHRINK'


_classes = (MMY_MT_SculptFaceSets,)


def _draw_sculpt_context_menu(self, context):
    """扩展雕刻模式右键菜单"""
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'SCULPT':
        return

    layout = self.layout
    layout.separator()

    # 添加面组菜单
    layout.menu("MMY_MT_sculpt_face_sets", text="面组", icon='GROUP_VERTEX')


def register():
    """注册模块"""
    # 注册菜单类
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

    # 挂载到雕刻模式右键菜单
    try:
        bpy.types.VIEW3D_MT_sculpt_context_menu.append(_draw_sculpt_context_menu)
        print("[MMY Sculpt] 面组菜单已添加到雕刻右键菜单")
    except Exception as e:
        print(f"[MMY Sculpt] 挂载右键菜单失败: {e}")


def unregister():
    """注销模块"""
    # 移除右键菜单挂载
    try:
        bpy.types.VIEW3D_MT_sculpt_context_menu.remove(_draw_sculpt_context_menu)
    except:
        pass

    # 注销菜单类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass