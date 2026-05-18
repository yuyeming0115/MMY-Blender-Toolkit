"""自动检测法线贴图并设置 Non-Color 颜色空间"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]

# 已处理图像集合（模块级缓存，避免重复检测）
_processed_images = set()


def _is_normal_map(image_name):
    """检查图像文件名是否匹配法线贴图关键词"""
    if not image_name:
        return False
    # 去掉扩展名后匹配
    base = os.path.splitext(image_name)[0].lower()
    prefs = bpy.context.preferences.addons.get("mmy_toolkit")
    if prefs and prefs.preferences:
        keywords = [k.strip().lower() for k in prefs.preferences.normal_map_keywords if k.strip()]
    else:
        keywords = DEFAULT_KEYWORDS
    for kw in keywords:
        if kw and kw in base:
            return True
    return False


def _process_image_texture_nodes():
    """遍历所有材质节点树，处理未设置的 IMAGE_TEXTURE 节点"""
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'IMAGE_TEXTURE':
                continue
            if not node.image:
                continue
            img = node.image
            if img.name in _processed_images:
                continue
            if _is_normal_map(img.name):
                if node.color_space != 'NONE':
                    node.color_space = 'NONE'
                    print(f"[MMY] 自动设置 Non-Color: {img.name}")
            _processed_images.add(img.name)


@bpy.app.handlers.persistent
def _on_depsgraph_update(dummy, context):
    """depsgraph 更新后检查是否有新的 IMAGE_TEXTURE 节点"""
    if not context:
        return
    prefs = context.preferences.addons.get("mmy_toolkit")
    if not prefs or not prefs.preferences:
        return
    if not prefs.preferences.auto_set_non_color:
        return
    try:
        _process_image_texture_nodes()
    except:
        pass


def register():
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    _processed_images.clear()
