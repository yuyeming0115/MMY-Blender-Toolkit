# 界面语言切换模块
# 一键切换 Blender 界面中/英文

import bpy

from .operators import MMY_OT_ToggleTranslation
from .ui import (
    draw_translation_button_topbar,
    draw_translation_button_header,
    update_visual_settings,
    _init_header_locations,
)

# 模块级变量，存储 Header 位置配置
_HEADER_LOCATIONS = None


def _sync_buttons_delayed():
    """延迟同步按钮状态（在 Blender 完全启动后）"""
    if _HEADER_LOCATIONS is None:
        return None

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    for loc in _HEADER_LOCATIONS:
        default_show = loc.get('default_show', True)
        update_visual_settings(
            loc['menu'], loc['attr'], loc['drawing_func'],
            default_show=default_show
        )
    return None


def register():
    global _HEADER_LOCATIONS
    _HEADER_LOCATIONS = _init_header_locations()

    bpy.utils.register_class(MMY_OT_ToggleTranslation)

    if _HEADER_LOCATIONS:
        for loc in _HEADER_LOCATIONS:
            try:
                loc['menu'].prepend(loc['drawing_func'])
            except:
                pass

    bpy.app.timers.register(_sync_buttons_delayed, first_interval=0.1)


def unregister():
    if _HEADER_LOCATIONS:
        for loc in _HEADER_LOCATIONS:
            try:
                loc['menu'].remove(loc['drawing_func'])
            except:
                pass

    try:
        bpy.app.timers.unregister(_sync_buttons_delayed)
    except:
        pass

    try:
        bpy.utils.unregister_class(MMY_OT_ToggleTranslation)
    except:
        pass