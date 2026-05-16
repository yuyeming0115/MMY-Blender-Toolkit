import bpy
from . import operators

_classes = (
    operators.MMY_OT_MarkUVIslandSeams,
    operators.MMY_OT_ImportFBX,
)


def register():
    # 注册场景属性
    bpy.types.Scene.mmy_import_anim = bpy.props.BoolProperty(
        name="动画",
        description="导入FBX时是否包含动画数据",
        default=False
    )

    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass


def unregister():
    # 删除场景属性
    del bpy.types.Scene.mmy_import_anim

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass