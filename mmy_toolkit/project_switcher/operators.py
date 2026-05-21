"""项目文件快速切换 - 操作符实现"""

import bpy
import os
import subprocess
import platform
import tempfile
import struct


# ============ 缩略图缓存 ============
_thumbnail_cache = {}  # filepath -> {'icon_id': int, 'image_name': str}
_temp_images = []  # 临时加载的图像列表，用于清理


def extract_blend_thumbnail(filepath):
    """从.blend文件中提取嵌入的缩略图PNG数据

    .blend文件结构：文件头部包含一个嵌入的预览图（如果启用了"Save Preview"选项）
    预览图是PNG格式，嵌入在文件开头约200字节后的位置
    """
    try:
        with open(filepath, 'rb') as f:
            # 读取前64KB足够找到缩略图
            data = f.read(65536)

            # PNG文件头标识
            png_header = b'\x89PNG\r\n\x1a\n'
            png_start = data.find(png_header)

            if png_start == -1:
                # 没有找到PNG，文件可能没有保存预览图
                return None

            # 找到PNG的结尾 (IEND chunk)
            iend_marker = b'IEND'
            iend_pos = data.find(iend_marker, png_start)
            if iend_pos == -1:
                return None

            # IEND chunk完整结束位置（包含CRC）
            png_end = iend_pos + 8  # IEND(4) + CRC(4)

            # 提取完整的PNG数据
            png_data = data[png_start:png_end]

            return png_data
    except Exception:
        return None


def get_thumbnail_icon_id(filepath):
    """获取文件缩略图的icon_id（带缓存）"""

    # 检查缓存
    if filepath in _thumbnail_cache:
        cache_entry = _thumbnail_cache[filepath]
        # 验证图像仍然存在
        if cache_entry['image_name'] in bpy.data.images:
            return cache_entry['icon_id']
        else:
            # 缓存失效，清理
            _thumbnail_cache.pop(filepath, None)

    # 提取缩略图
    png_data = extract_blend_thumbnail(filepath)

    if png_data is None:
        # 没有缩略图，返回默认图标
        return None

    # 创建临时文件
    temp_dir = tempfile.gettempdir()
    thumb_filename = f"mmy_thumb_{os.path.basename(filepath)}.png"
    temp_path = os.path.join(temp_dir, thumb_filename)

    try:
        # 写入临时PNG文件
        with open(temp_path, 'wb') as f:
            f.write(png_data)

        # 加载为Blender图像
        try:
            image = bpy.data.images.load(temp_path)
        except RuntimeError:
            # 图像可能已存在
            image = bpy.data.images.get(thumb_filename)
            if image is None:
                return None

        # 确保图像有预览
        if image.preview is None:
            # 强制生成预览
            image.reload()

        # 获取icon_id
        icon_id = image.preview.icon_id

        # 缓存
        _thumbnail_cache[filepath] = {
            'icon_id': icon_id,
            'image_name': image.name
        }
        _temp_images.append(image.name)

        return icon_id

    except Exception:
        return None


def cleanup_thumbnail_cache():
    """清理缩略图缓存和临时图像"""
    global _thumbnail_cache, _temp_images

    # 删除临时图像
    for img_name in _temp_images:
        try:
            img = bpy.data.images.get(img_name)
            if img:
                bpy.data.images.remove(img)
        except:
            pass

    _thumbnail_cache.clear()
    _temp_images.clear()


# ============ 操作符 ============
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


class MMY_OT_ClearThumbnailCache(bpy.types.Operator):
    """清理缩略图缓存"""
    bl_idname = "mmy.clear_thumbnail_cache"
    bl_label = "清理缩略图缓存"
    bl_options = {'REGISTER'}

    def execute(self, context):
        cleanup_thumbnail_cache()
        self.report({'INFO'}, "缩略图缓存已清理")
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

            # 尝试获取缩略图
            icon_id = get_thumbnail_icon_id(full_path)

            # 当前文件标记 ✓
            if f == current_name:
                text = f"✓ {f}"
            else:
                text = f

            # 使用缩略图或默认图标
            row = layout.row(align=True)
            if icon_id is not None:
                # 显示缩略图
                row.template_icon(icon_value=icon_id, scale=1.0)
                op = row.operator("mmy.open_project_file", text=text)
            else:
                # 使用默认图标
                op = row.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
            op.filepath = full_path

        # 如果有更多文件，显示提示
        if len(blend_files) > max_files:
            layout.label(text=f"... 还有 {len(blend_files) - max_files} 个文件")

        # 分隔线
        layout.separator()

        # 打开目录
        layout.operator("mmy.open_project_directory", text="打开目录", icon='FILE_FOLDER')

        # 清理缓存（可选）
        layout.separator()
        layout.operator("mmy.clear_thumbnail_cache", text="刷新缩略图", icon='FILE_REFRESH')


_classes = (
    MMY_OT_OpenProjectFile,
    MMY_OT_OpenProjectDirectory,
    MMY_OT_ClearThumbnailCache,
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
    # 清理缩略图缓存
    cleanup_thumbnail_cache()

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