# 修改器显示切换操作符

import bpy


class MMY_OT_HideAllModifiers(bpy.types.Operator):
    """隐藏所有修改器并记住显隐状态"""
    bl_idname = "mmy.hide_all_modifiers"
    bl_label = "隐藏所有修改器"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.modifiers and len(obj.modifiers) > 0

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.modifiers:
            return {'CANCELLED'}

        # 保存当前状态
        state = {}
        for mod in obj.modifiers:
            state[mod.name] = mod.show_viewport
            # 隐藏所有
            mod.show_viewport = False

        # 存储到对象属性
        obj["mmy_modifier_visibility"] = str(state)

        self.report({'INFO'}, "已隐藏所有修改器")
        return {'FINISHED'}


class MMY_OT_RestoreModifierVisibility(bpy.types.Operator):
    """恢复修改器显隐状态"""
    bl_idname = "mmy.restore_modifier_visibility"
    bl_label = "恢复修改器显隐"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and "mmy_modifier_visibility" in obj

    def execute(self, context):
        obj = context.active_object
        if not obj or "mmy_modifier_visibility" not in obj:
            self.report({'WARNING'}, "无保存的状态")
            return {'CANCELLED'}

        try:
            import ast
            state = ast.literal_eval(obj["mmy_modifier_visibility"])

            restored = 0
            for mod in obj.modifiers:
                if mod.name in state:
                    mod.show_viewport = state[mod.name]
                    restored += 1

            # 清除存储
            del obj["mmy_modifier_visibility"]

            self.report({'INFO'}, f"已恢复 {restored} 个修改器状态")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"恢复失败: {str(e)}")
            return {'CANCELLED'}


class MMY_OT_ToggleAllModifiersViewport(bpy.types.Operator):
    """切换所有修改器视口显示（简单切换，不记住状态）"""
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
    MMY_OT_HideAllModifiers,
    MMY_OT_RestoreModifierVisibility,
    MMY_OT_ToggleAllModifiersViewport,
)