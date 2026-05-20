import bpy
import json
import os
import re

# ============ bl_info ============
bl_info = {
    "name": "MMY Blender Toolkit",
    "author": "会叫喵的鱼",
    "blender": (4, 5, 0),
    "version": (0, 5, 0),
    "category": "Pipeline",
    "description": "MMY 系列 Blender 效率优化工具集",
}

# ============ 配置模块 ============
PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")
PRESET_FILE = os.path.join(PRESETS_DIR, "suffix_presets.json")

DEFAULT_PRESETS = {
    "完整流程": ["_Mesh", "_Mat", "_Rig", "_Ani", "_Render"],
    "动画流程": ["_Mesh", "_Rig", "_Ani"],
    "渲染流程": ["_Mat", "_Light", "_Render"],
}


def ensure_presets_dir():
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)


def load_presets():
    ensure_presets_dir()
    if os.path.exists(PRESET_FILE):
        try:
            with open(PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    data = {"current_preset": "完整流程", "presets": DEFAULT_PRESETS}
    save_presets(data)
    return data


def save_presets(data):
    ensure_presets_dir()
    with open(PRESET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_suffixes():
    data = load_presets()
    current_name = data.get("current_preset", "完整流程")
    presets = data.get("presets", DEFAULT_PRESETS)
    return presets.get(current_name, DEFAULT_PRESETS["完整流程"])


def get_current_preset_name():
    return load_presets().get("current_preset", "完整流程")


def set_current_preset(name):
    data = load_presets()
    if name in data.get("presets", {}):
        data["current_preset"] = name
        save_presets(data)


def get_all_preset_names():
    return list(load_presets().get("presets", DEFAULT_PRESETS).keys())


def update_preset(name, suffixes):
    data = load_presets()
    data["presets"][name] = suffixes
    save_presets(data)


def delete_preset(name):
    if name in DEFAULT_PRESETS:
        return False
    data = load_presets()
    if name in data.get("presets", {}):
        del data["presets"][name]
        save_presets(data)
        return True
    return False


# ============ 工具函数 ============
BLEND_EXT = ".blend"


def apply_suffix(filename, suffix):
    base = filename
    has_blend = base.lower().endswith(BLEND_EXT)
    if has_blend:
        base = base[:-len(BLEND_EXT)]

    suffix_lower = suffix.lower()
    if base.lower().endswith(suffix_lower):
        pass
    else:
        other = re.sub(r"_[A-Za-z]+$", "", base)
        base = other + suffix

    return base + BLEND_EXT if has_blend else base


# ============ PropertyGroup ============
class MMY_SuffixItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="后缀", default="_")


# ============ Operators ============
class MMY_OT_SaveWithSuffix(bpy.types.Operator):
    bl_idname = "mmy.save_with_suffix"
    bl_label = "Save with suffix"

    suffix: bpy.props.StringProperty(name="Suffix")

    def execute(self, context):
        params = context.space_data.params
        original = params.filename
        if original == "Untitled.blend":
            self.report({"WARNING"}, "请先命名文件")
            return {"CANCELLED"}
        params.filename = apply_suffix(original, self.suffix)
        return {"FINISHED"}


class MMY_OT_SelectPreset(bpy.types.Operator):
    bl_idname = "mmy.select_preset"
    bl_label = "选择预设"

    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        set_current_preset(self.preset_name)
        prefs = context.preferences.addons.get("mmy_toolkit")
        if prefs and prefs.preferences:
            prefs.preferences.current_suffixes.clear()
            for suffix in get_current_suffixes():
                item = prefs.preferences.current_suffixes.add()
                item.name = suffix
        return {"FINISHED"}


class MMY_OT_AddSuffix(bpy.types.Operator):
    bl_idname = "mmy.add_suffix"
    bl_label = "添加后缀"

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        item = prefs.current_suffixes.add()
        item.name = "_New"
        return {"FINISHED"}


class MMY_OT_RemoveSuffix(bpy.types.Operator):
    bl_idname = "mmy.remove_suffix"
    bl_label = "删除后缀"

    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        prefs.current_suffixes.remove(self.index)
        return {"FINISHED"}


class MMY_OT_AddRenderSuffix(bpy.types.Operator):
    """添加渲染后缀去除项"""
    bl_idname = "mmy.add_render_suffix"
    bl_label = "添加后缀"

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        item = prefs.render_remove_suffixes.add()
        item.name = "_New"
        return {"FINISHED"}


class MMY_OT_RemoveRenderSuffix(bpy.types.Operator):
    """删除渲染后缀去除项"""
    bl_idname = "mmy.remove_render_suffix"
    bl_label = "删除后缀"

    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        prefs.render_remove_suffixes.remove(self.index)
        return {"FINISHED"}


class MMY_OT_AddAniCollectionName(bpy.types.Operator):
    """添加动画集合名称预设"""
    bl_idname = "mmy.add_ani_collection_name"
    bl_label = "添加集合名"

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        item = prefs.ani_collection_names.add()
        item.name = "Ani"
        return {"FINISHED"}


class MMY_OT_RemoveAniCollectionName(bpy.types.Operator):
    """删除动画集合名称预设"""
    bl_idname = "mmy.remove_ani_collection_name"
    bl_label = "删除集合名"

    index: bpy.props.IntProperty()

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        prefs.ani_collection_names.remove(self.index)
        return {"FINISHED"}


class MMY_OT_SavePreset(bpy.types.Operator):
    bl_idname = "mmy.save_preset"
    bl_label = "保存为预设"

    preset_name: bpy.props.StringProperty(name="预设名称", default="自定义")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = context.preferences.addons["mmy_toolkit"].preferences
        suffixes = [item.name for item in prefs.current_suffixes]
        update_preset(self.preset_name, suffixes)
        self.report({"INFO"}, f"已保存预设: {self.preset_name}")
        return {"FINISHED"}


class MMY_OT_DeletePreset(bpy.types.Operator):
    bl_idname = "mmy.delete_preset"
    bl_label = "删除预设"

    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        if delete_preset(self.preset_name):
            self.report({"INFO"}, f"已删除预设: {self.preset_name}")
        return {"FINISHED"}


class MMY_OT_OpenPrefs(bpy.types.Operator):
    bl_idname = "mmy.open_prefs"
    bl_label = "配置"

    def execute(self, context):
        bpy.ops.screen.userpref_show()
        bpy.context.preferences.active_section = "ADDONS"
        bpy.context.window_manager.addon_search = "MMY"
        return {"FINISHED"}


# ============ Menu ============
class MMY_MT_PresetMenu(bpy.types.Menu):
    bl_idname = "MMY_MT_preset_menu"
    bl_label = "预设"

    def draw(self, context):
        layout = self.layout
        for name in get_all_preset_names():
            op = layout.operator("mmy.select_preset", text=name)
            op.preset_name = name


# ============ 快捷键管理 ============
addon_keymaps = []


def _get_keymap_item(operator_id, context=None):
    """获取指定操作符的keymap item"""
    try:
        if context:
            wm = context.window_manager
        else:
            wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.find("Mesh", space_type="VIEW_3D")
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == operator_id:
                        return km, kmi
    except:
        pass
    return None, None


class MMY_OT_RestoreKeymaps(bpy.types.Operator):
    """恢复默认快捷键"""
    bl_idname = "mmy.restore_keymaps"
    bl_label = "恢复快捷键"

    def execute(self, context):
        _register_keymaps()
        self.report({'INFO'}, "快捷键已恢复")
        return {'FINISHED'}


# ============ Preferences ============
class MMY_Preferences(bpy.types.AddonPreferences):
    bl_idname = "mmy_toolkit"

    current_suffixes: bpy.props.CollectionProperty(type=MMY_SuffixItem)

    # === 渲染预览图后缀去除列表 ===
    render_remove_suffixes: bpy.props.CollectionProperty(type=MMY_SuffixItem)

    # === 动画集合名称预设列表 ===
    ani_collection_names: bpy.props.CollectionProperty(type=MMY_SuffixItem)

    # 自动备份属性
    enabled_backup: bpy.props.BoolProperty(
        name="启用自动备份",
        description="开启定时自动备份功能",
        default=True
    )
    minor_interval_backup: bpy.props.IntProperty(
        name="小版本间隔（分钟）",
        description="小版本备份的时间间隔",
        default=2,
        min=1,
        max=60
    )
    major_interval_backup: bpy.props.IntProperty(
        name="大版本间隔（分钟）",
        description="大版本备份的时间间隔",
        default=30,
        min=5,
        max=120
    )
    daily_max_backups: bpy.props.IntProperty(
        name="每日最大备份数",
        description="每个日期文件夹内每种类型的最大备份数量",
        default=20,
        min=5,
        max=100
    )
    keep_days_backup: bpy.props.IntProperty(
        name="保留天数",
        description="保留最近多少天的备份文件夹",
        default=7,
        min=1,
        max=30
    )
    capacity_threshold_mb: bpy.props.IntProperty(
        name="容量警告阈值（MB）",
        description="超过此容量时在状态栏显示警告",
        default=500,
        min=100,
        max=5000
    )

    # === 语言切换按钮位置 ===
    translation_topbar: bpy.props.BoolProperty(
        name="顶栏菜单",
        description="在顶部菜单栏显示语言切换按钮",
        default=True,
        update=lambda self, ctx: _update_translation_buttons()
    )
    translation_node_header: bpy.props.BoolProperty(
        name="Shader Editor",
        description="在 Shader Editor Header 显示语言切换按钮",
        default=True,
        update=lambda self, ctx: _update_translation_buttons()
    )
    translation_properties_header: bpy.props.BoolProperty(
        name="属性面板",
        description="在属性面板 Header 显示语言切换按钮",
        default=True,
        update=lambda self, ctx: _update_translation_buttons()
    )
    translation_view3d_header: bpy.props.BoolProperty(
        name="3D视图",
        description="在 3D视图 Header 显示语言切换按钮",
        default=False,
        update=lambda self, ctx: _update_translation_buttons()
    )

    def draw(self, context):
        layout = self.layout

        # === 快捷键配置 ===
        layout.label(text="快捷键配置:")
        box = layout.box()
        row = box.row()
        row.label(text="UV孤岛缝合边:")
        try:
            km, kmi = _get_keymap_item("mmy.mark_uv_island_seams", context)
            if kmi:
                row.prop(kmi, "type", text="")
                row.prop(kmi, "value", text="")
                row.operator("mmy.restore_keymaps", text="恢复默认")
            else:
                row.label(text="未设置")
                row.operator("mmy.restore_keymaps", text="添加快捷键")
        except:
            row.label(text="请重启Blender后配置")
        row.label(text="(编辑模式)")

        layout.separator()

        # === 左右两列布局 ===
        row = layout.row()
        col_left = row.column()
        col_right = row.column()

        # 左列：后缀编辑
        col_left.label(text="当前后缀:")
        box = col_left.box()
        for i, item in enumerate(self.current_suffixes):
            r = box.row(align=True)
            r.prop(item, "name", text="")
            op = r.operator("mmy.remove_suffix", text="", icon="X")
            op.index = i
        box.operator("mmy.add_suffix", text="添加", icon="ADD")
        box.operator("mmy.save_preset", text="保存预设", icon="FILE_TICK")

        # 右列：预设列表
        col_right.label(text="预设列表:")
        box = col_right.box()
        current = get_current_preset_name()
        for name in get_all_preset_names():
            r = box.row(align=True)
            r.label(text="★" if name == current else "  ")
            r.operator("mmy.select_preset", text=name).preset_name = name
            if name not in DEFAULT_PRESETS:
                r.operator("mmy.delete_preset", text="", icon="X").preset_name = name

        # 提示
        layout.separator()
        layout.label(text="预设文件: presets/suffix_presets.json（可迁移）")

        layout.separator()

        # === 渲染预览图后缀去除配置 ===
        layout.label(text="渲染预览图后缀去除:", icon='RENDER_STILL')
        box = layout.box()
        row = box.row()
        row.label(text="渲染时自动去掉以下后缀:")
        for i, item in enumerate(self.render_remove_suffixes):
            r = box.row(align=True)
            r.prop(item, "name", text="")
            op = r.operator("mmy.remove_render_suffix", text="", icon="X")
            op.index = i
        r = box.row(align=True)
        r.operator("mmy.add_render_suffix", text="添加后缀", icon="ADD")
        r.label(text="示例: Model_Render.blend → Model.png")

        layout.separator()

        # === 动画集合名称预设 ===
        layout.label(text="动画集合名称预设:", icon='OUTLINER_COLLECTION')
        box = layout.box()
        row = box.row()
        row.label(text="关联动画时查找的集合名称:")
        for i, item in enumerate(self.ani_collection_names):
            r = box.row(align=True)
            r.prop(item, "name", text="")
            op = r.operator("mmy.remove_ani_collection_name", text="", icon="X")
            op.index = i
        r = box.row(align=True)
        r.operator("mmy.add_ani_collection_name", text="添加名称", icon="ADD")
        r.label(text="示例: Ani, Animation, 动画")

        layout.separator()

        # === 自动备份设置 ===
        layout.label(text="自动备份设置:", icon='FILE_BACKUP')
        box = layout.box()

        # 启用开关
        row = box.row()
        row.prop(self, "enabled_backup", text="启用自动备份")

        try:
            enabled = bool(self.enabled_backup)
        except:
            enabled = True

        if enabled:
            # 间隔设置
            col = box.column(align=True)
            col.prop(self, "minor_interval_backup", text="小版本间隔")
            col.prop(self, "major_interval_backup", text="大版本间隔")

            # 数量限制
            col = box.column(align=True)
            col.prop(self, "daily_max_backups", text="每日最大备份数")
            col.prop(self, "keep_days_backup", text="保留天数")

            # 容量阈值
            box.prop(self, "capacity_threshold_mb", text="容量警告阈值(MB)")

            # 备份目录显示
            import os
            try:
                temp_dir = context.preferences.filepaths.temporary_directory
                if not temp_dir:
                    temp_dir = os.environ.get('TEMP', os.environ.get('TMP', ''))
                backup_dir = os.path.join(temp_dir, "MMY_Backups")
                box.label(text=f"备份目录: {backup_dir}")
            except:
                box.label(text="备份目录: (系统临时目录)")

            # 状态信息
            from .auto_backup import get_status, get_next_save_time
            status = get_status()
            layout.separator()
            stat_box = layout.box()
            stat_box.label(text=f"当前容量: {status['capacity_mb']:.1f}MB | 备份数: {status['backup_count']}个")
            stat_box.label(text=f"下次备份: {get_next_save_time()}")

            # 容量警告
            if status['warning']:
                stat_box.label(text="⚠️ 容量超过阈值，请清理备份目录", icon='ERROR')

        layout.separator()

        # === 语言切换按钮位置 ===
        layout.label(text="语言切换按钮位置:", icon='FILE_FONT')
        box = layout.box()
        row = box.row()
        row.prop(self, "translation_topbar")
        row.prop(self, "translation_node_header")
        row = box.row()
        row.prop(self, "translation_properties_header")
        row.prop(self, "translation_view3d_header")
        box.label(text="点击按钮切换中/英文，Ctrl+点击打开偏好设置")


def _update_translation_buttons():
    """更新语言切换按钮显示"""
    from .translation_toggle.ui import update_translation_buttons
    update_translation_buttons(None, None)


# ============ 绘制函数 ============
def _draw_header_buttons(self, context):
    """统一的 Header 按钮绘制函数（焦距预设 + 渲染预览图）"""
    # 焦距在前，渲染在后
    from .camera_tools.operators import _draw_lens_header
    from .render_preview import _append_render_button

    _draw_lens_header(self, context)
    _append_render_button(self, context)


def draw_suffix_menu(self, context):
    space = context.space_data
    if not space or space.type != "FILE_BROWSER":
        return

    area = context.area
    if area and getattr(area, "ui_type", None) == "ASSETS":
        return

    params = space.params
    if not params:
        return

    layout = self.layout
    row = layout.row(align=True)
    row.label(text="快速后缀:")

    # 从偏好设置获取后缀
    prefs = context.preferences.addons.get("mmy_toolkit")
    if prefs and prefs.preferences and len(prefs.preferences.current_suffixes) > 0:
        suffixes = [item.name for item in prefs.preferences.current_suffixes]
    else:
        suffixes = get_current_suffixes()

    for suffix in suffixes:
        op = row.operator("mmy.save_with_suffix", text=suffix)
        op.suffix = suffix

    row.operator("mmy.open_prefs", text="", icon="SETTINGS")
    row.menu("MMY_MT_preset_menu", text="", icon="DOWNARROW_HLT")


def draw_statusbar_backup(self, context):
    """状态栏显示自动备份状态"""
    addon = context.preferences.addons.get("mmy_toolkit")
    if not addon or not addon.preferences:
        return

    prefs = addon.preferences
    try:
        if not bool(prefs.enabled_backup):
            return
    except:
        return

    from .auto_backup import get_status, get_next_save_time
    status = get_status()

    layout = self.layout
    row = layout.row(align=True)

    # 容量警告时显示红色
    if status['warning']:
        row.alert = True
        row.label(text=f"[MMY备份] ⚠️ {status['capacity_mb']:.0f}MB | 请清理")
    else:
        row.label(text=f"[MMY备份] {status['capacity_mb']:.0f}MB | 下次: {get_next_save_time()}")


# ============ 所有类 ============
_classes = (
    MMY_SuffixItem,
    MMY_OT_SaveWithSuffix,
    MMY_OT_SelectPreset,
    MMY_OT_AddSuffix,
    MMY_OT_RemoveSuffix,
    MMY_OT_AddRenderSuffix,
    MMY_OT_RemoveRenderSuffix,
    MMY_OT_AddAniCollectionName,
    MMY_OT_RemoveAniCollectionName,
    MMY_OT_SavePreset,
    MMY_OT_DeletePreset,
    MMY_OT_OpenPrefs,
    MMY_OT_RestoreKeymaps,
    MMY_MT_PresetMenu,
    MMY_Preferences,
)


# ============ 子模块 ============
from . import mesh_tools
from . import ui
from . import asset_browser
from . import auto_color_space
from . import camera_tools
from . import auto_backup
from . import mat_replacer
from . import render_preview
from . import shapekey_tools
from . import cleaning
from . import poly_edit
from . import translation_toggle


# ============ 快捷键注册 ============
def _register_keymaps():
    """注册插件快捷键"""
    global addon_keymaps
    try:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.find("Mesh", space_type="VIEW_3D")
            if km:
                # UV孤岛缝合边快捷键（默认不绑定）
                kmi = km.keymap_items.new(
                    idname="mmy.mark_uv_island_seams",
                    type="NONE",
                    value="PRESS",
                    shift=False,
                    ctrl=False,
                    alt=False
                )
                addon_keymaps.append((km, kmi))
    except:
        pass


def _unregister_keymaps():
    """注销插件快捷键"""
    global addon_keymaps
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except:
            pass
    addon_keymaps.clear()


# ============ 注册/注销 ============
def register():
    # 先注册所有类（包括偏好设置），确保 addon.preferences 可用
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

    # 再注册子模块（此时偏好设置已可用）
    mesh_tools.register()
    ui.register()
    asset_browser.register()
    auto_color_space.register()
    camera_tools.register()
    auto_backup.register()
    mat_replacer.register()
    render_preview.register()
    shapekey_tools.register()
    cleaning.register()
    poly_edit.register()
    translation_toggle.register()

    # 注册快捷键
    _register_keymaps()

    # 挂载绘制函数
    try:
        bpy.types.FILEBROWSER_PT_directory_path.append(draw_suffix_menu)
    except:
        try:
            bpy.types.FILEBROWSER_HT_header.prepend(draw_suffix_menu)
        except:
            pass

    # 挂载统一的 Header 按钮（左边位置）
    try:
        bpy.types.VIEW3D_HT_header.prepend(_draw_header_buttons)
    except:
        pass

    # 挂载状态栏备份状态显示
    try:
        bpy.types.STATUSBAR_HT_header.append(draw_statusbar_backup)
    except:
        pass

    # 初始化默认后缀
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if addon and addon.preferences:
        if len(addon.preferences.current_suffixes) == 0:
            for suffix in get_current_suffixes():
                item = addon.preferences.current_suffixes.add()
                item.name = suffix

        # 初始化默认渲染后缀去除列表
        if len(addon.preferences.render_remove_suffixes) == 0:
            default_render_suffixes = ["_Render", "_Preview", "_Test"]
            for suffix in default_render_suffixes:
                item = addon.preferences.render_remove_suffixes.add()
                item.name = suffix

        # 初始化默认动画集合名称预设
        if len(addon.preferences.ani_collection_names) == 0:
            default_ani_names = ["Ani", "Animation", "动画"]
            for name in default_ani_names:
                item = addon.preferences.ani_collection_names.add()
                item.name = name

    # 启动自动备份定时器（类注册后）
    auto_backup.start_backup_if_enabled()


def unregister():
    # 注销快捷键
    _unregister_keymaps()

    # 注销子模块
    poly_edit.unregister()
    cleaning.unregister()
    shapekey_tools.unregister()
    render_preview.unregister()
    mat_replacer.unregister()
    auto_backup.unregister()
    camera_tools.unregister()
    auto_color_space.unregister()
    asset_browser.unregister()
    ui.unregister()
    mesh_tools.unregister()
    translation_toggle.unregister()

    # 移除绘制函数
    try:
        bpy.types.FILEBROWSER_PT_directory_path.remove(draw_suffix_menu)
    except:
        pass
    try:
        bpy.types.FILEBROWSER_HT_header.remove(draw_suffix_menu)
    except:
        pass
    # 移除统一的 Header 按钮
    try:
        bpy.types.VIEW3D_HT_header.remove(_draw_header_buttons)
    except:
        pass
    try:
        bpy.types.STATUSBAR_HT_header.remove(draw_statusbar_backup)
    except:
        pass

    # 注销所有类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


if __name__ == "__main__":
    register()