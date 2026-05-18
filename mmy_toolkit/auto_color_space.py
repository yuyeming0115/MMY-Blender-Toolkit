"""自动检测法线贴图并设置 Non-Color 颜色空间

实现方式：hook bpy.data.images.load 和 bpy.ops.node.add_image，
在图片加载时立即检查所有使用它的节点并设置 Non-Color。
"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]


def _get_keywords():
    try:
        prefs = bpy.context.preferences.addons.get("mmy_toolkit")
        if prefs and prefs.preferences:
            return [k.strip().lower() for k in prefs.preferences.normal_map_keywords if k.strip()]
    except:
        pass
    return DEFAULT_KEYWORDS


def _is_enabled():
    try:
        prefs = bpy.context.preferences.addons.get("mmy_toolkit")
        return prefs and prefs.preferences and prefs.preferences.auto_set_non_color
    except:
        return False


def _is_normal_map(image_name):
    if not image_name:
        return False
    base = os.path.splitext(image_name)[0].lower()
    for kw in _get_keywords():
        if kw and kw in base:
            return True
    return False


def _check_image_nodes(img):
    """检查所有材质中使用该图像的节点，如果是法线贴图则设置 Non-Color"""
    if not _is_normal_map(img.name):
        return
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'IMAGE_TEXTURE' and node.image == img:
                if node.color_space != 'NONE':
                    node.color_space = 'NONE'
                    print(f"[MMY] 自动设置 Non-Color: {img.name}")


_original_images_load = None
_original_add_image = None


def _wrapped_images_load(filepath, check_existing=True, load_still=False):
    """hook Images.load — 图片加载时检查"""
    img = _original_images_load(filepath, check_existing=check_existing, load_still=load_still)
    if img:
        _check_image_nodes(img)
    return img


def _wrapped_add_image(self, context, **kwargs):
    """hook node.add_image — Shift+A 或菜单添加时检查"""
    result = _original_add_image(self, context, **kwargs)
    # 立即检查当前节点编辑器中的最新节点
    try:
        space = context.space_data
        if space and space.type == 'NODE_EDITOR':
            tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
            if tree:
                for node in reversed(tree.nodes):
                    if node.type == 'IMAGE_TEXTURE' and node.image:
                        if _is_normal_map(node.image.name) and node.color_space != 'NONE':
                            node.color_space = 'NONE'
                            print(f"[MMY] 自动设置 Non-Color: {node.image.name}")
                        break
    except:
        pass
    return result


def register():
    global _original_images_load, _original_add_image

    # 方式1：hook bpy.data.images.load（覆盖拖放、文件浏览器加载等）
    if hasattr(bpy.data, 'images') and hasattr(bpy.data.images, 'load'):
        _original_images_load = bpy.data.images.load
        bpy.data.images.load = _wrapped_images_load

    # 方式2：hook bpy.ops.node.add_image（覆盖 Shift+A 和菜单）
    if hasattr(bpy.ops, 'node') and hasattr(bpy.ops.node, 'add_image'):
        _original_add_image = bpy.ops.node.add_image
        bpy.ops.node.add_image = _wrapped_add_image


def unregister():
    global _original_images_load, _original_add_image
    if _original_images_load is not None:
        bpy.data.images.load = _original_images_load
        _original_images_load = None
    if _original_add_image is not None:
        bpy.ops.node.add_image = _original_add_image
        _original_add_image = None
