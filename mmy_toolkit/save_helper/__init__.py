import bpy

from . import operators

classes = (operators.MMY_OT_SaveWithSuffix,)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass
    _mount_header(operators.draw_suffix_menu)


def unregister():
    _unmount_header(operators.draw_suffix_menu)
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass


def _mount_header(draw_func):
    # 挂载到目录路径面板（文件名输入框旁边）
    for name in ("FILEBROWSER_PT_directory_path",):
        try:
            cls = getattr(bpy.types, name)
            if hasattr(cls, "append"):
                cls.append(draw_func)
                return
        except (AttributeError, TypeError):
            pass
    # 备用：挂载到 header
    for name in ("FILEBROWSER_HT_header",):
        try:
            cls = getattr(bpy.types, name)
            if hasattr(cls, "prepend"):
                cls.prepend(draw_func)
                return
        except (AttributeError, TypeError):
            pass


def _unmount_header(draw_func):
    for name in ("FILEBROWSER_HT_header", "FILEBROWSER_MT_header", "FILEBROWSER_MT_header_append"):
        try:
            menu = getattr(bpy.types, name)
            if hasattr(menu, "remove"):
                menu.remove(draw_func)
        except (AttributeError, TypeError, ValueError):
            pass
