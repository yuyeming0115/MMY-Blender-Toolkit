"""自动检测法线贴图并设置 Non-Color 颜色空间

实现方式：
1. 持续性 timer（每秒扫描一次）— 覆盖拖放等不走 operator 的路径
2. hook bpy.ops.node.add_image — 覆盖 Shift+A 和菜单添加
"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]

# 记录已处理的图像
_processed_images = set()


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


def _scan_all():
    """扫描所有材质节点树，返回下次执行间隔（持续运行）"""
    try:
        if not _is_enabled():
            return 1.0
    except:
        return 1.0

    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'IMAGE_TEXTURE' or not node.image:
                continue
            img_name = node.image.name
            if img_name in _processed_images:
                continue
            if _is_normal_map(img_name) and node.color_space != 'NONE':
                node.color_space = 'NONE'
                _processed_images.add(img_name)
                print(f"[MMY] 自动设置 Non-Color: {img_name}")
    return 1.0


_original_add_image = None


def _wrapped_add_image(self, context, **kwargs):
    """包装 node.add_image 操作符"""
    result = _original_add_image(self, context, **kwargs)
    # 立即扫描（不依赖 timer）
    try:
        space = context.space_data
        if space and space.type == 'NODE_EDITOR':
            tree = getattr(space, 'node_tree', None) or getattr(space, 'edit_tree', None)
            if tree:
                for node in reversed(tree.nodes):
                    if node.type == 'IMAGE_TEXTURE' and node.image:
                        img_name = node.image.name
                        if _is_normal_map(img_name) and node.color_space != 'NONE':
                            node.color_space = 'NONE'
                            _processed_images.add(img_name)
                            print(f"[MMY] 自动设置 Non-Color: {img_name}")
                        break
    except:
        pass
    return result


def register():
    global _original_add_image
    _processed_images.clear()

    # 方式1：hook 操作符
    if hasattr(bpy.ops, 'node') and hasattr(bpy.ops.node, 'add_image'):
        _original_add_image = bpy.ops.node.add_image
        bpy.ops.node.add_image = _wrapped_add_image

    # 方式2：持续性 timer（每秒扫描一次）
    bpy.app.timers.register(_scan_all, first_interval=1.0)


def unregister():
    global _original_add_image
    if _original_add_image is not None:
        bpy.ops.node.add_image = _original_add_image
        _original_add_image = None
    _processed_images.clear()
