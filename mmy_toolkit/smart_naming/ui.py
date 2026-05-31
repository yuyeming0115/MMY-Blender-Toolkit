"""智能命名 UI - N面板 + 大纲右键菜单"""

import bpy
from bpy.props import EnumProperty
from .presets import get_prefix_presets, get_suffix_presets, get_separator, get_digits
from .collection_templates import get_all_template_names, get_default_template_name


# 模板选择缓存（避免 GC 回收）
_TEMPLATE_ITEMS_CACHE = []


def get_template_enum_items(self, context):
    """动态生成模板选项列表"""
    _TEMPLATE_ITEMS_CACHE.clear()
    names = get_all_template_names()
    for name in names:
        # 使用 UTF-8 hex 编码作为安全 identifier
        safe_id = 'c' + name.encode('utf-8').hex()
        _TEMPLATE_ITEMS_CACHE.append((safe_id, name, ""))
    return _TEMPLATE_ITEMS_CACHE


class MMY_PT_CollectionTemplateProps(bpy.types.PropertyGroup):
    """集合模板属性"""
    selected_template: EnumProperty(
        name="模板",
        items=get_template_enum_items,
        description="选择集合架构模板",
    )


# ===================================================================
# 后缀预设菜单（大纲右键子菜单）
# ===================================================================

class MMY_MT_SuffixPresets(bpy.types.Menu):
    """后缀预设选择菜单"""
    bl_idname = "MMY_MT_suffix_presets"
    bl_label = "选择后缀"

    def draw(self, context):
        layout = self.layout
        suffixes = get_suffix_presets()

        for suffix in suffixes:
            op = layout.operator("mmy.apply_suffix", text=suffix, icon='TEXT')
            op.suffix = suffix


class MMY_MT_PrefixPresets(bpy.types.Menu):
    """前缀预设选择菜单"""
    bl_idname = "MMY_MT_prefix_presets"
    bl_label = "选择前缀"

    def draw(self, context):
        layout = self.layout
        prefixes = get_prefix_presets()

        for prefix in prefixes:
            op = layout.operator("mmy.apply_prefix", text=prefix, icon='TEXT')
            op.prefix = prefix


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

        # === 增量复制 ===
        box = layout.box()
        box.label(text="增量复制", icon='DUPLICATE')

        row = box.row(align=True)
        row.operator("mmy.smart_duplicate_collection", text="复制集合", icon='OUTLINER_COLLECTION')
        row.operator("mmy.smart_duplicate_object", text="复制对象", icon='OBJECT_DATAMODE')

        # === 烘焙分组 ===
        layout.separator()
        box = layout.box()
        box.label(text="烘焙分组", icon='GROUP')

        row = box.row(align=True)
        row.operator("mmy.create_lod_collections", text="创建高低模容器", icon='ADD')

        # === 集合架构 ===
        layout.separator()
        box = layout.box()
        box.label(text="集合架构", icon='OUTLINER')

        # 模板选择 + 3个按钮在一行
        props = context.scene.mmy_collection_template_props
        row = box.row(align=True)
        row.prop(props, "selected_template", text="")

        # 从 enum identifier 解码回原始名称
        selected_id = props.selected_template
        if selected_id.startswith('c'):
            try:
                template_name = bytes.fromhex(selected_id[1:]).decode('utf-8')
            except:
                template_name = get_default_template_name()
        else:
            template_name = get_default_template_name()

        op = row.operator("mmy.generate_collection_template", text="", icon='ADD')
        op.template_name = template_name
        row.operator("mmy.quick_generate_collections", text="", icon='MODIFIER')
        row.operator("mmy.save_current_architecture", text="", icon='FILE_NEW')

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

    # 只有选中对象时才显示
    if context.selected_objects:
        layout.separator()

        # 归组功能
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("mmy.group_selected_objects", text="归组到新集合", icon='GROUP')

        # 快速添加后缀/前缀子菜单
        layout.menu("MMY_MT_suffix_presets", text="添加后缀", icon='TEXT')
        layout.menu("MMY_MT_prefix_presets", text="添加前缀", icon='TEXT')

        # 高低模副本：检测是否有 _low/_high 后缀的对象（大小写不敏感）
        has_lod_suffix = False
        for obj in context.selected_objects:
            name_lower = obj.name.lower()
            if '_low' in name_lower or '_high' in name_lower:
                has_lod_suffix = True
                break

        if has_lod_suffix:
            layout.separator()
            layout.operator("mmy.create_high_low_copy", text="生成高低模副本", icon='MODIFIER')


class MMY_MT_CollectionTemplates(bpy.types.Menu):
    """集合架构模板选择菜单"""
    bl_idname = "MMY_MT_collection_templates"
    bl_label = "选择模板"

    def draw(self, context):
        layout = self.layout
        names = get_all_template_names()

        for name in names:
            op = layout.operator("mmy.generate_collection_template", text=name, icon='OUTLINER')
            op.template_name = name


def _append_init_architecture_menu(self, context):
    """在大纲空白处右键菜单添加初始化架构入口"""
    layout = self.layout
    layout.separator()
    layout.menu("MMY_MT_collection_templates", text="初始化集合架构", icon='OUTLINER')


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
    MMY_PT_CollectionTemplateProps,
    MMY_PT_SmartNamingPanel,
    MMY_MT_CollectionTemplates,
    MMY_MT_SuffixPresets,
    MMY_MT_PrefixPresets,
    MMY_OT_ApplyPrefix,
    MMY_OT_ApplySuffix,
)


def register():
    # 注册面板和操作符
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 注册场景属性
    bpy.types.Scene.mmy_collection_template_props = bpy.props.PointerProperty(
        type=MMY_PT_CollectionTemplateProps
    )

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

    # 对象右键菜单（尝试多个可能的菜单名）
    object_menus = [
        'OUTLINER_MT_object',
        'OUTLINER_MT_object_context_menu',
        'OUTLINER_MT_context_menu',  # 也尝试添加到空白处菜单（选中对象时也能触发）
    ]
    for menu_name in object_menus:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.append(_append_to_outliner_object_menu)
        except:
            pass

    # 初始化架构菜单（只挂载到空白处右键菜单）
    try:
        bpy.types.OUTLINER_MT_context_menu.append(_append_init_architecture_menu)
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
    object_menus = [
        'OUTLINER_MT_object',
        'OUTLINER_MT_object_context_menu',
        'OUTLINER_MT_context_menu',
    ]
    for menu_name in object_menus:
        try:
            menu = getattr(bpy.types, menu_name)
            menu.remove(_append_to_outliner_object_menu)
        except:
            pass

    # 移除初始化架构菜单
    try:
        bpy.types.OUTLINER_MT_context_menu.remove(_append_init_architecture_menu)
    except:
        pass

    # 移除场景属性
    try:
        del bpy.types.Scene.mmy_collection_template_props
    except:
        pass

    # 注销面板和操作符
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass