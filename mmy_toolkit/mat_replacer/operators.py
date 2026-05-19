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
    """选择外部 .blend 文件"""
    bl_idname = "mmy.select_external_file"
    bl_label = "选择外部文件"
    bl_options = {'REGISTER'}

    filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = self.filepath

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在: {filepath}")
            return {'CANCELLED'}

        props.external_file = filepath
        props.external_materials.clear()

        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                for mat_name in data_from.materials:
                    item = props.external_materials.add()
                    item.name = mat_name
                    item.is_selected = True
            self.report({'INFO'}, f"已加载 {len(props.external_materials)} 个材质")
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

            # 自动生成映射列表（场景材质 → 待选择）
            self._build_mapping_list(context)

            linked_count = len(bpy.data.materials) - before_count
            self.report({'INFO'}, f"已Link {linked_count} 个材质")

        except Exception as e:
            self.report({'ERROR'}, f"Link失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def _build_mapping_list(self, context):
        """构建映射列表：左侧场景材质，右侧下拉选择框"""
        props = context.scene.mmy_mat_replacer
        props.mappings.clear()

        scene_mats = get_scene_materials()
        linked_mats = get_linked_material_names()

        # 解析材质名用于自动匹配
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

        # 构建映射字典：源材质名 → Link材质对象（通过library区分）
        mapping_dict = {}
        for m in props.mappings:
            target_name = decode_target_mat_id(m.target_mat_id)
            print(f"[MMY] 映射项: 源={m.source_mat_name}, 解码={target_name}")

            if target_name:
                # 关键：通过 library 属性找到 Link 材质，而不是本地同名材质
                target_mat = None
                for mat in bpy.data.materials:
                    if mat.name == target_name and mat.library is not None:
                        target_mat = mat
                        break

                if target_mat:
                    mapping_dict[m.source_mat_name] = target_mat
                    print(f"[MMY] 找到Link材质: {target_mat.name} (库: {target_mat.library.name})")
                else:
                    print(f"[MMY] 未找到Link材质: {target_name}")

        print(f"[MMY] 映射字典keys: {list(mapping_dict.keys())}")

        # 遍历场景所有对象，替换材质
        for obj in bpy.context.scene.objects:
            if hasattr(obj, 'material_slots'):
                for i, slot in enumerate(obj.material_slots):
                    old_mat = slot.material
                    if old_mat:
                        print(f"[MMY] 对象 {obj.name} 槽 {i}: 材质={old_mat.name}, library={old_mat.library}")

                        if old_mat.name in mapping_dict:
                            new_mat = mapping_dict[old_mat.name]
                            # 检查是否是同一个对象（通过比较对象引用，不是名字）
                            if old_mat != new_mat:
                                slot.material = new_mat
                                replaced_count += 1
                                print(f"[MMY] 替换: {old_mat.name} → {new_mat.name} (Link)")
                            else:
                                print(f"[MMY] 已是同一材质对象，跳过")
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

        # 移除Link材质
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

        # 检查文件中是否存在 Ani 集合
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                collections = list(data_from.collections)
                has_ani = "Ani" in collections

                props.has_ani_collection = has_ani
                props.ani_collection_name = "Ani" if has_ani else ""

                if has_ani:
                    self.report({'INFO'}, f"找到 Ani 集合")
                else:
                    self.report({'WARNING'}, f"文件中未找到 Ani 集合")
                    # 列出可用的集合供参考
                    if collections:
                        self.report({'INFO'}, f"可用集合: {', '.join(collections[:5])}")

        except Exception as e:
            self.report({'ERROR'}, f"读取失败: {str(e)}")
            props.has_ani_collection = False
            return {'CANCELLED'}

        return {'FINISHED'}


class MMY_OT_LinkAnimation(bpy.types.Operator):
    """关联 Ani 集合到世界中心"""
    bl_idname = "mmy.link_animation"
    bl_label = "关联动画"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_mat_replacer
        return props.anim_file and props.has_ani_collection

    def execute(self, context):
        props = context.scene.mmy_mat_replacer
        filepath = props.anim_file

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在")
            return {'CANCELLED'}

        try:
            # Link Ani 集合
            with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
                data_to.collections = ["Ani"]

            # 获取 Link 的集合
            ani_collection = bpy.data.collections.get("Ani")
            if not ani_collection:
                self.report({'ERROR'}, "Link 失败：未找到 Ani 集合")
                return {'CANCELLED'}

            # 检查是否已存在同名实例
            existing_instance = bpy.data.objects.get("Ani")
            if existing_instance and existing_instance.instance_collection == ani_collection:
                self.report({'WARNING'}, "Ani 集合已存在，跳过创建")
                return {'FINISHED'}

            # 创建集合实例并放入场景
            instance = bpy.data.objects.new("Ani", None)
            instance.empty_display_type = 'COLLECTION'
            instance.instance_collection = ani_collection
            instance.location = (0, 0, 0)  # 世界中心

            # 链接到场景集合
            context.scene.collection.objects.link(instance)

            self.report({'INFO'}, f"已关联 Ani 集合到世界中心")

        except Exception as e:
            self.report({'ERROR'}, f"关联失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


_classes = (
    MMY_OT_SelectExternalFile,
    MMY_OT_LinkMaterials,
    MMY_OT_ExecuteReplace,
    MMY_OT_ClearAll,
    MMY_OT_SelectAnimFile,
    MMY_OT_LinkAnimation,
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