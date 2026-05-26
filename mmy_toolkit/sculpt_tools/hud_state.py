"""雕刻 HUD 状态管理"""

# 所有可用按钮定义（id -> {symbol, label, action_type}）
_AVAILABLE_BUTTONS = {
    "face_sets": {"symbol": "◈", "label": "面组", "action": "toggle_overlay"},
    "mask": {"symbol": "✗", "label": "遮罩", "action": "toggle_overlay"},
    "wireframe": {"symbol": "◇", "label": "线框", "action": "toggle_overlay"},
    "backface_culling": {"symbol": "◐", "label": "背面", "action": "toggle_overlay"},
    "symmetry": {"symbol": "⇆", "label": "对称", "action": "toggle_symmetry"},
    "dynamic_topology": {"symbol": "⚡", "label": "动态", "action": "toggle_dyntopo"},
}

# 默认用户按钮列表
_DEFAULT_USER_BUTTONS = ["face_sets", "mask", "wireframe"]

# HUD 常量（用于计算高度）
_HUD_BUTTON_HEIGHT = 24
_HUD_HANDLE_WIDTH = 20
_HUD_MARGIN = 10
_HUD_BUTTON_GAP = 4

# 预留的顶部安全区域（Header 高度约 30-40px，加上透明层约 100px）
_TOP_SAFE_MARGIN = 100

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
    # 用户按钮配置（存储用户选择的按钮列表）
    "user_buttons": ["face_sets", "mask", "wireframe"],
    # 手动跟踪状态（Blender API 不直接暴露）
    "dyntopo_active": False,  # 动态拓扑状态
    "symmetry_x": False,      # 对称 X 轴状态
    "symmetry_y": False,      # 对称 Y 轴状态
    "symmetry_z": False,      # 对称 Z 轴状态
}


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
    """设置全局 HUD 偏移值（动态计算边界确保 HUD 不超出屏幕）"""
    # 水平方向限制
    _HUD_STATE["global_offset_x"] = max(-0.35, min(0.35, offset_x))

    # 动态计算垂直方向限制（根据按钮数量）
    button_count = len(_HUD_STATE["user_buttons"]) + 1  # +1 for add button

    # 计算 HUD 高度（垂直布局）
    total_height = _HUD_HANDLE_WIDTH + button_count * _HUD_BUTTON_HEIGHT + (button_count - 1) * _HUD_BUTTON_GAP + 2 * _HUD_MARGIN

    # 使用更保守的估算（假设 region 高度较小）
    estimated_region_height = 600

    # 计算最小 offset_y（确保 HUD 顶部有足够安全距离）
    # 公式：确保 HUD 不会进入顶部安全区域
    min_offset_y = (_TOP_SAFE_MARGIN + total_height * 0.5 - estimated_region_height * 0.5) / estimated_region_height

    # 确保限制值合理（向上移动限制最多 -0.35）
    min_offset_y = max(-0.35, min_offset_y)

    _HUD_STATE["global_offset_y"] = max(min_offset_y, min(0.30, offset_y))


def reset_global_offset():
    """重置全局 HUD 偏移值"""
    _HUD_STATE["global_offset_x"] = 0.0
    _HUD_STATE["global_offset_y"] = 0.0


def get_user_buttons():
    """获取用户当前启用的按钮列表"""
    return _HUD_STATE["user_buttons"]


def set_user_buttons(buttons):
    """设置用户按钮列表"""
    _HUD_STATE["user_buttons"] = buttons


def add_user_button(button_id):
    """添加一个按钮到用户列表"""
    if button_id in _AVAILABLE_BUTTONS and button_id not in _HUD_STATE["user_buttons"]:
        _HUD_STATE["user_buttons"].append(button_id)


def remove_user_button(button_id):
    """从用户列表移除一个按钮"""
    if button_id in _HUD_STATE["user_buttons"]:
        _HUD_STATE["user_buttons"].remove(button_id)


def reset_user_buttons():
    """重置为默认按钮配置"""
    _HUD_STATE["user_buttons"] = list(_DEFAULT_USER_BUTTONS)


__all__ = [
    '_HUD_STATE',
    '_AVAILABLE_BUTTONS',
    '_DEFAULT_USER_BUTTONS',
    'reset_hud_runtime_state',
    'get_global_offset',
    'set_global_offset',
    'reset_global_offset',
    'get_user_buttons',
    'set_user_buttons',
    'add_user_button',
    'remove_user_button',
    'reset_user_buttons',
]