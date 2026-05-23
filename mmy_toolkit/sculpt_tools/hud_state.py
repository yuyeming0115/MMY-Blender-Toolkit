"""雕刻 HUD 状态管理"""

# HUD 运行时状态
_HUD_STATE = {
    "enabled": False,
    "hover": None,           # (region_key, button_id) 或 None
    "dragging": False,
    "drag_start_x": 0,
    "drag_start_y": 0,
    "drag_start_offset_x": 0,
    "drag_start_offset_y": 0,
    "modal_windows": set(),  # 运行中的 modal operator 窗口 ID
    "modal_running": False,
    "timer_registered": False,
    "draw_handler": None,
}

# 默认按钮列表
_DEFAULT_BUTTONS = ["face_sets", "mask", "wireframe", "add"]


def reset_hud_runtime_state():
    """重置 HUD 运行时状态"""
    _HUD_STATE["hover"] = None
    _HUD_STATE["dragging"] = False
    _HUD_STATE["modal_windows"].clear()
    _HUD_STATE["modal_running"] = False
    _HUD_STATE["timer_registered"] = False


__all__ = [
    '_HUD_STATE',
    '_DEFAULT_BUTTONS',
    'reset_hud_runtime_state',
]