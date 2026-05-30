# -*- coding: utf-8 -*-
"""UV 工具 UI 面板"""

import os
import bpy


class VIEW3D_PT_uv_hub(bpy.types.Panel):
    """UV 中台面板 - 3D视图"""
    bl_label = "UV 中台"
    bl_idname = "VIEW3D_PT_mmy_uv_hub"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # UV传递区域
        box = layout.box()
        box.label(text="UV传递", icon='UV')

        row = box.row()
        row.alert = not scene.uv_source_object
        row.prop(scene, "uv_source_object", text="新UV对象")

        row = box.row()
        row.alert = not scene.uv_target_object
        row.prop(scene, "uv_target_object", text="绑定对象")

        row = box.row(align=True)
        row.operator("object.mmy_transfer_uv", text="传递UV", icon='ARROW_LEFTRIGHT')

        layout.separator()

        # UVMap检查区域
        box = layout.box()
        box.label(text="UVMap检查", icon='GROUP_UVS')

        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_meshes:
            box.label(text="未选中mesh对象", icon='INFO')
        else:
            uv_names = set()
            for obj in selected_meshes:
                if obj.data.uv_layers:
                    for uv in obj.data.uv_layers:
                        uv_names.add(uv.name)

            is_inconsistent = len(uv_names) > 1

            if is_inconsistent:
                warning_row = box.row()
                warning_row.alert = True
                warning_row.label(text="UVMap名称不统一", icon='ERROR')

            for obj in selected_meshes[:5]:  # 最多显示5个
                row = box.row()
                row.label(text=obj.name, icon='OBJECT_DATA')

                if obj.data.uv_layers:
                    uv_text = ", ".join([uv.name for uv in obj.data.uv_layers])
                    if len(uv_text) > 20:
                        uv_text = uv_text[:17] + "..."
                    uv_row = row.row()
                    if is_inconsistent:
                        uv_row.alert = True
                    uv_row.label(text=uv_text)
                else:
                    row.label(text="无UV", icon='X')

            if len(selected_meshes) > 5:
                box.label(text=f"... 还有 {len(selected_meshes) - 5} 个对象")

            layout.separator()

            # 统一UVMap名称
            unify_box = layout.box()
            unify_box.label(text="统一UVMap名称", icon='SORTALPHA')
            unify_box.prop(scene, "uv_unified_name", text="目标名称")
            unify_box.operator("object.mmy_unify_uvmap_name", text="统一选中对象")


class VIEW3D_PT_rizomuv_tools(bpy.types.Panel):
    """RizomUV 桥接面板 - 3D视图"""
    bl_label = "RizomUV 桥接"
    bl_idname = "VIEW3D_PT_mmy_rizomuv_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        prefs = context.preferences.addons.get("mmy_toolkit")
        if prefs is None:
            return False
        return (
            ob is not None
            and ob.type == 'MESH'
            and context.mode == 'OBJECT'
            and getattr(prefs.preferences, "rizomuv_enable", True)
        )

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = context.preferences.addons["mmy_toolkit"].preferences

        ruv_path = prefs.rizomuv_app_path
        multi_uv = prefs.rizomuv_multi_uv
        has_path = bool(ruv_path)

        # 模式和UV通道选择
        if not multi_uv:
            row = layout.row(align=True)
            row.prop(scene, "uv_ruv_mode", text="", icon='GROUP_UVS')
            row.prop(scene, "uv_ruv_map", text="通道")

        # 发送按钮
        col = layout.column(align=True)
        col.enabled = has_path
        col.operator("uv.mmy_send_to_rizomuv", text="发送到 RizomUV", icon='EXPORT')

        # 手动回取按钮
        col.operator("uv.mmy_retake_rizomuv", text="手动回取 UV", icon='IMPORT')

        # 路径未设置时提示
        if not has_path:
            layout.label(text="请先在偏好设置中配置 RizomUV 路径", icon='ERROR')

        # 多UV和自动关闭选项
        layout.separator()
        row = layout.row(align=True)
        row.prop(prefs, "rizomuv_multi_uv", text="多通道")
        row.prop(prefs, "rizomuv_exit_after_save", text="自动关闭")

        # 展开参数（折叠）
        layout.separator()
        box = layout.box()
        icon = 'TRIA_RIGHT' if not prefs.rizomuv_unwrap_tab else 'TRIA_DOWN'
        row = box.row(align=True)
        row.prop(prefs, "rizomuv_unwrap_tab", text="", icon=icon, emboss=False)
        row.label(text="展开参数", icon='SETTINGS')

        if prefs.rizomuv_unwrap_tab:
            sub = box.column(align=True)
            r = sub.row(align=True)
            r.prop(prefs, "rizomuv_unwrap_unfold_itr")
            r.prop(prefs, "rizomuv_unwrap_optimize_itr")
            sub.prop(prefs, "rizomuv_unwrap_tflips")
            sub.prop(prefs, "rizomuv_unwrap_free")
            sub.prop(prefs, "rizomuv_unwrap_fill")
            sub.prop(prefs, "rizomuv_unwrap_keep_metric")
            sub.prop(prefs, "rizomuv_unwrap_overlaps")
            if prefs.rizomuv_unwrap_overlaps:
                sub.prop(prefs, "rizomuv_unwrap_overlaps_dist")

        # 排列参数（折叠）
        box = layout.box()
        icon = 'TRIA_RIGHT' if not prefs.rizomuv_layout_tab else 'TRIA_DOWN'
        row = box.row(align=True)
        row.prop(prefs, "rizomuv_layout_tab", text="", icon=icon, emboss=False)
        row.label(text="排列参数", icon='PACKAGE')

        if prefs.rizomuv_layout_tab:
            sub = box.column(align=True)
            r = sub.row(align=True)
            r.prop(prefs, "rizomuv_layout_margin")
            r.prop(prefs, "rizomuv_layout_spacing")
            sub.prop(prefs, "rizomuv_layout_map_size")


class IMAGE_EDITOR_PT_uv_export_tools(bpy.types.Panel):
    """UV 快速导出面板 - UV编辑器"""
    bl_label = "UV 工具"
    bl_idname = "IMAGE_EDITOR_PT_mmy_uv_export_tools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "MMY工具"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'IMAGE_EDITOR' and space.mode == 'UV'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # UV显示辅助
        box = layout.box()
        box.label(text="显示辅助", icon='OVERLAY')

        row = box.row(align=True)
        row.prop(scene, "uv_show_stretch", text="拉伸")
        row.prop(scene, "uv_show_overlap", text="重叠")

        if scene.uv_show_stretch:
            box.row(align=True).prop(scene, "uv_stretch_type", expand=True)

        if scene.uv_show_overlap:
            overlap_col = box.column(align=True)
            overlap_col.prop(scene, "uv_overlap_selection_mode", text="")
            overlap_col.operator("uv.mmy_detect_overlap_highlight", text="立即检测", icon='VIEWZOOM').silent = False

            invert_row = overlap_col.row()
            invert_row.enabled = bool(getattr(scene, "uv_cached_overlap_faces", ""))
            invert_row.operator("uv.mmy_invert_overlap_selection", text="反选重叠面")

            overlap_col.label(text=f"重叠面: {scene.uv_overlap_face_count}")

        layout.separator()

        # 快速导出
        box = layout.box()
        box.label(text="快速导出", icon='EXPORT')

        row = box.row(align=True)
        row.operator("uv.mmy_quick_export_layout", text="512").target_size = 512
        row.operator("uv.mmy_quick_export_layout", text="1024").target_size = 1024

        row = box.row(align=True)
        row.operator("uv.mmy_quick_export_layout", text="2048").target_size = 2048
        row.operator("uv.mmy_quick_export_layout", text="4096").target_size = 4096

        # Photoshop联动
        layout.separator()
        box = layout.box()
        box.label(text="Photoshop", icon='IMAGE_DATA')

        action_row = box.row()
        action_row.enabled = bool(scene.uv_last_export_path)
        action_row.operator("uv.mmy_open_last_export_in_photoshop", text="发送到 Photoshop")

        last_name = "无"
        if scene.uv_last_export_path:
            last_name = os.path.basename(scene.uv_last_export_path)
            if len(last_name) > 20:
                last_name = last_name[:17] + "..."
        box.label(text=f"最近: {last_name}", icon='FILE_IMAGE')


classes = (
    VIEW3D_PT_uv_hub,
    VIEW3D_PT_rizomuv_tools,
    IMAGE_EDITOR_PT_uv_export_tools,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)