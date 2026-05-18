"""材质编辑器快捷操作：切换颜色空间和 Alpha 模式"""

import bpy


class MMY_OT_ToggleColorSpace(bpy.types.Operator):
    """切换选中贴图节点的颜色空间（sRGB ↔ Non-Color）"""
    bl_idname = "mmy.toggle_color_space"
    bl_label = "切换颜色空间"
    bl_description = "切换选中贴图节点的颜色空间（sRGB ↔ Non-Color）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        if not space or space.type != 'NODE_EDITOR':
            return False
        tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
        if not tree:
            return False
        for node in tree.nodes:
            if node.select and node.type == 'IMAGE_TEXTURE' and node.image:
                return True
        return False

    def execute(self, context):
        space = context.space_data
        tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
        if not tree:
            return {'CANCELLED'}

        count = 0
        for node in tree.nodes:
            if not (node.select and node.type == 'IMAGE_TEXTURE' and node.image):
                continue
            if node.color_space == 'NONE':
                node.color_space = 'sRGB'
                count += 1
            else:
                node.color_space = 'NONE'
                count += 1
        if count > 0:
            self.report({'INFO'}, f"已切换 {count} 个贴图节点的颜色空间")
        return {'FINISHED'}


class MMY_OT_ToggleAlphaMode(bpy.types.Operator):
    """切换选中贴图节点的 Alpha 模式（Straight ↔ Packed）"""
    bl_idname = "mmy.toggle_alpha_mode"
    bl_label = "切换 Alpha 模式"
    bl_description = "切换选中贴图节点的 Alpha 模式（Straight ↔ Packed）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        if not space or space.type != 'NODE_EDITOR':
            return False
        tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
        if not tree:
            return False
        for node in tree.nodes:
            if node.select and node.type == 'IMAGE_TEXTURE' and node.image:
                return True
        return False

    def execute(self, context):
        space = context.space_data
        tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
        if not tree:
            return {'CANCELLED'}

        count = 0
        for node in tree.nodes:
            if not (node.select and node.type == 'IMAGE_TEXTURE' and node.image):
                continue
            img = node.image
            if img.alpha_mode == 'PREMUL':
                img.alpha_mode = 'STRAIGHT'
                count += 1
            else:
                img.alpha_mode = 'PREMUL'
                count += 1
        if count > 0:
            self.report({'INFO'}, f"已切换 {count} 个贴图节点的 Alpha 模式")
        return {'FINISHED'}


_classes = (
    MMY_OT_ToggleColorSpace,
    MMY_OT_ToggleAlphaMode,
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

    # 挂载到着色器编辑器顶部菜单
    try:
        bpy.types.NODE_HT_header.append(_draw_shader_header_menu)
    except:
        pass


def unregister():
    # 移除菜单
    try:
        bpy.types.NODE_HT_header.remove(_draw_shader_header_menu)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _draw_shader_header_menu(self, context):
    """在着色器编辑器顶部菜单添加快捷按钮"""
    space = context.space_data
    if not space or space.type != 'NODE_EDITOR':
        return
    tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
    if not tree:
        return

    # 检查是否有选中的 IMAGE_TEXTURE 节点
    has_selection = False
    for node in tree.nodes:
        if node.select and node.type == 'IMAGE_TEXTURE' and node.image:
            has_selection = True
            break
    if not has_selection:
        return

    self.layout.separator()
    row = self.layout.row(align=True)
    row.operator("mmy.toggle_color_space", icon='COLOR')
    row.operator("mmy.toggle_alpha_mode", icon='IMAGE_ALPHA')
