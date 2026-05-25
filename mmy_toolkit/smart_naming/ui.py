"""智能命名 UI - N面板 + 大纲右键菜单"""

import bpy
from .presets import get_prefix_presets, get_suffix_presets, get_separator, get_digits


# ===================================================================
# N面板
# ===================================================================

class MMY_PT_SmartNamingPanel(bpy.types.Panel):
    """智能命名 N面板"""
    bl_label = "智能命名"
    bl_idname = "MMY_PT_smart_naming"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"

    def draw(self, context):
        layout = self.layout

        # === 快捷复制 ===
        box = layout.box()
        box.label(text="快捷复制", icon='DUPLICATE')

        row = box.row(align=True)
        row.operator("mmy.smart_duplicate_collection", text="复制集合", icon='OUTLINER_COLLECTION')
        row.operator("mmy.smart_duplicate_object", text="复制对象", icon='OBJECT_DATAMODE')

        # === 烘焙分组 ===
        layout.separator()
        box = layout.box()
        box.label(text="烘焙分组", icon='GROUP')

        row = box.row(align=True)
        row.operator("mmy.create_lod_collections", text="创建高低模容器", icon='ADD')

        # === 快捷归组 ===
        layout.separator()
        box = layout.box()
        box.label(text="快捷归组", icon='OUTLINER_COLLECTION')

        row = box.row(align=True)
        row.operator("mmy.group_selected_objects", text="归组到新集合", icon='GROUP')

        # === 批量重命名 ===
        layout.separator()
        box = layout.box()
        box.label(text="批量重命名", icon='TEXT')

        row = box.row(align=True)
        row.operator("mmy.batch_rename", text="批量重命名", icon='SORTBYEXT')

        # === 单个重命名 ===
        layout.separator()
        box = layout.box()
        box.label(text="单个重命名", icon='FONT_DATA')

        if context.active_object:
            row = box.row(align=True)
            row.prop(context.active_object, "name", text="")
            row.operator("mmy.rename_single", text="", icon='CHECKMARK')

        # === 预设快捷按钮 ===
        layout.separator()
        box = layout.box()
        box.label(text="常用预设", icon='PRESET')

        # 前缀预设
        prefix_presets = get_prefix_presets()
        if prefix_presets:
            row = box.row(align=True)
            row.label(text="前缀:")
            for prefix in prefix_presets[:5]:  # 只显示前5个
                op = row.operator("mmy.apply_prefix", text=prefix)
                op.prefix = prefix

        # 后缀预设
        suffix_presets = get_suffix_presets()
        if suffix_presets:
            row = box.row(align=True)
            row.label(text="后缀:")
            for suffix in suffix_presets[:5]:  # 只显示前5个
                op = row.operator("mmy.apply_suffix", text=suffix)
                op.suffix = suffix

        # === 配置入口 ===
        layout.separator()
        row = layout.row()
        row.operator("mmy.open_prefs", text="配置预设", icon='SETTINGS')


# ===================================================================
# 大纲右键菜单
# ===================================================================

def _append_to_outliner_menu(self, context):
    """在大纲右键菜单添加智能复制选项"""
    layout = self.layout

    # 检查是否在集合上右键
    if context.collection:
        layout.separator()
        layout.operator("mmy.smart_duplicate_collection", text="智能复制集合", icon='OUTLINER_COLLECTION')
        layout.operator("mmy.create_lod_collections", text="创建高低模容器", icon='GROUP')

    # 如果选中了对象，显示归组选项
    if context.selected_objects:
        layout.separator()
        layout.operator("mmy.group_selected_objects", text="归组到新集合", icon='GROUP')


def _append_to_outliner_object_menu(self, context):
    """在大纲对象右键菜单添加选项"""
    layout = self.layout

    # 归组功能：只有选中对象时才显示
    if context.selected_objects:
        layout.separator()
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("mmy.group_selected_objects", text="归组到新集合", icon='GROUP')


def _append_to_outliner_context_menu(self, context):
    """在大纲上下文菜单添加选项（集合/空白区域）"""
    layout = self.layout

    layout.separator()
    layout.operator("mmy.smart_duplicate_collection", text="智能复制集合")
    layout.operator("mmy.create_lod_collections", text="创建高低模容器")

    # 归组功能：设置 INVOKE_DEFAULT 确保弹出对话框
    if context.selected_objects:
        layout.separator()
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("mmy.group_selected_objects", text="归组到新集合", icon='GROUP')


# ===================================================================
# 辅助操作符（应用预设）
# ===================================================================

class MMY_OT_ApplyPrefix(bpy.types.Operator):
    """应用前缀预设到选中对象"""
    bl_idname = "mmy.apply_prefix"
    bl_label = "应用前缀"

    prefix: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.selected_objects:
            obj.name = f"{self.prefix}{obj.name}"
        self.report({'INFO'}, f"已应用前缀: {self.prefix}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects


class MMY_OT_ApplySuffix(bpy.types.Operator):
    """应用后缀预设到选中对象"""
    bl_idname = "mmy.apply_suffix"
    bl_label = "应用后缀"

    suffix: bpy.props.StringProperty()

    def execute(self, context):
        for obj in context.selected_objects:
            obj.name = f"{obj.name}{self.suffix}"
        self.report({'INFO'}, f"已应用后缀: {self.suffix}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects


_classes = (
    MMY_PT_SmartNamingPanel,
    MMY_OT_ApplyPrefix,
    MMY_OT_ApplySuffix,
)


def register():
    # 注册面板和操作符
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 挂载大纲右键菜单（多个位置）
    # 集合/空白区域菜单
    collection_menus = [
        'OUTLINER_MT_context_menu',      # 主右键菜单（空白处）
        'OUTLINER_MT_collection',         # 集合右键菜单
        'OUTLINER_MT_collection_context_menu',  # 集合上下文菜单
    ]
    for menu_name in collection_menus:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.append(_append_to_outliner_context_menu)
        except:
            pass

    # 对象右键菜单
    try:
        bpy.types.OUTLINER_MT_object.append(_append_to_outliner_object_menu)
    except:
        pass


def unregister():
    # 移除大纲右键菜单
    collection_menus = [
        'OUTLINER_MT_context_menu',
        'OUTLINER_MT_collection',
        'OUTLINER_MT_collection_context_menu',
    ]
    for menu_name in collection_menus:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.remove(_append_to_outliner_context_menu)
        except:
            pass

    # 移除对象右键菜单
    try:
        bpy.types.OUTLINER_MT_object.remove(_append_to_outliner_object_menu)
    except:
        pass

    # 注销面板和操作符
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass