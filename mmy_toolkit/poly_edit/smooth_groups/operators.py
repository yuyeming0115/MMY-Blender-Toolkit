"""平滑组操作符"""

import bpy
import bmesh
import time
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty

from .algo import calc_max_style_normals, hide_sharp_edge_overlay
from ..ui.lang import get_text, get_text_formatted
from .overlay import register_overlay, unregister_overlay


def safe_bit_mask(group_id):
    """获取安全的位掩码，处理 Group 32 的符号位溢出问题"""
    if group_id < 1 or group_id > 32:
        return 0

    bit_mask = 1 << (group_id - 1)

    if bit_mask > 0x7FFFFFFF:
        bit_mask = bit_mask - 0x100000000

    return bit_mask


def check_bit(value, group_id):
    """检查某个 group_id 是否在 value 中被设置"""
    bit_mask = safe_bit_mask(group_id)
    return (value & bit_mask) != 0


class MESH_OT_set_true_sg_v3(Operator):
    """Assign smoothing group to selected faces"""
    bl_idname = "mmy.set_sg"
    bl_label = "Set Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_id: bpy.props.IntProperty()
    toggle: bpy.props.BoolProperty(default=True)
    force_mode: bpy.props.StringProperty(default="")
    select_modifier: bpy.props.StringProperty(default='NONE')

    def invoke(self, context, event):
        if event.shift:
            self.select_modifier = 'SHIFT'
        elif event.ctrl:
            self.select_modifier = 'CTRL'
        else:
            self.select_modifier = 'NONE'
        return self.execute(context)

    def execute(self, context):
        mode = 'SET'
        if hasattr(context.scene, "mmy_poly_edit_interaction_mode"):
            mode = self.force_mode if self.force_mode else context.scene.mmy_poly_edit_interaction_mode

        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        sg_layer = bm.faces.layers.int.get("smoothing_groups")
        if not sg_layer:
            sg_layer = bm.faces.layers.int.new("smoothing_groups")

        bit_mask = safe_bit_mask(self.group_id)

        if mode == 'SELECT':
            if self.select_modifier == 'CTRL':
                removed_count = 0
                for f in bm.faces:
                    if f.select and check_bit(f[sg_layer], self.group_id):
                        f.select = False
                        removed_count += 1
                bmesh.update_edit_mesh(me)

                if removed_count > 0:
                    msg = get_text_formatted("msg_deselected_faces", count=removed_count, group=self.group_id)
                    self.report({'INFO'}, msg)
                else:
                    msg = get_text_formatted("msg_no_faces_to_deselect", group=self.group_id)
                    self.report({'WARNING'}, msg)
                return {'FINISHED'}

            elif self.select_modifier == 'SHIFT':
                added_count = 0
                for f in bm.faces:
                    if check_bit(f[sg_layer], self.group_id):
                        if not f.select:
                            f.select = True
                            added_count += 1
                bmesh.update_edit_mesh(me)

                if added_count > 0:
                    msg = get_text_formatted("msg_added_faces", count=added_count, group=self.group_id)
                    self.report({'INFO'}, msg)
                else:
                    msg = get_text_formatted("msg_no_faces", group=self.group_id)
                    self.report({'WARNING'}, msg)
                return {'FINISHED'}

            else:
                bpy.ops.mesh.select_all(action='DESELECT')
                found_count = 0
                for f in bm.faces:
                    f.select = False
                    if check_bit(f[sg_layer], self.group_id):
                        f.select = True
                        found_count += 1
                bmesh.update_edit_mesh(me)

                if found_count > 0:
                    msg = get_text_formatted("msg_selected_faces", count=found_count, group=self.group_id)
                    self.report({'INFO'}, msg)
                else:
                    msg = get_text_formatted("msg_no_faces", group=self.group_id)
                    self.report({'WARNING'}, msg)
                return {'FINISHED'}

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            return {'CANCELLED'}

        all_have_group = True
        for f in selected_faces:
            if not check_bit(f[sg_layer], self.group_id):
                all_have_group = False
                break

        should_add = not all_have_group

        for f in selected_faces:
            current_val = f[sg_layer]
            if self.toggle:
                if should_add:
                    new_val = current_val | bit_mask
                else:
                    new_val = current_val & ~bit_mask
            else:
                new_val = current_val | bit_mask

            if new_val > 0x7FFFFFFF:
                new_val = new_val - 0x100000000
            f[sg_layer] = new_val

        bmesh.update_edit_mesh(me)

        bpy.ops.object.mode_set(mode='OBJECT')
        calc_max_style_normals(me)
        hide_sharp_edge_overlay()
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


class MESH_OT_reset_normal_system(Operator):
    """Fix shading errors. Clear all plugin data."""
    bl_idname = "mmy.reset_normal_system"
    bl_label = "Fix Shading Errors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        sg_layer = bm.faces.layers.int.get("smoothing_groups")
        if sg_layer:
            for f in bm.faces:
                f[sg_layer] = 0

        for edge in bm.edges:
            edge.smooth = True

        bmesh.update_edit_mesh(me)

        bpy.ops.object.mode_set(mode='OBJECT')

        if hasattr(me, "normals_split_custom_clear"):
            me.normals_split_custom_clear()
            if hasattr(me, "use_auto_smooth"):
                me.use_auto_smooth = False
        else:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            if hasattr(bpy.ops.mesh, "customdata_custom_splitnormals_clear"):
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.mode_set(mode='EDIT')

        msg = get_text("msg_fix_done")
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class MESH_OT_clear_sg_v3(Operator):
    """Clear smoothing groups from selected faces"""
    bl_idname = "mmy.clear_sg"
    bl_label = "Clear Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        sg_layer = bm.faces.layers.int.get("smoothing_groups")

        if sg_layer:
            for f in bm.faces:
                if f.select:
                    f[sg_layer] = 0
            bmesh.update_edit_mesh(me)

            bpy.ops.object.mode_set(mode='OBJECT')
            calc_max_style_normals(me)
            hide_sharp_edge_overlay()
            bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


_classes = (
    MESH_OT_set_true_sg_v3,
    MESH_OT_reset_normal_system,
    MESH_OT_clear_sg_v3,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 交互模式
    bpy.types.Scene.mmy_poly_edit_interaction_mode = bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('SET', "Set / Toggle", "Click to assign group to selected faces"),
            ('SELECT', "Select Faces", "Click to select all faces with this group ID")
        ],
        default='SET'
    )

    # Overlay 开关
    def update_overlay(self, context):
        from .overlay import register_overlay, unregister_overlay
        if self.mmy_poly_edit_show_overlay:
            register_overlay()
        else:
            unregister_overlay()

    bpy.types.Scene.mmy_poly_edit_show_overlay = bpy.props.BoolProperty(
        name="Show IDs",
        default=False,
        update=update_overlay
    )

    # 仅选中
    bpy.types.Scene.mmy_poly_edit_overlay_selected_only = bpy.props.BoolProperty(
        name="Selected Only",
        default=True
    )

    # 隐藏锐边显示
    def update_hide_sharp(self, context):
        from .algo import hide_sharp_edge_overlay, show_sharp_edge_overlay
        if self.mmy_poly_edit_hide_sharp_display:
            hide_sharp_edge_overlay()
        else:
            show_sharp_edge_overlay()

    bpy.types.Scene.mmy_poly_edit_hide_sharp_display = bpy.props.BoolProperty(
        name="Hide Sharp Edges",
        default=True,
        update=update_hide_sharp
    )


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    try:
        unregister_overlay()
    except:
        pass

    del bpy.types.Scene.mmy_poly_edit_hide_sharp_display
    del bpy.types.Scene.mmy_poly_edit_overlay_selected_only
    del bpy.types.Scene.mmy_poly_edit_show_overlay
    del bpy.types.Scene.mmy_poly_edit_interaction_mode