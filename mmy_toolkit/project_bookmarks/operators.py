"""项目书签操作符实现"""

import bpy
import os
import subprocess
import platform


class MMY_OT_OpenProjectFolder(bpy.types.Operator):
    """打开项目文件夹"""
    bl_idname = "mmy.open_project_folder"
    bl_label = "打开项目文件夹"
    bl_options = {'REGISTER'}

    def execute(self, context):
        filepath = bpy.data.filepath
        if not filepath:
            self.report({'WARNING'}, "请先保存文件")
            return {'CANCELLED'}

        directory = os.path.dirname(filepath)
        if platform.system() == 'Windows':
            subprocess.run(['explorer', directory])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', directory])
        else:
            subprocess.run(['xdg-open', directory])

        self.report({'INFO'}, f"已打开: {directory}")
        return {'FINISHED'}


class MMY_OT_AddProjectBookmark(bpy.types.Operator):
    """添加当前路径到项目书签"""
    bl_idname = "mmy.add_project_bookmark"
    bl_label = "添加书签"
    bl_options = {'REGISTER'}

    alias: bpy.props.StringProperty(name="别名", default="")

    def execute(self, context):
        filepath = bpy.data.filepath
        if not filepath:
            self.report({'WARNING'}, "请先保存文件")
            return {'CANCELLED'}

        from ..config import add_project_bookmark

        # 使用路径目录名作为默认别名
        directory = os.path.dirname(filepath)
        display_alias = self.alias or os.path.basename(directory) or directory

        if add_project_bookmark(filepath, display_alias):
            # 同步到属性
            self._sync_bookmarks(context)
            self.report({'INFO'}, f"已添加书签: {display_alias}")
        else:
            self.report({'WARNING'}, "该路径已在书签中")

        return {'FINISHED'}

    def _sync_bookmarks(self, context):
        """同步书签到场景属性"""
        if not hasattr(context.scene, 'mmy_project_access'):
            return

        props = context.scene.mmy_project_access
        from ..config import get_project_bookmarks

        props.bookmarks.clear()
        for bookmark in get_project_bookmarks():
            item = props.bookmarks.add()
            item.path = bookmark.get("path", "")
            item.alias = bookmark.get("alias", "")


class MMY_OT_RemoveProjectBookmark(bpy.types.Operator):
    """移除项目书签"""
    bl_idname = "mmy.remove_project_bookmark"
    bl_label = "移除书签"
    bl_options = {'REGISTER'}

    path: bpy.props.StringProperty()

    def execute(self, context):
        from ..config import remove_project_bookmark
        remove_project_bookmark(self.path)

        # 同步到属性
        self._sync_bookmarks(context)
        self.report({'INFO'}, "已移除书签")
        return {'FINISHED'}

    def _sync_bookmarks(self, context):
        """同步书签到场景属性"""
        if not hasattr(context.scene, 'mmy_project_access'):
            return

        props = context.scene.mmy_project_access
        from ..config import get_project_bookmarks

        props.bookmarks.clear()
        for bookmark in get_project_bookmarks():
            item = props.bookmarks.add()
            item.path = bookmark.get("path", "")
            item.alias = bookmark.get("alias", "")


class MMY_OT_OpenBookmarkFile(bpy.types.Operator):
    """打开书签中的文件"""
    bl_idname = "mmy.open_bookmark_file"
    bl_label = "打开书签文件"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        if not self.filepath or not os.path.exists(self.filepath):
            self.report({'ERROR'}, "文件不存在")
            return {'CANCELLED'}

        # 保存当前文件（如果有修改）
        if bpy.data.filepath and bpy.data.is_dirty:
            try:
                bpy.ops.wm.save_mainfile()
            except:
                pass

        bpy.ops.wm.open_mainfile(filepath=self.filepath)
        self.report({'INFO'}, f"已打开: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class MMY_OT_OpenBookmarkFolder(bpy.types.Operator):
    """打开书签文件所在文件夹"""
    bl_idname = "mmy.open_bookmark_folder"
    bl_label = "打开书签文件夹"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        if not self.filepath:
            return {'CANCELLED'}

        directory = os.path.dirname(self.filepath)
        if platform.system() == 'Windows':
            subprocess.run(['explorer', directory])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', directory])
        else:
            subprocess.run(['xdg-open', directory])

        return {'FINISHED'}


class MMY_OT_CopyProjectPath(bpy.types.Operator):
    """复制项目路径到剪贴板"""
    bl_idname = "mmy.copy_project_path"
    bl_label = "复制路径"
    bl_options = {'REGISTER'}

    def execute(self, context):
        filepath = bpy.data.filepath
        if not filepath:
            self.report({'WARNING'}, "请先保存文件")
            return {'CANCELLED'}

        context.window_manager.clipboard = filepath
        self.report({'INFO'}, "已复制路径到剪贴板")
        return {'FINISHED'}


class MMY_OT_ClearRecentProjectPaths(bpy.types.Operator):
    """清空最近打开的项目路径"""
    bl_idname = "mmy.clear_recent_project_paths"
    bl_label = "清空历史"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..config import clear_recent_project_paths
        clear_recent_project_paths()

        # 同步到属性
        if hasattr(context.scene, 'mmy_project_access'):
            context.scene.mmy_project_access.recent_paths.clear()

        self.report({'INFO'}, "历史已清空")
        return {'FINISHED'}


_classes = (
    MMY_OT_OpenProjectFolder,
    MMY_OT_AddProjectBookmark,
    MMY_OT_RemoveProjectBookmark,
    MMY_OT_OpenBookmarkFile,
    MMY_OT_OpenBookmarkFolder,
    MMY_OT_CopyProjectPath,
    MMY_OT_ClearRecentProjectPaths,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)