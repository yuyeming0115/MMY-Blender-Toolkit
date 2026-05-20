"""菜单挂载：将应用修改器菜单添加到 Object 菜单"""

import bpy


def _safe_enum_id(name: str) -> str:
    return 'c' + name.encode('utf-8').hex()


class MMY_MT_ApplyModifierMenu(bpy.types.Menu):
    """应用修改器(保留形态键)下拉菜单"""
    bl_idname = "MMY_MT_apply_modifier_menu"
    bl_label = "应用修改器(保留形态键)"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            layout.label(text="仅网格对象可用")
            return

        if len(obj.modifiers) == 0:
            layout.label(text="无修改器")
            return

        # 添加每个修改器的选项
        for mod in obj.modifiers:
            op = layout.operator("mmy.apply_modifier_with_shapekeys", text=mod.name)
            op.modifier_id = _safe_enum_id(mod.name)

        # 分隔线 + 全部应用
        layout.separator()
        layout.operator("mmy.apply_all_modifiers_with_shapekeys", text="全部应用")


def _append_to_object_menu(self, context):
    """将菜单挂载到 Object 主菜单"""
    layout = self.layout

    # 分隔线 + 菜单
    layout.separator()
    layout.menu("MMY_MT_apply_modifier_menu", text="应用修改器(保留形态键)", icon='SHAPEKEY_DATA')


_classes = (
    MMY_MT_ApplyModifierMenu,
)