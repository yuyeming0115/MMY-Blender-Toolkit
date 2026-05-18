"""自动检测法线贴图并设置 Non-Color 颜色空间

实现方式：
1. override bpy.ops.node.add_image 操作符
2. 定期 timer 扫描所有节点树作为兜底
两种方式互相补充，确保覆盖所有添加图片的方式。
"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]


def _is_normal_map(image_name):
    """检查图像文件名是否匹配法线贴图关键词"""
    if not image_name:
        return False
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


def _auto_set_color_space():
    """扫描所有材质节点树，为匹配的 IMAGE_TEXTURE 节点设置 Non-Color"""
    try:
        prefs = bpy.context.preferences.addons.get("mmy_toolkit")
        if not prefs or not prefs.preferences or not prefs.preferences.auto_set_non_color:
            return 1.0  # 未启用时每秒检查一次是否重新启用
    except:
        return 1.0

    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'IMAGE_TEXTURE' or not node.image:
                continue
            img = node.image
            if node.color_space != 'NONE' and _is_normal_map(img.name):
                node.color_space = 'NONE'
                print(f"[MMY] 自动设置 Non-Color: {img.name}")
    return 1.0  # 每秒执行一次


_original_add_image = None


def _wrapped_add_image(self, context, **kwargs):
    """包装 node.add_image 操作符，创建节点后立即设置颜色空间"""
    result = _original_add_image(self, context, **kwargs)
    # 延迟一帧执行，确保节点已完全创建
    bpy.app.timers.register(_auto_set_color_space, first_interval=0.0)
    return result


def register():
    global _original_add_image
    # 方式1：hook 操作符
    if hasattr(bpy.ops, 'node') and hasattr(bpy.ops.node, 'add_image'):
        _original_add_image = bpy.ops.node.add_image
        bpy.ops.node.add_image = _wrapped_add_image
    # 方式2：注册 timer 兜底扫描（每秒检查一次）
    bpy.app.timers.register(_auto_set_color_space, first_interval=1.0)


def unregister():
    global _original_add_image
    if _original_add_image is not None:
        bpy.ops.node.add_image = _original_add_image
        _original_add_image = None
