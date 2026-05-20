"""清理工具操作符"""

import os
import bpy
from bpy.types import Operator
from .utils import (
    clean_name,
    is_purple_material,
    reassign_material,
    reassign_image_textures,
    is_empty_collection,
    find_node_groups_to_clean,
)


# ===================================================================
# 一键清理（全部）
# ===================================================================
class MMY_OT_CleanAll(Operator):
    bl_idname = "mmy.clean_all"
    bl_label = "一键清理"
    bl_description = "执行所有清理操作"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        results = []

        # 依次执行清理操作
        try:
            bpy.ops.mmy.clean_missing_images()
            results.append("丢失图片")
        except:
            pass

        try:
            bpy.ops.mmy.clean_unused_materials()
            results.append("未用材质")
        except:
            pass

        try:
            bpy.ops.mmy.clean_unused_images()
            results.append("未用贴图")
        except:
            pass

        try:
            bpy.ops.mmy.clean_invalid_references()
            results.append("无效引用")
        except:
            pass

        try:
            bpy.ops.mmy.clean_unused_animations()
            results.append("动画")
        except:
            pass

        try:
            bpy.ops.mmy.merge_duplicate_materials()
            results.append("重复材质")
        except:
            pass

        try:
            bpy.ops.mmy.repair_purple_materials()
            results.append("紫色材质")
        except:
            pass

        if results:
            self.report({'INFO'}, f"已清理: {', '.join(results)}")
        else:
            self.report({'INFO'}, "未发现需要清理的内容")

        return {'FINISHED'}


# ===================================================================
# Operator 1: 删除路径丢失的图片
# ===================================================================
class MMY_OT_CleanMissingImages(Operator):
    bl_idname = "mmy.clean_missing_images"
    bl_label = "删除丢失图片"
    bl_description = "删除硬盘上文件已不存在的图片数据块"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        for img in list(bpy.data.images):
            if img.source != 'FILE':
                continue
            if img.packed_file:
                continue
            file_path = bpy.path.abspath(img.filepath)
            if file_path and not os.path.exists(file_path):
                try:
                    bpy.data.images.remove(img)
                    removed_count += 1
                except Exception as e:
                    print(f"[错误] 无法删除 {img.name}: {e}")
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        if removed_count > 0:
            self.report({'INFO'}, f"删除了 {removed_count} 个丢失的图片。")
        else:
            self.report({'INFO'}, "未发现路径丢失的图片。")
        return {'FINISHED'}


# ===================================================================
# Operator 2: 删除未使用的材质
# ===================================================================
class MMY_OT_CleanUnusedMaterials(Operator):
    bl_idname = "mmy.clean_unused_materials"
    bl_label = "删除未用材质"
    bl_description = "删除场景中未被任何物体使用的材质球"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        for mat in list(bpy.data.materials):
            real_users = mat.users if not mat.use_fake_user else mat.users - 1
            if real_users <= 0:
                mat.use_fake_user = False
                bpy.data.materials.remove(mat)
                removed_count += 1
        if removed_count > 0:
            self.report({'INFO'}, f"删除了 {removed_count} 个未使用的材质球。")
        else:
            self.report({'INFO'}, "没有发现未使用的材质球。")
        return {'FINISHED'}


# ===================================================================
# Operator 3: 删除未使用的贴图
# ===================================================================
class MMY_OT_CleanUnusedImages(Operator):
    bl_idname = "mmy.clean_unused_images"
    bl_label = "删除未用贴图"
    bl_description = "删除未被任何材质引用的贴图数据"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        for img in list(bpy.data.images):
            if img.name in ('Render Result', 'Viewer Node'):
                continue
            real_users = img.users if not img.use_fake_user else img.users - 1
            if real_users <= 0:
                img.use_fake_user = False
                bpy.data.images.remove(img)
                removed_count += 1
        if removed_count > 0:
            self.report({'INFO'}, f"删除了 {removed_count} 个未使用的贴图。")
        else:
            self.report({'INFO'}, "没有发现未使用的贴图。")
        return {'FINISHED'}


# ===================================================================
# Operator 4: 删除无效引用
# ===================================================================
class MMY_OT_CleanInvalidReferences(Operator):
    bl_idname = "mmy.clean_invalid_references"
    bl_label = "删除无效引用"
    bl_description = "删除空集合和无引用的节点组"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_coll = 0
        for coll in list(bpy.data.collections):
            if is_empty_collection(coll):
                links = list(coll.user_children)
                for parent in links:
                    parent.children.unlink(coll)
                if coll.users == 0:
                    bpy.data.collections.remove(coll)
                    removed_coll += 1

        removed_ng = 0
        for ng in find_node_groups_to_clean():
            bpy.data.node_groups.remove(ng)
            removed_ng += 1

        total = removed_coll + removed_ng
        if total > 0:
            msg = f"删除了 {removed_coll} 个空集合, {removed_ng} 个无效节点组。"
            self.report({'INFO'}, msg)
        else:
            self.report({'INFO'}, "未发现无效引用。")
        return {'FINISHED'}


# ===================================================================
# Operator 5: 删除无关动画资源
# ===================================================================
class MMY_OT_CleanUnusedAnimations(Operator):
    bl_idname = "mmy.clean_unused_animations"
    bl_label = "清理动画"
    bl_description = "删除未使用的 Action、空动画数据和 NLA 数据"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def is_action_empty(action) -> bool:
        """检查 Action 是否不包含任何关键帧数据"""
        fcurves = getattr(action, 'fcurves', None) or getattr(action, 'curves', None)
        if not fcurves:
            return True
        for fcurve in fcurves:
            keyframe_points = getattr(fcurve, 'keyframe_points', None) or getattr(fcurve, 'points', None)
            if keyframe_points:
                return False
        return True

    def execute(self, context):
        removed_actions = 0

        # 清理空 Action
        empty_actions = [action for action in bpy.data.actions if self.is_action_empty(action)]
        for action in empty_actions:
            for obj in bpy.data.objects:
                if obj.animation_data and obj.animation_data.action == action:
                    obj.animation_data.action = None
            action.use_fake_user = False
            try:
                bpy.data.actions.remove(action)
                removed_actions += 1
            except Exception as e:
                print(f"[清理动画] 无法删除 {action.name}: {e}")

        # 清理未使用的 Action
        for action in list(bpy.data.actions):
            real_users = action.users if not action.use_fake_user else action.users - 1
            if real_users <= 0:
                action.use_fake_user = False
                bpy.data.actions.remove(action)
                removed_actions += 1

        # 清理空 NLA 轨道
        removed_strips = 0
        for obj in bpy.data.objects:
            if obj.animation_data:
                for track in list(obj.animation_data.nla_tracks):
                    if len(track.strips) == 0:
                        obj.animation_data.nla_tracks.remove(track)
                        removed_strips += 1

        total = removed_actions + removed_strips
        if total > 0:
            msg = f"删除了 {removed_actions} 个空/未用 Action, {removed_strips} 个空 NLA 轨道。"
            self.report({'INFO'}, msg)
        else:
            self.report({'INFO'}, "没有发现需要清理的动画资源。")
        return {'FINISHED'}


# ===================================================================
# Operator 6: 合并重复的材质和贴图
# ===================================================================
class MMY_OT_MergeDuplicateMaterials(Operator):
    bl_idname = "mmy.merge_duplicate_materials"
    bl_label = "合并重复材质"
    bl_description = "合并通过复制/导入产生的 .001 等重复材质和贴图"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merged_mats = 0
        merged_imgs = 0

        # 合并重复材质
        dup_map = {}
        for mat in bpy.data.materials:
            base = clean_name(mat.name)
            if base == mat.name:
                continue
            if base not in dup_map:
                base_mat = bpy.data.materials.get(base)
                if not base_mat:
                    continue
                dup_map[base] = (base_mat, [])
            dup_map[base][1].append(mat)

        for base_name, (base_mat, dups) in dup_map.items():
            for dup_mat in dups:
                reassign_material(dup_mat, base_mat)
                merged_mats += 1

        # 合并重复贴图
        img_dup_map = {}
        for img in bpy.data.images:
            base = clean_name(img.name)
            if base == img.name:
                continue
            if base not in img_dup_map:
                base_img = bpy.data.images.get(base)
                if not base_img:
                    continue
                img_dup_map[base] = (base_img, [])
            img_dup_map[base][1].append(img)

        for base_name, (base_img, dups) in img_dup_map.items():
            for dup_img in dups:
                reassign_image_textures(dup_img, base_img)
                merged_imgs += 1

        total = merged_mats + merged_imgs
        if total > 0:
            msg = f"合并了 {merged_mats} 个材质, {merged_imgs} 个贴图。"
            self.report({'INFO'}, msg)
        else:
            self.report({'INFO'}, "未发现重复的材质或贴图。")
        return {'FINISHED'}


# ===================================================================
# Operator 7: 一键同名替换（紫色材质 → 正确材质）
# ===================================================================
class MMY_OT_RepairPurpleMaterials(Operator):
    bl_idname = "mmy.repair_purple_materials"
    bl_label = "一键同名替换"
    bl_description = "一键扫描紫色丢失材质，自动替换为同名的正确材质"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        all_mats = {mat.name: mat for mat in bpy.data.materials}
        replaced = 0

        for mat_name, mat in all_mats.items():
            if not is_purple_material(mat):
                continue
            candidate_name = clean_name(mat_name)
            if candidate_name == mat_name:
                continue
            target = all_mats.get(candidate_name)
            if not target or not target.use_nodes:
                continue
            if is_purple_material(target):
                continue

            reassign_material(mat, target)
            replaced += 1

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        if replaced > 0:
            self.report({'INFO'}, f"替换了 {replaced} 个紫色丢失材质。")
        else:
            self.report({'INFO'}, "未发现可匹配的紫色材质。")
        return {'FINISHED'}


# ===================================================================
# 注册
# ===================================================================
_classes = (
    MMY_OT_CleanAll,
    MMY_OT_CleanMissingImages,
    MMY_OT_CleanUnusedMaterials,
    MMY_OT_CleanUnusedImages,
    MMY_OT_CleanInvalidReferences,
    MMY_OT_CleanUnusedAnimations,
    MMY_OT_MergeDuplicateMaterials,
    MMY_OT_RepairPurpleMaterials,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass