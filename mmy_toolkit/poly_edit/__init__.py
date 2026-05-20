"""Poly @ Edit 模块入口

整合平滑组和选择集功能
"""

import bpy

from .smooth_groups import register as register_smooth_groups
from .smooth_groups import unregister as unregister_smooth_groups
from .selection_sets import register as register_selection_sets
from .selection_sets import unregister as unregister_selection_sets
from .ui import register as register_ui
from .ui import unregister as unregister_ui


def register():
    register_smooth_groups()
    register_selection_sets()
    register_ui()


def unregister():
    unregister_ui()
    unregister_selection_sets()
    unregister_smooth_groups()


__all__ = ['register', 'unregister']