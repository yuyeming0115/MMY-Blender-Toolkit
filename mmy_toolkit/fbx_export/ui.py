# -*- coding: utf-8 -*-
"""FBX 导出侧边栏面板"""

import bpy
from bpy.types import Panel, UIList


class MMYFbx_UL_nla_tracks(UIList):
    """NLA轨道列表"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "enabled", text="")
            layout.label(text=item.label, icon='NLA')


class MMY_PT_FbxExport(Panel):
    """FBX 规范化导出面板"""
    bl_label = "FBX 规范化导出"
    bl_idname = "MMY_PT_fbx_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mmy_fbx_settings

        # 导出路径
        box = layout.box()
        box.label(text="导出路径", icon='EXPORT')
        row = box.row(align=True)
        row.prop(settings, "export_path", text="")
        row.operator("mmy.open_export_folder", text="", icon='FOLDER_REDIRECT')

        # 导出选项折叠区域
        box = layout.box()
        icon = 'TRIA_RIGHT' if settings.export_options_collapsed else 'TRIA_DOWN'
        row = box.row(align=True)
        row.prop(settings, "export_options_collapsed", text="", icon=icon, emboss=False)
        row.label(text="导出选项", icon='PREFERENCES')

        if not settings.export_options_collapsed:
            # 快速选项
            box.label(text="快速选项", icon='DOT')
            grid = box.grid_flow(row_major=True, columns=2, even_columns=True)
            grid.prop(settings, "quick_selected_only")
            grid.prop(settings, "quick_batch_export")
            grid.prop(settings, "use_date_folder")
            grid.prop(settings, "quick_export_textures")

            if settings.quick_export_textures:
                row = box.row(align=True)
                row.label(text="贴图尺寸:", icon='IMAGE')
                row.prop(settings, "texture_resize_mode", text="")
                box.prop(settings, "keep_original_texture_names")

            box.separator(factor=0.5)
            box.label(text="变换处理", icon='OBJECT_ORIGIN')
            grid = box.grid_flow(row_major=True, columns=2)
            grid.prop(settings, "quick_reset_transforms")
            grid.prop(settings, "quick_zero_transforms")

            box.separator(factor=0.5)
            box.label(text="几何数据", icon='MESH_DATA')
            grid = box.grid_flow(row_major=True, columns=2)
            grid.prop(settings, "tangent_space")
            grid.prop(settings, "triangulate_faces")

            box.separator(factor=0.5)
            box.label(text="骨架", icon='ARMATURE_DATA')
            grid = box.grid_flow(row_major=True, columns=2)
            grid.prop(settings, "deform_bones")
            grid.prop(settings, "leaf_bones")
            row = box.row(align=True)
            row.prop(settings, "primary_bbone_axis", text="主轴")
            row.prop(settings, "secondary_bbone_axis", text="次轴")

        # NLA动画
        box = layout.box()
        box.label(text="NLA动画", icon='NLA')
        row = box.row()
        row.operator("mmy.refresh_nla_list", text="刷新NLA列表", icon='FILE_REFRESH')

        if settings.nla_items:
            rows = min(6, max(3, len(settings.nla_items)))
            box.template_list("MMYFbx_UL_nla_tracks", "", settings, "nla_items", settings, "nla_active_index", rows=rows)
            enabled_count = sum(1 for item in settings.nla_items if item.enabled)
            box.label(text=f"已选 {enabled_count}/{len(settings.nla_items)}", icon='INFO')
        else:
            box.label(text="当前选择无NLA轨道", icon='INFO')

        # 导出按钮
        layout.separator()
        col = layout.column(align=True)
        col.scale_y = 1.5

        row_fbx = col.row(align=True)
        row_fbx.operator("mmy.quick_export_fbx", icon='EXPORT')
        row_fbx.prop(settings, "quick_independent_export", text="单个FBX", toggle=True)

        col.operator("mmy.quick_export_animation_fbx", icon='ARMATURE_DATA')
        col.operator("mmy.native_export_fbx", icon='BLENDER', text="原生FBX")


_classes = (MMYFbx_UL_nla_tracks, MMY_PT_FbxExport)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)