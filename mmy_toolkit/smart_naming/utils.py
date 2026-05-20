"""智能命名工具函数"""

import re
import bpy


def smart_increment_name(name: str, separator: str = '_', digits: int = 2) -> str:
    """
    智能递增名称中的数字部分。

    Args:
        name: 原始名称（如 "Char_01", "集合1", "Model"）
        separator: 分隔符（'', '_', '-'）
        digits: 数字位数（1, 2, 3, 4）

    Returns:
        递增后的名称

    Examples:
        smart_increment_name("Char_01", '_', 2) → "Char_02"
        smart_increment_name("集合1", '', 1) → "集合2"
        smart_increment_name("Model", '_', 2) → "Model_01"
    """
    # 检测末尾数字
    match = re.search(r'(\d+)$', name)
    if match:
        # 有数字，递增
        num = int(match.group(1))
        prefix = name[:match.start()]
        new_num = num + 1
        # 保持原有位数或使用配置位数
        original_digits = len(match.group(1))
        format_digits = max(original_digits, digits)
        return f"{prefix}{str(new_num).zfill(format_digits)}"
    else:
        # 无数字，添加新数字后缀
        if separator:
            return f"{name}{separator}{str(1).zfill(digits)}"
        else:
            return f"{name}{str(1).zfill(digits)}"


def find_next_available_name(base_name: str, existing_names: set, separator: str = '_', digits: int = 2) -> str:
    """
    找到下一个可用的名称（避免冲突）。

    Args:
        base_name: 基础名称
        existing_names: 已存在的名称集合
        separator: 分隔符
        digits: 数字位数

    Returns:
        不冲突的新名称
    """
    # 先尝试智能递增
    candidate = smart_increment_name(base_name, separator, digits)

    # 如果候选名称已存在，继续递增直到找到可用名称
    while candidate in existing_names:
        candidate = smart_increment_name(candidate, separator, digits)

    return candidate


def extract_number_suffix(name: str) -> tuple:
    """
    提取名称中的数字后缀。

    Args:
        name: 名称字符串

    Returns:
        (前缀部分, 数字部分) 或 (原名称, None)

    Examples:
        extract_number_suffix("Char_01") → ("Char_", 1)
        extract_number_suffix("集合123") → ("集合", 123)
        extract_number_suffix("Model") → ("Model", None)
    """
    match = re.search(r'(\d+)$', name)
    if match:
        prefix = name[:match.start()]
        number = int(match.group(1))
        return (prefix, number)
    return (name, None)


def clean_blender_suffix(name: str) -> str:
    """
    去除 Blender 自动追加的 .001 .002 后缀。

    Args:
        name: 名称字符串

    Returns:
        清理后的名称
    """
    return re.sub(r'\.\d{3}$', '', name)


def get_separator_display(separator: str) -> str:
    """获取分隔符的显示文本"""
    if separator == '':
        return '无'
    elif separator == '_':
        return '下划线'
    elif separator == '-':
        return '连字符'
    return separator


def apply_prefix_suffix(name: str, prefix: str = '', suffix: str = '', num: int = None,
                         separator: str = '_', digits: int = 2) -> str:
    """
    应用前缀和后缀到名称。

    Args:
        name: 原始名称
        prefix: 前缀（如 "Model"）
        suffix: 后缀（如 "_LOD"）
        num: 序号（可选，用于批量重命名）
        separator: 数字分隔符
        digits: 数字位数

    Returns:
        新名称

    Examples:
        apply_prefix_suffix("Body", "Char", "", 1, '_', 2) → "CharBody_01"
        apply_prefix_suffix("Mesh", "", "_LOD", 3, '_', 2) → "Mesh_LOD_03"
    """
    result = name

    # 应用前缀
    if prefix:
        result = f"{prefix}{result}"

    # 应用后缀
    if suffix:
        result = f"{result}{suffix}"

    # 添加序号
    if num is not None:
        num_str = str(num).zfill(digits)
        if separator:
            result = f"{result}{separator}{num_str}"
        else:
            result = f"{result}{num_str}"

    return result


def get_all_collection_names() -> set:
    """获取所有集合名称"""
    return {coll.name for coll in bpy.data.collections}


def get_all_object_names() -> set:
    """获取所有对象名称"""
    return {obj.name for obj in bpy.data.objects}


def get_all_material_names() -> set:
    """获取所有材质名称"""
    return {mat.name for mat in bpy.data.materials}


def get_selected_collections(context) -> list:
    """
    获取大纲视图选中的集合。

    Returns:
        选中的集合列表
    """
    # 通过 outliner 获取选中集合比较复杂
    # 这里使用备用方案：查找当前场景中被选中的集合
    selected = []

    # 方法1：通过 outliner context
    if context.area and context.area.type == 'OUTLINER':
        space = context.space_data
        if space and hasattr(space, 'display_mode'):
            # 尝试获取选中项
            pass

    # 方法2：通过激活集合判断
    active_coll = context.collection
    if active_coll:
        selected.append(active_coll)

    return selected


def duplicate_collection_contents(source_coll, new_name: str, context) -> object:
    """
    复制集合内容到新集合。

    Args:
        source_coll: 源集合
        new_name: 新集合名称
        context: Blender context

    Returns:
        新创建的集合
    """
    # 创建新集合
    new_coll = bpy.data.collections.new(new_name)

    # 复制所有对象
    for obj in source_coll.objects:
        # 复制对象
        new_obj = obj.copy()
        # 复制网格数据（如果是网格对象）
        if obj.data and hasattr(obj.data, 'copy'):
            new_obj.data = obj.data.copy()
        # 链接到新集合
        new_coll.objects.link(new_obj)

    # 递归复制子集合
    for child_coll in source_coll.children:
        child_new_name = smart_increment_name(child_coll.name)
        child_new_coll = duplicate_collection_contents(child_coll, child_new_name, context)
        new_coll.children.link(child_new_coll)

    # 链接到父级（如果源集合有父级）
    parent_colls = [p for p in bpy.data.collections if source_coll in p.children]
    for parent in parent_colls:
        parent.children.link(new_coll)

    # 如果源集合在场景根集合中，也链接新集合
    if source_coll in context.scene.collection.children:
        context.scene.collection.children.link(new_coll)

    return new_coll