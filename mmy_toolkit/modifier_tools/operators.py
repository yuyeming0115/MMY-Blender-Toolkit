# 修改器显示切换操作符

import bpy


class MMY_OT_ToggleAllModifiersViewport(bpy.types.Operator):
    """切换所有修改器视口显示"""
    bl_idname = "mmy.toggle_all_modifiers_viewport"
    bl_label = "全部显示/隐藏"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.modifiers and len(obj.modifiers) > 0

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.modifiers:
            self.report({'WARNING'}, "无修改器")
            return {'CANCELLED'}

        # 智能切换：全部显示则隐藏，有隐藏则显示
        all_visible = all(mod.show_viewport for mod in obj.modifiers)
        new_state = not all_visible

        for mod in obj.modifiers:
            mod.show_viewport = new_state

        status = "显示" if new_state else "隐藏"
        self.report({'INFO'}, f"全部修改器: {status}")
        return {'FINISHED'}


_classes = (
    MMY_OT_ToggleAllModifiersViewport,
)