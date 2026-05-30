# -*- coding: utf-8 -*-
"""UV 工具模块"""

import bpy
from bpy.types import AddonPreferences

from . import operators
from . import ui


class MMYUVToolsPreferences:
    """UV 工具偏好设置（作为主插件偏好设置的一部分）"""

    photoshop_path: bpy.props.StringProperty(
        name="Photoshop 可执行文件",
        description="photoshop.exe 的完整路径",
        subtype='FILE_PATH',
        default=r"C:\Program Files\Adobe\Adobe Photoshop\Photoshop.exe"
    )

    # RizomUV 设置
    rizomuv_enable: bpy.props.BoolProperty(
        name="启用 RizomUV 桥接",
        description="在面板中显示 RizomUV 桥接工具",
        default=True,
    )
    rizomuv_app_path: bpy.props.StringProperty(
        name="RizomUV 路径",
        description="RizomUV 可执行文件所在目录（包含 rizomuv.exe）",
        subtype='DIR_PATH',
    )
    rizomuv_exit_after_save: bpy.props.BoolProperty(
        name="保存后自动关闭 RizomUV",
        description="RizomUV 保存后自动关闭进程",
        default=False,
    )
    rizomuv_multi_uv: bpy.props.BoolProperty(
        name="多 UV 通道模式",
        description="发送所有 UV 通道到 RizomUV（需使用 Edit 模式）",
        default=False,
    )

    # Unwrap 参数
    rizomuv_unwrap_tab: bpy.props.BoolProperty(
        name="Unwrap 设置",
        description="启用后 RizomUV 将加载以下展开参数",
        default=False,
    )
    rizomuv_unwrap_unfold_itr: bpy.props.IntProperty(
        name="展开迭代",
        default=1, min=1, max=1000,
    )
    rizomuv_unwrap_optimize_itr: bpy.props.IntProperty(
        name="优化迭代",
        default=10, min=1, max=1000,
    )
    rizomuv_unwrap_tflips: bpy.props.BoolProperty(
        name="防止三角翻转",
        default=False,
    )
    rizomuv_unwrap_overlaps: bpy.props.BoolProperty(
        name="防止自交重叠",
        default=False,
    )
    rizomuv_unwrap_overlaps_dist: bpy.props.FloatProperty(
        name="最小间距",
        default=0.001, min=0.0, max=1.0, step=0.1, precision=3,
    )
    rizomuv_unwrap_free: bpy.props.BoolProperty(
        name="释放边界",
        default=False,
    )
    rizomuv_unwrap_fill: bpy.props.BoolProperty(
        name="填充孔洞",
        default=False,
    )
    rizomuv_unwrap_keep_metric: bpy.props.BoolProperty(
        name="保持比例",
        default=False,
    )

    # Layout 参数
    rizomuv_layout_tab: bpy.props.BoolProperty(
        name="Layout 设置",
        description="启用后 RizomUV 将加载以下排列参数",
        default=False,
    )
    rizomuv_layout_margin: bpy.props.FloatProperty(
        name="边距",
        default=0.001, min=0.0, max=100.0, step=0.1, precision=3,
    )
    rizomuv_layout_spacing: bpy.props.FloatProperty(
        name="间距",
        default=0.001, min=0.0, max=100.0, step=0.1, precision=3,
    )
    rizomuv_layout_map_size: bpy.props.IntProperty(
        name="贴图分辨率",
        default=2048, min=1, max=65536, step=256,
    )


def get_uv_preferences(context):
    """获取 UV 工具偏好设置"""
    addon = context.preferences.addons.get("mmy_toolkit")
    if addon is None:
        return None
    return addon.preferences


def register():
    operators.register()
    ui.register()

    # Scene 属性
    bpy.types.Scene.uv_source_object = bpy.props.PointerProperty(
        name="新UV对象",
        type=bpy.types.Object,
        description="选择提供UV数据的mesh对象"
    )
    bpy.types.Scene.uv_target_object = bpy.props.PointerProperty(
        name="绑定对象",
        type=bpy.types.Object,
        description="选择接收UV数据的mesh对象"
    )
    bpy.types.Scene.uv_last_export_path = bpy.props.StringProperty(
        name="最近导出路径",
        subtype='FILE_PATH',
        options={'HIDDEN'}
    )
    bpy.types.Scene.uv_unified_name = bpy.props.StringProperty(
        name="统一名称",
        default="UVMap"
    )
    bpy.types.Scene.uv_show_stretch = bpy.props.BoolProperty(
        name="显示拉伸",
        default=False,
        update=operators.update_uv_stretch_display
    )
    bpy.types.Scene.uv_show_overlap = bpy.props.BoolProperty(
        name="显示重叠",
        default=False,
        update=operators.update_uv_overlap_display
    )
    bpy.types.Scene.uv_overlap_face_count = bpy.props.IntProperty(
        name="重叠面数量",
        default=0, min=0
    )
    bpy.types.Scene.uv_stretch_type = bpy.props.EnumProperty(
        name="拉伸类型",
        items=[
            ('AREA', "面积", ""),
            ('ANGLE', "角度", ""),
        ],
        default='AREA',
        update=operators.update_uv_stretch_display
    )
    bpy.types.Scene.uv_overlap_selection_mode = bpy.props.EnumProperty(
        name="选择模式",
        items=[
            ('REPLACE', "替换选择", ""),
            ('ADD', "添加到选择", ""),
        ],
        default='REPLACE'
    )
    bpy.types.Scene.uv_cached_overlap_faces = bpy.props.StringProperty(
        name="缓存的重叠面索引",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    # RizomUV Scene 属性
    bpy.types.Scene.uv_ruv_map = bpy.props.IntProperty(
        name="UV Map 通道",
        default=1, min=1, max=8,
    )
    bpy.types.Scene.uv_ruv_mode = bpy.props.EnumProperty(
        name="模式",
        items=[
            ('New', "New", ""),
            ('Edit', "Edit", ""),
        ],
        default='Edit',
    )
    bpy.types.Scene.uv_ruv_toggle = bpy.props.BoolProperty(
        name="RUV_Toggle",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )


def unregister():
    operators.stop_all_timers()

    for attr in ("uv_ruv_toggle", "uv_ruv_mode", "uv_ruv_map",
                 "uv_cached_overlap_faces", "uv_overlap_selection_mode",
                 "uv_stretch_type", "uv_overlap_face_count",
                 "uv_show_overlap", "uv_show_stretch",
                 "uv_unified_name", "uv_last_export_path",
                 "uv_target_object", "uv_source_object"):
        if hasattr(bpy.types.Scene, attr):
            delattr(bpy.types.Scene, attr)

    ui.unregister()
    operators.unregister()