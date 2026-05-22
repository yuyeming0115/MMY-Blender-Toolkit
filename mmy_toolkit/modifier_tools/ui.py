# 修改器面板按钮绘制

import bpy


# 存储每个修改器的显隐状态（使用对象自定义属性）
def _save_modifier_visibility(obj):
    """保存修改器显隐状态到对象属性"""
    if not obj:
        return

    # 创建状态字典
    state = {}
    for mod in obj.modifiers:
        state[mod.name] = mod.show_viewport

    # 存储到对象属性
    obj["mmy_modifier_visibility"] = str(state)


def _restore_modifier_visibility(obj):
    """从对象属性恢复修改器显隐状态"""
    if not obj or "mmy_modifier_visibility" not in obj:
        return False

    try:
        import ast
        state = ast.literal_eval(obj["mmy_modifier_visibility"])
        for mod in obj.modifiers:
            if mod.name in state:
                mod.show_viewport = state[mod.name]
        # 清除存储
        del obj["mmy_modifier_visibility"]
        return True
    except:
        return False


def _has_saved_visibility(obj):
    """检查是否有保存的显隐状态"""
    return obj and "mmy_modifier_visibility" in obj


def draw_modifier_buttons_panel(self, context):
    """绘制修改器面板工具按钮（Panel 内部）"""
    layout = self.layout
    obj = context.active_object

    # 仅对网格对象显示
    if not obj or obj.type != 'MESH':
        return

    # 仅在有修改器时显示工具行
    if not obj.modifiers:
        return

    # 工具按钮行：显隐开关 + 应用
    row = layout.row(align=True)

    # 显隐开关
    if _has_saved_visibility(obj):
        # 有保存状态 → 恢复按钮
        row.operator("mmy.restore_modifier_visibility", text="", icon='HIDE_OFF')
    else:
        # 无保存状态 → 隐藏按钮
        row.operator("mmy.hide_all_modifiers", text="", icon='HIDE_ON')

    # 应用修改器（保留形态键）
    row.operator("mmy.apply_all_modifiers_with_shapekeys", text="", icon='CHECKMARK')

    layout.separator()  # 与下方修改器列表分隔


def draw_modifier_buttons_header(self, context):
    """Header 绘制（备用位置）"""
    layout = self.layout
    obj = context.active_object

    if not obj or not obj.modifiers:
        return

    row = layout.row(align=True)
    if _has_saved_visibility(obj):
        row.operator("mmy.restore_modifier_visibility", text="", icon='HIDE_OFF')
    else:
        row.operator("mmy.hide_all_modifiers", text="", icon='HIDE_ON')


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
            'drawing_func': draw_modifier_buttons_panel,
            'default_show': True,
            'use_prepend': True
        })

    # 备用：PROPERTIES_HT_header
    if hasattr(bpy.types, 'PROPERTIES_HT_header'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.PROPERTIES_HT_header,
            'attr': 'modifier_properties_header',
            'drawing_func': draw_modifier_buttons_header,
            'default_show': False,
            'use_append': True
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