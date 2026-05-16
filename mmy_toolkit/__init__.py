import bpy
import json
import os
import re

# ============ bl_info ============
bl_info = {
    "name": "MMY Blender Toolkit",
    "blender": (4, 5, 0),
    "version": (0, 4, 1),
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


# ============ 绘制函数 ============
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


# ============ 所有类 ============
_classes = (
    MMY_SuffixItem,
    MMY_OT_SaveWithSuffix,
    MMY_OT_SelectPreset,
    MMY_OT_AddSuffix,
    MMY_OT_RemoveSuffix,
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
    # 注册子模块
    mesh_tools.register()
    ui.register()

    # 注册所有类
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

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

    # 初始化默认后缀
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if addon and addon.preferences:
        if len(addon.preferences.current_suffixes) == 0:
            for suffix in get_current_suffixes():
                item = addon.preferences.current_suffixes.add()
                item.name = suffix


def unregister():
    # 注销快捷键
    _unregister_keymaps()

    # 注销子模块
    ui.unregister()
    mesh_tools.unregister()

    # 移除绘制函数
    try:
        bpy.types.FILEBROWSER_PT_directory_path.remove(draw_suffix_menu)
    except:
        pass
    try:
        bpy.types.FILEBROWSER_HT_header.remove(draw_suffix_menu)
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