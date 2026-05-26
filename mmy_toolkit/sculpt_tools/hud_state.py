"""雕刻 HUD 状态管理"""

import bpy

# 所有可用按钮定义（id -> {symbol, label, action_type}）
_AVAILABLE_BUTTONS = {
    "face_sets": {"symbol": "◈", "label": "面组", "action": "toggle_overlay"},
    "mask": {"symbol": "✗", "label": "遮罩", "action": "toggle_overlay"},
    "wireframe": {"symbol": "◇", "label": "线框", "action": "toggle_overlay"},
    "backface_culling": {"symbol": "◐", "label": "背面", "action": "toggle_overlay"},
    "symmetry": {"symbol": "⇆", "label": "对称", "action": "toggle_symmetry"},
    "dynamic_topology": {"symbol": "⚡", "label": "动态", "action": "toggle_dyntopo"},
}

# 默认用户按钮列表（包含所有常用按钮）
_DEFAULT_USER_BUTTONS = ["face_sets", "mask", "wireframe", "backface_culling", "symmetry", "dynamic_topology"]

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
    # 用户按钮配置（存储用户选择的按钮列表）
    "user_buttons": ["face_sets", "mask", "wireframe", "backface_culling", "symmetry", "dynamic_topology"],
    # 手动跟踪状态（Blender API 不直接暴露）
    "dyntopo_active": False,  # 动态拓扑状态
    "symmetry_x": False,      # 对称 X 轴状态
    "symmetry_y": False,      # 对称 Y 轴状态
    "symmetry_z": False,      # 对称 Z 轴状态
}


# ============ Scene 属性（按文件记忆） ============

def register_scene_properties():
    """注册 Scene 属性用于按文件记忆 HUD 位置"""
    bpy.types.Scene.sculpt_hud_offset_x = bpy.props.FloatProperty(
        name="HUD 水平偏移",
        default=0.0,
        min=-0.5,
        max=0.5
    )
    bpy.types.Scene.sculpt_hud_offset_y = bpy.props.FloatProperty(
        name="HUD 垂直偏移",
        default=0.0,
        min=-1.5,
        max=1.5
    )


def unregister_scene_properties():
    """注销 Scene 属性"""
    try:
        del bpy.types.Scene.sculpt_hud_offset_x
    except:
        pass
    try:
        del bpy.types.Scene.sculpt_hud_offset_y
    except:
        pass


def reset_hud_runtime_state():
    """重置 HUD 运行时状态"""
    _HUD_STATE["hover"] = None
    _HUD_STATE["dragging"] = False
    _HUD_STATE["drag_window_id"] = None
    _HUD_STATE["drag_region_key"] = None
    _HUD_STATE["modal_windows"].clear()
    _HUD_STATE["modal_running"] = False


def get_global_offset():
    """获取 HUD 偏移值（根据偏好设置选择全局或按文件）"""
    context = bpy.context
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    if prefs and prefs.sculpt_hud_per_file_position:
        # 按文件记忆：从 Scene 属性获取
        scene = context.scene
        return scene.sculpt_hud_offset_x, scene.sculpt_hud_offset_y
    else:
        # 全局记忆：从偏好设置获取
        if prefs:
            return prefs.sculpt_hud_global_offset_x, prefs.sculpt_hud_global_offset_y
        else:
            return _HUD_STATE.get("global_offset_x", 0.0), _HUD_STATE.get("global_offset_y", 0.0)


def set_global_offset(offset_x, offset_y):
    """设置 HUD 偏移值（根据偏好设置选择全局或按文件）"""
    context = bpy.context
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    # 水平方向限制
    offset_x = max(-0.5, min(0.5, offset_x))
    # 垂直方向放宽限制
    offset_y = max(-1.0, min(1.0, offset_y))

    if prefs and prefs.sculpt_hud_per_file_position:
        # 按文件记忆：存储到 Scene 属性
        scene = context.scene
        scene.sculpt_hud_offset_x = offset_x
        scene.sculpt_hud_offset_y = offset_y
    else:
        # 全局记忆：存储到偏好设置
        if prefs:
            prefs.sculpt_hud_global_offset_x = offset_x
            prefs.sculpt_hud_global_offset_y = offset_y
        else:
            # 偏好设置不可用时，存储到内存
            _HUD_STATE["global_offset_x"] = offset_x
            _HUD_STATE["global_offset_y"] = offset_y


def reset_global_offset():
    """重置 HUD 偏移值为默认"""
    set_global_offset(0.0, 0.0)


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
    'register_scene_properties',
    'unregister_scene_properties',
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