# 语言切换操作符

import bpy


class MMY_OT_ToggleTranslation(bpy.types.Operator):
    """切换界面语言翻译"""
    bl_idname = "mmy.toggle_translation"
    bl_label = "切换语言"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        if event.ctrl:
            # Ctrl: 打开偏好设置
            bpy.ops.screen.userpref_show()
            bpy.context.preferences.active_section = "ADDONS"
            bpy.context.window_manager.addon_search = "MMY"
        else:
            # 切换翻译
            view = context.preferences.view
            current = view.use_translate_interface
            view.use_translate_interface = not current
            view.use_translate_tooltips = view.use_translate_interface
            view.use_translate_new_dataname = view.use_translate_interface

            # 显示切换结果
            status = "中文" if view.use_translate_interface else "英文"
            self.report({'INFO'}, f"界面语言: {status}")

        return {'FINISHED'}