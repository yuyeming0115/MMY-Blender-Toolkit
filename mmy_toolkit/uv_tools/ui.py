# -*- coding: utf-8 -*-
"""UV 工具 UI 面板"""

import os
import bpy


class VIEW3D_PT_uv_hub(bpy.types.Panel):
    """UV 中台面板 - 3D视图（含 RizomUV 桥接）"""
    bl_label = "UV 中台"
    bl_idname = "VIEW3D_PT_mmy_uv_hub"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = context.preferences.addons.get("mmy_toolkit")
        ruv_enabled = prefs is not None and getattr(prefs.preferences, "rizomuv_enable", True)
        ruv_prefs = prefs.preferences if prefs else None

        # ── UV传递区域 ──
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

        # ── UVMap检查区域 ──
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

            for obj in selected_meshes[:5]:
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

            # 统一UVMap名称
            unify_row = box.row(align=True)
            unify_row.prop(scene, "uv_unified_name", text="")
            unify_row.operator("object.mmy_unify_uvmap_name", text="统一", icon='SORTALPHA')

        # ── RizomUV桥接区域 ──
        if ruv_enabled and ruv_prefs:
            layout.separator()
            ruv_box = layout.box()
            ruv_box.label(text="RizomUV 桥接", icon='COMMUNITY')

            ruv_path = ruv_prefs.rizomuv_app_path
            multi_uv = ruv_prefs.rizomuv_multi_uv
            has_path = bool(ruv_path)

            # 模式和UV通道选择
            if not multi_uv:
                row = ruv_box.row(align=True)
                row.prop(scene, "uv_ruv_mode", text="", icon='GROUP_UVS')
                row.prop(scene, "uv_ruv_map", text="通道")

            # 发送/回取按钮
            col = ruv_box.column(align=True)
            col.enabled = has_path
            col.operator("uv.mmy_send_to_rizomuv", text="发送到 RizomUV", icon='EXPORT')
            col.operator("uv.mmy_retake_rizomuv", text="手动回取 UV", icon='IMPORT')

            # 路径未设置时提示
            if not has_path:
                ruv_box.label(text="请先在偏好设置中配置 RizomUV 路径", icon='ERROR')

            # 多UV和自动关闭选项
            row = ruv_box.row(align=True)
            row.prop(ruv_prefs, "rizomuv_multi_uv", text="多通道")
            row.prop(ruv_prefs, "rizomuv_exit_after_save", text="自动关闭")

            # 展开参数（折叠）
            icon = 'TRIA_RIGHT' if not ruv_prefs.rizomuv_unwrap_tab else 'TRIA_DOWN'
            row = ruv_box.row(align=True)
            row.prop(ruv_prefs, "rizomuv_unwrap_tab", text="", icon=icon, emboss=False)
            row.label(text="展开参数")

            if ruv_prefs.rizomuv_unwrap_tab:
                sub = ruv_box.column(align=True)
                r = sub.row(align=True)
                r.prop(ruv_prefs, "rizomuv_unwrap_unfold_itr", text="展开")
                r.prop(ruv_prefs, "rizomuv_unwrap_optimize_itr", text="优化")
                row = sub.row(align=True)
                row.prop(ruv_prefs, "rizomuv_unwrap_tflips")
                row.prop(ruv_prefs, "rizomuv_unwrap_free")
                row = sub.row(align=True)
                row.prop(ruv_prefs, "rizomuv_unwrap_fill")
                row.prop(ruv_prefs, "rizomuv_unwrap_keep_metric")
                sub.prop(ruv_prefs, "rizomuv_unwrap_overlaps")
                if ruv_prefs.rizomuv_unwrap_overlaps:
                    sub.prop(ruv_prefs, "rizomuv_unwrap_overlaps_dist", text="间距")

            # 排列参数（折叠）
            icon = 'TRIA_RIGHT' if not ruv_prefs.rizomuv_layout_tab else 'TRIA_DOWN'
            row = ruv_box.row(align=True)
            row.prop(ruv_prefs, "rizomuv_layout_tab", text="", icon=icon, emboss=False)
            row.label(text="排列参数")

            if ruv_prefs.rizomuv_layout_tab:
                sub = ruv_box.column(align=True)
                r = sub.row(align=True)
                r.prop(ruv_prefs, "rizomuv_layout_margin", text="边距")
                r.prop(ruv_prefs, "rizomuv_layout_spacing", text="间距")
                sub.prop(ruv_prefs, "rizomuv_layout_map_size", text="分辨率")


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
    IMAGE_EDITOR_PT_uv_export_tools,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)