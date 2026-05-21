"""项目文件快速切换 - 操作符实现"""

import bpy
import os
import subprocess
import platform
import tempfile
import struct


# ============ 缩略图提取 ============
_thumbnail_cache = {}  # filepath -> {'icon_id': int, 'image_name': str}
_no_thumb_files = set()  # 无缩略图文件记录


def extract_blend_thumbnail(filepath):
    """从.blend文件头部提取PNG缩略图"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read(1048576)  # 1MB

            png_sig = b'\x89PNG\r\n\x1a\n'
            png_start = data.find(png_sig)

            if png_start == -1:
                return None

            iend_pos = data.find(b'IEND', png_start)
            if iend_pos == -1:
                return None

            png_data = data[png_start:iend_pos + 8]

            if len(png_data) < 100:
                return None

            return png_data

    except Exception:
        return None


def get_windows_thumbnail_via_shell(filepath):
    """通过 Windows Shell API 获取缩略图"""
    if platform.system() != 'Windows':
        return None

    import ctypes
    from ctypes import wintypes

    try:
        # 初始化 COM
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED

        # SHGetFileInfo 获取图标信息
        shell32 = ctypes.windll.shell32

        # 定义结构体
        class SHFILEINFO(ctypes.Structure):
            _fields_ = [
                ("hIcon", wintypes.HICON),
                ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80),
            ]

        SHGFI_ICON = 0x000000100
        SHGFI_LARGEICON = 0x000000000
        SHGFI_SMALLICON = 0x000000001
        SHGFI_ICONLOCATION = 0x0000002000

        # 获取文件图标（不是缩略图）
        shfi = SHFILEINFO()
        ret = shell32.SHGetFileInfoW(
            filepath,
            0,
            ctypes.byref(shfi),
            ctypes.sizeof(shfi),
            SHGFI_ICON | SHGFI_LARGEICON
        )

        if ret and shfi.hIcon:
            # 这里获得的是图标，不是缩略图
            # 需要使用更高级的 IThumbnailProvider API
            # 暂时返回 None
            return None

        return None

    except Exception:
        return None
    finally:
        try:
            ctypes.windll.ole32.CoUninitialize()
        except:
            pass


def generate_thumbnail_via_blender(filepath):
    """使用 Blender 自带的 thumbnailer 生成缩略图"""
    if platform.system() != 'Windows':
        return None

    # Blender thumbnailer 路径
    blender_exe = bpy.app.binary_path
    blender_dir = os.path.dirname(blender_exe)

    # 可能的 thumbnailer 名称
    thumbnailer_names = ['blender-thumbnailer.exe', 'blender-thumbnailer.bat']
    thumbnailer_path = None

    for name in thumbnailer_names:
        path = os.path.join(blender_dir, name)
        if os.path.exists(path):
            thumbnailer_path = path
            break

    if thumbnailer_path is None:
        return None

    # 生成临时输出路径
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"thumb_{abs(hash(filepath) % 100000)}.png")

    try:
        # 调用 thumbnailer
        subprocess.run(
            [thumbnailer_path, filepath, output_path],
            capture_output=True,
            timeout=10
        )

        if os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                return f.read()
    except Exception:
        pass

    return None


def get_thumbnail_icon_id(filepath):
    """获取缩略图icon_id"""

    if filepath in _no_thumb_files:
        return None

    if filepath in _thumbnail_cache:
        cache = _thumbnail_cache[filepath]
        if cache['image_name'] in bpy.data.images:
            return cache['icon_id']
        else:
            _thumbnail_cache.pop(filepath, None)

    # 尝试多种方式获取缩略图
    png_data = None

    # 方式1: 从文件头提取
    png_data = extract_blend_thumbnail(filepath)

    # 方式2: 使用 Blender thumbnailer
    if png_data is None:
        png_data = generate_thumbnail_via_blender(filepath)

    if png_data is None:
        _no_thumb_files.add(filepath)
        return None

    # 保存并加载
    temp_dir = tempfile.gettempdir()
    thumb_name = f"mmy_thumb_{abs(hash(filepath) % 100000)}.png"
    temp_path = os.path.join(temp_dir, thumb_name)

    try:
        with open(temp_path, 'wb') as f:
            f.write(png_data)

        if thumb_name in bpy.data.images:
            image = bpy.data.images[thumb_name]
            image.reload()
        else:
            image = bpy.data.images.load(temp_path, check_existing=True)

        if image.preview:
            icon_id = image.preview.icon_id
            _thumbnail_cache[filepath] = {
                'icon_id': icon_id,
                'image_name': image.name
            }
            return icon_id

    except Exception:
        _no_thumb_files.add(filepath)

    return None


# ============ 操作符 ============
class MMY_OT_OpenProjectFile(bpy.types.Operator):
    bl_idname = "mmy.open_project_file"
    bl_label = "打开项目文件"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=self.filepath)
        return {'FINISHED'}


class MMY_OT_OpenProjectDirectory(bpy.types.Operator):
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

        blend_files.sort(key=lambda x: x[1], reverse=True)
        max_files = 10

        for i, (f, mtime, full_path) in enumerate(blend_files[:max_files]):
            text = f"✓ {f}" if f == current_name else f
            icon_id = get_thumbnail_icon_id(full_path)

            row = layout.row(align=True)
            if icon_id:
                row.template_icon(icon_value=icon_id, scale=1.0)
                op = row.operator("mmy.open_project_file", text=text)
            else:
                op = row.operator("mmy.open_project_file", text=text, icon='FILE_BLEND')
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
    for cache in _thumbnail_cache.values():
        img_name = cache.get('image_name')
        if img_name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[img_name])

    _thumbnail_cache.clear()
    _no_thumb_files.clear()

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _draw_project_switcher(self, context):
    space = context.space_data
    if not space or space.type != 'VIEW_3D':
        return

    filepath = bpy.data.filepath
    row = self.layout.row(align=True)

    if filepath:
        filename = os.path.splitext(os.path.basename(filepath))[0]
        row.menu("MMY_MT_project_files", text=f"📂 {filename}")
    else:
        row.label(text="📂 未保存", icon='FILE_BLEND')