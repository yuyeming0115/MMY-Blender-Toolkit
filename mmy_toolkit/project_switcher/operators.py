"""项目文件快速切换 - 操作符实现"""

import bpy
import os
import subprocess
import platform


class MMY_OT_OpenProjectFile(bpy.types.Operator):
    """打开项目文件"""
    bl_idname = "mmy.open_project_file"
    bl_label = "打开项目文件"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=self.filepath)
        return {'FINISHED'}


class MMY_OT_OpenProjectDirectory(bpy.types.Operator):
    """打开项目目录"""
    bl_idname = "mmy.open_project_directory"
    bl_label = "打开项目目录"
    bl_options = {'REGISTER'}

    def execute(self, context):
        filepath = bpy.data.filepath
        if not filepath:
            return {'CANCELLED'}

        directory = os.path.dirname(filepath)
        if platform.system() == 'Windows':
            subprocess.run(['explorer', directory])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', directory])
        else:
            subprocess.run(['xdg-open', directory])
        return {'FINISHED'}


class MMY_MT_ProjectFiles(bpy.types.Menu):
    """项目文件下拉菜单"""
    bl_idname = "MMY_MT_project_files"
    bl_label = "项目文件"

    def draw(self, context):
        layout = self.layout
        filepath = bpy.data.filepath

        if not filepath:
            layout.label(text="请先保存文件")
            return

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
            layout.label(text="无法读取目录")
            return

        # 按修改时间排序
        blend_files.sort(key=lambda x: x[1], reverse=True)
        max_files = 10

        for i, (f, mtime, full_path) in enumerate(blend_files[:max_files]):
            text = f"✓ {f}" if f == current_name else f
            op = layout.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
            op.filepath = full_path

        if len(blend_files) > max_files:
            layout.label(text=f"... 还有 {len(blend_files) - max_files} 个")

        layout.separator()
        layout.operator("mmy.open_project_directory", text="打开目录", icon='FILE_FOLDER')


_classes = (
    MMY_OT_OpenProjectFile,
    MMY_OT_OpenProjectDirectory,
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

    if filepath:
        row.menu("MMY_MT_project_files", text="", icon='FILE_FOLDER')
    else:
        row.label(text="", icon='FILE_BLEND')