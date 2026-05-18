"""自动检测法线贴图并设置 Non-Color 颜色空间

实现方式：
1. override bpy.ops.node.add_image — 拖放/Shift+A 添加图片时立即设置
2. 定期 timer 扫描作为兜底
"""

import bpy
import os

# 默认关键词列表
DEFAULT_KEYWORDS = ["normal", "nrm", "normalmap", "nmap", "bump"]

# 记录已处理的图像名 -> color_space，避免重复打印
_done = {}


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
    """扫描所有材质节点树"""
    print("[MMY] _scan_all 被调用了")
    if not _is_enabled():
        print("[MMY] 功能未启用")
        return None
    print(f"[MMY] 共检查 {len(bpy.data.materials)} 个材质")
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != 'IMAGE_TEXTURE' or not node.image:
                continue
            img_name = node.image.name
            if node.color_space == 'NONE':
                if img_name not in _done or _done[img_name] != 'NONE':
                    _done[img_name] = 'NONE'
                continue
            print(f"[MMY] 检查节点: {img_name} color_space={node.color_space}")
            if _is_normal_map(img_name):
                node.color_space = 'NONE'
                _done[img_name] = 'NONE'
                print(f"[MMY] 自动设置 Non-Color: {img_name}")
    return None


_original_add_image = None
_original_invoke = None


def _wrapped_add_image(self, context, **kwargs):
    """包装 node.add_image 操作符"""
    print("[MMY] _wrapped_add_image 被调用")
    result = _original_add_image(self, context, **kwargs)
    bpy.app.timers.register(_scan_all, first_interval=0.0)
    return result


def register():
    global _original_add_image
    _done.clear()
    print("[MMY] auto_color_space 注册开始")
    # 方式1：hook 操作符
    if hasattr(bpy.ops, 'node') and hasattr(bpy.ops.node, 'add_image'):
        _original_add_image = bpy.ops.node.add_image
        bpy.ops.node.add_image = _wrapped_add_image
        print("[MMY] 已 hook bpy.ops.node.add_image")
    else:
        print("[MMY] bpy.ops.node.add_image 不存在")
    # 方式2：定期 timer 扫描兜底
    bpy.app.timers.register(_scan_all, first_interval=1.0)
    print("[MMY] auto_color_space 注册完成")


def unregister():
    global _original_add_image
    if _original_add_image is not None:
        bpy.ops.node.add_image = _original_add_image
        _original_add_image = None
