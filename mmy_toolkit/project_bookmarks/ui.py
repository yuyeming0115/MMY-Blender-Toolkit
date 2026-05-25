"""项目书签 UI 组件"""

import bpy
import os


class MMY_MT_ProjectBookmarks(bpy.types.Menu):
    """项目书签菜单"""
    bl_idname = "MMY_MT_project_bookmarks"
    bl_label = "项目书签"

    def draw(self, context):
        layout = self.layout

        if not hasattr(context.scene, 'mmy_project_access'):
            layout.label(text="加载失败")
            return

        props = context.scene.mmy_project_access

        if len(props.bookmarks) == 0:
            layout.label(text="暂无书签")
            layout.operator("mmy.add_project_bookmark", text="添加当前文件", icon='ADD')
            return

        for bookmark in props.bookmarks:
            row = layout.row(align=True)
            # 打开文件
            op = row.operator("mmy.open_bookmark_file", text=bookmark.alias, icon='FILE_BLEND')
            op.filepath = bookmark.path
            # 打开文件夹
            op2 = row.operator("mmy.open_bookmark_folder", text="", icon='FILE_FOLDER')
            op2.filepath = bookmark.path
            # 移除书签
            op3 = row.operator("mmy.remove_project_bookmark", text="", icon='X')
            op3.path = bookmark.path

        layout.separator()
        layout.operator("mmy.add_project_bookmark", text="添加当前文件", icon='ADD')


class MMY_MT_RecentProjectPaths(bpy.types.Menu):
    """最近打开的项目路径菜单"""
    bl_idname = "MMY_MT_recent_project_paths"
    bl_label = "最近打开"

    def draw(self, context):
        layout = self.layout

        if not hasattr(context.scene, 'mmy_project_access'):
            layout.label(text="加载失败")
            return

        props = context.scene.mmy_project_access

        if len(props.recent_paths) == 0:
            layout.label(text="暂无历史")
            return

        current_filepath = bpy.data.filepath

        for item in props.recent_paths:
            if item.path == current_filepath:
                text = f"✓ {item.filename}"
            else:
                text = item.filename

            row = layout.row(align=True)
            op = row.operator("mmy.open_bookmark_file", text=text, icon='FILE_BLEND')
            op.filepath = item.path
            # 打开文件夹
            op2 = row.operator("mmy.open_bookmark_folder", text="", icon='FILE_FOLDER')
            op2.filepath = item.path

        layout.separator()
        layout.operator("mmy.clear_recent_project_paths", text="清空历史", icon='X')


_classes = (
    MMY_MT_ProjectBookmarks,
    MMY_MT_RecentProjectPaths,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)