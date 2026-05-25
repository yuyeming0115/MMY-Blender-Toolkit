"""项目文件快速切换 - 操作符实现"""

import bpy
import os
import subprocess
import platform
from bpy_extras.io_utils import ImportHelper


def get_blender_config_dir():
    """获取 Blender 用户配置目录"""
    # 方法1：直接从 bpy.app.binary_path 推断（portable 版本最可靠）
    blender_exe = bpy.app.binary_path
    if blender_exe:
        # portable 版本结构: C:\BlenderAPP\Blender5.1\blender.exe
        # 配置目录: C:\BlenderAPP\Blender5.1\portable\config
        blender_root = os.path.dirname(blender_exe)
        config_dir = os.path.join(blender_root, "portable", "config")
        if os.path.exists(config_dir):
            return config_dir

        # 另一种结构: blender.exe 在子目录中
        blender_root = os.path.dirname(os.path.dirname(blender_exe))
        config_dir = os.path.join(blender_root, "portable", "config")
        if os.path.exists(config_dir):
            return config_dir

    # 方法2：从 preferences.filepaths.temporary_directory 推断
    prefs = bpy.context.preferences
    if prefs and prefs.filepaths:
        temp_dir = prefs.filepaths.temporary_directory
        if temp_dir:
            # temp 目录通常在 portable/temp
            parent = os.path.dirname(temp_dir)
            config_dir = os.path.join(parent, "config")
            if os.path.exists(config_dir):
                return config_dir

    # 方法3：Windows AppData 路径（非 portable 版本）
    if platform.system() == 'Windows':
        appdata = os.environ.get('APPDATA', '')
        blender_appdata = os.path.join(appdata, "Blender Foundation", "Blender")
        if os.path.exists(blender_appdata):
            for item in sorted(os.listdir(blender_appdata), reverse=True):
                if item.startswith("5.") or item.startswith("4."):
                    config_dir = os.path.join(blender_appdata, item, "config")
                    if os.path.exists(config_dir):
                        return config_dir

    return None


def read_blender_bookmarks():
    """读取 Blender 书签文件 (bookmarks.txt)"""
    config_dir = get_blender_config_dir()
    if not config_dir:
        return [], []

    bookmarks_file = os.path.join(config_dir, "bookmarks.txt")
    if not os.path.exists(bookmarks_file):
        return [], []

    bookmarks = []  # [Bookmarks] 部分
    recent_dirs = []  # [Recent] 部分

    try:
        with open(bookmarks_file, "r", encoding="utf-8") as f:
            current_section = None
            for line in f:
                line = line.strip()
                if line == "[Bookmarks]":
                    current_section = "bookmarks"
                elif line == "[Recent]":
                    current_section = "recent"
                elif line and current_section:
                    if current_section == "bookmarks":
                        bookmarks.append(line)
                    elif current_section == "recent":
                        recent_dirs.append(line)
    except Exception:
        pass

    return bookmarks, recent_dirs


def read_blender_recent_files():
    """读取 Blender 最近文件列表 (recent-files.txt)"""
    config_dir = get_blender_config_dir()
    if not config_dir:
        return []

    recent_file = os.path.join(config_dir, "recent-files.txt")
    if not os.path.exists(recent_file):
        return []

    recent_files = []
    try:
        with open(recent_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.endswith('.blend'):
                    recent_files.append(line)
    except Exception:
        pass

    return recent_files


class MMY_OT_OpenProjectFile(bpy.types.Operator):
    """打开项目文件（自动保存当前文件）"""
    bl_idname = "mmy.open_project_file"
    bl_label = "打开项目文件"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        # 先保存当前文件（如果有路径）
        current_filepath = bpy.data.filepath
        if current_filepath:
            try:
                bpy.ops.wm.save_mainfile()
                self.report({'INFO'}, "已保存当前文件")
            except:
                self.report({'WARNING'}, "保存失败，继续打开新文件")

        # 打开目标文件
        bpy.ops.wm.open_mainfile(filepath=self.filepath)
        return {'FINISHED'}


class MMY_OT_OpenProjectDirectory(bpy.types.Operator):
    """打开项目目录（单击=File Browser，Ctrl+单击=打开最近文件）"""
    bl_idname = "mmy.open_project_directory"
    bl_label = "打开项目目录"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(default="")
    open_recent_file: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        # Ctrl+单击：打开目录下最近的文件
        if event.ctrl:
            self.open_recent_file = True
        return self.execute(context)

    def execute(self, context):
        # 如果没有指定目录，使用当前文件目录
        if not self.directory:
            filepath = bpy.data.filepath
            if not filepath:
                self.report({'WARNING'}, "请先保存文件")
                return {'CANCELLED'}
            self.directory = os.path.dirname(filepath)

        if not os.path.exists(self.directory):
            self.report({'ERROR'}, f"目录不存在: {self.directory}")
            return {'CANCELLED'}

        if self.open_recent_file:
            # Ctrl 模式：保存当前文件，打开该目录下最近的 .blend 文件
            return self._open_recent_blend(context)
        else:
            # 普通模式：在 File Browser 中切换到该目录
            return self._open_in_file_browser(context)

    def _open_in_file_browser(self, context):
        """打开 File Browser 对话框并预设目录"""
        # 方案：弹出 File Browser 对话框，预设到书签目录
        # 用户可以在里面浏览并选择文件打开

        # 确保目录路径格式正确（Windows 需要 \\ 结尾）
        dir_path = self.directory.rstrip('\\/') + '\\'

        # 使用 wm.file_browser 打开文件浏览器对话框
        try:
            # 方法：直接打开 File Browser 并设置目录
            # 需要通过 context override 来设置初始目录
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'FILE_BROWSER':
                        for space in area.spaces:
                            if space.type == 'FILE_BROWSER':
                                params = space.params
                                if params:
                                    params.directory = dir_path
                                    # 刷新显示
                                    for region in area.regions:
                                        region.tag_redraw()
                                    return {'FINISHED'}

            # 如果没有打开的 File Browser，尝试用文件操作触发
            # 使用 filepath 参数触发 File Browser 打开
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}

        except Exception as e:
            print(f"File Browser 操作失败: {e}")

        # Fallback：打开系统文件管理器
        self.report({'INFO'}, f"打开目录: {self.directory}")
        if platform.system() == 'Windows':
            subprocess.run(['explorer', self.directory])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', self.directory])
        else:
            subprocess.run(['xdg-open', self.directory])

        return {'FINISHED'}

    def _open_recent_blend(self, context):
        """保存当前文件，打开目录下最近的 .blend 文件"""
        # 获取目录及其子目录下的 .blend 文件列表
        blend_files = []
        try:
            # 先检查当前目录
            for f in os.listdir(self.directory):
                if f.endswith('.blend') and not f.startswith('.'):
                    full_path = os.path.join(self.directory, f)
                    mtime = os.path.getmtime(full_path)
                    blend_files.append((f, mtime, full_path))
        except Exception:
            self.report({'ERROR'}, "无法读取目录")
            return {'CANCELLED'}

        if not blend_files:
            # 没有找到 .blend 文件，fallback 到打开 File Browser
            self.report({'INFO'}, "目录下无 .blend 文件，打开 File Browser")
            return self._open_in_file_browser(context)

        # 按修改时间排序，获取最近的文件
        blend_files.sort(key=lambda x: x[1], reverse=True)
        target_file = blend_files[0][2]

        # 保存当前文件（如果有路径）
        current_filepath = bpy.data.filepath
        if current_filepath:
            try:
                bpy.ops.wm.save_mainfile()
                self.report({'INFO'}, "已保存当前文件")
            except:
                self.report({'WARNING'}, "保存失败，继续打开新文件")

        # 打开目标文件
        bpy.ops.wm.open_mainfile(filepath=target_file)
        self.report({'INFO'}, f"已打开: {blend_files[0][0]}")
        return {'FINISHED'}


class MMY_OT_CopyProjectPath(bpy.types.Operator):
    """复制项目路径到剪贴板"""
    bl_idname = "mmy.copy_project_path"
    bl_label = "复制路径"
    bl_options = {'REGISTER'}

    path: bpy.props.StringProperty(default="")

    def execute(self, context):
        if not self.path:
            self.path = bpy.data.filepath
        if not self.path:
            self.report({'WARNING'}, "请先保存文件")
            return {'CANCELLED'}

        context.window_manager.clipboard = self.path
        self.report({'INFO'}, "已复制路径")
        return {'FINISHED'}


class MMY_OT_BrowseBookmarkDirectory(bpy.types.Operator, ImportHelper):
    """在书签目录中浏览并打开文件"""
    bl_idname = "mmy.browse_bookmark_directory"
    bl_label = "浏览书签目录"
    bl_options = {'REGISTER'}

    # 隐藏扩展名筛选
    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(
        default="*.blend",
        options={'HIDDEN'},
        maxlen=255,
    )

    # 预设目录
    directory: bpy.props.StringProperty(
        default="",
        subtype='DIR_PATH',
    )

    def invoke(self, context, event):
        # ImportHelper 会自动打开 File Browser
        # 我们通过设置 filepath 属性来预设目录
        if self.directory and os.path.exists(self.directory):
            # 设置初始文件路径为目录（这样 File Browser 会从该目录开始）
            self.filepath = self.directory
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        filepath = self.filepath

        if not filepath.endswith('.blend'):
            self.report({'WARNING'}, "请选择 .blend 文件")
            return {'CANCELLED'}

        # 保存当前文件（如果有路径）
        current_filepath = bpy.data.filepath
        if current_filepath:
            try:
                bpy.ops.wm.save_mainfile()
                self.report({'INFO'}, "已保存当前文件")
            except:
                self.report({'WARNING'}, "保存失败，继续打开新文件")

        # 打开选择的文件
        bpy.ops.wm.open_mainfile(filepath=filepath)
        self.report({'INFO'}, f"已打开: {os.path.basename(filepath)}")
        return {'FINISHED'}


class MMY_MT_BlenderBookmarks(bpy.types.Menu):
    """Blender 书签菜单"""
    bl_idname = "MMY_MT_blender_bookmarks"
    bl_label = "书签"

    def draw(self, context):
        layout = self.layout
        bookmarks, recent_dirs = read_blender_bookmarks()

        # [Bookmarks] 部分
        if bookmarks:
            layout.label(text="收藏目录", icon='BOOKMARKS')
            for path in bookmarks[:15]:  # 限制显示数量
                display_name = os.path.basename(path) or path
                # 点击后弹出 File Browser 对话框，预设到该目录
                op = layout.operator("mmy.browse_bookmark_directory", text=display_name, icon='FILE_FOLDER')
                op.directory = path

        layout.separator()

        # [Recent] 部分（最近访问的目录）
        if recent_dirs:
            layout.label(text="最近目录", icon='RECOVER_LAST')
            for path in recent_dirs[:10]:
                display_name = os.path.basename(path) or path
                op = layout.operator("mmy.browse_bookmark_directory", text=display_name, icon='FILE_FOLDER')
                op.directory = path

        if not bookmarks and not recent_dirs:
            layout.label(text="暂无书签", icon='ERROR')
            layout.label(text="在 File Browser 中添加")


class MMY_MT_BlenderRecentFiles(bpy.types.Menu):
    """Blender 最近文件菜单"""
    bl_idname = "MMY_MT_blender_recent_files"
    bl_label = "最近文件"

    def draw(self, context):
        layout = self.layout
        recent_files = read_blender_recent_files()
        current_filepath = bpy.data.filepath

        if not recent_files:
            layout.label(text="暂无历史", icon='ERROR')
            return

        for filepath in recent_files[:20]:  # 限制显示数量
            filename = os.path.basename(filepath)
            if filepath == current_filepath:
                text = f"✓ {filename}"
            else:
                text = filename

            # 直接显示文件名作为按钮，点击打开文件
            op = layout.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
            op.filepath = filepath


class MMY_MT_ProjectFiles(bpy.types.Menu):
    """项目文件下拉菜单"""
    bl_idname = "MMY_MT_project_files"
    bl_label = "项目"

    def draw(self, context):
        layout = self.layout
        filepath = bpy.data.filepath

        # === 当前文件信息 ===
        if filepath:
            filename = os.path.basename(filepath)
            row = layout.row(align=True)
            row.label(text=f"当前: {filename}", icon='FILE_BLEND')
            op = row.operator("mmy.copy_project_path", text="", icon='COPYDOWN')
            op.path = filepath
        else:
            layout.label(text="未保存文件", icon='ERROR')

        layout.separator()

        # === 同目录文件 ===
        if filepath:
            directory = os.path.dirname(filepath)
            current_name = os.path.basename(filepath)

            # 获取.blend文件列表
            blend_files = []
            try:
                for f in os.listdir(directory):
                    if f.endswith('.blend') and not f.startswith('.'):
                        full_path = os.path.join(directory, f)
                        mtime = os.path.getmtime(full_path)
                        blend_files.append((f, mtime, full_path))
            except Exception:
                pass

            if blend_files:
                # 按修改时间排序
                blend_files.sort(key=lambda x: x[1], reverse=True)
                max_files = 8

                layout.label(text="同目录文件:", icon='FILE_BLEND')
                for i, (f, mtime, full_path) in enumerate(blend_files[:max_files]):
                    text = f"✓ {f}" if f == current_name else f
                    op = layout.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
                    op.filepath = full_path

                if len(blend_files) > max_files:
                    layout.label(text=f"... 还有 {len(blend_files) - max_files} 个")

            layout.separator()
            op = layout.operator("mmy.open_project_directory", text="打开目录", icon='FILE_FOLDER')
            op.directory = directory


_classes = (
    MMY_OT_OpenProjectFile,
    MMY_OT_OpenProjectDirectory,
    MMY_OT_CopyProjectPath,
    MMY_OT_BrowseBookmarkDirectory,
    MMY_MT_BlenderBookmarks,
    MMY_MT_BlenderRecentFiles,
    MMY_MT_ProjectFiles,
)


def register():
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _draw_project_switcher(self, context):
    """顶栏项目文件切换按钮（右侧区域）"""
    if context.region.alignment != 'RIGHT':
        return

    filepath = bpy.data.filepath
    row = self.layout.row(align=True)

    # 项目菜单按钮
    if filepath:
        row.menu("MMY_MT_project_files", text="项目", icon='FILE_FOLDER')
    else:
        row.label(text="", icon='FILE_BLEND')

    # 书签按钮（只显示图标）
    row.menu("MMY_MT_blender_bookmarks", text="", icon='BOOKMARKS')

    # 最近文件按钮（只显示图标）
    row.menu("MMY_MT_blender_recent_files", text="", icon='RECOVER_LAST')