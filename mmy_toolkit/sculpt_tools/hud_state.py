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
    "timer_active": False,   # Timer 是否激活
    "draw_handler": None,
    # 全局 HUD 偏移值（所有窗口同步）
    "global_offset_x": 0.0,
    "global_offset_y": 0.0,
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


def get_global_offset():
    """获取全局 HUD 偏移值"""
    return _HUD_STATE["global_offset_x"], _HUD_STATE["global_offset_y"]


def set_global_offset(offset_x, offset_y):
    """设置全局 HUD 偏移值"""
    _HUD_STATE["global_offset_x"] = offset_x
    _HUD_STATE["global_offset_y"] = offset_y


def reset_global_offset():
    """重置全局 HUD 偏移值"""
    _HUD_STATE["global_offset_x"] = 0.0
    _HUD_STATE["global_offset_y"] = 0.0


__all__ = [
    '_HUD_STATE',
    '_DEFAULT_BUTTONS',
    'reset_hud_runtime_state',
    'get_global_offset',
    'set_global_offset',
    'reset_global_offset',
]