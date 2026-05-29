"""形态键工具：应用修改器并保留形态键

基于 SKkeeper (blender_org/shapekey_keeper) 的算法实现
"""

import bpy
from bpy.props import StringProperty


def _log(msg):
    print(f"[MMY形态键] {msg}")


def _copy_object(obj):
    """复制对象及其网格数据"""
    copy_obj = obj.copy()
    copy_obj.data = obj.data.copy()
    copy_obj.name = f"{obj.name}_sk_temp"
    bpy.context.collection.objects.link(copy_obj)
    return copy_obj


def _apply_single_shapekey(obj, sk_index):
    """只保留指定索引的形态键，其他全部删除，并烘焙到网格"""
    shape_keys = obj.data.shape_keys.key_blocks

    if not shape_keys or sk_index >= len(shape_keys):
        return

    # 删除其他形态键（从后向前删除）
    for i in reversed(range(len(shape_keys))):
        if i != sk_index:
            obj.shape_key_remove(shape_keys[i])

    # 删除 Basis（将形态键烘焙到网格）
    obj.shape_key_remove(shape_keys[0])


def _apply_modifiers_convert(obj):
    """使用 object.convert 应用所有修改器（绕过形态键限制）"""
    for o in bpy.context.scene.objects:
        o.select_set(False)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Subsurf 特殊处理
    for mod in obj.modifiers:
        if mod.type == 'SUBSURF':
            mod.show_only_control_edges = False

    bpy.ops.object.convert(target='MESH')


def _apply_modifier_direct(obj, modifier_name):
    """直接应用单个修改器"""
    for o in bpy.context.scene.objects:
        o.select_set(False)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.modifier_apply(modifier=modifier_name)


def _join_shapes(destination, sources):
    """将源对象作为形态键合并到目标对象"""
    for o in bpy.context.scene.objects:
        o.select_set(False)

    for src in sources:
        src.select_set(True)

    bpy.context.view_layer.objects.active = destination
    bpy.ops.object.join_shapes()


def _safe_enum_id(name: str) -> str:
    return 'c' + name.encode('utf-8').hex()


def _decode_modifier_id(identifier):
    if identifier in ('all', 'none'):
        return identifier
    if identifier.startswith('c'):
        try:
            return bytes.fromhex(identifier[1:]).decode('utf-8')
        except:
            return identifier
    return identifier


class MMY_OT_ApplyModifierWithShapeKeys(bpy.types.Operator):
    """应用修改器并保留形态键"""
    bl_idname = "mmy.apply_modifier_with_shapekeys"
    bl_label = "应用修改器(保留形态键)"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_id: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and len(obj.modifiers) > 0

    def execute(self, context):
        obj = context.active_object
        modifier_name = _decode_modifier_id(self.modifier_id)

        if modifier_name == 'none':
            self.report({'WARNING'}, "没有可应用的修改器")
            return {'CANCELLED'}

        if modifier_name == 'all':
            return self._apply_all_modifiers(obj)
        else:
            return self._apply_single_modifier(obj, modifier_name)

    def _apply_all_modifiers(self, obj):
        """应用所有修改器"""
        shape_keys = obj.data.shape_keys
        has_shapekeys = shape_keys and len(shape_keys.key_blocks) > 0

        if not has_shapekeys:
            _apply_modifiers_convert(obj)
            self.report({'INFO'}, "已应用所有修改器")
            return {'FINISHED'}

        return self._keep_shapekeys_apply_all(obj)

    def _apply_single_modifier(self, obj, modifier_name):
        """应用单个修改器"""
        shape_keys = obj.data.shape_keys
        has_shapekeys = shape_keys and len(shape_keys.key_blocks) > 0

        if not has_shapekeys:
            _apply_modifier_direct(obj, modifier_name)
            self.report({'INFO'}, f"已应用修改器: {modifier_name}")
            return {'FINISHED'}

        return self._keep_shapekeys_apply_single(obj, modifier_name)

    def _keep_shapekeys_apply_all(self, obj):
        """保留形态键并应用所有修改器"""

        shape_key_names = [sk.name for sk in obj.data.shape_keys.key_blocks]
        num_shapekeys = len(shape_key_names)

        _log(f"处理 {num_shapekeys - 1} 个形态键")

        # 1. 创建接收器对象（保留 Basis，应用修改器）
        receiver = _copy_object(obj)
        receiver.name = "mmy_sk_receiver"
        _apply_single_shapekey(receiver, 0)  # 只保留 Basis
        _apply_modifiers_convert(receiver)   # 应用所有修改器

        # 2. 为每个形态键创建对象，应用修改器后合并到接收器
        for sk_index in range(1, num_shapekeys):
            sk_name = shape_key_names[sk_index]
            _log(f"处理形态键 [{sk_index}] {sk_name}")

            # 创建形态键捐献者
            sk_donor = _copy_object(obj)
            sk_donor.name = f"mmy_sk_donor_{sk_index}"

            # 只保留当前形态键
            _apply_single_shapekey(sk_donor, sk_index)

            # 应用所有修改器
            _apply_modifiers_convert(sk_donor)

            # 作为形态键合并到接收器
            _join_shapes(receiver, [sk_donor])

            # 检查是否成功添加
            if receiver.data.shape_keys is None:
                bpy.data.objects.remove(sk_donor)
                bpy.data.meshes.remove(sk_donor.data)
                bpy.data.objects.remove(receiver)
                bpy.data.meshes.remove(receiver.data)
                self.report({'ERROR'}, f"形态键 {sk_name} 顶点数量不匹配，无法传递")
                return {'CANCELLED'}

            # 恢复形态键名称
            receiver.data.shape_keys.key_blocks[-1].name = sk_name

            # 清理捐献者
            mesh_data = sk_donor.data
            bpy.data.objects.remove(sk_donor)
            bpy.data.meshes.remove(mesh_data)

        # 3. 转移动画驱动器（如果有）
        orig_data = obj.data
        if orig_data.shape_keys and orig_data.shape_keys.animation_data:
            receiver.data.shape_keys.animation_data_create()
            for orig_driver in orig_data.shape_keys.animation_data.drivers:
                receiver.data.shape_keys.animation_data.drivers.from_existing(src_driver=orig_driver)

        # 4. 清理原对象
        orig_name = obj.name
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(orig_data)

        # 5. 重命名接收器
        receiver.name = orig_name

        self.report({'INFO'}, f"已应用所有修改器，保留 {num_shapekeys - 1} 个形态键")
        return {'FINISHED'}

    def _keep_shapekeys_apply_single(self, obj, modifier_name):
        """保留形态键并应用单个修改器"""

        shape_key_names = [sk.name for sk in obj.data.shape_keys.key_blocks]
        num_shapekeys = len(shape_key_names)

        _log(f"处理 {num_shapekeys - 1} 个形态键，应用修改器 {modifier_name}")

        # 1. 创建接收器对象
        receiver = _copy_object(obj)
        receiver.name = "mmy_sk_receiver"
        _apply_single_shapekey(receiver, 0)

        # 应用单个修改器
        _apply_modifier_direct(receiver, modifier_name)

        # 2. 为每个形态键处理
        for sk_index in range(1, num_shapekeys):
            sk_name = shape_key_names[sk_index]

            sk_donor = _copy_object(obj)
            sk_donor.name = f"mmy_sk_donor_{sk_index}"

            _apply_single_shapekey(sk_donor, sk_index)
            _apply_modifier_direct(sk_donor, modifier_name)

            _join_shapes(receiver, [sk_donor])

            if receiver.data.shape_keys is None:
                bpy.data.objects.remove(sk_donor)
                bpy.data.meshes.remove(sk_donor.data)
                bpy.data.objects.remove(receiver)
                bpy.data.meshes.remove(receiver.data)
                self.report({'ERROR'}, f"形态键 {sk_name} 顶点数量不匹配")
                return {'CANCELLED'}

            receiver.data.shape_keys.key_blocks[-1].name = sk_name

            mesh_data = sk_donor.data
            bpy.data.objects.remove(sk_donor)
            bpy.data.meshes.remove(mesh_data)

        # 3. 转移驱动器
        orig_data = obj.data
        if orig_data.shape_keys and orig_data.shape_keys.animation_data:
            receiver.data.shape_keys.animation_data_create()
            for orig_driver in orig_data.shape_keys.animation_data.drivers:
                receiver.data.shape_keys.animation_data.drivers.from_existing(src_driver=orig_driver)

        # 4. 清理原对象
        orig_name = obj.name
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(orig_data)

        # 5. 重命名接收器
        receiver.name = orig_name

        self.report({'INFO'}, f"已应用修改器 {modifier_name}，保留 {num_shapekeys - 1} 个形态键")
        return {'FINISHED'}


class MMY_OT_ApplyAllModifiersWithShapeKeys(bpy.types.Operator):
    """应用所有修改器并保留形态键（支持多选）"""
    bl_idname = "mmy.apply_all_modifiers_with_shapekeys"
    bl_label = "全部应用(保留形态键)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中的网格对象且有修改器
        for obj in context.selected_objects:
            if obj.type == 'MESH' and len(obj.modifiers) > 0:
                return True
        return False

    def execute(self, context):
        objects = [obj for obj in context.selected_objects
                   if obj.type == 'MESH' and len(obj.modifiers) > 0]

        if not objects:
            self.report({'WARNING'}, "没有可应用的对象")
            return {'CANCELLED'}

        count = 0
        for obj in objects:
            # 设置为活动对象
            bpy.context.view_layer.objects.active = obj

            try:
                # 调用单对象应用逻辑（传入 'all' 表示应用所有修改器）
                bpy.ops.mmy.apply_modifier_with_shapekeys(modifier_id='all')
                count += 1
            except Exception as e:
                self.report({'WARNING'}, f"{obj.name} 应用失败: {e}")
                continue

        self.report({'INFO'}, f"已应用 {count} 个对象的修改器")
        return {'FINISHED'}


_classes = (
    MMY_OT_ApplyModifierWithShapeKeys,
    MMY_OT_ApplyAllModifiersWithShapeKeys,
)