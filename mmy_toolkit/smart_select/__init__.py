"""智能选择模块

提供双击智能选择功能：UV孤岛、材质、缝合边。
使用 Blender 原生 keymap 双击事件实现。
"""

import bpy
from . import operators
from . import ui

# Keymap 条目存储
_keymap_items = []


def register_keymaps():
    """注册双击快捷键"""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    # UV Editor - 双击选中孤岛
    km = kc.keymaps.new(name='UV Editor', space_type='EMPTY')
    kmi = km.keymap_items.new(
        "mmy.smart_select_uv_island",
        type='LEFTMOUSE',
        value='DOUBLE_CLICK'
    )
    _keymap_items.append((km, kmi))

    # Mesh (3D视图编辑模式) - 双击选中相连元素
    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    kmi = km.keymap_items.new(
        "mmy.smart_select_mesh_linked",
        type='LEFTMOUSE',
        value='DOUBLE_CLICK'
    )
    _keymap_items.append((km, kmi))

    # Mesh - Shift+双击选中相同材质
    kmi = km.keymap_items.new(
        "mmy.smart_select_material",
        type='LEFTMOUSE',
        value='DOUBLE_CLICK',
        shift=True
    )
    _keymap_items.append((km, kmi))

    # Mesh - Ctrl+双击选中缝合边
    kmi = km.keymap_items.new(
        "mmy.smart_select_uv_seams",
        type='LEFTMOUSE',
        value='DOUBLE_CLICK',
        ctrl=True
    )
    _keymap_items.append((km, kmi))


def unregister_keymaps():
    """注销快捷键"""
    for km, kmi in _keymap_items:
        try:
            km.keymap_items.remove(kmi)
        except:
            pass
    _keymap_items.clear()


def register():
    """注册模块"""
    operators.register()
    ui.register()
    register_keymaps()


def unregister():
    """注销模块"""
    unregister_keymaps()
    ui.unregister()
    operators.unregister()