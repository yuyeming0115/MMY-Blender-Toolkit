"""项目书签和路径快速访问模块"""

import os
import bpy
from bpy.app.handlers import save_post, load_post

from . import properties
from . import operators
from . import ui

# Handler 函数引用（用于注销）
_handler_saved = None
_handler_loaded = None


def _on_file_change(dummy):
    """文件保存或打开时自动记录路径"""
    filepath = bpy.data.filepath
    if filepath:
        from ..config import add_recent_project_path
        add_recent_project_path(filepath)
        # 同步到场景属性
        _sync_to_props()


def _sync_to_props():
    """同步书签和最近路径到场景属性"""
    if not hasattr(bpy.context.scene, 'mmy_project_access'):
        return

    props = bpy.context.scene.mmy_project_access
    from ..config import get_project_bookmarks, get_recent_project_paths

    # 同步书签
    props.bookmarks.clear()
    for bookmark in get_project_bookmarks():
        item = props.bookmarks.add()
        item.path = bookmark.get("path", "")
        item.alias = bookmark.get("alias", "")

    # 同步最近路径
    props.recent_paths.clear()
    for filepath in get_recent_project_paths():
        item = props.recent_paths.add()
        item.path = filepath
        item.filename = os.path.basename(filepath) if filepath else ""


def register():
    properties.register()
    operators.register()
    ui.register()

    # 注册文件事件 handlers
    global _handler_saved, _handler_loaded
    _handler_saved = _on_file_change
    _handler_loaded = _on_file_change

    if _handler_saved not in save_post:
        save_post.append(_handler_saved)
    if _handler_loaded not in load_post:
        load_post.append(_handler_loaded)


def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()

    # 移除 handlers
    global _handler_saved, _handler_loaded
    if _handler_saved in save_post:
        save_post.remove(_handler_saved)
    if _handler_loaded in load_post:
        load_post.remove(_handler_loaded)

    _handler_saved = None
    _handler_loaded = None