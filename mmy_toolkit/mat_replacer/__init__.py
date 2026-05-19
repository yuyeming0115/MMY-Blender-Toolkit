"""材质关联替换模块"""

from .properties import register as register_props, unregister as unregister_props
from .operators import register as register_ops, unregister as unregister_ops


def register():
    register_props()
    register_ops()


def unregister():
    unregister_ops()
    unregister_props()