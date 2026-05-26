"""雕刻 HUD GPU 绘制"""

import bpy
from .hud_state import _HUD_STATE, _AVAILABLE_BUTTONS, get_user_buttons

# 常量
HUD_TEXT_SIZE = 12
HUD_BUTTON_HEIGHT = 24
HUD_BUTTON_WIDTH = 80  # 加宽以容纳符号+文字
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
        print(f"[MMY Sculpt] 绘制错误: {e}")
        import traceback
        traceback.print_exc()


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

    # 获取偏好设置（布局模式）
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    layout_mode = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"

    # 使用全局偏移值（所有窗口同步）
    from .hud_state import get_global_offset
    offset_x, offset_y = get_global_offset()

    # 获取用户按钮列表，末尾添加 + 按钮
    user_buttons = get_user_buttons()
    buttons = user_buttons + ["add"]  # +按钮始终在末尾
    button_count = len(buttons)

    handle_width = HUD_HANDLE_WIDTH
    if layout_mode == "horizontal":
        total_width = handle_width + button_count * HUD_BUTTON_WIDTH + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = handle_width + button_count * HUD_BUTTON_HEIGHT + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
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
        # 水平布局：把手在左边
        handle_x = start_x
        handle_y = start_y
        handle_w = handle_width
        handle_h = total_height
    else:
        # 垂直布局：把手在底部
        handle_x = start_x
        handle_y = start_y + total_height - handle_width
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
        # 横线把手（在底部）
        line_y = handle_y + handle_h * 0.5
        draw_text("─", handle_x + handle_w * 0.5 - 4, line_y - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)

    # 绘制按钮（垂直布局时反转顺序）
    if layout_mode == "horizontal":
        button_order = buttons
    else:
        button_order = list(reversed(buttons))  # 反转顺序

    for i, button_id in enumerate(button_order):
        if layout_mode == "horizontal":
            btn_x = start_x + handle_width + HUD_MARGIN + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            btn_y = start_y + HUD_MARGIN
        else:
            # 垂直布局：按钮从上往下，把手在底部
            btn_x = start_x + HUD_MARGIN
            btn_y = start_y + HUD_MARGIN + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)

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

        # 绘制符号+文字
        label = _get_button_label(button_id, is_active)
        # 计算文字位置（居中）
        text_offset = len(label) * 3.5  # 粗略估算字符宽度
        draw_text(label, btn_x + HUD_BUTTON_WIDTH * 0.5 - text_offset, btn_y + HUD_BUTTON_HEIGHT * 0.5 - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)


def _check_button_active(space, obj, button_id):
    """检查按钮激活状态"""
    context = bpy.context
    overlay = space.overlay if space else None
    shading = space.shading if space else None
    tool_settings = context.tool_settings if context else None
    sculpt = tool_settings.sculpt if tool_settings else None

    if button_id == "face_sets":
        return overlay.show_sculpt_face_sets if overlay else False
    elif button_id == "mask":
        return overlay.show_sculpt_mask if overlay else False
    elif button_id == "wireframe":
        return overlay.show_wireframes if overlay else False
    elif button_id == "backface_culling":
        return shading.show_backface_culling if shading else False
    elif button_id == "symmetry":
        # 雕刻对称（检查 use_symmetry_x）
        if sculpt:
            return bool(getattr(sculpt, 'use_symmetry_x', False))
        return False
    elif button_id == "dynamic_topology":
        # 动态拓扑（检查属性值，而不是存在性）
        # 动态拓扑属性始终存在，需要检查是否处于活跃状态
        # 使用 dyntopo 开启时 detail_size 会有实际值
        try:
            if sculpt:
                detail_size = getattr(sculpt, 'detail_size', 0)
                # 动态拓扑开启时 detail_size 会有非零值
                return detail_size > 0
        except:
            pass
        return False
    elif button_id == "add":
        return False

    return False


def _get_button_label(button_id, is_active):
    """获取按钮显示文字（符号 + 文字）"""
    # 从 _AVAILABLE_BUTTONS 获取符号和标签
    from .hud_state import _AVAILABLE_BUTTONS

    if button_id == "add":
        return "+"

    button_info = _AVAILABLE_BUTTONS.get(button_id, {})
    symbol = button_info.get("symbol", "?")
    label = button_info.get("label", "?")

    # 符号 + 文字（激活状态加标记）
    if is_active:
        return f"{symbol} {label}"
    else:
        return f"{symbol} {label}"


__all__ = [
    'draw_sculpt_hud_callback',
    'HUD_BUTTON_WIDTH',
    'HUD_BUTTON_HEIGHT',
    'HUD_BUTTON_GAP',
    'HUD_MARGIN',
    'HUD_HANDLE_WIDTH',
]