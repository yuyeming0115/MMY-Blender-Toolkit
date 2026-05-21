# Header 按钮绘制

import bpy


def draw_modifier_toggle_button(self, context):
    """绘制修改器显示切换按钮"""
    layout = self.layout

    # 仅在有修改器时显示
    obj = context.active_object
    if not obj or not obj.modifiers:
        return

    # 检测当前状态
    all_visible = all(mod.show_viewport for mod in obj.modifiers)
    icon = 'HIDE_OFF' if all_visible else 'HIDE_ON'
    text = "全部隐藏" if all_visible else "全部显示"

    row = layout.row(align=True)
    row.operator("mmy.toggle_all_modifiers_viewport", text=text, icon=icon)


def draw_modifier_toggle_button_properties(self, context):
    """属性面板 Header 绘制"""
    draw_modifier_toggle_button(self, context)


# Header 挂载位置配置（延迟初始化）
HEADER_LOCATIONS = None


def _init_header_locations():
    """初始化 Header 位置配置（在 register 时调用）"""
    global HEADER_LOCATIONS
    HEADER_LOCATIONS = []

    # DATA_HT_header 在 Blender 5.1 中被移除，需检查是否存在
    if hasattr(bpy.types, 'DATA_HT_header'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.DATA_HT_header,
            'attr': 'modifier_data_header',
            'drawing_func': draw_modifier_toggle_button,
            'default_show': True
        })

    # PROPERTIES_HT_header 在所有版本中都可用
    HEADER_LOCATIONS.append({
        'menu': bpy.types.PROPERTIES_HT_header,
        'attr': 'modifier_properties_header',
        'drawing_func': draw_modifier_toggle_button_properties,
        'default_show': False
    })

    return HEADER_LOCATIONS


def update_visual_settings(menu, attr, drawing_func, default_show=True, unregister=False):
    """更新 Header 按钮显示"""
    if unregister:
        try:
            menu.remove(drawing_func)
        except:
            pass
        return

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if not addon or not addon.preferences:
        # preferences 未初始化时使用默认值
        if default_show:
            try:
                menu.append(drawing_func)  # 使用 append 挂载到右边
            except:
                pass
        return

    show = getattr(addon.preferences, attr, default_show)
    # 处理 None 的情况
    if show is None:
        show = default_show

    if not show:
        try:
            menu.remove(drawing_func)
        except:
            pass
    else:
        try:
            menu.remove(drawing_func)
        except:
            pass
        menu.append(drawing_func)  # 使用 append 挂载到右边


def update_modifier_buttons(self, context):
    """偏好设置变化时更新所有 Header 按钮"""
    if HEADER_LOCATIONS is None:
        return
    for loc in HEADER_LOCATIONS:
        update_visual_settings(
            loc['menu'], loc['attr'], loc['drawing_func'],
            default_show=loc.get('default_show', True)
        )