# -*- coding: utf-8 -*-
"""FBX 导出属性定义"""

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty, CollectionProperty
from bpy.types import PropertyGroup


class MMYFbxNlaItem(PropertyGroup):
    """NLA track item for export selection"""
    object_name: StringProperty()
    track_name: StringProperty()
    label: StringProperty()
    enabled: BoolProperty(name="Export", default=True)


class MMYFbxExportSettings(PropertyGroup):
    """FBX 导出场景级设置"""
    export_path: StringProperty(
        name="导出路径",
        description="FBX文件导出目录（相对于.blend文件）",
        default="//FBX",
        subtype='DIR_PATH'
    )
    quick_selected_only: BoolProperty(
        name="仅选中物体",
        description="只导出选中的物体",
        default=True
    )
    quick_reset_transforms: BoolProperty(
        name="重置变换",
        description="导出时将旋转/缩放应用到顶点数据，位移归零",
        default=True
    )
    quick_zero_transforms: BoolProperty(
        name="归零变换（不烘焙）",
        description="导出时直接将位移/旋转/缩放数值归零",
        default=False
    )
    quick_export_textures: BoolProperty(
        name="导出贴图",
        description="导出并重命名贴图文件",
        default=True
    )
    keep_original_texture_names: BoolProperty(
        name="保持原贴图命名",
        description="保留贴图的原始文件名",
        default=True
    )
    texture_resize_mode: EnumProperty(
        name="贴图尺寸",
        description="导出时将贴图缩放到指定尺寸",
        items=[
            ('0', "原始尺寸", "保持贴图原始分辨率"),
            ('512', "512", "长边缩放到 512 像素"),
            ('1024', "1024", "长边缩放到 1024 像素"),
            ('2048', "2048", "长边缩放到 2048 像素"),
        ],
        default='0'
    )
    quick_batch_export: BoolProperty(
        name="批量导出",
        description="批量导出选中的多个物体",
        default=True
    )
    quick_independent_export: BoolProperty(
        name="单个FBX",
        description="所有选中对象合并导出为一个FBX文件",
        default=False
    )
    use_date_folder: BoolProperty(
        name="按日期建立文件夹",
        description="在导出路径下按日期创建子文件夹",
        default=False
    )
    tangent_space: BoolProperty(name="导出切线", default=False)
    triangulate_faces: BoolProperty(name="三角化面", default=False)
    deform_bones: BoolProperty(name="仅变形骨骼", default=False)
    leaf_bones: BoolProperty(name="添加叶骨", default=False)
    export_options_collapsed: BoolProperty(
        name="导出选项",
        default=True,
        options={'HIDDEN'}
    )
    nla_items: CollectionProperty(type=MMYFbxNlaItem)
    nla_active_index: IntProperty(default=0)


_classes = (MMYFbxNlaItem, MMYFbxExportSettings)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mmy_fbx_settings = bpy.props.PointerProperty(type=MMYFbxExportSettings)


def unregister():
    del bpy.types.Scene.mmy_fbx_settings
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)