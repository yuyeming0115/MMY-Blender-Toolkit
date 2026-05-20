"""Poly @ Edit N面板"""

import bpy
import bmesh
from .lang import get_text, get_text_formatted


class VIEW3D_PT_mmy_poly_edit(bpy.types.Panel):
    """Poly @ Edit 主面板"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMY工具'
    bl_label = "Poly @ Edit"

    def draw(self, context):
        pass


class VIEW3D_PT_mmy_poly_edit_smooth_groups(bpy.types.Panel):
    """平滑组面板"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMY工具'
    bl_label = "平滑组"
    bl_parent_id = "VIEW3D_PT_mmy_poly_edit"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        obj = context.object
        scene = context.scene

        if obj.mode != 'EDIT':
            layout.label(text=get_text("enter_edit_mode"), icon='EDITMODE_HLT')
            return

        # 显示选项
        box_opt = layout.box()
        row = box_opt.row(align=True)
        row.prop(scene, "mmy_poly_edit_show_overlay", text=get_text("show_ids"), icon='TEXT')
        if scene.mmy_poly_edit_show_overlay:
            row.prop(scene, "mmy_poly_edit_overlay_selected_only", text=get_text("sel_only"), toggle=True)

        row = box_opt.row(align=True)
        row.prop(scene, "mmy_poly_edit_hide_sharp_display", text=get_text("hide_sharp"),
                 icon='HIDE_ON' if scene.mmy_poly_edit_hide_sharp_display else 'HIDE_OFF')

        # 交互模式
        layout.separator()
        layout.label(text=get_text("interaction_mode"))
        row = layout.row(align=True)

        items = [
            ('SET', get_text("mode_set")),
            ('SELECT', get_text("mode_select"))
        ]

        for value, text in items:
            is_active = (scene.mmy_poly_edit_interaction_mode == value)
            op = row.operator("wm.context_set_enum", text=text, depress=is_active)
            op.data_path = "scene.mmy_poly_edit_interaction_mode"
            op.value = value

        # 按钮网格
        box = layout.box()
        col = box.column(align=True)

        bm = bmesh.from_edit_mesh(obj.data)
        active_sg = 0
        used_sg_mask = 0
        sg_layer = bm.faces.layers.int.get("smoothing_groups")

        if sg_layer:
            if bm.faces.active:
                active_sg = bm.faces.active[sg_layer]
            if scene.mmy_poly_edit_interaction_mode == 'SELECT':
                for f in bm.faces:
                    used_sg_mask |= f[sg_layer]

        is_select_mode = (scene.mmy_poly_edit_interaction_mode == 'SELECT')
        if is_select_mode:
            box.label(text=get_text("click_to_select"), icon='RESTRICT_SELECT_OFF')
            box.label(text=get_text("select_mode_hint"), icon='EVENT_SHIFT')

        for row_idx in range(4):
            row = col.row(align=True)
            for col_idx in range(8):
                idx = row_idx * 8 + col_idx + 1
                bit_mask = 1 << (idx - 1)

                if is_select_mode:
                    is_active = (used_sg_mask & bit_mask) != 0
                else:
                    is_active = (active_sg & bit_mask) != 0

                op = row.operator("mmy.set_sg", text=str(idx), depress=is_active)
                op.group_id = idx

        # 底部按钮
        layout.separator()
        layout.operator("mmy.clear_sg", text=get_text("clear_selected"), icon='X')
        layout.operator("mmy.reset_normal_system", text=get_text("fix_shading"), icon='BRUSH_DATA')


class VIEW3D_PT_mmy_poly_edit_selection_sets(bpy.types.Panel):
    """选择集面板"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMY工具'
    bl_label = "选择集"
    bl_parent_id = "VIEW3D_PT_mmy_poly_edit"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        row = box.row(align=True)
        row.label(text=get_text("quick_operations"), icon='INFO')

        grid = box.grid_flow(row_major=True, align=True)
        grid.label(text=get_text("click_normal"), icon='RESTRICT_SELECT_OFF')
        grid.label(text=get_text("click_shift"), icon='ADD')
        grid.label(text=get_text("click_ctrl"), icon='REMOVE')

        scene = context.scene

        col = layout.column()

        if not scene.mmy_poly_edit_selection_sets:
            layout.label(text=get_text("no_selection_sets"), icon='INFO')
        else:
            for idx, sel_set in enumerate(scene.mmy_poly_edit_selection_sets):
                is_edit_set = sel_set.name.startswith('-') and sel_set.name.endswith('-')

                box = col.box()

                header = box.box()
                header_row = header.row(align=True)

                if is_edit_set:
                    header_row.label(text=get_text("edit_mode"), icon='EDITMODE_HLT')
                else:
                    header_row.label(text=get_text("object_mode"), icon='OBJECT_DATA')

                display_name = sel_set.name.strip('-')
                name_col = header_row.column()
                name_col.label(text=display_name)

                grid = box.grid_flow(row_major=True, align=True)

                load_row = grid.row(align=True)
                load_row.label(text=get_text("load_label"))

                replace_op = load_row.operator(
                    "mmy.load_selection_set",
                    text="替换",
                    icon='RESTRICT_SELECT_OFF'
                )
                replace_op.set_name = sel_set.name
                replace_op.mode = 'REPLACE'

                add_op = load_row.operator(
                    "mmy.load_selection_set",
                    text="加选",
                    icon='ADD'
                )
                add_op.set_name = sel_set.name
                add_op.mode = 'ADD'

                subtract_op = load_row.operator(
                    "mmy.load_selection_set",
                    text="减选",
                    icon='REMOVE'
                )
                subtract_op.set_name = sel_set.name
                subtract_op.mode = 'SUBTRACT'

                btn_row = box.row(align=True)

                update_op = btn_row.operator(
                    "mmy.update_selection_set",
                    text=get_text("update_selection_set"),
                    icon='FILE_REFRESH'
                )
                update_op.set_index = idx

                rename_op = btn_row.operator(
                    "mmy.rename_selection_set",
                    text=get_text("rename_selection_set"),
                    icon='GREASEPENCIL'
                )
                rename_op.set_index = idx

                delete_op = btn_row.operator(
                    "mmy.delete_selection_set",
                    text=get_text("delete_selection_set"),
                    icon='TRASH'
                )
                delete_op.set_index = idx

        layout.operator(
            "mmy.save_selection_set",
            text=get_text("new_selection_set"),
            icon='ADD'
        )


_classes = (
    VIEW3D_PT_mmy_poly_edit,
    VIEW3D_PT_mmy_poly_edit_smooth_groups,
    VIEW3D_PT_mmy_poly_edit_selection_sets,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass