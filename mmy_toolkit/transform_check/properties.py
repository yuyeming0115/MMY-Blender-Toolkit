"""Transform 质检模块 - 属性定义"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)


class TQA_Properties(PropertyGroup):
    """Transform 质检设置"""

    scan_scope: EnumProperty(
        name="范围",
        description="扫描范围",
        items=(
            ("SELECTED", "选定对象", "扫描当前选中的对象"),
            ("VISIBLE", "可见对象", "扫描当前视图层中可见的对象"),
            ("SCENE", "整个场景", "扫描当前场景中的全部对象"),
        ),
        default="SELECTED",
    )

    check_rotation: BoolProperty(name="旋转非零", default=True)
    check_scale: BoolProperty(name="缩放非 1", default=True)
    check_negative_scale: BoolProperty(name="负缩放", default=True)
    check_location: BoolProperty(name="位移非零", default=False)
    check_parent_dirty: BoolProperty(name="父级变换异常", default=True)

    filter_mesh: BoolProperty(name="网格", default=True)
    filter_armature: BoolProperty(name="骨架", default=True)
    filter_empty: BoolProperty(name="空物体", default=True)
    filter_curve: BoolProperty(name="曲线", default=False)

    epsilon: FloatProperty(
        name="容差",
        description="Transform 判断容差",
        default=0.0001,
        min=1e-8,
        soft_max=0.1,
        precision=6,
    )

    has_scan_result: BoolProperty(default=False)
    last_scanned_count: IntProperty(default=0)
    last_problem_count: IntProperty(default=0)
    last_safe_fix_count: IntProperty(default=0)
    show_result_details: BoolProperty(name="展开扫描结果", default=False)
    issue_count_rotation: IntProperty(default=0)
    issue_count_scale: IntProperty(default=0)
    issue_count_negative_scale: IntProperty(default=0)
    issue_count_location: IntProperty(default=0)
    issue_count_parent_dirty: IntProperty(default=0)
    problem_names_preview: StringProperty(default="")
    fix_skip_summary: StringProperty(default="")
    last_action_report: StringProperty(default="点击'扫描'开始检查。")


_classes = (TQA_Properties,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.tqa_settings = PointerProperty(type=TQA_Properties)


def unregister():
    try:
        del bpy.types.Scene.tqa_settings
    except:
        pass
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass