"""雕刻 HUD GPU 绘制"""

import bpy
from .hud_state import _HUD_STATE, _DEFAULT_BUTTONS

# 常量
HUD_TEXT_SIZE = 12
HUD_BUTTON_HEIGHT = 24
HUD_BUTTON_WIDTH = 60
HUD_BUTTON_GAP = 4
HUD_CORNER_RADIUS = 6
HUD_MARGIN = 10
HUD_HANDLE_WIDTH = 20  # 拖拽把手宽度

# 颜色
HUD_BG_COLOR = (0.15, 0.15, 0.15, 0.85)
HUD_BORDER_COLOR = (0.3, 0.3, 0.3, 0.9)
HUD_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)
HUD_ACTIVE_COLOR = (0.2, 0.5, 0.8, 0.9)
HUD_HOVER_COLOR = (0.25, 0.25, 0.25, 0.9)
HUD_HANDLE_COLOR = (0.18, 0.18, 0.18, 0.9)


def draw_sculpt_hud_callback():
    """雕刻模式悬浮按钮绘制回调"""
    try:
        _draw_sculpt_hud_inner()
    except Exception as e:
        # 静默处理绘制错误
        pass


def _draw_sculpt_hud_inner():
    """实际绘制逻辑"""
    if not _HUD_STATE["enabled"]:
        return

    context = bpy.context
    window = getattr(context, "window", None)
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    space = getattr(context, "space_data", None)
    obj = getattr(context, "active_object", None)

    # 检查条件
    if window is None or area is None or region is None or space is None:
        return
    if area.type != "VIEW_3D" or region.type != "WINDOW" or space.type != "VIEW_3D":
        return
    if obj is None or obj.mode != 'SCULPT':
        return

    # 获取偏好设置
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    layout_mode = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"
    offset_x = getattr(prefs, "sculpt_hud_offset_x", 0) if prefs else 0
    offset_y = getattr(prefs, "sculpt_hud_offset_y", 0) if prefs else 0

    # 计算位置（包含拖拽把手）
    buttons = _DEFAULT_BUTTONS
    handle_width = HUD_HANDLE_WIDTH
    if layout_mode == "horizontal":
        total_width = handle_width + len(buttons) * HUD_BUTTON_WIDTH + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = handle_width + len(buttons) * HUD_BUTTON_HEIGHT + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5

    # 绘制背景
    from .draw_utils import draw_rounded_rect, draw_rounded_rect_outline, draw_text
    draw_rounded_rect(start_x, start_y, total_width, total_height, HUD_BG_COLOR, HUD_CORNER_RADIUS)
    draw_rounded_rect_outline(start_x, start_y, total_width, total_height, HUD_BORDER_COLOR, HUD_CORNER_RADIUS)

    # 绘制拖拽把手
    hovered = _HUD_STATE.get("hover")
    region_key = (window.as_pointer(), area.as_pointer(), region.as_pointer())
    is_handle_hovered = hovered == (region_key, "handle")

    if layout_mode == "horizontal":
        handle_x = start_x
        handle_y = start_y
        handle_w = handle_width
        handle_h = total_height
    else:
        handle_x = start_x
        handle_y = start_y
        handle_w = total_width
        handle_h = handle_width

    handle_color = HUD_HOVER_COLOR if is_handle_hovered else HUD_HANDLE_COLOR
    draw_rounded_rect(handle_x, handle_y, handle_w, handle_h, handle_color, HUD_CORNER_RADIUS)
    # 绘制把手图标（两条竖线或横线）
    if layout_mode == "horizontal":
        # 竖线把手
        line_x = handle_x + handle_w * 0.5
        draw_text("│", line_x - 4, handle_y + handle_h * 0.5 - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)
    else:
        # 横线把手
        line_y = handle_y + handle_h * 0.5
        draw_text("─", handle_x + handle_w * 0.5 - 4, line_y - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)

    for i, button_id in enumerate(buttons):
        if layout_mode == "horizontal":
            btn_x = start_x + handle_width + HUD_MARGIN + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            btn_y = start_y + HUD_MARGIN
        else:
            btn_x = start_x + HUD_MARGIN
            btn_y = start_y + handle_width + HUD_MARGIN + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)

        # 检查状态
        is_active = _check_button_active(space, obj, button_id)
        is_hovered = hovered == (region_key, button_id)

        # 确定颜色
        if is_active and is_hovered:
            fill_color = (HUD_ACTIVE_COLOR[0] + 0.1, HUD_ACTIVE_COLOR[1] + 0.1, HUD_ACTIVE_COLOR[2] + 0.1, HUD_ACTIVE_COLOR[3])
        elif is_active:
            fill_color = HUD_ACTIVE_COLOR
        elif is_hovered:
            fill_color = HUD_HOVER_COLOR
        else:
            fill_color = (HUD_BG_COLOR[0] + 0.05, HUD_BG_COLOR[1] + 0.05, HUD_BG_COLOR[2] + 0.05, HUD_BG_COLOR[3])

        # 绘制按钮
        draw_rounded_rect(btn_x, btn_y, HUD_BUTTON_WIDTH, HUD_BUTTON_HEIGHT, fill_color, HUD_CORNER_RADIUS - 2)
        draw_rounded_rect_outline(btn_x, btn_y, HUD_BUTTON_WIDTH, HUD_BUTTON_HEIGHT, HUD_BORDER_COLOR, HUD_CORNER_RADIUS - 2)

        # 绘制文字
        label = _get_button_label(button_id, is_active)
        draw_text(label, btn_x + HUD_BUTTON_WIDTH * 0.5 - len(label) * 3, btn_y + HUD_BUTTON_HEIGHT * 0.5 - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)


def _check_button_active(space, obj, button_id):
    """检查按钮激活状态"""
    overlay = space.overlay if space else None

    if button_id == "face_sets":
        return overlay.show_sculpt_face_sets if overlay else False
    elif button_id == "mask":
        # 遮罩显示
        return overlay.show_sculpt_mask if overlay else False
    elif button_id == "wireframe":
        return overlay.show_wireframes if overlay else False
    elif button_id == "add":
        return False

    return False


def _get_button_label(button_id, is_active):
    """获取按钮显示文字"""
    labels = {
        "face_sets": "面组" if is_active else "面组",
        "mask": "遮罩" if is_active else "遮罩",
        "wireframe": "线框" if is_active else "线框",
        "add": "+",
    }
    return labels.get(button_id, "?")


__all__ = [
    'draw_sculpt_hud_callback',
    'HUD_BUTTON_WIDTH',
    'HUD_BUTTON_HEIGHT',
    'HUD_BUTTON_GAP',
    'HUD_MARGIN',
    'HUD_HANDLE_WIDTH',
]