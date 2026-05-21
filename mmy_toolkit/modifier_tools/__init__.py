# 修改器显示切换模块
# 一键控制所有修改器的视口显示状态

import bpy

from .operators import MMY_OT_ToggleAllModifiersViewport, _classes as _op_classes
from .ui import (
    draw_modifier_toggle_button_panel,
    draw_modifier_toggle_button_header,
    update_visual_settings,
    _init_header_locations,
)

# 模块级变量，存储挂载位置配置
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
            default_show=default_show,
            use_prepend=loc.get('use_prepend', False),
            use_append=loc.get('use_append', False)
        )
    return None


def register():
    global _HEADER_LOCATIONS
    _HEADER_LOCATIONS = _init_header_locations()

    for cls in _op_classes:
        bpy.utils.register_class(cls)

    if _HEADER_LOCATIONS:
        for loc in _HEADER_LOCATIONS:
            try:
                if loc.get('use_prepend'):
                    loc['menu'].prepend(loc['drawing_func'])
                elif loc.get('use_append'):
                    loc['menu'].append(loc['drawing_func'])
                else:
                    loc['menu'].append(loc['drawing_func'])
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

    for cls in reversed(_op_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass