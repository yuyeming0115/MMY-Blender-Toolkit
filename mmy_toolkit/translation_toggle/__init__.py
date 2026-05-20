# 界面语言切换模块
# 一键切换 Blender 界面中/英文

import bpy

from .operators import MMY_OT_ToggleTranslation
from .ui import (
    draw_translation_button_topbar,
    draw_translation_button_header,
    update_visual_settings,
    _init_header_locations,
    HEADER_LOCATIONS,
)


def _sync_buttons_delayed():
    """延迟同步按钮状态（在 Blender 完全启动后）"""
    if HEADER_LOCATIONS is None:
        return None

    for loc in HEADER_LOCATIONS:
        default_show = loc.get('default_show', True)
        update_visual_settings(
            loc['menu'], loc['attr'], loc['drawing_func'],
            default_show=default_show
        )
    return None  # 定时器只执行一次


def register():
    # 初始化 Header 位置配置（延迟加载 bpy.types）
    _init_header_locations()

    # 注册操作符
    bpy.utils.register_class(MMY_OT_ToggleTranslation)

    # 挂载 Header 按钮（先无条件挂载）
    if HEADER_LOCATIONS:
        for loc in HEADER_LOCATIONS:
            try:
                loc['menu'].prepend(loc['drawing_func'])
            except:
                pass

    # 延迟同步按钮状态（0.1秒后执行）
    bpy.app.timers.register(_sync_buttons_delayed, first_interval=0.1)


def unregister():
    # 移除 Header 按钮
    if HEADER_LOCATIONS:
        for loc in HEADER_LOCATIONS:
            try:
                loc['menu'].remove(loc['drawing_func'])
            except:
                pass

    # 取消定时器
    try:
        bpy.app.timers.unregister(_sync_buttons_delayed)
    except:
        pass

    # 注销操作符
    try:
        bpy.utils.unregister_class(MMY_OT_ToggleTranslation)
    except:
        pass