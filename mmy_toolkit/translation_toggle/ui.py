# Header 按钮绘制

import bpy


def draw_translation_button_topbar(self, context):
    """顶栏菜单绘制（带分隔符）"""
    layout = self.layout
    layout.operator('mmy.toggle_translation', text='', icon='FILE_FONT')
    layout.separator()


def draw_translation_button_header(self, context):
    """普通 Header 绘制（无分隔符）"""
    layout = self.layout
    layout.operator('mmy.toggle_translation', text='', icon='FILE_FONT')


# Header 挂载位置配置
HEADER_LOCATIONS = [
    {
        'menu': bpy.types.TOPBAR_HT_header,
        'attr': 'translation_topbar',
        'drawing_func': draw_translation_button_topbar
    },
    {
        'menu': bpy.types.NODE_HT_header,
        'attr': 'translation_node_header',
        'drawing_func': draw_translation_button_header
    },
    {
        'menu': bpy.types.PROPERTIES_HT_header,
        'attr': 'translation_properties_header',
        'drawing_func': draw_translation_button_header
    },
    {
        'menu': bpy.types.VIEW3D_HT_header,
        'attr': 'translation_view3d_header',
        'drawing_func': draw_translation_button_header
    },
]


def update_visual_settings(menu, attr, drawing_func, unregister=False):
    """更新 Header 按钮显示"""
    if unregister:
        try:
            menu.remove(drawing_func)
        except:
            pass
        return

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if not addon or not addon.preferences:
        return

    show = getattr(addon.preferences, attr, False)
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
        menu.prepend(drawing_func)


def update_translation_buttons(self, context):
    """偏好设置变化时更新所有 Header 按钮"""
    for loc in HEADER_LOCATIONS:
        update_visual_settings(loc['menu'], loc['attr'], loc['drawing_func'])