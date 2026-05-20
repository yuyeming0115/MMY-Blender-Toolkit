# 界面语言切换模块
# 一键切换 Blender 界面中/英文

import bpy

from .operators import MMY_OT_ToggleTranslation
from .ui import (
    draw_translation_button_topbar,
    draw_translation_button_header,
    update_visual_settings,
    HEADER_LOCATIONS,
)


def register():
    # 注册操作符
    bpy.utils.register_class(MMY_OT_ToggleTranslation)

    # 挂载 Header 按钮
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if addon and addon.preferences:
        prefs = addon.preferences
        for loc in HEADER_LOCATIONS:
            if getattr(prefs, loc['attr'], False):
                try:
                    loc['menu'].prepend(loc['drawing_func'])
                except:
                    pass


def unregister():
    # 移除 Header 按钮
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if addon and addon.preferences:
        prefs = addon.preferences
        for loc in HEADER_LOCATIONS:
            try:
                loc['menu'].remove(loc['drawing_func'])
            except:
                pass

    # 注销操作符
    try:
        bpy.utils.unregister_class(MMY_OT_ToggleTranslation)
    except:
        pass