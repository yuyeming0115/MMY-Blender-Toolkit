"""雕刻 HUD 状态管理"""

# HUD 运行时状态
_HUD_STATE = {
    "enabled": False,
    "hover": None,           # (region_key, button_id) 或 None
    "dragging": False,
    "drag_start_x": 0,
    "drag_start_y": 0,
    "drag_window_id": None,  # 当前拖拽的窗口 ID
    "drag_region_key": None, # 当前拖拽的 region key
    "modal_windows": set(),  # 运行中的 modal operator 窗口 ID
    "modal_running": False,
    "timer_registered": False,
    "draw_handler": None,
    # 视窗特定的偏移值存储 (window_id -> (offset_x, offset_y))
    "window_offsets": {},
}

# 默认按钮列表
_DEFAULT_BUTTONS = ["face_sets", "mask", "wireframe", "add"]


def reset_hud_runtime_state():
    """重置 HUD 运行时状态"""
    _HUD_STATE["hover"] = None
    _HUD_STATE["dragging"] = False
    _HUD_STATE["drag_window_id"] = None
    _HUD_STATE["drag_region_key"] = None
    _HUD_STATE["modal_windows"].clear()
    _HUD_STATE["modal_running"] = False
    _HUD_STATE["timer_registered"] = False


def get_window_offset(window_id):
    """获取指定视窗的偏移值"""
    return _HUD_STATE["window_offsets"].get(window_id, (0.0, 0.0))


def set_window_offset(window_id, offset_x, offset_y):
    """设置指定视窗的偏移值"""
    _HUD_STATE["window_offsets"][window_id] = (offset_x, offset_y)


def reset_window_offset(window_id):
    """重置指定视窗的偏移值"""
    _HUD_STATE["window_offsets"][window_id] = (0.0, 0.0)


__all__ = [
    '_HUD_STATE',
    '_DEFAULT_BUTTONS',
    'reset_hud_runtime_state',
    'get_window_offset',
    'set_window_offset',
    'reset_window_offset',
]