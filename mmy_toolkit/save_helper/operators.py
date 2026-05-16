import bpy

from ..config import get_suffixes
from ..utils import apply_suffix


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


def _has_suffix_active(filename: str, suffix: str) -> bool:
    base = filename
    if base.lower().endswith(".blend"):
        base = base[:-len(".blend")]
    return base.lower().endswith(suffix.lower())


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
    for suffix in get_suffixes():
        op = row.operator("mmy.save_with_suffix", text=suffix)
        op.suffix = suffix
