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
        print("[MMY] _HEADER_LOCATIONS is None in timer")
        return None

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    print(f"[MMY] timer - addon: {addon}")
    if addon:
        print(f"[MMY] timer - addon.preferences: {addon.preferences}")

    for loc in _HEADER_LOCATIONS:
        attr = loc['attr']
        default_show = loc.get('default_show', True)

        if addon and addon.preferences:
            try:
                show = getattr(addon.preferences, attr)
                print(f"[MMY] timer - {attr} = {show} (type: {type(show)})")
            except AttributeError:
                show = None
                print(f"[MMY] timer - {attr} AttributeError")
        else:
            show = None
            print(f"[MMY] timer - no addon.preferences for {attr}")

        if show is None:
            show = default_show
            print(f"[MMY] timer - {attr} using default: {show}")

        print(f"[MMY] timer - {attr} final show: {show}")

    return None  # 定时器只执行一次


def register():
    print("[MMY] translation_toggle.register() 开始")
    # 初始化 Header 位置配置（延迟加载 bpy.types）
    global _HEADER_LOCATIONS
    _HEADER_LOCATIONS = _init_header_locations()
    print(f"[MMY] _init_header_locations 成功, _HEADER_LOCATIONS: {_HEADER_LOCATIONS}")

    # 注册操作符
    bpy.utils.register_class(MMY_OT_ToggleTranslation)
    print("[MMY] MMY_OT_ToggleTranslation 已注册")

    # 挂载 Header 按钮（先无条件挂载）
    if _HEADER_LOCATIONS:
        for loc in _HEADER_LOCATIONS:
            try:
                loc['menu'].prepend(loc['drawing_func'])
                print(f"[MMY] {loc['attr']} 按钮已挂载")
            except Exception as e:
                print(f"[MMY] {loc['attr']} 挂载失败: {e}")

    # 延迟同步按钮状态（0.1秒后执行）
    bpy.app.timers.register(_sync_buttons_delayed, first_interval=0.1)
    print("[MMY] 定时器已注册")


def unregister():
    # 移除 Header 按钮
    if _HEADER_LOCATIONS:
        for loc in _HEADER_LOCATIONS:
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