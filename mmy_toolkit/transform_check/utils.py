"""Transform 质检模块 - 工具函数"""

from collections import Counter
from dataclasses import dataclass, field

import bpy


ISSUE_ORDER = (
    "rotation",
    "scale",
    "negative_scale",
    "location",
    "parent_dirty",
)

ISSUE_LABELS = {
    "rotation": "旋转非零",
    "scale": "缩放非 1",
    "negative_scale": "负缩放",
    "location": "位移非零",
    "parent_dirty": "父级变换异常",
}

ISSUE_PROPERTY_MAP = (
    ("旋转", "issue_count_rotation"),
    ("缩放", "issue_count_scale"),
    ("负缩放", "issue_count_negative_scale"),
    ("位移", "issue_count_location"),
    ("父级", "issue_count_parent_dirty"),
)

BLOCKER_ORDER = (
    "含 Shape Keys",
    "含动画数据",
    "含约束",
    "骨架修改器风险",
    "链接/Override 风险",
    "不在当前视图层",
)

PREVIEW_LIMIT = 6


@dataclass
class ScanEntry:
    obj: bpy.types.Object
    issues: list[str]
    fix_blockers: list[str] = field(default_factory=list)


@dataclass
class ScanSummary:
    scanned_objects: list[bpy.types.Object] = field(default_factory=list)
    issue_entries: list[ScanEntry] = field(default_factory=list)
    issue_counts: dict[str, int] = field(
        default_factory=lambda: {key: 0 for key in ISSUE_ORDER}
    )
    blocker_counts: Counter = field(default_factory=Counter)

    @property
    def problem_count(self) -> int:
        return len(self.issue_entries)

    @property
    def safe_fix_count(self) -> int:
        return sum(
            1
            for entry in self.issue_entries
            if has_fixable_issue(entry.issues, True, True, True) and not entry.fix_blockers
        )

    @property
    def blocked_fix_count(self) -> int:
        return sum(
            1
            for entry in self.issue_entries
            if has_fixable_issue(entry.issues, True, True, True) and entry.fix_blockers
        )


def any_check_enabled(settings) -> bool:
    return any(
        (
            settings.check_rotation,
            settings.check_scale,
            settings.check_negative_scale,
            settings.check_location,
            settings.check_parent_dirty,
        )
    )


def any_type_filter_enabled(settings) -> bool:
    return any(
        (
            settings.filter_mesh,
            settings.filter_armature,
            settings.filter_empty,
            settings.filter_curve,
        )
    )


def object_type_enabled(obj: bpy.types.Object, settings) -> bool:
    enabled_map = {
        "MESH": settings.filter_mesh,
        "ARMATURE": settings.filter_armature,
        "EMPTY": settings.filter_empty,
        "CURVE": settings.filter_curve,
    }
    return enabled_map.get(obj.type, False)


def gather_scan_objects(context, settings) -> list[bpy.types.Object]:
    if settings.scan_scope == "SELECTED":
        source = list(context.selected_objects)
    elif settings.scan_scope == "VISIBLE":
        source = [
            obj
            for obj in context.view_layer.objects
            if obj.visible_get(view_layer=context.view_layer)
        ]
    else:
        source = list(context.scene.objects)

    filtered = [obj for obj in source if object_type_enabled(obj, settings)]
    return sorted(filtered, key=lambda item: item.name.casefold())


def has_non_zero_location(obj: bpy.types.Object, epsilon: float) -> bool:
    return any(abs(value) > epsilon for value in obj.location)


def has_non_zero_rotation(obj: bpy.types.Object, epsilon: float) -> bool:
    if obj.rotation_mode == "QUATERNION":
        quat = obj.rotation_quaternion
        return (
            abs(abs(quat.w) - 1.0) > epsilon
            or abs(quat.x) > epsilon
            or abs(quat.y) > epsilon
            or abs(quat.z) > epsilon
        )
    if obj.rotation_mode == "AXIS_ANGLE":
        return abs(obj.rotation_axis_angle[0]) > epsilon
    return any(abs(value) > epsilon for value in obj.rotation_euler)


def has_non_unit_scale(obj: bpy.types.Object, epsilon: float) -> bool:
    return any(abs(value - 1.0) > epsilon for value in obj.scale)


def has_negative_scale(obj: bpy.types.Object, epsilon: float) -> bool:
    return any(value < -epsilon for value in obj.scale)


def has_any_local_transform_issue(obj: bpy.types.Object, epsilon: float) -> bool:
    return (
        has_non_zero_location(obj, epsilon)
        or has_non_zero_rotation(obj, epsilon)
        or has_non_unit_scale(obj, epsilon)
        or has_negative_scale(obj, epsilon)
    )


def has_parent_dirty_transform(obj: bpy.types.Object, epsilon: float) -> bool:
    parent = obj.parent
    while parent:
        if has_any_local_transform_issue(parent, epsilon):
            return True
        parent = parent.parent
    return False


def collect_object_issues(obj: bpy.types.Object, settings) -> list[str]:
    epsilon = settings.epsilon
    issues: list[str] = []

    if settings.check_rotation and has_non_zero_rotation(obj, epsilon):
        issues.append("rotation")
    if settings.check_scale and has_non_unit_scale(obj, epsilon):
        issues.append("scale")
    if settings.check_negative_scale and has_negative_scale(obj, epsilon):
        issues.append("negative_scale")
    if settings.check_location and has_non_zero_location(obj, epsilon):
        issues.append("location")
    if settings.check_parent_dirty and has_parent_dirty_transform(obj, epsilon):
        issues.append("parent_dirty")

    return issues


def has_shape_keys(obj: bpy.types.Object) -> bool:
    data = getattr(obj, "data", None)
    shape_keys = getattr(data, "shape_keys", None) if data else None
    key_blocks = getattr(shape_keys, "key_blocks", None) if shape_keys else None
    return bool(key_blocks and len(key_blocks) > 0)


def has_animation_data(obj: bpy.types.Object) -> bool:
    if obj.animation_data:
        return True
    data = getattr(obj, "data", None)
    return bool(data and getattr(data, "animation_data", None))


def has_constraints(obj: bpy.types.Object) -> bool:
    return len(obj.constraints) > 0


def has_armature_modifier_risk(obj: bpy.types.Object) -> bool:
    modifiers = getattr(obj, "modifiers", None)
    if not modifiers:
        return False
    return any(mod.type == "ARMATURE" for mod in modifiers)


def is_linked_or_override_risky(obj: bpy.types.Object) -> bool:
    data = getattr(obj, "data", None)
    if obj.library or obj.override_library:
        return True
    if data and (
        getattr(data, "library", None) or getattr(data, "override_library", None)
    ):
        return True
    if hasattr(obj, "is_editable") and not obj.is_editable:
        return True
    if data and hasattr(data, "is_editable") and not data.is_editable:
        return True
    return False


def has_fixable_issue(
    issues: list[str], apply_location: bool, apply_rotation: bool, apply_scale: bool
) -> bool:
    if apply_location and "location" in issues:
        return True
    if apply_rotation and "rotation" in issues:
        return True
    if apply_scale and ("scale" in issues or "negative_scale" in issues):
        return True
    return False


def collect_fix_blockers(obj: bpy.types.Object, issues: list[str]) -> list[str]:
    if not has_fixable_issue(issues, True, True, True):
        return []

    blockers: list[str] = []

    if has_shape_keys(obj):
        blockers.append("含 Shape Keys")
    if has_animation_data(obj):
        blockers.append("含动画数据")
    if has_constraints(obj):
        blockers.append("含约束")
    if has_armature_modifier_risk(obj):
        blockers.append("骨架修改器风险")
    if is_linked_or_override_risky(obj):
        blockers.append("链接/Override 风险")

    return blockers


def build_scan_summary(context, settings) -> ScanSummary:
    summary = ScanSummary()
    summary.scanned_objects = gather_scan_objects(context, settings)

    for obj in summary.scanned_objects:
        issues = collect_object_issues(obj, settings)
        if not issues:
            continue

        blockers = collect_fix_blockers(obj, issues)
        entry = ScanEntry(obj=obj, issues=issues, fix_blockers=blockers)
        summary.issue_entries.append(entry)

        for issue in issues:
            summary.issue_counts[issue] += 1

        if has_fixable_issue(issues, True, True, True):
            for blocker in blockers:
                summary.blocker_counts[blocker] += 1

    return summary


def summarize_issue_names(issues: list[str]) -> str:
    return "、".join(ISSUE_LABELS[key] for key in issues)


def build_problem_preview(entries: list[ScanEntry]) -> str:
    if not entries:
        return ""

    lines = []
    for entry in entries[:PREVIEW_LIMIT]:
        lines.append(f"{entry.obj.name}（{summarize_issue_names(entry.issues)}）")

    remaining = len(entries) - PREVIEW_LIMIT
    if remaining > 0:
        lines.append(f"……其余 {remaining} 个")

    return "\n".join(lines)


def format_counter_lines(counter, order: tuple[str, ...]) -> str:
    lines = []
    for key in order:
        count = counter.get(key, 0)
        if count:
            lines.append(f"{key}: {count}")
    return "\n".join(lines)


def update_result_properties(settings, summary: ScanSummary) -> None:
    settings.has_scan_result = True
    settings.last_scanned_count = len(summary.scanned_objects)
    settings.last_problem_count = summary.problem_count
    settings.last_safe_fix_count = summary.safe_fix_count
    settings.issue_count_rotation = summary.issue_counts["rotation"]
    settings.issue_count_scale = summary.issue_counts["scale"]
    settings.issue_count_negative_scale = summary.issue_counts["negative_scale"]
    settings.issue_count_location = summary.issue_counts["location"]
    settings.issue_count_parent_dirty = summary.issue_counts["parent_dirty"]
    settings.problem_names_preview = build_problem_preview(summary.issue_entries)
    settings.fix_skip_summary = format_counter_lines(summary.blocker_counts, BLOCKER_ORDER)


def build_scan_action_report(settings, summary: ScanSummary) -> str:
    if not any_type_filter_enabled(settings):
        return "未启用任何对象类型过滤。"
    if not any_check_enabled(settings):
        return "未启用任何检查项。"
    if not summary.scanned_objects:
        return "扫描对象数为 0，当前范围和过滤条件下没有匹配对象。"
    if not summary.issue_entries:
        return f"已扫描 {len(summary.scanned_objects)} 个对象，未发现 Transform 问题。"

    lines = [
        f"已扫描 {len(summary.scanned_objects)} 个对象",
        f"问题对象 {summary.problem_count} 个",
        f"可安全修复 {summary.safe_fix_count} 个",
    ]

    if summary.blocked_fix_count:
        lines.append(f"自动跳过 {summary.blocked_fix_count} 个风险对象")

    return "\n".join(lines)


def ensure_object_mode(context) -> tuple[bool, str]:
    active_obj = context.object
    if active_obj and active_obj.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError as exc:
            return False, str(exc)
    return True, ""


def tag_redraw_view3d(context) -> None:
    screen = getattr(context, "screen", None)
    if not screen:
        return
    for area in screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()


def evaluate_fix_targets(
    context,
    summary: ScanSummary,
    apply_location: bool,
    apply_rotation: bool,
    apply_scale: bool,
) -> tuple[list[bpy.types.Object], Counter, int]:
    view_layer_names = {obj.name for obj in context.view_layer.objects}
    targets: list[bpy.types.Object] = []
    skipped_counter: Counter = Counter()
    skipped_object_count = 0

    for entry in summary.issue_entries:
        if not has_fixable_issue(entry.issues, apply_location, apply_rotation, apply_scale):
            continue

        blockers = list(entry.fix_blockers)
        if entry.obj.name not in view_layer_names:
            blockers.append("不在当前视图层")

        if blockers:
            skipped_object_count += 1
            for blocker in blockers:
                skipped_counter[blocker] += 1
            continue

        targets.append(entry.obj)

    return targets, skipped_counter, skipped_object_count


def capture_object_states(
    view_layer, objects: list[bpy.types.Object]
) -> dict[str, dict[str, bool]]:
    states: dict[str, dict[str, bool]] = {}
    for obj in objects:
        states[obj.name] = {
            "hide_select": bool(getattr(obj, "hide_select", False)),
            "hide_viewport": bool(getattr(obj, "hide_viewport", False)),
            "hide_view_layer": bool(obj.hide_get(view_layer=view_layer)),
        }
    return states


def prepare_object_for_object_ops(obj: bpy.types.Object, view_layer) -> None:
    if obj.hide_get(view_layer=view_layer):
        obj.hide_set(False, view_layer=view_layer)
    if getattr(obj, "hide_viewport", False):
        obj.hide_viewport = False
    if getattr(obj, "hide_select", False):
        obj.hide_select = False


def restore_object_states(
    view_layer,
    objects: list[bpy.types.Object],
    states: dict[str, dict[str, bool]],
) -> None:
    for obj in objects:
        state = states.get(obj.name)
        if not state:
            continue
        obj.hide_select = state["hide_select"]
        obj.hide_viewport = state["hide_viewport"]
        obj.hide_set(state["hide_view_layer"], view_layer=view_layer)


def apply_transform_fix(
    context,
    targets: list[bpy.types.Object],
    apply_location: bool,
    apply_rotation: bool,
    apply_scale: bool,
) -> tuple[bool, str]:
    if not targets:
        return False, "当前修复模式下没有可安全处理的对象。"

    ok, message = ensure_object_mode(context)
    if not ok:
        return False, message

    view_layer = context.view_layer
    view_layer_names = {obj.name for obj in view_layer.objects}
    eligible = [obj for obj in targets if obj.name in view_layer_names]
    if not eligible:
        return False, "没有可在当前视图层中执行修复的对象。"

    previous_active = view_layer.objects.active
    previous_selected = [obj for obj in view_layer.objects if obj.select_get()]
    states = capture_object_states(view_layer, eligible)

    try:
        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action="DESELECT")

        for obj in eligible:
            prepare_object_for_object_ops(obj, view_layer)
            obj.select_set(True)

        view_layer.objects.active = eligible[0]

        result = bpy.ops.object.transform_apply(
            location=apply_location,
            rotation=apply_rotation,
            scale=apply_scale,
        )

        if "FINISHED" not in result:
            return False, "应用 Transform 失败。"

    except RuntimeError as exc:
        return False, str(exc)

    finally:
        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action="DESELECT")

        for obj in previous_selected:
            if obj.name in view_layer_names:
                obj.select_set(True)

        if previous_active and previous_active.name in view_layer_names:
            view_layer.objects.active = previous_active

        restore_object_states(view_layer, eligible, states)

    return True, ""


def build_fix_action_report(
    action_label: str,
    applied_count: int,
    skipped_counter: Counter,
    skipped_object_count: int,
    post_summary: ScanSummary,
) -> str:
    lines = []
    if applied_count:
        lines.append(f"{action_label}：已处理 {applied_count} 个对象")
    else:
        lines.append(f"{action_label}：没有修改任何安全对象")

    if skipped_object_count:
        lines.append(f"跳过风险对象 {skipped_object_count} 个")
        for line in format_counter_lines(skipped_counter, BLOCKER_ORDER).splitlines():
            lines.append(line)

    if post_summary.problem_count:
        lines.append(f"剩余问题对象 {post_summary.problem_count} 个")
    else:
        lines.append("修复后未发现 Transform 问题")

    return "\n".join(lines)


def build_issue_count_summary(settings) -> str:
    parts = []
    for label, attr_name in ISSUE_PROPERTY_MAP:
        count = getattr(settings, attr_name)
        if count:
            parts.append(f"{label}:{count}")
    return "  ".join(parts)


def selection_has_transform_issue(context) -> bool:
    settings = getattr(context.scene, "tqa_settings", None)
    if not settings:
        return False

    selected_objects = getattr(context, "selected_objects", None) or []
    epsilon = settings.epsilon
    return any(has_any_local_transform_issue(obj, epsilon) for obj in selected_objects)