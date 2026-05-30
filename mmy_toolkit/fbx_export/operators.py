# -*- coding: utf-8 -*-
"""FBX 导出操作符"""

import bpy
import os
import subprocess
import platform
from datetime import datetime
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import Operator

from . import export_core
from . import nla_utils
from .properties import MMYFbxNlaItem


class MMY_OT_OpenExportFolder(Operator):
    """打开导出文件夹"""
    bl_idname = "mmy.open_export_folder"
    bl_label = "打开导出文件夹"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.mmy_fbx_settings
        export_dir = bpy.path.abspath(settings.export_path)

        if not os.path.exists(export_dir):
            self.report({'WARNING'}, f"导出目录不存在: {export_dir}")
            return {'CANCELLED'}

        try:
            system = platform.system()
            if system == 'Windows':
                os.startfile(export_dir)
            elif system == 'Darwin':
                subprocess.Popen(['open', export_dir])
            else:
                subprocess.Popen(['xdg-open', export_dir])
            self.report({'INFO'}, f"已打开: {export_dir}")
        except Exception as e:
            self.report({'ERROR'}, f"无法打开文件夹: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class MMY_OT_RefreshNlaList(Operator):
    """刷新NLA轨道列表"""
    bl_idname = "mmy.refresh_nla_list"
    bl_label = "刷新NLA列表"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.mmy_fbx_settings
        nla_tracks = nla_utils.gather_export_nla_tracks(context, settings.quick_selected_only)

        previous_states = {
            (item.object_name, item.track_name): item.enabled
            for item in settings.nla_items
        }

        settings.nla_items.clear()
        for object_name, track_name, label in nla_tracks:
            entry = settings.nla_items.add()
            entry.object_name = object_name
            entry.track_name = track_name
            entry.label = label
            entry.enabled = previous_states.get((object_name, track_name), True)

        self.report({'INFO'}, f"已刷新 {len(nla_tracks)} 条NLA轨道")
        return {'FINISHED'}


class MMY_OT_QuickExportFBX(Operator):
    """快速导出静态FBX模型"""
    bl_idname = "mmy.quick_export_fbx"
    bl_label = "Export-FBX (静态模型)"
    bl_description = "快速导出静态FBX模型"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.mmy_fbx_settings

        if settings.quick_selected_only and not context.selected_objects:
            self.report({'WARNING'}, "没有选中任何物体")
            return {'CANCELLED'}

        export_dir = bpy.path.abspath(settings.export_path)
        if settings.use_date_folder:
            date_folder = datetime.now().strftime("%Y-%m-%d")
            export_dir = os.path.join(export_dir, date_folder)
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except Exception as e:
                self.report({'ERROR'}, f"无法创建导出目录: {e}")
                return {'CANCELLED'}

        # 单个FBX模式
        if settings.quick_independent_export and settings.quick_selected_only and context.selected_objects:
            blend_name = "export"
            if bpy.data.filepath:
                blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            filename = bpy.path.clean_name(blend_name) + ".fbx"
            filepath = os.path.join(export_dir, filename)

            result = export_core.export_unity_fbx(
                context=context,
                filepath=filepath,
                active_collection=False,
                selected_objects=settings.quick_selected_only,
                deform_bones=settings.deform_bones,
                leaf_bones=settings.leaf_bones,
                primary_bbone_axis=settings.primary_bbone_axis,
                secondary_bbone_axis=settings.secondary_bbone_axis,
                tangent_space=settings.tangent_space,
                triangulate_faces=settings.triangulate_faces,
                reset_transforms=settings.quick_reset_transforms,
                export_textures=settings.quick_export_textures,
                nla_items=[],
                zero_transforms=settings.quick_zero_transforms
            )
            if 'FINISHED' in result:
                self.report({'INFO'}, f"导出成功: {filename}")
            return result

        # 批量导出模式
        if settings.quick_batch_export and settings.quick_selected_only and len(context.selected_objects) > 1:
            original_selection_names = [obj.name for obj in context.selected_objects]
            original_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

            cached_settings = {
                'deform_bones': settings.deform_bones,
                'leaf_bones': settings.leaf_bones,
                'primary_bbone_axis': settings.primary_bbone_axis,
                'secondary_bbone_axis': settings.secondary_bbone_axis,
                'tangent_space': settings.tangent_space,
                'triangulate_faces': settings.triangulate_faces,
                'reset_transforms': settings.quick_reset_transforms,
                'export_textures': settings.quick_export_textures,
                'zero_transforms': settings.quick_zero_transforms,
            }
            cached_nla_items = list(settings.nla_items)

            valid_objects = []
            for obj in context.selected_objects:
                has_armature = any(mod.type == 'ARMATURE' for mod in obj.modifiers) if obj.type == 'MESH' else False
                if obj.type == 'ARMATURE' or (not has_armature and obj.parent == None):
                    valid_objects.append(obj.name)

            export_count = 0
            for obj_name in valid_objects:
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    continue
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                except RuntimeError:
                    continue
                try:
                    obj.select_set(True)
                except (RuntimeError, ReferenceError):
                    continue
                for child in obj.children:
                    try:
                        if child.name in bpy.data.objects:
                            child.select_set(True)
                    except (RuntimeError, ReferenceError):
                        pass
                try:
                    context.view_layer.objects.active = obj
                except (RuntimeError, ReferenceError):
                    continue

                filename = bpy.path.clean_name(obj.name) + ".fbx"
                filepath = os.path.join(export_dir, filename)

                result = export_core.export_unity_fbx(
                    context=context,
                    filepath=filepath,
                    active_collection=False,
                    selected_objects=True,
                    deform_bones=cached_settings['deform_bones'],
                    leaf_bones=cached_settings['leaf_bones'],
                    primary_bbone_axis=cached_settings['primary_bbone_axis'],
                    secondary_bbone_axis=cached_settings['secondary_bbone_axis'],
                    tangent_space=cached_settings['tangent_space'],
                    triangulate_faces=cached_settings['triangulate_faces'],
                    reset_transforms=cached_settings['reset_transforms'],
                    export_textures=cached_settings['export_textures'],
                    nla_items=cached_nla_items,
                    zero_transforms=cached_settings['zero_transforms'],
                    batch_mode=True
                )

                if 'FINISHED' in result:
                    export_count += 1

            bpy.ops.object.select_all(action='DESELECT')
            for obj_name in original_selection_names:
                if obj_name in bpy.data.objects:
                    try:
                        bpy.data.objects[obj_name].select_set(True)
                    except (RuntimeError, ReferenceError):
                        pass
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]

            self.report({'INFO'}, f"批量导出完成: {export_count} 个物体")
            return {'FINISHED'}

        # 单文件导出
        if context.active_object:
            filename = bpy.path.clean_name(context.active_object.name) + ".fbx"
        else:
            filename = "export.fbx"

        filepath = os.path.join(export_dir, filename)

        result = export_core.export_unity_fbx(
            context=context,
            filepath=filepath,
            active_collection=False,
            selected_objects=settings.quick_selected_only,
            deform_bones=settings.deform_bones,
            leaf_bones=settings.leaf_bones,
            primary_bbone_axis=settings.primary_bbone_axis,
            secondary_bbone_axis=settings.secondary_bbone_axis,
            tangent_space=settings.tangent_space,
            triangulate_faces=settings.triangulate_faces,
            reset_transforms=settings.quick_reset_transforms,
            export_textures=settings.quick_export_textures,
            nla_items=[],
            zero_transforms=settings.quick_zero_transforms
        )

        if 'FINISHED' in result:
            self.report({'INFO'}, f"导出成功: {filename}")

        return result


class MMY_OT_QuickExportAnimationFBX(Operator):
    """快速导出动画FBX模型"""
    bl_idname = "mmy.quick_export_animation_fbx"
    bl_label = "Export-AnimationFBX"
    bl_description = "快速导出带骨骼/动画的FBX模型"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.mmy_fbx_settings

        if settings.quick_selected_only and not context.selected_objects:
            self.report({'WARNING'}, "没有选中任何物体")
            return {'CANCELLED'}

        export_dir = bpy.path.abspath(settings.export_path)
        if settings.use_date_folder:
            date_folder = datetime.now().strftime("%Y-%m-%d")
            export_dir = os.path.join(export_dir, date_folder)
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except Exception as e:
                self.report({'ERROR'}, f"无法创建导出目录: {e}")
                return {'CANCELLED'}

        # 批量导出模式
        if settings.quick_batch_export and settings.quick_selected_only and len(context.selected_objects) > 1:
            original_selection_names = [obj.name for obj in context.selected_objects]
            original_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

            cached_settings = {
                'deform_bones': settings.deform_bones,
                'leaf_bones': settings.leaf_bones,
                'primary_bbone_axis': settings.primary_bbone_axis,
                'secondary_bbone_axis': settings.secondary_bbone_axis,
                'tangent_space': settings.tangent_space,
                'triangulate_faces': settings.triangulate_faces,
                'reset_transforms': settings.quick_reset_transforms,
                'export_textures': settings.quick_export_textures,
                'zero_transforms': settings.quick_zero_transforms,
            }
            cached_nla_items = list(settings.nla_items)

            valid_objects = []
            for obj in context.selected_objects:
                has_armature = any(mod.type == 'ARMATURE' for mod in obj.modifiers) if obj.type == 'MESH' else False
                if obj.type == 'ARMATURE' or (not has_armature and obj.parent == None):
                    valid_objects.append(obj.name)

            export_count = 0
            for obj_name in valid_objects:
                obj = bpy.data.objects.get(obj_name)
                if not obj:
                    continue
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                except RuntimeError:
                    continue
                try:
                    obj.select_set(True)
                except (RuntimeError, ReferenceError):
                    continue

                mesh_obj = None
                if obj.type == 'MESH':
                    mesh_obj = obj
                else:
                    for child in obj.children:
                        try:
                            if child.type == 'MESH' and child.name in bpy.data.objects:
                                mesh_obj = child
                                break
                        except (RuntimeError, ReferenceError):
                            pass

                for child in obj.children:
                    try:
                        if child.name in bpy.data.objects:
                            child.select_set(True)
                    except (RuntimeError, ReferenceError):
                        pass
                try:
                    context.view_layer.objects.active = obj
                except (RuntimeError, ReferenceError):
                    continue

                filename = bpy.path.clean_name(mesh_obj.name if mesh_obj else obj.name) + ".fbx"
                filepath = os.path.join(export_dir, filename)

                result = export_core.export_unity_fbx(
                    context=context,
                    filepath=filepath,
                    active_collection=False,
                    selected_objects=True,
                    deform_bones=cached_settings['deform_bones'],
                    leaf_bones=cached_settings['leaf_bones'],
                    primary_bbone_axis=cached_settings['primary_bbone_axis'],
                    secondary_bbone_axis=cached_settings['secondary_bbone_axis'],
                    tangent_space=cached_settings['tangent_space'],
                    triangulate_faces=cached_settings['triangulate_faces'],
                    reset_transforms=cached_settings['reset_transforms'],
                    export_textures=cached_settings['export_textures'],
                    nla_items=cached_nla_items,
                    zero_transforms=cached_settings['zero_transforms'],
                    batch_mode=True
                )

                if 'FINISHED' in result:
                    export_count += 1

            bpy.ops.object.select_all(action='DESELECT')
            for obj_name in original_selection_names:
                if obj_name in bpy.data.objects:
                    try:
                        bpy.data.objects[obj_name].select_set(True)
                    except (RuntimeError, ReferenceError):
                        pass
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]

            self.report({'INFO'}, f"批量导出完成: {export_count} 个物体")
            return {'FINISHED'}

        # 单文件导出
        if context.active_object:
            filename = bpy.path.clean_name(context.active_object.name) + "_anim.fbx"
        else:
            filename = "export_anim.fbx"

        filepath = os.path.join(export_dir, filename)

        result = export_core.export_unity_fbx(
            context=context,
            filepath=filepath,
            active_collection=False,
            selected_objects=settings.quick_selected_only,
            deform_bones=settings.deform_bones,
            leaf_bones=settings.leaf_bones,
            primary_bbone_axis=settings.primary_bbone_axis,
            secondary_bbone_axis=settings.secondary_bbone_axis,
            tangent_space=settings.tangent_space,
            triangulate_faces=settings.triangulate_faces,
            reset_transforms=settings.quick_reset_transforms,
            export_textures=settings.quick_export_textures,
            nla_items=[],
            zero_transforms=settings.quick_zero_transforms
        )

        if 'FINISHED' in result:
            self.report({'INFO'}, f"导出成功: {filename}")

        return result


class MMY_OT_NativeExportFBX(Operator, ExportHelper):
    """原生FBX导出"""
    bl_idname = "mmy.native_export_fbx"
    bl_label = "原生FBX"
    bl_description = "使用Blender原生FBX导出"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        if not context.selected_objects:
            self.report({'WARNING'}, "没有选中任何物体")
            return {'CANCELLED'}

        try:
            bpy.ops.export_scene.fbx(filepath=self.filepath, use_selection=True)
            self.report({'INFO'}, f"原生FBX导出成功: {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"导出失败: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


_classes = (
    MMY_OT_OpenExportFolder,
    MMY_OT_RefreshNlaList,
    MMY_OT_QuickExportFBX,
    MMY_OT_QuickExportAnimationFBX,
    MMY_OT_NativeExportFBX,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
