"""材质编辑器快捷操作：切换颜色空间和 Alpha 模式

同时挂载到右键菜单和着色器编辑器顶部菜单。
"""

import bpy


class MMY_OT_ToggleColorSpace(bpy.types.Operator):
    """切换选中贴图节点的颜色空间（sRGB ↔ Non-Color）"""
    bl_idname = "mmy.toggle_color_space"
    bl_label = "Toggle sRGB / Non-Color (切换色彩空间)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def execute(self, context):
        count = 0
        for node in context.selected_nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                try:
                    current = node.image.colorspace_settings.name
                    if current in ('sRGB', 'sRGB OETF'):
                        node.image.colorspace_settings.name = 'Non-Color'
                    else:
                        node.image.colorspace_settings.name = 'sRGB'
                    count += 1
                except:
                    pass
        if count > 0:
            self.report({'INFO'}, f"已切换 {count} 个贴图节点的颜色空间")
        return {'FINISHED'}


class MMY_OT_ToggleAlphaMode(bpy.types.Operator):
    """切换选中贴图节点的 Alpha 模式（Straight ↔ Channel Packed）"""
    bl_idname = "mmy.toggle_alpha_mode"
    bl_label = "Toggle Alpha: Straight ↔ Packed (切换Alpha模式)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def execute(self, context):
        count = 0
        for node in context.selected_nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                try:
                    current = node.image.alpha_mode
                    if current == 'STRAIGHT':
                        node.image.alpha_mode = 'CHANNEL_PACKED'
                    elif current == 'CHANNEL_PACKED':
                        node.image.alpha_mode = 'STRAIGHT'
                    else:
                        node.image.alpha_mode = 'CHANNEL_PACKED'
                    count += 1
                except Exception as e:
                    print(f"[MMY] 切换Alpha模式失败 {node.image.name}: {e}")
        if count > 0:
            self.report({'INFO'}, f"已切换 {count} 个贴图节点的 Alpha 模式")
        return {'FINISHED'}


_classes = (
    MMY_OT_ToggleColorSpace,
    MMY_OT_ToggleAlphaMode,
)


def _has_image_node(context):
    """检查是否有选中的图片节点"""
    selected = getattr(context, 'selected_nodes', [])
    return any(node.type == 'TEX_IMAGE' for node in selected)


def _draw_context_menu(self, context):
    """右键菜单：仅在有选中的图片节点时显示"""
    if not _has_image_node(context):
        return
    self.layout.separator()
    self.layout.operator("mmy.toggle_color_space", icon='COLOR')
    self.layout.operator("mmy.toggle_alpha_mode", icon='FILE_REFRESH')


def _draw_header_menu(self, context):
    """顶部菜单：仅在有选中的图片节点时显示"""
    if context.space_data.type != 'NODE_EDITOR':
        return
    if not _has_image_node(context):
        return
    self.layout.separator()
    row = self.layout.row(align=True)
    row.operator("mmy.toggle_color_space", text="", icon='COLOR')
    row.operator("mmy.toggle_alpha_mode", text="", icon='FILE_REFRESH')


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

    # 右键菜单
    try:
        bpy.types.NODE_MT_context_menu.append(_draw_context_menu)
    except:
        pass

    # 顶部菜单
    try:
        bpy.types.NODE_HT_header.append(_draw_header_menu)
    except:
        pass


def unregister():
    try:
        bpy.types.NODE_MT_context_menu.remove(_draw_context_menu)
    except:
        pass
    try:
        bpy.types.NODE_HT_header.remove(_draw_header_menu)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
