import bpy
import os

from ..config import (
    get_current_suffixes,
    get_current_preset_name,
    set_current_preset,
    get_all_preset_names,
    update_preset,
)
from ..utils import apply_suffix


class MMY_OT_GetDirectoryName(bpy.types.Operator):
    """获取当前目录名称作为文件名"""
    bl_idname = "mmy.get_directory_name"
    bl_label = "获取目录名"
    bl_description = "将当前文件夹名称设为保存文件名"

    def execute(self, context):
        params = context.space_data.params
        if not params:
            self.report({'WARNING'}, "无法获取参数")
            return {'CANCELLED'}

        # 获取当前目录路径
        directory = params.directory
        if not directory:
            self.report({'WARNING'}, "无法获取目录路径")
            return {'CANCELLED'}

        # 提取文件夹名称（去除路径分隔符）
        directory = directory.rstrip('\\/').rstrip('/')
        folder_name = os.path.basename(directory)

        if not folder_name:
            self.report({'WARNING'}, "无法提取文件夹名称")
            return {'CANCELLED'}

        # 设置文件名
        params.filename = folder_name
        self.report({'INFO'}, f"文件名已设为: {folder_name}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'FILE_BROWSER' and space.params


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


class MMY_MT_PresetMenu(bpy.types.Menu):
    bl_idname = "MMY_MT_preset_menu"
    bl_label = "预设选择"

    def draw(self, context):
        layout = self.layout
        current = get_current_preset_name()
        for name in get_all_preset_names():
            op = layout.operator("mmy.select_preset", text=name)
            op.preset_name = name


class MMY_OT_SelectPreset(bpy.types.Operator):
    bl_idname = "mmy.select_preset"
    bl_label = "选择预设"

    preset_name: bpy.props.StringProperty(name="预设名称")

    def execute(self, context):
        from .. import config
        set_current_preset(self.preset_name)

        # 更新偏好设置中的后缀列表
        prefs = context.preferences.addons.get("mmy_toolkit")
        if prefs and prefs.preferences:
            prefs.preferences.current_suffixes.clear()
            for suffix in config.get_current_suffixes():
                item = prefs.preferences.current_suffixes.add()
                item.name = suffix

        return {"FINISHED"}


class MMY_OT_OpenPreferences(bpy.types.Operator):
    """打开插件偏好设置"""
    bl_idname = "mmy.open_preferences"
    bl_label = "配置"

    def execute(self, context):
        bpy.ops.screen.userpref_show()
        # 切换到插件页面
        bpy.context.preferences.active_section = "ADDONS"
        # 搜索插件
        bpy.context.window_manager.addon_search = "MMY"
        return {"FINISHED"}


def draw_suffix_menu(self, context):
    space = context.space_data
    if not space or space.type != "FILE_BROWSER":
        return

    # 排除资产浏览器（ui_type 为 ASSETS）
    area = context.area
    ui_type = getattr(area, "ui_type", None) if area else None
    if area and ui_type == "ASSETS":
        return

    params = space.params
    if not params:
        return

    layout = self.layout
    row = layout.row(align=True)
    row.label(text="快速后缀:")

    # 获取目录名按钮
    row.operator("mmy.get_directory_name", text="", icon="FILE_FOLDER")

    # 从偏好设置获取后缀
    prefs = context.preferences.addons.get("mmy_toolkit")
    if prefs and prefs.preferences and len(prefs.preferences.current_suffixes) > 0:
        suffixes = [item.name for item in prefs.preferences.current_suffixes]
    else:
        suffixes = get_current_suffixes()

    # 后缀按钮
    for suffix in suffixes:
        op = row.operator("mmy.save_with_suffix", text=suffix)
        op.suffix = suffix

    # 配置按钮 - 打开偏好设置
    row.operator("mmy.open_preferences", text="", icon="SETTINGS")

    # 预设下拉菜单
    row.menu("MMY_MT_preset_menu", text="", icon="DOWNARROW_HLT")