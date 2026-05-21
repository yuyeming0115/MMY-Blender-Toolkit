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
        if not self.filepath:
            self.report({'WARNING'}, "文件路径无效")
            return {'CANCELLED'}

        # Blender会自动处理未保存文件的确认提示
        bpy.ops.wm.open_mainfile(filepath=self.filepath)
        return {'FINISHED'}


class MMY_OT_OpenProjectDirectory(bpy.types.Operator):
    """打开项目目录（系统文件管理器）"""
    bl_idname = "mmy.open_project_directory"
    bl_label = "打开项目目录"
    bl_options = {'REGISTER'}

    def execute(self, context):
        filepath = bpy.data.filepath
        if not filepath:
            self.report({'WARNING'}, "请先保存文件")
            return {'CANCELLED'}

        directory = os.path.dirname(filepath)

        # 根据系统打开文件管理器
        if platform.system() == 'Windows':
            subprocess.run(['explorer', directory])
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', directory])
        else:  # Linux
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

        # 获取同目录下的.blend文件
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

        # 按修改时间排序（最近优先）
        blend_files.sort(key=lambda x: x[1], reverse=True)

        # 限制显示数量（最多10个）
        max_files = 10

        for i, (f, mtime, full_path) in enumerate(blend_files[:max_files]):
            if i >= max_files:
                break
            # 当前文件标记 ✓
            if f == current_name:
                text = f"✓ {f}"
            else:
                text = f
            op = layout.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
            op.filepath = full_path

        # 如果有更多文件，显示提示
        if len(blend_files) > max_files:
            layout.label(text=f"... 还有 {len(blend_files) - max_files} 个文件")

        # 分隔线
        layout.separator()

        # 打开目录
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
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _draw_project_switcher(self, context):
    """在3D视图Header绘制项目文件切换按钮"""
    space = context.space_data
    if not space or space.type != 'VIEW_3D':
        return

    filepath = bpy.data.filepath
    layout = self.layout
    row = layout.row(align=True)

    if filepath:
        # 有文件名，显示下拉菜单
        filename = os.path.splitext(os.path.basename(filepath))[0]
        row.menu("MMY_MT_project_files", text=f"📂 {filename}")
    else:
        # 未命名文件，显示禁用提示
        row.label(text="📂 未保存", icon='FILE_BLEND')