"""智能选择 HUD 提示系统

在执行选择操作后，在屏幕显示完整的快捷键指南。
智能避开左右面板（N面板、T面板）。
"""

import bpy
import time

# 提示状态
_HUD_TIP_STATE = {
    "active": False,
    "highlight_type": None,
    "start_time": 0,
    "duration": 3.0,
    "fade_start": 2.5,
}

# 所有快捷键提示
_TIPS = [
    {"type": "uv_island", "label": "UV 孤岛", "shortcut": "双击", "color": (0.3, 0.8, 1.0)},
    {"type": "mesh_linked", "label": "相连元素", "shortcut": "双击", "color": (0.4, 1.0, 0.6)},
    {"type": "material", "label": "相同材质", "shortcut": "Shift+双击", "color": (1.0, 0.85, 0.2)},
    {"type": "seam", "label": "缝合边", "shortcut": "Ctrl+双击", "color": (1.0, 0.5, 0.8)},
]

_draw_handlers = {}


# ============ 面板宽度检测 ============

def get_sidebar_width(area, space):
    """获取右侧 N 面板宽度"""
    if not hasattr(space, "show_region_ui") or not space.show_region_ui:
        return 0
    for region in area.regions:
        if region.type == "UI":
            return region.width
    return 0


def get_left_toolbar_width(area, space):
    """获取左侧 T 面板宽度"""
    if not hasattr(space, "show_region_toolbar") or not space.show_region_toolbar:
        return 0
    for region in area.regions:
        if region.type == "TOOLS":
            return region.width
    return 0


def get_bottom_toolbar_height(area):
    """获取底部工具栏高度"""
    height = 0
    for region in area.regions:
        if region.type in ("ASSET_SHELF", "FOOTER") and region.height > 0:
            height = max(height, region.height)
    return height


def get_effective_bounds(area, space, region):
    """获取有效视口边界（扣除面板后）"""
    left = get_left_toolbar_width(area, space)
    right = region.width - get_sidebar_width(area, space)
    bottom = get_bottom_toolbar_height(area) + 20  # 额外安全距离
    top = region.height - 40  # 顶部安全距离

    return {"left": left, "right": right, "bottom": bottom, "top": top}


# ============ HUD 功能 ============

def show_tip(highlight_type="default"):
    """显示 HUD 提示"""
    _HUD_TIP_STATE["active"] = True
    _HUD_TIP_STATE["highlight_type"] = highlight_type
    _HUD_TIP_STATE["start_time"] = time.time()

    ensure_draw_handlers()
    tag_redraw_all()


def tag_redraw_all():
    """刷新所有相关区域"""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in ('VIEW_3D', 'IMAGE_EDITOR'):
                    area.tag_redraw()
    except:
        pass


def ensure_draw_handlers():
    """确保绘制处理器已注册"""
    global _draw_handlers

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            space = area.spaces.active
            if space is None:
                continue

            area_key = f"{area.type}_{id(area)}"

            if area_key in _draw_handlers:
                continue

            if area.type not in ('VIEW_3D', 'IMAGE_EDITOR'):
                continue

            try:
                for region in area.regions:
                    if region.type == 'WINDOW':
                        if hasattr(space, 'draw_handler_add'):
                            handler = space.draw_handler_add(
                                _draw_callback,
                                (area, space),
                                'WINDOW',
                                'POST_PIXEL'
                            )
                            _draw_handlers[area_key] = (handler, space)
                        break
            except Exception as e:
                print(f"[Smart Select HUD] 注册失败: {e}")


def remove_draw_handlers():
    """移除所有绘制处理器"""
    global _draw_handlers
    for area_key, (handler, space) in _draw_handlers.items():
        try:
            if hasattr(space, 'draw_handler_remove'):
                space.draw_handler_remove(handler, 'WINDOW')
        except:
            pass
    _draw_handlers.clear()


def _draw_callback(area, space):
    """绘制 HUD 提示"""
    if not _HUD_TIP_STATE["active"]:
        return

    elapsed = time.time() - _HUD_TIP_STATE["start_time"]
    if elapsed > _HUD_TIP_STATE["duration"]:
        _HUD_TIP_STATE["active"] = False
        return

    alpha = 1.0
    if elapsed > _HUD_TIP_STATE["fade_start"]:
        fade_progress = (elapsed - _HUD_TIP_STATE["fade_start"]) / (_HUD_TIP_STATE["duration"] - _HUD_TIP_STATE["fade_start"])
        alpha = max(0, 1.0 - fade_progress)

    try:
        region = None
        for r in area.regions:
            if r.type == 'WINDOW':
                region = r
                break

        if region:
            bounds = get_effective_bounds(area, space, region)

            # 提示框尺寸
            tip_width = 160
            tip_height = 100  # 4行 + 标题

            # 位置：右下角，但在有效区域内
            x = bounds["right"] - tip_width - 10
            y = bounds["bottom"] + tip_height + 10

            # 如果右侧空间不够，放左边
            if x < bounds["left"] + 10:
                x = bounds["left"] + 10

            # 绘制背景
            _draw_background(x - 5, y - tip_height - 5, tip_width + 10, tip_height + 15, alpha)

            # 绘制标题
            _draw_title(x, y, alpha)

            # 绘制所有提示项
            for i, tip in enumerate(_TIPS):
                is_highlight = tip["type"] == _HUD_TIP_STATE["highlight_type"]
                _draw_tip_item(x, y - 20 - i * 22, tip, is_highlight, alpha)

    except Exception as e:
        print(f"[Smart Select HUD] 绘制失败: {e}")


def _draw_background(x, y, width, height, alpha):
    """绘制半透明背景（带 padding）"""
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float("color", (0.12, 0.12, 0.14, alpha * 0.85))

    # 内部 padding
    padding = 12

    # 绘制圆角矩形（简化为矩形）
    points = [
        (x - padding, y - padding),
        (x + width + padding, y - padding),
        (x + width + padding, y + height + padding),
        (x - padding, y + height + padding)
    ]
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": points})
    batch.draw(shader)

    # 绘制边框
    shader.uniform_float("color", (0.25, 0.25, 0.28, alpha * 0.6))
    border_points = [
        (x - padding, y - padding),
        (x + width + padding, y - padding),
        (x + width + padding, y + height + padding),
        (x - padding, y + height + padding),
    ]
    border_batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": border_points})
    border_batch.draw(shader)


def _draw_title(x, y, alpha):
    """绘制标题"""
    import blf

    font_id = 0
    blf.size(font_id, 13)
    blf.color(font_id, 0.6, 0.6, 0.65, alpha)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, "智能选择快捷键")


def _draw_tip_item(x, y, tip, is_highlight, alpha):
    """绘制单个提示项"""
    import blf

    font_id = 0
    font_size = 14 if is_highlight else 13
    blf.size(font_id, font_size)

    r, g, b = tip["color"]

    if is_highlight:
        r = min(1.0, r + 0.15)
        g = min(1.0, g + 0.15)
        b = min(1.0, b + 0.15)
        prefix = "● "
    else:
        prefix = "○ "
        r *= 0.7
        g *= 0.7
        b *= 0.7

    # 快捷键（灰色）
    blf.color(font_id, 0.5, 0.5, 0.5, alpha * 0.8)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, tip["shortcut"])

    # 标签（彩色）
    blf.color(font_id, r, g, b, alpha)
    blf.position(font_id, x + 85, y, 0)
    blf.draw(font_id, prefix + tip["label"])


def register():
    pass


def unregister():
    global _draw_handlers
    _HUD_TIP_STATE["active"] = False
    remove_draw_handlers()