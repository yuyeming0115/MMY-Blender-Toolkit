"""GPU 绘制工具函数"""

import gpu
from gpu.types import GPUBatch, GPUVertBuf


def draw_rounded_rect(x, y, width, height, color, radius):
    """绘制圆角矩形填充（简化为矩形）"""
    if width <= 0 or height <= 0:
        return

    # Blender 5.1 可能没有 GPUExtrasGrid2D，使用简单矩形
    shader = gpu.shader.from_builtin('UNIFORM_COLOR_2D')
    shader.bind()
    shader.uniform_set("color", color)

    vertices = (
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    )

    indices = ((0, 1, 2), (0, 2, 3))

    vbo = GPUVertBuf(len(vertices), 2)
    vbo.attr_fill(0, vertices)

    ibo = GPUVertBuf(len(indices), 1)
    ibo.attr_fill(0, indices)

    batch = GPUBatch(type='TRIS', buf=vbo, elem=ibo)
    batch.draw(shader)


def draw_rounded_rect_outline(x, y, width, height, color, radius):
    """绘制圆角矩形边框（简化为矩形边框）"""
    if width <= 0 or height <= 0:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR_2D')
    shader.bind()
    shader.uniform_set("color", color)

    vertices = (
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
        (x, y),  # 闭合
    )

    vbo = GPUVertBuf(len(vertices), 2)
    vbo.attr_fill(0, vertices)

    batch = GPUBatch(type='LINE_STRIP', buf=vbo)
    batch.draw(shader)


def draw_text(text, x, y, color, size):
    """绘制文字"""
    import blf

    # 使用默认字体
    font_id = 0

    blf.position(font_id, x, y, 0)
    blf.size(font_id, size)
    blf.color(font_id, color[0], color[1], color[2], color[3])
    blf.draw(font_id, text)


def get_text_dimensions(text, size):
    """获取文字尺寸"""
    import blf

    font_id = 0
    blf.size(font_id, size)
    width = blf.dimensions(font_id, text)[0]
    height = size  # 简化处理
    return width, height


__all__ = [
    'draw_rounded_rect',
    'draw_rounded_rect_outline',
    'draw_text',
    'get_text_dimensions',
]