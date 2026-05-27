"""材质替换器操作符"""

import bpy
import re
import os
from bpy_extras.io_utils import ImportHelper


def parse_material_name(name):
    """解析材质名称，提取前缀和后缀"""
    clean_name = re.sub(r'\.\d+$', '', name)
    parts = clean_name.split('_')
    if len(parts) >= 2:
        return {'prefix': parts[0], 'suffix': parts[-1], 'full': clean_name}
    return {'prefix': clean_name, 'suffix': '', 'full': clean_name}


def get_linked_material_names():
    """获取当前场景中所有Link材质的名称"""
    linked = []
    for mat in bpy.data.materials:
        if mat.library is not None:
            linked.append(mat.name)
    return linked


def get_scene_materials():
    """获取场景中所有对象使用的材质（区分本地和Link）"""
    scene_mats = set()
    for obj in bpy.context.scene.objects:
        if hasattr(obj, 'material_slots'):
            for slot in obj.material_slots:
                if slot.material and slot.material.library is None:
                    scene_mats.add(slot.material.name)
    return list(scene_mats)


# 目标材质枚举缓存
_TARGET_MAT_CACHE = []

def get_target_mat_items(self, context):
    """动态生成目标材质枚举项（Link材质列表）"""
    _TARGET_MAT_CACHE.clear()
    _TARGET_MAT_CACHE.append(("none", "不替换", ""))

    linked_mats = get_linked_material_names()
    for mat_name in linked_mats:
        display = mat_name.split('@')[0] if '@' in mat_name else mat_name
        safe_id = 'c' + mat_name.encode('utf-8').hex()
        _TARGET_MAT_CACHE.append((safe_id, display, ""))

    return _TARGET_MAT_CACHE


def decode_target_mat_id(safe_id):
    """解码安全枚举ID，返回实际材质名"""
    if safe_id == "none":
        return None
    if safe_id.startswith('c'):
        try:
            return bytes.fromhex(safe_id[1:]).decode('utf-8')
        except:
            return safe_id
    return safe_id


class MMY_OT_SelectExternalFile(bpy.types.Operator, ImportHelper):
    """选择外部 .blend 文件（材质替换 + 材质分配同步共用）"""
    bl_idname = "mmy.select_external_file"
    bl_label = "选择Mat文件"
    bl_description = "选择材质源文件，用于材质Link和材质分配同步"
    bl_options = {'REGISTER'}

    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = self.filepath

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在: {filepath}")
            return {'CANCELLED'}

        # 设置文件路径（材质替换和材质分配同步共用）
        props.external_file = filepath
        props.mat_source_file = filepath  # 同时设置材质分配同步的源文件

        # 清空旧数据
        props.external_materials.clear()
        props.source_objects.clear()
        props.source_materials.clear()

        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                # 加载材质列表
                for mat_name in data_from.materials:
                    item = props.external_materials.add()
                    item.name = mat_name
                    item.is_selected = True

                # 加载对象列表
                for obj_name in data_from.objects:
                    item = props.source_objects.add()
                    item.name = obj_name

                # 加载源材质列表
                for mat_name in data_from.materials:
                    item = props.source_materials.add()
                    item.name = mat_name

            self.report({'INFO'}, f"已加载: {len(props.external_materials)} 个材质, {len(props.source_objects)} 个对象")

        except Exception as e:
            self.report({'ERROR'}, f"读取失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class MMY_OT_LinkMaterials(bpy.types.Operator):
    """Link选中的材质到当前场景"""
    bl_idname = "mmy.link_materials"
    bl_label = "Link材质"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return props.external_file and len(props.external_materials) > 0

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = props.external_file

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在")
            return {'CANCELLED'}

        selected_names = [item.name for item in props.external_materials if item.is_selected]
        if not selected_names:
            self.report({'WARNING'}, "请选择要Link的材质")
            return {'CANCELLED'}

        try:
            before_count = len(bpy.data.materials)
            with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
                data_to.materials = selected_names

            # 更新已Link材质列表
            props.linked_materials.clear()
            for name in get_linked_material_names():
                item = props.linked_materials.add()
                item.name = name

            # 自动生成映射列表
            self._build_mapping_list(context)

            linked_count = len(bpy.data.materials) - before_count
            self.report({'INFO'}, f"已Link {linked_count} 个材质")

        except Exception as e:
            self.report({'ERROR'}, f"Link失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def _build_mapping_list(self, context):
        """构建映射列表"""
        props = context.scene.mmy_mat_replacer
        props.mappings.clear()

        scene_mats = get_scene_materials()
        linked_mats = get_linked_material_names()

        scene_parsed = {mat: parse_material_name(mat) for mat in scene_mats}
        linked_parsed = {}
        for mat in linked_mats:
            clean = mat.split('@')[0] if '@' in mat else mat
            linked_parsed[mat] = parse_material_name(clean)

        matched_linked = set()

        for src_mat in scene_mats:
            item = props.mappings.add()
            item.source_mat_name = src_mat

            src_info = scene_parsed[src_mat]
            target_id = "none"

            # 1. 完全同名匹配
            for lnk_mat in linked_mats:
                if lnk_mat in matched_linked:
                    continue
                if src_info['full'] == linked_parsed[lnk_mat]['full']:
                    target_id = 'c' + lnk_mat.encode('utf-8').hex()
                    matched_linked.add(lnk_mat)
                    break

            # 2. 后缀匹配
            if target_id == "none" and src_info['suffix']:
                for lnk_mat in linked_mats:
                    if lnk_mat in matched_linked:
                        continue
                    if linked_parsed[lnk_mat]['suffix'] == src_info['suffix']:
                        target_id = 'c' + lnk_mat.encode('utf-8').hex()
                        matched_linked.add(lnk_mat)
                        break

            item.target_mat_id = target_id


class MMY_OT_ExecuteReplace(bpy.types.Operator):
    """执行材质替换"""
    bl_idname = "mmy.execute_replace"
    bl_label = "执行替换"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return len(props.mappings) > 0 and len(get_linked_material_names()) > 0

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        replaced_count = 0

        print(f"[MMY] === 开始替换 ===")
        print(f"[MMY] 映射数量: {len(props.mappings)}")

        # 构建映射字典
        mapping_dict = {}
        for m in props.mappings:
            target_name = decode_target_mat_id(m.target_mat_id)
            print(f"[MMY] 映射项: 源={m.source_mat_name}, 解码={target_name}")

            if target_name:
                target_mat = None
                for mat in bpy.data.materials:
                    if mat.name == target_name and mat.library is not None:
                        target_mat = mat
                        break

                if target_mat:
                    mapping_dict[m.source_mat_name] = target_mat
                    print(f"[MMY] 找到Link材质: {target_mat.name}")
                else:
                    print(f"[MMY] 未找到Link材质: {target_name}")

        # 遍历场景对象替换材质
        for obj in bpy.context.scene.objects:
            if hasattr(obj, 'material_slots'):
                for i, slot in enumerate(obj.material_slots):
                    old_mat = slot.material
                    if old_mat:
                        print(f"[MMY] 对象 {obj.name} 槽 {i}: 材质={old_mat.name}")

                        if old_mat.name in mapping_dict:
                            new_mat = mapping_dict[old_mat.name]
                            if old_mat != new_mat:
                                slot.material = new_mat
                                replaced_count += 1
                                print(f"[MMY] 替换: {old_mat.name} → {new_mat.name}")
                            else:
                                print(f"[MMY] 已是同一材质，跳过")
                        else:
                            print(f"[MMY] 材质 {old_mat.name} 不在映射字典中")

        print(f"[MMY] 替换完成: {replaced_count} 个")
        self.report({'INFO'}, f"已替换 {replaced_count} 个材质槽")
        return {'FINISHED'}


class MMY_OT_ClearAll(bpy.types.Operator):
    """清除所有Link材质和映射"""
    bl_idname = "mmy.clear_all"
    bl_label = "清除"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.mmy_mat_replacer

        for mat in bpy.data.materials:
            if mat.library is not None and mat.users == 0:
                bpy.data.materials.remove(mat)

        props.linked_materials.clear()
        props.external_materials.clear()
        props.mappings.clear()
        props.external_file = ""

        self.report({'INFO'}, "已清除")
        return {'FINISHED'}


# === 动画关联操作符 ===

class MMY_OT_SelectAnimFile(bpy.types.Operator, ImportHelper):
    """选择动画源文件"""
    bl_idname = "mmy.select_anim_file"
    bl_label = "选择动画文件"
    bl_options = {'REGISTER'}

    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = self.filepath

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在: {filepath}")
            return {'CANCELLED'}

        props.anim_file = filepath

        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                collections = list(data_from.collections)

                # 从偏好设置获取预设集合名称
                addon = context.preferences.addons.get("mmy_toolkit")
                preset_names = []
                if addon and addon.preferences:
                    preset_names = [item.name for item in addon.preferences.ani_collection_names]

                # 如果没有预设，使用默认值
                if not preset_names:
                    preset_names = ["Ani"]

                # 查找匹配的集合
                found_name = None
                for preset in preset_names:
                    if preset in collections:
                        found_name = preset
                        break

                props.has_ani_collection = found_name is not None
                props.ani_collection_name = found_name if found_name else ""

                if found_name:
                    self.report({'INFO'}, f"找到集合: {found_name}")
                else:
                    self.report({'WARNING'}, f"未找到预设集合")
                    if collections:
                        self.report({'INFO'}, f"可用集合: {', '.join(collections[:5])}")

        except Exception as e:
            self.report({'ERROR'}, f"读取失败: {str(e)}")
            props.has_ani_collection = False
            return {'CANCELLED'}

        return {'FINISHED'}


class MMY_OT_LinkAnimation(bpy.types.Operator):
    """关联动画集合到世界中心"""
    bl_idname = "mmy.link_animation"
    bl_label = "关联动画"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return props.anim_file and props.has_ani_collection and props.ani_collection_name

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = props.anim_file
        collection_name = props.ani_collection_name

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在")
            return {'CANCELLED'}

        try:
            # Link 集合（使用预设中的名称）
            with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
                data_to.collections = [collection_name]

            # 查找 Link 集合（可能带文件路径前缀）
            ani_collection = None
            for coll in bpy.data.collections:
                if coll.library is not None:
                    if coll.name == collection_name or collection_name in coll.name.split('@')[0]:
                        ani_collection = coll
                        print(f"[MMY] 找到Link集合: {coll.name}, library={coll.library}")
                        break

            if not ani_collection:
                self.report({'ERROR'}, f"Link 失败：未找到 {collection_name} 集合")
                return {'CANCELLED'}

            # 检查集合是否为空
            print(f"[MMY] 集合内容: objects={len(ani_collection.objects)}, children={len(ani_collection.children)}")

            # 检查是否已有实例
            for obj in context.scene.objects:
                if obj.instance_collection == ani_collection:
                    self.report({'WARNING'}, f"{collection_name} 集合已存在实例")
                    return {'FINISHED'}

            # 创建集合实例
            instance = bpy.data.objects.new(collection_name, None)
            instance.empty_display_type = 'PLAIN_AXES'
            instance.instance_type = 'COLLECTION'
            instance.instance_collection = ani_collection
            instance.location = (0, 0, 0)

            context.scene.collection.objects.link(instance)

            self.report({'INFO'}, f"已关联 {ani_collection.name} 到世界中心")

        except Exception as e:
            print(f"[MMY] 关联动画失败: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"关联失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


# === 骨骼缩放约束操作符 ===

class MMY_OT_CreateScaleConstraint(bpy.types.Operator):
    """创建Scale空物体并给骨骼添加Copy Scale约束"""
    bl_idname = "mmy.create_scale_constraint"
    bl_label = "创建缩放约束"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return props.target_armature_enum != "none"

    def execute(self, context):
        props = context.scene.mmy_mat_replacer

        from .properties import decode_armature_id
        armature_name = decode_armature_id(props.target_armature_enum)

        if not armature_name:
            self.report({'ERROR'}, "请选择目标骨骼")
            return {'CANCELLED'}

        armature = bpy.data.objects.get(armature_name)
        if not armature:
            self.report({'ERROR'}, f"未找到骨骼: {armature_name}")
            return {'CANCELLED'}

        scale_obj = bpy.data.objects.get("Scale")
        if not scale_obj:
            scale_obj = bpy.data.objects.new("Scale", None)
            scale_obj.empty_display_type = 'PLAIN_AXES'
            scale_obj.location = (0, 0, 0)
            scale_obj.scale = (1.0, 1.0, 1.0)
            context.scene.collection.objects.link(scale_obj)
            self.report({'INFO'}, "已创建 Scale 空物体")
        else:
            self.report({'INFO'}, "复用已存在的 Scale 空物体")

        existing_constraint = None
        for c in armature.constraints:
            if c.name == "MMY_Copy_Scale":
                existing_constraint = c
                break

        if existing_constraint:
            self.report({'WARNING'}, "骨骼已有缩放约束，跳过添加")
            # 同步约束状态到属性
            props.constraint_enabled = not existing_constraint.mute
        else:
            constraint = armature.constraints.new('COPY_SCALE')
            constraint.name = "MMY_Copy_Scale"
            constraint.target = scale_obj
            constraint.use_x = True
            constraint.use_y = True
            constraint.use_z = True
            constraint.use_offset = props.use_offset
            constraint.owner_space = 'LOCAL'
            constraint.target_space = 'LOCAL'
            constraint.mute = not props.constraint_enabled  # 根据属性设置启用状态
            self.report({'INFO'}, f"已给 {armature_name} 添加 Copy Scale 约束")

        props.scale_value = scale_obj.scale.x

        return {'FINISHED'}


# === 材质分配同步操作符 ===

class MMY_OT_SelectMatSourceFile(bpy.types.Operator, ImportHelper):
    """选择材质源文件（Mat.blend）"""
    bl_idname = "mmy.select_mat_source_file"
    bl_label = "选择材质源文件"
    bl_description = "选择包含材质分配信息的源 .blend 文件"
    bl_options = {'REGISTER'}

    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = self.filepath

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在: {filepath}")
            return {'CANCELLED'}

        props.mat_source_file = filepath

        # 读取源文件中的对象列表
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                # 保存源对象列表到属性
                props.source_objects.clear()
                for obj_name in data_from.objects:
                    item = props.source_objects.add()
                    item.name = obj_name

                # 保存材质列表
                props.source_materials.clear()
                for mat_name in data_from.materials:
                    item = props.source_materials.add()
                    item.name = mat_name

                self.report({'INFO'}, f"已加载: {len(props.source_objects)} 个对象, {len(props.source_materials)} 个材质")

        except Exception as e:
            self.report({'ERROR'}, f"读取失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class MMY_OT_SyncMaterialAssignment(bpy.types.Operator):
    """同步材质分配信息"""
    bl_idname = "mmy.sync_material_assignment"
    bl_label = "同步材质分配"
    bl_description = "从源文件同步材质槽和面分配到当前对象"
    bl_options = {'REGISTER', 'UNDO'}

    # 允许手动指定源对象名称
    source_object_name: bpy.props.StringProperty(
        name="源对象名",
        default="",
        description="手动指定源对象名称，为空则使用同名匹配"
    )

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return props.mat_source_file and context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = props.mat_source_file

        target_obj = context.active_object
        if not target_obj or target_obj.type != 'MESH':
            self.report({'ERROR'}, "请选中网格对象")
            return {'CANCELLED'}

        # 确定源对象名称：手动指定 或 同名匹配 或 使用手动源名属性
        if self.source_object_name:
            source_obj_name = self.source_object_name
        elif props.manual_source_name:
            source_obj_name = props.manual_source_name
        else:
            source_obj_name = target_obj.name

        # 检查源对象是否存在
        source_obj_found = False
        for item in props.source_objects:
            if item.name == source_obj_name:
                source_obj_found = True
                break

        if not source_obj_found:
            # 尝试在源对象列表中找可能的匹配
            self.report({'WARNING'}, f"源文件未找到对象: {source_obj_name}")
            self.report({'INFO'}, f"可用对象: {', '.join([item.name for item in props.source_objects[:10]])}")
            return {'CANCELLED'}

        try:
            # 使用更直接的方式：临时 append 源对象，读取数据，然后删除
            self._sync_via_temp_append(context, filepath, source_obj_name, target_obj)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"同步失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def _sync_via_temp_append(self, context, filepath, source_name, target_obj):
        """通过临时 append 源对象来同步材质分配"""
        import tempfile
        import shutil

        # 保存目标对象的指针（重要！防止误删）
        target_obj_ptr = target_obj
        target_obj_name = target_obj.name

        # 临时保存当前场景状态
        original_selected = [obj.name for obj in context.selected_objects]
        original_active = context.active_object.name if context.active_object else None

        # 记录当前对象列表（用于识别新 append 的对象）
        existing_objects = set(obj.name for obj in bpy.data.objects)

        # 在临时集合中 append 源对象
        temp_coll_name = "_MMY_TEMP_SYNC_"
        temp_coll = bpy.data.collections.new(temp_coll_name)
        context.scene.collection.children.link(temp_coll)

        try:
            # Append 源对象
            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                # 找到源对象
                if source_name in data_from.objects:
                    data_to.objects = [source_name]

            # 查找新 append 的对象（通过对比对象列表）
            source_obj = None
            for obj in bpy.data.objects:
                if obj.name not in existing_objects:
                    source_obj = obj
                    break

            # 如果没找到新对象，可能是源对象名被重命名了
            if not source_obj:
                # 查找可能的 append 对象（名称包含源名）
                for obj in bpy.data.objects:
                    if source_name in obj.name and obj != target_obj_ptr:
                        source_obj = obj
                        break

            if not source_obj:
                self.report({'ERROR'}, f"未能加载源对象: {source_name}")
                return

            # 链接到临时集合（如果还没链接）
            if source_obj.name not in temp_coll.objects:
                temp_coll.objects.link(source_obj)

            # 检查拓扑是否匹配
            source_mesh = source_obj.data
            target_mesh = target_obj_ptr.data

            if len(source_mesh.polygons) != len(target_mesh.polygons):
                self.report({'WARNING'}, f"拓扑不匹配: 源{len(source_mesh.polygons)}面 vs 目标{len(target_mesh.polygons)}面")
                self.report({'INFO'}, "尝试部分同步...")

            # 同步材质槽
            self._sync_material_slots(context, source_obj, target_obj_ptr)

            # 同步材质分配索引
            synced_count = 0
            min_faces = min(len(source_mesh.polygons), len(target_mesh.polygons))

            for i in range(min_faces):
                target_mesh.polygons[i].material_index = source_mesh.polygons[i].material_index
                synced_count += 1

            # 更新材质槽显示
            for area in context.screen.areas:
                if area.type == 'PROPERTIES':
                    for space in area.spaces:
                        if space.type == 'PROPERTIES':
                            space.context = 'MATERIAL'
                            break

            self.report({'INFO'}, f"已同步 {synced_count} 个面的材质分配")

        finally:
            # 安全清理临时对象和集合（保护目标对象！）
            # 只清理新添加的对象，不清理目标对象
            objs_to_remove = []
            meshes_to_remove = []

            for obj in bpy.data.objects:
                # 只清理新 append 的对象（不在原有列表中）且不是目标对象
                if obj.name not in existing_objects and obj != target_obj_ptr:
                    objs_to_remove.append(obj)
                    if obj.data:
                        meshes_to_remove.append(obj.data)

            # 取消链接并移除
            for obj in objs_to_remove:
                try:
                    if obj.name in temp_coll.objects:
                        temp_coll.objects.unlink(obj)
                    bpy.data.objects.remove(obj, do_unlink=True)
                except:
                    pass

            # 移除临时 mesh 数据
            for mesh in meshes_to_remove:
                if mesh and mesh.users == 0:
                    try:
                        bpy.data.meshes.remove(mesh)
                    except:
                        pass

            # 移除临时集合
            try:
                context.scene.collection.children.unlink(temp_coll)
            except:
                pass
            try:
                bpy.data.collections.remove(temp_coll)
            except:
                pass

            # 恢复选中状态（确保目标对象存在）
            bpy.ops.object.select_all(action='DESELECT')

            # 确保目标对象仍然存在
            if target_obj_ptr and target_obj_ptr.name in bpy.data.objects:
                target_obj_ptr.select_set(True)
                context.view_layer.objects.active = target_obj_ptr

            # 恢复其他选中对象
            for name in original_selected:
                if name != target_obj_name:  # 避免重复选中
                    obj = bpy.data.objects.get(name)
                    if obj:
                        obj.select_set(True)

    def _sync_material_slots(self, context, source_obj, target_obj):
        """同步材质槽（使用 Link 方式关联材质）"""
        # 先 Link 源文件的所有材质
        props = context.scene.mmy_mat_replacer
        filepath = props.mat_source_file

        # 获取源对象的材质列表
        source_materials = []
        for slot in source_obj.material_slots:
            if slot.material:
                source_materials.append(slot.material.name)

        # Link 这些材质到当前文件
        linked_materials = {}
        if filepath and source_materials:
            try:
                with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
                    data_to.materials = source_materials

                # 查找 Link 的材质
                for mat_name in source_materials:
                    for mat in bpy.data.materials:
                        if mat.name == mat_name and mat.library is not None:
                            linked_materials[mat_name] = mat
                            break
                        # Blender 可能会给 Link 材质添加后缀
                        if mat.library is not None and mat_name in mat.name:
                            linked_materials[mat_name] = mat
                            break
            except Exception as e:
                print(f"[MMY] Link材质失败: {e}")
                # 如果 Link 失败，使用原材质（复制方式）
                for mat_name in source_materials:
                    for slot in source_obj.material_slots:
                        if slot.material and slot.material.name == mat_name:
                            linked_materials[mat_name] = slot.material
                            break

        # 清除目标对象的多余材质槽
        while len(target_obj.material_slots) > len(source_obj.material_slots):
            target_obj.active_material_index = len(target_obj.material_slots) - 1
            bpy.ops.object.material_slot_remove()

        # 确保材质槽数量匹配，使用 Link 的材质
        for i in range(len(source_obj.material_slots)):
            source_slot = source_obj.material_slots[i]
            source_mat = source_slot.material

            if source_mat:
                # 获取 Link 的材质
                linked_mat = linked_materials.get(source_mat.name, source_mat)

                # 如果目标材质槽不够，添加新槽
                if i >= len(target_obj.material_slots):
                    target_obj.data.materials.append(linked_mat)
                else:
                    # 替换材质为 Link 版本
                    target_obj.material_slots[i].material = linked_mat


_classes = (
    MMY_OT_SelectExternalFile,
    MMY_OT_LinkMaterials,
    MMY_OT_ExecuteReplace,
    MMY_OT_ClearAll,
    MMY_OT_SelectAnimFile,
    MMY_OT_LinkAnimation,
    MMY_OT_CreateScaleConstraint,
    MMY_OT_SelectMatSourceFile,
    MMY_OT_SyncMaterialAssignment,
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