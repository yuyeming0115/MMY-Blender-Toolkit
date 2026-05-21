"""Transform 质检模块 - 操作符"""

import bpy
from bpy.types import Operator

from .utils import (
    build_scan_summary,
    update_result_properties,
    build_scan_action_report,
    tag_redraw_view3d,
    ensure_object_mode,
    build_fix_action_report,
    evaluate_fix_targets,
    apply_transform_fix,
    selection_has_transform_issue,
    has_fixable_issue,
)


class TQA_OT_scan(Operator):
    bl_idname = "mmy.tqa_scan"
    bl_label = "扫描"
    bl_description = "扫描对象的 Transform 风险"

    def execute(self, context):
        settings = context.scene.tqa_settings
        summary = build_scan_summary(context, settings)
        update_result_properties(settings, summary)
        settings.last_action_report = build_scan_action_report(settings, summary)
        tag_redraw_view3d(context)
        self.report({"INFO"}, settings.last_action_report.replace("\n", " | "))
        return {"FINISHED"}


class TQA_OT_select_problem_objects(Operator):
    bl_idname = "mmy.tqa_select_problem"
    bl_label = "选择问题对象"
    bl_description = "选中全部问题对象"

    def execute(self, context):
        from .utils import prepare_object_for_object_ops

        settings = context.scene.tqa_settings
        summary = build_scan_summary(context, settings)
        update_result_properties(settings, summary)

        if not summary.issue_entries:
            settings.last_action_report = "未发现 Transform 问题。"
            tag_redraw_view3d(context)
            self.report({"INFO"}, settings.last_action_report)
            return {"FINISHED"}

        ok, message = ensure_object_mode(context)
        if not ok:
            self.report({"WARNING"}, message)
            return {"CANCELLED"}

        view_layer = context.view_layer
        view_layer_names = {obj.name for obj in view_layer.objects}
        target_objects = []
        skipped_count = 0

        for entry in summary.issue_entries:
            obj = entry.obj
            if obj.name not in view_layer_names:
                skipped_count += 1
                continue
            prepare_object_for_object_ops(obj, view_layer)
            target_objects.append(obj)

        if not target_objects:
            settings.last_action_report = "存在问题对象，但不在当前视图层。"
            tag_redraw_view3d(context)
            self.report({"WARNING"}, settings.last_action_report)
            return {"CANCELLED"}

        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action="DESELECT")

        for obj in target_objects:
            obj.select_set(True)

        view_layer.objects.active = target_objects[0]

        lines = [f"已选中 {len(target_objects)} 个问题对象"]
        if skipped_count:
            lines.append(f"跳过 {skipped_count} 个不在当前视图层的对象")

        settings.last_action_report = "\n".join(lines)
        tag_redraw_view3d(context)
        self.report({"INFO"}, settings.last_action_report.replace("\n", " | "))
        return {"FINISHED"}


class TQA_OT_fix_base(Operator):
    bl_options = {"REGISTER", "UNDO"}

    apply_location = False
    apply_rotation = False
    apply_scale = False
    action_label = "修复"

    def execute(self, context):
        settings = context.scene.tqa_settings
        pre_summary = build_scan_summary(context, settings)
        update_result_properties(settings, pre_summary)

        targets, skipped_counter, skipped_object_count = evaluate_fix_targets(
            context,
            pre_summary,
            self.apply_location,
            self.apply_rotation,
            self.apply_scale,
        )

        success, error_message = apply_transform_fix(
            context,
            targets,
            self.apply_location,
            self.apply_rotation,
            self.apply_scale,
        )
        if not success and targets:
            self.report({"WARNING"}, error_message)
            return {"CANCELLED"}

        post_summary = build_scan_summary(context, settings)
        update_result_properties(settings, post_summary)
        settings.last_action_report = build_fix_action_report(
            self.action_label,
            len(targets) if success else 0,
            skipped_counter,
            skipped_object_count,
            post_summary,
        )
        tag_redraw_view3d(context)
        self.report({"INFO"}, settings.last_action_report.replace("\n", " | "))
        return {"FINISHED"}


class TQA_OT_fix_rotation(TQA_OT_fix_base):
    bl_idname = "mmy.tqa_fix_rotation"
    bl_label = "修旋转"
    bl_description = "应用旋转修复"

    apply_rotation = True
    apply_scale = False
    action_label = "修复旋转"


class TQA_OT_fix_location(TQA_OT_fix_base):
    bl_idname = "mmy.tqa_fix_location"
    bl_label = "修位移"
    bl_description = "应用位移修复"

    apply_location = True
    apply_rotation = False
    apply_scale = False
    action_label = "修复位移"


class TQA_OT_fix_scale(TQA_OT_fix_base):
    bl_idname = "mmy.tqa_fix_scale"
    bl_label = "修缩放"
    bl_description = "应用缩放修复"

    apply_rotation = False
    apply_scale = True
    action_label = "修复缩放"


class TQA_OT_fix_rotation_scale(TQA_OT_fix_base):
    bl_idname = "mmy.tqa_fix_rotation_scale"
    bl_label = "修旋转+缩放"
    bl_description = "应用旋转和缩放修复"

    apply_rotation = True
    apply_scale = True
    action_label = "修复旋转和缩放"


class TQA_OT_popup(Operator):
    bl_idname = "mmy.tqa_popup"
    bl_label = "Transform 质检"
    bl_description = "打开 Transform 质检弹窗"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context) -> bool:
        return context.area is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=360)

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        from .utils import build_issue_count_summary, build_problem_preview

        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        settings = context.scene.tqa_settings

        # 操作按钮
        action_box = layout.box()
        action_box.label(text="操作", icon="TOOL_SETTINGS")
        row = action_box.row(align=True)
        row.operator("mmy.tqa_scan", text="扫描", icon="VIEWZOOM")
        row.operator("mmy.tqa_select_problem", text="选择问题对象", icon="RESTRICT_SELECT_OFF")

        fix_grid = action_box.grid_flow(columns=2, align=True)
        fix_grid.operator("mmy.tqa_fix_location", text="修位移", icon="CHECKMARK")
        fix_grid.operator("mmy.tqa_fix_rotation", text="修旋转", icon="CHECKMARK")
        fix_grid.operator("mmy.tqa_fix_scale", text="修缩放", icon="CHECKMARK")
        fix_grid.operator("mmy.tqa_fix_rotation_scale", text="修旋转+缩放", icon="CHECKMARK")

        # 扫描结果
        if settings.has_scan_result:
            result_box = layout.box()
            result_box.label(text="扫描结果", icon="INFO")

            # 问题统计
            issue_summary = build_issue_count_summary(settings)
            if issue_summary:
                result_box.label(text=issue_summary)

            # 问题对象预览
            if settings.problem_names_preview:
                result_box.label(text="问题对象:")
                for line in settings.problem_names_preview.splitlines():
                    result_box.label(text=f"  {line}")

            # 跳过统计
            if settings.fix_skip_summary:
                result_box.label(text="跳过风险:")
                for line in settings.fix_skip_summary.splitlines():
                    result_box.label(text=f"  {line}")

        # 操作报告
        report_box = layout.box()
        report_box.label(text="报告", icon="TEXT")
        for line in settings.last_action_report.splitlines():
            report_box.label(text=line)


_classes = (
    TQA_OT_scan,
    TQA_OT_select_problem_objects,
    TQA_OT_fix_location,
    TQA_OT_fix_rotation,
    TQA_OT_fix_scale,
    TQA_OT_fix_rotation_scale,
    TQA_OT_popup,
)


def register():
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _draw_tqa_header_button(self, context):
    """顶栏按钮绘制（右侧区域）"""
    if context.region.alignment != 'RIGHT':
        return

    row = self.layout.row(align=True)
    row.alert = selection_has_transform_issue(context)
    row.operator("mmy.tqa_popup", text="TQA", icon="CHECKMARK")