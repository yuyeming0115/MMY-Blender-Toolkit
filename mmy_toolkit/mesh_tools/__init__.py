import bpy
from . import operators

_classes = (
    operators.MMY_OT_MarkUVIslandSeams,
    operators.MMY_OT_ImportFBX,
    operators.MMY_OT_BetterImportFBX,
)


def register():
    # 注册场景属性
    bpy.types.Scene.mmy_import_anim = bpy.props.BoolProperty(
        name="动画",
        description="导入FBX时是否包含动画数据",
        default=False
    )
    bpy.types.Scene.mmy_reuse_materials = bpy.props.BoolProperty(
        name="引用已有材质",
        description="导入FBX时，如果场景中已有同名材质则使用现有材质",
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
    del bpy.types.Scene.mmy_reuse_materials

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass