# -*- coding: utf-8 -*-
"""FBX 导出核心逻辑"""

import bpy
import os
from . import texture_utils
from . import nla_utils


def unhide_collections(col):
    """递归取消所有集合的隐藏"""
    if col.exclude:
        return
    hidden = [item for item in col.children if not item.exclude and item.hide_viewport]
    for item in hidden:
        item.hide_viewport = False
    disabled = [item for item in col.children if not item.exclude and item.collection.hide_viewport]
    for item in disabled:
        item.collection.hide_viewport = False
    for item in col.children:
        unhide_collections(item)


def unhide_objects(context):
    """取消当前视图层所有对象的隐藏"""
    view_layer_objects = [ob for ob in bpy.data.objects if ob.name in context.view_layer.objects]
    for ob in view_layer_objects:
        if ob.hide_get():
            ob.hide_set(False)
        if ob.hide_viewport:
            ob.hide_viewport = False


def get_export_objects(context, selected_objects_only, active_collection_only):
    """获取导出对象列表"""
    view_layer_names = {ob.name for ob in context.view_layer.objects}

    if selected_objects_only:
        objects = list(context.selected_objects)
        if active_collection_only and context.view_layer.active_layer_collection:
            collection_names = {ob.name for ob in context.view_layer.active_layer_collection.collection.all_objects}
            objects = [ob for ob in objects if ob.name in collection_names]
        return objects

    if active_collection_only and context.view_layer.active_layer_collection:
        return [ob for ob in context.view_layer.active_layer_collection.collection.all_objects if ob.name in view_layer_names]

    return list(context.view_layer.objects)


def export_contains_armature_content(objects):
    """检查导出内容是否包含骨骼"""
    for ob in objects:
        if ob.type == 'ARMATURE':
            return True
        if ob.type == 'MESH' and any(mod.type == 'ARMATURE' for mod in ob.modifiers):
            return True
    return False


def apply_object_modifiers(objects, context):
    """应用修改器（排除骨骼修改器和形态键）"""
    bpy.ops.object.select_all(action='DESELECT')
    to_convert = []
    for ob in objects:
        if ob.name not in context.view_layer.objects:
            continue
        bypass_modifiers = any(mod.type == 'ARMATURE' for mod in ob.modifiers)
        has_shape_keys = False
        if ob.type == 'MESH' and ob.data.shape_keys:
            if len(ob.data.shape_keys.key_blocks) > 0:
                has_shape_keys = True

        if not bypass_modifiers and not has_shape_keys:
            try:
                ob.select_set(True)
                to_convert.append(ob)
            except RuntimeError:
                continue

    if to_convert and bpy.ops.object.convert.poll():
        try:
            bpy.ops.object.convert(target='MESH')
        except Exception as e:
            print(f"Warning: apply_object_modifiers failed: {e}")


def export_unity_fbx(context, filepath, active_collection, selected_objects, deform_bones, leaf_bones,
                     tangent_space, triangulate_faces,
                     reset_transforms, export_textures, nla_items, animation_export_mode='NLA_ONLY',
                     zero_transforms=False, batch_mode=False, global_processed_images=None):
    """Unity FBX 主导出函数"""
    if not batch_mode:
        bpy.ops.ed.undo_push(message="Prepare Unity FBX")

    selection = list(context.selected_objects)
    export_objects = get_export_objects(context, selected_objects, active_collection)

    bake_space_transform = not export_contains_armature_content(export_objects)
    target_dir = os.path.dirname(filepath)

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")

    unhide_collections(context.view_layer.layer_collection)
    unhide_objects(context)
    apply_object_modifiers(export_objects, context)

    try:
        if export_textures:
            tex_targets = export_objects
            tex_size = 0
            keep_original_names = True
            if hasattr(context.scene, 'mmy_fbx_settings'):
                resize_mode = context.scene.mmy_fbx_settings.texture_resize_mode
                tex_size = int(resize_mode) if resize_mode != '0' else 0
            for ob in tex_targets:
                if ob.type == 'MESH':
                    texture_utils.copy_and_rename_texture(ob, target_dir, target_size=tex_size,
                                                          keep_original_names=keep_original_names,
                                                          global_processed_images=global_processed_images)

        original_nla_states = nla_utils.apply_nla_selection(context, selected_objects, nla_items)

        if reset_transforms:
            targets = selection if selected_objects else context.view_layer.objects
            targets = [o for o in targets if o.type in {'MESH', 'ARMATURE', 'EMPTY', 'CURVE', 'FONT', 'SURFACE'}]
            for ob in targets:
                try:
                    ob_name = ob.name
                    if ob_name not in context.view_layer.objects:
                        continue
                except (ReferenceError, AttributeError):
                    continue
                if hasattr(ob, "hide_get") and ob.hide_get():
                    continue
                if hasattr(ob, "library") and ob.library:
                    continue

                is_armature = (ob.type == 'ARMATURE')
                has_armature_mod = any(mod.type == 'ARMATURE' for mod in ob.modifiers) if ob.type == 'MESH' else False
                if is_armature or has_armature_mod:
                    continue

                if ob.animation_data:
                    ob.animation_data_clear()
                if ob.constraints:
                    ob.constraints.clear()
                ob.lock_location = ob.lock_rotation = ob.lock_scale = (False, False, False)
                if hasattr(ob, "delta_location"):
                    ob.delta_location = (0, 0, 0)
                    ob.delta_rotation_euler = (0, 0, 0)
                    ob.delta_scale = (1, 1, 1)
                if ob.parent:
                    mat = ob.matrix_world.copy()
                    try:
                        ob.parent = None
                        ob.matrix_world = mat
                    except Exception as e:
                        print(f"Warning: unparent {ob.name} failed: {e}")
                bpy.ops.object.select_all(action='DESELECT')
                try:
                    ob.select_set(True)
                except RuntimeError:
                    continue
                context.view_layer.objects.active = ob
                if bpy.ops.object.transform_apply.poll():
                    try:
                        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                    except Exception as e:
                        print(f"Warning: transform_apply failed on {ob.name}: {e}")
                ob.location = (0.0, 0.0, 0.0)

        elif zero_transforms:
            targets = selection if selected_objects else context.view_layer.objects
            targets = [o for o in targets if o.type in {'MESH', 'ARMATURE', 'EMPTY', 'CURVE', 'FONT', 'SURFACE'}]
            for ob in targets:
                try:
                    if ob.name not in context.view_layer.objects:
                        continue
                except (ReferenceError, AttributeError):
                    continue
                if hasattr(ob, "hide_get") and ob.hide_get():
                    continue
                if hasattr(ob, "library") and ob.library:
                    continue
                ob.location = (0.0, 0.0, 0.0)
                ob.rotation_euler = (0.0, 0.0, 0.0)
                ob.scale = (1.0, 1.0, 1.0)

        context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        for ob in list(selection):
            try:
                ob.select_set(True)
            except (RuntimeError, ReferenceError, AttributeError):
                pass

        use_nla_strips = animation_export_mode in ('NLA_ONLY', 'BOTH')
        use_all_actions = animation_export_mode in ('ACTIONS_ONLY', 'BOTH')

        params = dict(
            filepath=filepath,
            apply_scale_options='FBX_SCALE_UNITS',
            object_types={'EMPTY', 'MESH', 'ARMATURE'},
            axis_forward='-Z',
            axis_up='Y',
            use_space_transform=True,
            bake_space_transform=bake_space_transform,
            use_active_collection=active_collection,
            use_selection=selected_objects,
            use_armature_deform_only=deform_bones,
            add_leaf_bones=leaf_bones,
            use_tspace=tangent_space,
            use_triangles=triangulate_faces,
            use_mesh_modifiers=False,
            bake_anim=True,
            bake_anim_use_nla_strips=use_nla_strips,
            bake_anim_use_all_actions=use_all_actions,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0
        )

        try:
            bpy.ops.export_scene.fbx(**params)
        except Exception as e:
            print(f"FBX Export Error: {e}")
            nla_utils.restore_nla_selection(context, selected_objects, locals().get("original_nla_states", {}))
            if not batch_mode:
                try:
                    bpy.ops.ed.undo_push(message="")
                    bpy.ops.ed.undo()
                except Exception:
                    pass
            return {'CANCELLED'}
        nla_utils.restore_nla_selection(context, selected_objects, original_nla_states)

    except Exception as e:
        nla_utils.restore_nla_selection(context, selected_objects, locals().get("original_nla_states", {}))
        if not batch_mode:
            try:
                bpy.ops.ed.undo_push(message="")
                bpy.ops.ed.undo()
            except Exception:
                pass
        print(f"Export Error: {e}")
        return {'CANCELLED'}

    bpy.ops.ed.undo_push(message="")
    bpy.ops.ed.undo()
    return {'FINISHED'}