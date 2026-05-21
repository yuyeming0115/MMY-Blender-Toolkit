# Header 按钮绘制

import bpy


def draw_modifier_toggle_button_panel(self, context):
    """绘制修改器显示切换按钮（Panel 内部）"""
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
    layout.separator()  # 与下方"添加修改器"分隔


def draw_modifier_toggle_button_header(self, context):
    """Header 绘制（备用位置）"""
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


# 挂载位置配置（延迟初始化）
HEADER_LOCATIONS = None


def _init_header_locations():
    """初始化挂载位置配置（在 register 时调用）"""
    global HEADER_LOCATIONS
    HEADER_LOCATIONS = []

    # 优先：DATA_PT_modifiers Panel（按钮显示在修改器列表上方）
    if hasattr(bpy.types, 'DATA_PT_modifiers'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.DATA_PT_modifiers,
            'attr': 'modifier_panel',
            'drawing_func': draw_modifier_toggle_button_panel,
            'default_show': True,
            'use_prepend': True  # Panel 使用 prepend 放在最上方
        })

    # 备用：PROPERTIES_HT_header（Header 右侧）
    if hasattr(bpy.types, 'PROPERTIES_HT_header'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.PROPERTIES_HT_header,
            'attr': 'modifier_properties_header',
            'drawing_func': draw_modifier_toggle_button_header,
            'default_show': False,
            'use_append': True  # Header 使用 append 放在右侧
        })

    return HEADER_LOCATIONS


def update_visual_settings(menu, attr, drawing_func, default_show=True, use_prepend=False, use_append=False, unregister=False):
    """更新按钮显示"""
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
                if use_prepend:
                    menu.prepend(drawing_func)
                elif use_append:
                    menu.append(drawing_func)
                else:
                    menu.append(drawing_func)
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
        if use_prepend:
            menu.prepend(drawing_func)
        elif use_append:
            menu.append(drawing_func)
        else:
            menu.append(drawing_func)


def update_modifier_buttons(self, context):
    """偏好设置变化时更新所有按钮"""
    if HEADER_LOCATIONS is None:
        return
    for loc in HEADER_LOCATIONS:
        update_visual_settings(
            loc['menu'], loc['attr'], loc['drawing_func'],
            default_show=loc.get('default_show', True),
            use_prepend=loc.get('use_prepend', False),
            use_append=loc.get('use_append', False)
        )