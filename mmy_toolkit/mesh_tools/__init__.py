import bpy
from . import operators

_classes = (
    operators.MMY_OT_MarkUVIslandSeams,
    operators.MMY_OT_ImportFBX,
    operators.MMY_OT_BetterImportFBX,
    operators.MMY_OT_DetachSelection,
    operators.MMY_OT_DuplicateDetach,
    operators.MMY_OT_SeparateByMaterial,
    operators.MMY_OT_SeparateByLoose,
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
        default=True
    )
    bpy.types.Scene.mmy_clear_transforms = bpy.props.BoolProperty(
        name="清零变换",
        description="导入后清除模型的位移、缩放、旋转",
        default=True
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
    del bpy.types.Scene.mmy_clear_transforms

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass