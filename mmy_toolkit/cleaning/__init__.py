"""清理工具模块 - 顶栏按钮 + 弹出菜单"""

import bpy


class MMY_MT_CleaningMenu(bpy.types.Menu):
    """清理工具弹出菜单"""
    bl_idname = "MMY_MT_cleaning_menu"
    bl_label = "清理工具"

    def draw(self, context):
        layout = self.layout

        # 一键清理（全部）
        layout.operator("mmy.clean_all", text="⚡ 一键清理（全部）", icon='TRASH')
        layout.separator()

        # 各单项操作
        layout.operator("mmy.clean_missing_images", text="删除丢失图片", icon='IMAGE_DATA')
        layout.operator("mmy.clean_unused_materials", text="删除未用材质", icon='MATERIAL')
        layout.operator("mmy.clean_unused_images", text="删除未用贴图", icon='TEXTURE_DATA')
        layout.operator("mmy.clean_invalid_references", text="删除无效引用", icon='OUTLINER_COLLECTION')
        layout.operator("mmy.clean_unused_animations", text="清理动画", icon='ANIM_DATA')
        layout.operator("mmy.merge_duplicate_materials", text="合并重复材质", icon='SCRIPT')
        layout.operator("mmy.repair_purple_materials", text="一键同名替换", icon='MATERIAL_DATA')


def _draw_cleaning_button(self, context):
    """顶栏清理按钮绘制函数（右侧区域）"""
    if context.region.alignment != 'RIGHT':
        return

    layout = self.layout
    layout.menu("MMY_MT_cleaning_menu", text="", icon='BRUSH_DATA')


_classes = (
    MMY_MT_CleaningMenu,
)


def register():
    # 注册菜单类
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 注册操作符
    from .operators import register
    register()

    # 挂载到顶栏右侧
    bpy.types.TOPBAR_HT_upper_bar.prepend(_draw_cleaning_button)


def unregister():
    # 移除顶栏按钮
    try:
        bpy.types.TOPBAR_HT_upper_bar.remove(_draw_cleaning_button)
    except:
        pass

    # 注销操作符
    from .operators import unregister
    unregister()

    # 注销菜单类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass