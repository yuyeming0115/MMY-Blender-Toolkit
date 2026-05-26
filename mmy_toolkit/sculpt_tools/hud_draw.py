"""雕刻 HUD GPU 绘制"""

import bpy
from .hud_state import _HUD_STATE, _AVAILABLE_BUTTONS, get_user_buttons

# 常量
HUD_TEXT_SIZE = 12
HUD_BUTTON_HEIGHT = 24
HUD_BUTTON_WIDTH = 60  # 缩小宽度以适应符号+文字
HUD_BUTTON_GAP = 4
HUD_CORNER_RADIUS = 6
HUD_MARGIN = 10
HUD_HANDLE_WIDTH = 20  # 拖拽把手宽度

# 边缘吸附相关常量
HUD_EDGE_SNAP_THRESHOLD = 50  # 吸附触发阈值（像素）
HUD_TOP_SAFE_MARGIN = 80  # 顶部安全距离（Header + 透明层）
HUD_BOTTOM_SAFE_MARGIN = 20  # 底部安全距离
HUD_SIDE_SAFE_MARGIN = 10  # 侧边安全距离

# 颜色
HUD_BG_COLOR = (0.15, 0.15, 0.15, 0.85)
HUD_BORDER_COLOR = (0.3, 0.3, 0.3, 0.9)
HUD_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)
HUD_ACTIVE_COLOR = (0.2, 0.5, 0.8, 0.9)
HUD_HOVER_COLOR = (0.25, 0.25, 0.25, 0.9)
HUD_HANDLE_COLOR = (0.18, 0.18, 0.18, 0.9)


# ============ 区域宽度检测函数（借鉴 FocusMode） ============

def get_sidebar_width(area, space):
    """获取右侧侧边栏宽度（N 面板）"""
    if not hasattr(space, "show_region_ui") or not space.show_region_ui:
        return 0
    for region in area.regions:
        if region.type == "UI":
            return region.width
    return 0


def get_left_toolbar_width(area, space):
    """获取左侧工具栏宽度（T 面板）"""
    if not hasattr(space, "show_region_toolbar") or not space.show_region_toolbar:
        return 0
    for region in area.regions:
        if region.type == "TOOLS":
            return region.width
    return 0


def get_top_toolbar_height(area, space):
    """获取顶部工具栏高度（Header）"""
    if not hasattr(space, "show_region_header") or not space.show_region_header:
        return 0
    total_height = 0
    for region in area.regions:
        if region.type in ("HEADER", "TOOL_HEADER"):
            total_height += region.height
    return total_height


def get_bottom_toolbar_height(area, space):
    """获取底部工具栏高度（Footer）"""
    for region in area.regions:
        if region.type == "FOOTER" and region.height > 0:
            return region.height
    return 0


def get_effective_viewport_bounds(area, space, region):
    """获取有效视口边界（扣除各区域后的可用空间）"""
    left = get_left_toolbar_width(area, space)
    right = region.width - get_sidebar_width(area, space)
    top = region.height - max(HUD_TOP_SAFE_MARGIN, get_top_toolbar_height(area, space) + 40)
    bottom = max(HUD_BOTTOM_SAFE_MARGIN, get_bottom_toolbar_height(area, space))

    return {
        "left": left + HUD_SIDE_SAFE_MARGIN,
        "right": right - HUD_SIDE_SAFE_MARGIN,
        "top": top,
        "bottom": bottom + HUD_SIDE_SAFE_MARGIN,
        "width": right - left - 2 * HUD_SIDE_SAFE_MARGIN,
        "height": top - bottom - HUD_SIDE_SAFE_MARGIN,
    }


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

    # 导入绘制工具
    from .draw_utils import draw_rounded_rect, draw_rounded_rect_outline, draw_text

    # ============ 获取有效视口边界（智能 padding） ============
    bounds = get_effective_viewport_bounds(area, space, region)

    # ============ 新的位置计算逻辑 ============

    if layout_mode == "horizontal":
        # 水平布局：把手高度 = HUD 高度
        hud_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        handle_button_height = hud_height

        # 计算把手 Y 位置（带偏移），限制在有效边界内
        center_y = (bounds["top"] + bounds["bottom"]) * 0.5
        base_y = center_y - hud_height * 0.5
        handle_y = base_y + offset_y * bounds["height"]

        # 限制把手在有效边界内
        max_y = bounds["top"] - hud_height
        min_y = bounds["bottom"]
        handle_y = max(min_y, min(max_y, handle_y))

        # 计算把手 X 位置（带偏移），限制在有效边界内
        total_width = handle_width + button_count * HUD_BUTTON_WIDTH + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        center_x = (bounds["left"] + bounds["right"]) * 0.5
        base_x = center_x - total_width * 0.5
        handle_x = base_x + offset_x * bounds["width"]

        # 限制 X 在有效边界内
        handle_x = max(bounds["left"], min(bounds["right"] - total_width, handle_x))

        handle_w = handle_width
        handle_h = hud_height
    else:
        # 垂直布局：使用动态展开方向
        hud_total_height = handle_width + button_count * HUD_BUTTON_HEIGHT + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2

        # 计算把手中心 Y 位置（带偏移）
        center_y = (bounds["top"] + bounds["bottom"]) * 0.5
        handle_center_y = center_y + offset_y * bounds["height"]

        # 边缘吸附检测（使用有效边界）
        expand_downward = True
        force_expand_direction = None

        # 顶部吸附检测
        if handle_center_y >= bounds["top"] - HUD_EDGE_SNAP_THRESHOLD:
            force_expand_direction = "down"
            handle_y = bounds["top"] - handle_width
            expand_downward = True

        # 底部吸附检测
        elif handle_center_y <= bounds["bottom"] + HUD_EDGE_SNAP_THRESHOLD:
            force_expand_direction = "up"
            handle_y = bounds["bottom"]
            expand_downward = False
        else:
            # 正常位置：根据把手位置决定展开方向
            expand_downward = handle_center_y < center_y

            if expand_downward:
                handle_y = handle_center_y - handle_width * 0.5
                handle_y = max(bounds["bottom"], min(bounds["top"] - handle_width, handle_y))
            else:
                handle_y = handle_center_y - handle_width * 0.5
                handle_y = max(bounds["bottom"], handle_y)

        # 计算把手 X 位置（使用有效边界）
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        center_x = (bounds["left"] + bounds["right"]) * 0.5
        handle_x = center_x + offset_x * bounds["width"] - total_width * 0.5
        handle_x = max(bounds["left"], min(bounds["right"] - total_width, handle_x))

        handle_w = total_width
        handle_h = handle_width

    # 绘制把手
    hovered = _HUD_STATE.get("hover")
    region_key = (window.as_pointer(), area.as_pointer(), region.as_pointer())
    is_handle_hovered = hovered == (region_key, "handle")

    handle_color = HUD_HOVER_COLOR if is_handle_hovered else HUD_HANDLE_COLOR
    draw_rounded_rect(handle_x, handle_y, handle_w, handle_h, handle_color, HUD_CORNER_RADIUS)

    # 绘制把手图标
    if layout_mode == "horizontal":
        line_x = handle_x + handle_w * 0.5
        draw_text("│", line_x - 4, handle_y + handle_h * 0.5 - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)
    else:
        line_y = handle_y + handle_h * 0.5
        draw_text("─", handle_x + handle_w * 0.5 - 4, line_y - 6, HUD_TEXT_COLOR, HUD_TEXT_SIZE)

    # ============ 绘制按钮 ============

    if layout_mode == "horizontal":
        # 水平布局：按钮在把手右侧
        btn_start_x = handle_x + handle_width + HUD_MARGIN
        btn_y = handle_y + HUD_MARGIN

        for i, button_id in enumerate(buttons):
            btn_x = btn_start_x + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            _draw_button(btn_x, btn_y, button_id, space, obj, hovered, region_key, draw_rounded_rect, draw_rounded_rect_outline, draw_text)

    else:
        # 垂直布局：根据展开方向决定按钮位置
        btn_x = handle_x + HUD_MARGIN

        if expand_downward:
            btn_start_y = handle_y + handle_width + HUD_BUTTON_GAP
            button_order = list(reversed(buttons))  # 从下往上排列
        else:
            btn_start_y = handle_y - HUD_BUTTON_HEIGHT - HUD_BUTTON_GAP
            button_order = buttons  # 从上往下排列

        for i, button_id in enumerate(button_order):
            if expand_downward:
                btn_y = btn_start_y + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)
            else:
                btn_y = btn_start_y - i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)
            _draw_button(btn_x, btn_y, button_id, space, obj, hovered, region_key, draw_rounded_rect, draw_rounded_rect_outline, draw_text)


def _draw_button(btn_x, btn_y, button_id, space, obj, hovered, region_key, draw_rounded_rect, draw_rounded_rect_outline, draw_text):
    """绘制单个按钮"""
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
    text_offset = len(label) * 3.5
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
        # 对称：检查网格镜像属性（mesh.use_mirror_x）
        mesh = obj.data if obj and obj.type == 'MESH' else None
        if mesh:
            return bool(getattr(mesh, 'use_mirror_x', False))
        return False
    elif button_id == "dynamic_topology":
        # 动态拓扑：使用手动跟踪状态（Blender API 不直接暴露）
        return _HUD_STATE.get("dyntopo_active", False)
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