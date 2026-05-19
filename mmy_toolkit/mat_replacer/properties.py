"""材质替换器属性定义"""

import bpy
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty


# 目标材质枚举缓存
_TARGET_MAT_CACHE = []

def get_target_mat_items(self, context):
    """动态生成目标材质枚举项"""
    _TARGET_MAT_CACHE.clear()
    _TARGET_MAT_CACHE.append(("none", "不替换", ""))

    # 从 bpy.data.materials 获取 Link 材质
    for mat in bpy.data.materials:
        if mat.library is not None:
            display = mat.name.split('@')[0] if '@' in mat.name else mat.name
            safe_id = 'c' + mat.name.encode('utf-8').hex()
            _TARGET_MAT_CACHE.append((safe_id, display, ""))

    return _TARGET_MAT_CACHE


class MMY_MaterialMappingItem(bpy.types.PropertyGroup):
    """材质映射项：场景材质 → Link材质选择"""
    source_mat_name: StringProperty(name="场景材质", default="")

    target_mat_id: EnumProperty(
        items=get_target_mat_items,
        name="目标材质",
        description="选择要替换为的Link材质"
    )


class MMY_ExternalMaterialItem(bpy.types.PropertyGroup):
    """外部文件材质项"""
    name: StringProperty(name="材质名", default="")
    is_selected: BoolProperty(name="选中", default=True)


class MMY_LinkedMaterialItem(bpy.types.PropertyGroup):
    """已Link材质项"""
    name: StringProperty(name="材质名", default="")


class MMY_MatReplacerProps(bpy.types.PropertyGroup):
    """材质替换器属性组"""
    external_file: StringProperty(subtype="FILE_PATH", default="")

    external_materials: CollectionProperty(type=MMY_ExternalMaterialItem)
    linked_materials: CollectionProperty(type=MMY_LinkedMaterialItem)
    mappings: CollectionProperty(type=MMY_MaterialMappingItem)

    active_index: IntProperty(default=0)

    # === 动画关联属性 ===
    anim_file: StringProperty(subtype="FILE_PATH", default="", name="动画文件")
    has_ani_collection: BoolProperty(default=False, name="存在Ani集合")
    ani_collection_name: StringProperty(default="", name="Ani集合名")


_classes = (
    MMY_MaterialMappingItem,
    MMY_ExternalMaterialItem,
    MMY_LinkedMaterialItem,
    MMY_MatReplacerProps,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mmy_mat_replacer = bpy.props.PointerProperty(type=MMY_MatReplacerProps)


def unregister():
    if hasattr(bpy.types.Scene, 'mmy_mat_replacer'):
        del bpy.types.Scene.mmy_mat_replacer
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass