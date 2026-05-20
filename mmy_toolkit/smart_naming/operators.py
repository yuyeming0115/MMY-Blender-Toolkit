"""智能命名操作符"""

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty
from .utils import (
    smart_increment_name,
    find_next_available_name,
    get_all_collection_names,
    get_all_object_names,
    get_all_material_names,
    duplicate_collection_contents,
)
from .presets import get_separator, get_digits


class MMY_OT_SmartDuplicateCollection(bpy.types.Operator):
    """智能复制集合 - 名称数字自动递增"""
    bl_idname = "mmy.smart_duplicate_collection"
    bl_label = "智能复制集合"
    bl_description = "复制集合内容，名称数字自动递增（如 集合1 → 集合2）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取选中的集合
        selected_colls = []

        # 尝试从大纲视图获取选中集合
        if context.area and context.area.type == 'OUTLINER':
            # 大纲视图：通过激活的集合判断
            if context.collection:
                selected_colls.append(context.collection)

        # 备用：从场景集合层级查找
        if not selected_colls:
            # 查找当前激活集合
            active_coll = context.collection
            if active_coll and active_coll.name != "Scene Collection":
                selected_colls.append(active_coll)

        if not selected_colls:
            self.report({'WARNING'}, "请先在大纲视图选中一个集合")
            return {'CANCELLED'}

        # 处理每个选中的集合
        separator = get_separator()
        digits = get_digits()
        created_count = 0

        for source_coll in selected_colls:
            # 计算新名称
            existing_names = get_all_collection_names()
            new_name = find_next_available_name(
                source_coll.name,
                existing_names,
                separator,
                digits
            )

            # 复制集合内容
            new_coll = duplicate_collection_contents(source_coll, new_name, context)
            created_count += 1

            self.report({'INFO'}, f"已创建: {new_name}")

        if created_count > 0:
            self.report({'INFO'}, f"已智能复制 {created_count} 个集合")

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        # 在大纲视图或3D视图中可用
        return context.area and (context.area.type in ('OUTLINER', 'VIEW_3D'))


class MMY_OT_SmartDuplicateObject(bpy.types.Operator):
    """智能复制对象 - 名称数字自动递增"""
    bl_idname = "mmy.smart_duplicate_object"
    bl_label = "智能复制对象"
    bl_description = "复制选中对象，名称数字自动递增"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = context.selected_objects

        if not selected_objs:
            self.report({'WARNING'}, "请先选中对象")
            return {'CANCELLED'}

        separator = get_separator()
        digits = get_digits()
        created_objs = []

        # 取消所有选择
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selected_objs:
            # 计算新名称
            existing_names = get_all_object_names()
            new_name = find_next_available_name(obj.name, existing_names, separator, digits)

            # 复制对象
            new_obj = obj.copy()
            new_obj.name = new_name

            # 复制数据（网格、材质槽等）
            if obj.data:
                new_obj.data = obj.data.copy()

            # 链接到同一集合
            for coll in bpy.data.collections:
                if obj in coll.objects:
                    coll.objects.link(new_obj)
                    break

            # 如果原对象在场景根集合
            if obj in context.scene.collection.objects:
                context.scene.collection.objects.link(new_obj)

            # 选中新对象
            new_obj.select_set(True)
            created_objs.append(new_obj)

        # 设置最后一个对象为活动对象
        if created_objs:
            context.view_layer.objects.active = created_objs[-1]

        self.report({'INFO'}, f"已智能复制 {len(created_objs)} 个对象")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.mode in ('OBJECT', 'EDIT_MESH') and context.selected_objects


class MMY_OT_BatchRename(bpy.types.Operator):
    """批量重命名"""
    bl_idname = "mmy.batch_rename"
    bl_label = "批量重命名"
    bl_description = "批量重命名选中的集合/对象/材质"
    bl_options = {'REGISTER', 'UNDO'}

    target_type: EnumProperty(
        name="目标类型",
        items=[
            ('collection', "集合", "重命名集合"),
            ('object', "对象", "重命名对象"),
            ('material', "材质", "重命名材质"),
        ],
        default='object'
    )

    prefix: StringProperty(name="前缀", default="")
    suffix: StringProperty(name="后缀", default="")
    start_num: IntProperty(name="起始序号", default=1, min=1)
    use_increment: BoolProperty(name="序号递增", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        # 目标类型
        layout.prop(self, "target_type")

        layout.separator()

        # 前缀和后缀
        row = layout.row()
        row.prop(self, "prefix")
        # 前缀预设按钮（简化版，直接显示输入框）

        row = layout.row()
        row.prop(self, "suffix")

        layout.separator()

        # 序号选项
        row = layout.row()
        row.prop(self, "use_increment")
        if self.use_increment:
            row.prop(self, "start_num")

    def execute(self, context):
        separator = get_separator()
        digits = get_digits()

        # 获取目标列表
        targets = []
        if self.target_type == 'collection':
            # 获取场景中的所有集合（排除 Scene Collection）
            targets = [coll for coll in bpy.data.collections]
        elif self.target_type == 'object':
            targets = list(context.selected_objects)
            if not targets:
                self.report({'WARNING'}, "请先选中对象")
                return {'CANCELLED'}
        elif self.target_type == 'material':
            # 获取选中对象的材质
            targets = []
            for obj in context.selected_objects:
                for slot in obj.material_slots:
                    if slot.material and slot.material not in targets:
                        targets.append(slot.material)
            if not targets:
                targets = list(bpy.data.materials)

        # 执行批量重命名
        renamed_count = 0
        for i, target in enumerate(targets):
            # 计算新名称
            base_name = target.name

            # 清理 Blender 后缀
            base_name = base_name.rstrip('.001').rstrip('.002').rstrip('.003')

            # 应用前缀和后缀
            new_name = base_name
            if self.prefix:
                new_name = f"{self.prefix}{new_name}"
            if self.suffix:
                new_name = f"{new_name}{self.suffix}"

            # 添加序号
            if self.use_increment:
                num = self.start_num + i
                num_str = str(num).zfill(digits)
                if separator:
                    new_name = f"{new_name}{separator}{num_str}"
                else:
                    new_name = f"{new_name}{num_str}"

            # 检查名称冲突
            existing_names = set()
            if self.target_type == 'collection':
                existing_names = get_all_collection_names()
            elif self.target_type == 'object':
                existing_names = get_all_object_names()
            elif self.target_type == 'material':
                existing_names = get_all_material_names()

            # 跳过自身
            existing_names.discard(target.name)

            # 如果冲突，继续递增
            if new_name in existing_names:
                new_name = find_next_available_name(new_name, existing_names, separator, digits)

            # 应用新名称
            try:
                target.name = new_name
                renamed_count += 1
            except:
                pass

        self.report({'INFO'}, f"已重命名 {renamed_count} 个目标")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return True


class MMY_OT_RenameSingle(bpy.types.Operator):
    """智能重命名单个对象"""
    bl_idname = "mmy.rename_single"
    bl_label = "智能重命名"
    bl_description = "将选中对象重命名为指定名称，自动处理数字递增"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(name="新名称", default="")

    def invoke(self, context, event):
        # 预填充当前名称
        if context.active_object:
            self.new_name = context.active_object.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "请先选中对象")
            return {'CANCELLED'}

        if not self.new_name:
            self.report({'WARNING'}, "请输入新名称")
            return {'CANCELLED'}

        # 检查冲突
        existing_names = get_all_object_names()
        existing_names.discard(obj.name)

        if self.new_name in existing_names:
            # 名称冲突，智能递增
            separator = get_separator()
            digits = get_digits()
            final_name = find_next_available_name(self.new_name, existing_names, separator, digits)
            self.report({'INFO'}, f"名称已调整: {final_name}")
        else:
            final_name = self.new_name

        obj.name = final_name
        self.report({'INFO'}, f"已重命名为: {final_name}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None


class MMY_OT_AddPrefixPreset(bpy.types.Operator):
    """添加前缀预设"""
    bl_idname = "mmy.add_prefix_preset"
    bl_label = "添加前缀预设"

    prefix: StringProperty(name="前缀", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from .presets import add_prefix_preset
        if add_prefix_preset(self.prefix):
            self.report({'INFO'}, f"已添加前缀预设: {self.prefix}")
        else:
            self.report({'WARNING'}, f"前缀预设已存在: {self.prefix}")
        return {'FINISHED'}


class MMY_OT_RemovePrefixPreset(bpy.types.Operator):
    """删除前缀预设"""
    bl_idname = "mmy.remove_prefix_preset"
    bl_label = "删除前缀预设"

    prefix: StringProperty(name="前缀")

    def execute(self, context):
        from .presets import remove_prefix_preset
        if remove_prefix_preset(self.prefix):
            self.report({'INFO'}, f"已删除前缀预设: {self.prefix}")
        return {'FINISHED'}


class MMY_OT_AddSuffixPreset(bpy.types.Operator):
    """添加后缀预设"""
    bl_idname = "mmy.add_suffix_preset"
    bl_label = "添加后缀预设"

    suffix: StringProperty(name="后缀", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from .presets import add_suffix_preset
        if add_suffix_preset(self.suffix):
            self.report({'INFO'}, f"已添加后缀预设: {self.suffix}")
        else:
            self.report({'WARNING'}, f"后缀预设已存在: {self.suffix}")
        return {'FINISHED'}


class MMY_OT_RemoveSuffixPreset(bpy.types.Operator):
    """删除后缀预设"""
    bl_idname = "mmy.remove_suffix_preset"
    bl_label = "删除后缀预设"

    suffix: StringProperty(name="后缀")

    def execute(self, context):
        from .presets import remove_suffix_preset
        if remove_suffix_preset(self.suffix):
            self.report({'INFO'}, f"已删除后缀预设: {self.suffix}")
        return {'FINISHED'}


_classes = (
    MMY_OT_SmartDuplicateCollection,
    MMY_OT_SmartDuplicateObject,
    MMY_OT_BatchRename,
    MMY_OT_RenameSingle,
    MMY_OT_AddPrefixPreset,
    MMY_OT_RemovePrefixPreset,
    MMY_OT_AddSuffixPreset,
    MMY_OT_RemoveSuffixPreset,
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