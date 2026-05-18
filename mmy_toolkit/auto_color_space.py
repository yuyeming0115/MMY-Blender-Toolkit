"""自动检测法线贴图并设置 Non-Color 颜色空间

实现方式：使用 depsgraph_update_post handler + bpy.data.images 变化检测，
比 timer 更可靠地触发。
"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]

# 记录已处理的图像
_processed_images = set()


def _get_keywords():
    """获取当前关键词列表"""
    try:
        prefs = bpy.context.preferences.addons.get("mmy_toolkit")
        if prefs and prefs.preferences:
            return [k.strip().lower() for k in prefs.preferences.normal_map_keywords if k.strip()]
    except:
        pass
    return DEFAULT_KEYWORDS


def _is_enabled():
    """检查功能是否启用"""
    try:
        prefs = bpy.context.preferences.addons.get("mmy_toolkit")
        if prefs and prefs.preferences:
            return prefs.preferences.auto_set_non_color
    except:
        pass
    return False


def _is_normal_map(image_name):
    """检查图像文件名是否匹配法线贴图关键词"""
    if not image_name:
        return False
    base = os.path.splitext(image_name)[0].lower()
    for kw in _get_keywords():
        if kw and kw in base:
            return True
    return False


@bpy.app.handlers.persistent
def _on_load_post(dummy):
    """文件加载后重置处理记录"""
    _processed_images.clear()


@bpy.app.handlers.persistent
def _on_depsgraph_update(dummy, depsgraph):
    """depsgraph 更新后检查新增的图像节点"""
    if not _is_enabled():
        return

    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'IMAGE_TEXTURE' or not node.image:
                continue
            img = node.image
            if img.name in _processed_images:
                continue
            if node.color_space != 'NONE' and _is_normal_map(img.name):
                node.color_space = 'NONE'
                print(f"[MMY] 自动设置 Non-Color: {img.name}")
            _processed_images.add(img.name)


def register():
    _processed_images.clear()
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    _processed_images.clear()
