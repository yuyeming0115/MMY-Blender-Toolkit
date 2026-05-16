import bpy


class VIEW3D_PT_MMYMeshTools(bpy.types.Panel):
    """MMY网格工具面板"""
    bl_label = "MMY网格工具"
    bl_idname = "VIEW3D_PT_MMY_mesh_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj.mode == 'EDIT':
            box = layout.box()
            box.label(text="缝合边工具", icon='MESH_DATA')
            row = box.row()
            row.operator("mmy.mark_uv_island_seams")
            row.scale_y = 1.5
        else:
            layout.label(text="请进入编辑模式", icon='INFO')


_classes = (
    VIEW3D_PT_MMYMeshTools,
)


def register():
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

    # 添加右键菜单项
    try:
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(_append_context_menu)
    except:
        pass


def unregister():
    # 移除右键菜单项
    try:
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(_append_context_menu)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _append_context_menu(self, context):
    """在编辑模式右键菜单中添加缝合边操作"""
    layout = self.layout
    obj = context.active_object
    if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
        layout.separator()
        layout.operator("mmy.mark_uv_island_seams", icon='MESH_DATA')