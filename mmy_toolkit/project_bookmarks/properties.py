"""项目书签属性定义"""

import bpy
from bpy.props import StringProperty, CollectionProperty, IntProperty


class MMY_ProjectBookmark(bpy.types.PropertyGroup):
    """项目书签项"""
    path: StringProperty(name="路径", default="")
    alias: StringProperty(name="别名", default="")


class MMY_RecentProjectPath(bpy.types.PropertyGroup):
    """最近打开的项目路径"""
    path: StringProperty(name="路径", default="")
    filename: StringProperty(name="文件名", default="")


class MMY_ProjectQuickAccessProps(bpy.types.PropertyGroup):
    """项目快捷访问属性组"""
    bookmarks: CollectionProperty(type=MMY_ProjectBookmark, name="书签")
    recent_paths: CollectionProperty(type=MMY_RecentProjectPath, name="最近路径")
    selected_bookmark_index: IntProperty(default=0)


_classes = (
    MMY_ProjectBookmark,
    MMY_RecentProjectPath,
    MMY_ProjectQuickAccessProps,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mmy_project_access = bpy.props.PointerProperty(
        type=MMY_ProjectQuickAccessProps
    )


def unregister():
    del bpy.types.Scene.mmy_project_access

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)