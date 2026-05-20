"""相机工具模块：快速视图焦距设置"""

import bpy
from ..config import (
    get_lens_presets,
    get_lens_preset_value,
    add_lens_preset,
    delete_lens_preset,
    get_all_lens_preset_names,
    DEFAULT_LENS_PRESETS,
)


class MMY_OT_SetLens(bpy.types.Operator):
    """设置3D视图焦距"""
    bl_idname = "mmy.set_lens"
    bl_label = "设置焦距"
    bl_options = {'REGISTER'}

    lens_value: bpy.props.FloatProperty(name="焦距", default=50.0, min=1.0, max=5000.0)

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space and space.type == 'VIEW_3D' and space.region_3d.view_perspective == 'PERSP'

    def execute(self, context):
        context.space_data.lens = self.lens_value
        self.report({'INFO'}, f"焦距已设置为 {self.lens_value:.0f}mm")
        return {'FINISHED'}


class MMY_OT_AddLensPreset(bpy.types.Operator):
    """添加焦距预设"""
    bl_idname = "mmy.add_lens_preset"
    bl_label = "添加焦距预设"

    preset_name: bpy.props.StringProperty(name="名称", default="")
    lens_value: bpy.props.FloatProperty(name="焦距(mm)", default=50.0, min=1.0, max=5000.0)

    def invoke(self, context, event):
        # 自动生成默认名称
        self.preset_name = f"{self.lens_value:.0f}mm"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if not self.preset_name:
            self.report({'WARNING'}, "请输入预设名称")
            return {'CANCELLED'}

        add_lens_preset(self.preset_name, self.lens_value)
        self.report({'INFO'}, f"已添加预设: {self.preset_name}")
        return {'FINISHED'}


class MMY_OT_DeleteLensPreset(bpy.types.Operator):
    """删除焦距预设"""
    bl_idname = "mmy.delete_lens_preset"
    bl_label = "删除预设"

    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        if delete_lens_preset(self.preset_name):
            self.report({'INFO'}, f"已删除预设: {self.preset_name}")
        else:
            self.report({'WARNING'}, "无法删除默认预设")
        return {'FINISHED'}


class MMY_MT_LensPresetMenu(bpy.types.Menu):
    """焦距预设下拉菜单"""
    bl_idname = "MMY_MT_lens_preset_menu"
    bl_label = "焦距预设"

    def draw(self, context):
        layout = self.layout
        current_lens = context.space_data.lens if context.space_data else 50.0

        # 显示所有预设
        presets = get_lens_presets()
        for name, value in presets.items():
            text = f"{name}"
            # 当前焦距标记
            if abs(value - current_lens) < 0.5:
                text = f"✓ {name}"
            op = layout.operator("mmy.set_lens", text=text)
            op.lens_value = value

        # 分隔线
        layout.separator()

        # 添加预设选项
        layout.operator("mmy.add_lens_preset", text="➕ 添加预设...", icon='ADD')


_classes = (
    MMY_OT_SetLens,
    MMY_OT_AddLensPreset,
    MMY_OT_DeleteLensPreset,
    MMY_MT_LensPresetMenu,
)


def _draw_lens_header(self, context):
    """在3D视图Header绘制焦距按钮"""
    space = context.space_data
    if not space or space.type != 'VIEW_3D':
        return

    # 仅透视视图显示
    if space.region_3d.view_perspective != 'PERSP':
        return

    layout = self.layout
    row = layout.row(align=True)

    # 当前焦距显示 + 下拉菜单
    current_lens = space.lens
    row.menu("MMY_MT_lens_preset_menu", text=f"{current_lens:.0f}mm")


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

    # Header 挂载由主模块统一管理
    # 不在此处单独 prepend


def unregister():
    # Header 挂载由主模块统一管理

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass