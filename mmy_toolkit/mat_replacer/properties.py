"""材质替换器属性定义"""

import bpy
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty, FloatProperty


# === 材质枚举缓存 ===
_TARGET_MAT_CACHE = []

def get_target_mat_items(self, context):
    """动态生成目标材质枚举项"""
    _TARGET_MAT_CACHE.clear()
    _TARGET_MAT_CACHE.append(("none", "不替换", ""))

    for mat in bpy.data.materials:
        if mat.library is not None:
            display = mat.name.split('@')[0] if '@' in mat.name else mat.name
            safe_id = 'c' + mat.name.encode('utf-8').hex()
            _TARGET_MAT_CACHE.append((safe_id, display, ""))

    return _TARGET_MAT_CACHE


# === 骨骼对象枚举缓存 ===
_ARMATURE_CACHE = []

def get_armature_items(self, context):
    """获取场景中的Armature类型对象列表"""
    _ARMATURE_CACHE.clear()
    _ARMATURE_CACHE.append(("none", "未选择", ""))

    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            safe_id = 'c' + obj.name.encode('utf-8').hex()
            _ARMATURE_CACHE.append((safe_id, obj.name, ""))

    return _ARMATURE_CACHE


def decode_armature_id(safe_id):
    """解码安全枚举ID，返回骨骼名"""
    if safe_id == "none":
        return None
    if safe_id.startswith('c'):
        try:
            return bytes.fromhex(safe_id[1:]).decode('utf-8')
        except:
            return safe_id
    return safe_id


def _update_scale_value(self, context):
    """当缩放值改变时，更新Scale空物体的缩放"""
    scale_obj = bpy.data.objects.get("Scale")
    if scale_obj:
        scale_obj.scale = (self.scale_value, self.scale_value, self.scale_value)


def _update_constraint_offset(self, context):
    """当偏移选项改变时，更新约束的offset设置"""
    armature_name = decode_armature_id(self.target_armature_enum)
    if not armature_name:
        return

    armature = bpy.data.objects.get(armature_name)
    if not armature:
        return

    for c in armature.constraints:
        if c.name == "MMY_Copy_Scale":
            c.use_offset = self.use_offset
            break


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

    # === 骨骼缩放控制属性 ===
    target_armature_enum: EnumProperty(
        items=get_armature_items,
        name="目标骨骼",
        description="选择要添加缩放约束的骨骼对象"
    )
    scale_value: FloatProperty(
        name="缩放值",
        default=1.0,
        min=0.01,
        max=10.0,
        soft_min=0.1,
        soft_max=5.0,
        description="Scale空物体的缩放值",
        update=_update_scale_value
    )
    use_offset: BoolProperty(
        name="偏移",
        default=True,
        description="约束叠加在原有缩放上，而不是直接覆盖",
        update=_update_constraint_offset
    )
    constraint_enabled: BoolProperty(
        name="启用",
        default=True,
        description="启用/禁用缩放约束",
        update=_update_constraint_enabled
    )


def _update_constraint_enabled(self, context):
    """当启用状态改变时，更新约束的mute设置"""
    armature_name = decode_armature_id(self.target_armature_enum)
    if not armature_name:
        return

    armature = bpy.data.objects.get(armature_name)
    if not armature:
        return

    for c in armature.constraints:
        if c.name == "MMY_Copy_Scale":
            c.mute = not self.constraint_enabled
            break


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