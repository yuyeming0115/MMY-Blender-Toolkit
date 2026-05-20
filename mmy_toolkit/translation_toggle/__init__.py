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
        print("[MMY] HEADER_LOCATIONS is None")
        return None

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    print(f"[MMY] addon: {addon}")
    if addon:
        print(f"[MMY] addon.preferences: {addon.preferences}")

    for loc in HEADER_LOCATIONS:
        attr = loc['attr']
        default_show = loc.get('default_show', True)

        if addon and addon.preferences:
            try:
                show = getattr(addon.preferences, attr)
                print(f"[MMY] {attr} = {show} (type: {type(show)})")
            except AttributeError:
                show = None
                print(f"[MMY] {attr} AttributeError")
        else:
            show = None
            print(f"[MMY] no addon.preferences for {attr}")

        if show is None:
            show = default_show
            print(f"[MMY] {attr} using default: {show}")

        print(f"[MMY] {attr} final show: {show}")

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