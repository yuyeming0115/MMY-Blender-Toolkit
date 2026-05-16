import re

BLEND_EXT = ".blend"


def apply_suffix(filename: str, suffix: str) -> str:
    """给文件名追加后缀，智能去重。

    - 如果文件名已有该后缀 → 不变
    - 如果文件名有另一个后缀 → 替换
    - 否则 → 追加
    """
    base = filename
    has_blend = base.lower().endswith(BLEND_EXT)
    if has_blend:
        base = base[: -len(BLEND_EXT)]

    # 规范化 suffix 为小写用于匹配
    suffix_lower = suffix.lower()

    # 检查末尾是否已有匹配的后缀（大小写不敏感）
    if base.lower().endswith(suffix_lower):
        # 已有该后缀，直接返回原样
        pass
    else:
        # 移除末尾已有的其他后缀（如 _Mat -> _Mesh）
        other = re.sub(r"_[A-Za-z]+$", "", base)
        base = other + suffix

    return base + BLEND_EXT if has_blend else base
