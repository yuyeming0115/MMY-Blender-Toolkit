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
                if coll.objects.get(obj.name):
                    coll.objects.link(new_obj)
                    break

            # 如果原对象在场景根集合
            if context.scene.collection.objects.get(obj.name):
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


class MMY_OT_CreateLODCollections(bpy.types.Operator):
    """创建 LOD 子集合"""
    bl_idname = "mmy.create_lod_collections"
    bl_label = "创建 LOD 子集合"
    bl_description = "为选中集合创建 _low 和 _high 子集合"
    bl_options = {'REGISTER', 'UNDO'}

    low_suffix: StringProperty(name="Low 后缀", default="_low")
    high_suffix: StringProperty(name="High 后缀", default="_high")

    def execute(self, context):
        # 获取选中的集合
        parent_coll = None

        # 尝试从大纲视图获取
        if context.area and context.area.type == 'OUTLINER':
            if context.collection:
                parent_coll = context.collection

        # 备用：从场景集合层级查找
        if not parent_coll:
            active_coll = context.collection
            if active_coll and active_coll.name != "Scene Collection":
                parent_coll = active_coll

        if not parent_coll:
            self.report({'WARNING'}, "请先选中一个集合")
            return {'CANCELLED'}

        # 创建 _low 子集合
        low_name = f"{parent_coll.name}{self.low_suffix}"
        low_coll = bpy.data.collections.new(low_name)
        parent_coll.children.link(low_coll)

        # 创建 _high 子集合
        high_name = f"{parent_coll.name}{self.high_suffix}"
        high_coll = bpy.data.collections.new(high_name)
        parent_coll.children.link(high_coll)

        self.report({'INFO'}, f"已创建: {low_name}, {high_name}")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        # 在大纲视图或3D视图中可用
        return context.area and (context.area.type in ('OUTLINER', 'VIEW_3D'))


class MMY_OT_GroupSelectedObjects(bpy.types.Operator):
    """将选中对象归组到新集合"""
    bl_idname = "mmy.group_selected_objects"
    bl_label = "归组到新集合"
    bl_description = "创建新集合并将选中对象放入"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: StringProperty(name="集合名称", default="NewGroup")

    def invoke(self, context, event):
        # 预填充建议名称
        if context.active_object:
            self.collection_name = context.active_object.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "collection_name")

    def execute(self, context):
        selected_objs = context.selected_objects

        if not selected_objs:
            self.report({'WARNING'}, "请先选中对象")
            return {'CANCELLED'}

        if not self.collection_name:
            self.report({'WARNING'}, "请输入集合名称")
            return {'CANCELLED'}

        # 获取当前激活的集合（作为父集合）
        parent_coll = context.collection
        if not parent_coll or parent_coll.name == "Scene Collection":
            # 使用场景根集合
            parent_coll = context.scene.collection

        # 创建新集合
        new_coll = bpy.data.collections.new(self.collection_name)

        # 检查名称冲突，自动添加后缀
        if parent_coll.children.get(new_coll.name):
            new_coll.name = f"{self.collection_name}.001"

        # 将新集合链接到父集合
        parent_coll.children.link(new_coll)

        # 将选中对象移动到新集合
        moved_count = 0
        for obj in selected_objs:
            # 从原有集合中取消链接
            for coll in bpy.data.collections:
                if coll.objects.get(obj.name):
                    coll.objects.unlink(obj)
                    break

            # 从场景根集合取消链接
            if context.scene.collection.objects.get(obj.name):
                context.scene.collection.objects.unlink(obj)

            # 链接到新集合
            new_coll.objects.link(obj)
            moved_count += 1

        self.report({'INFO'}, f"已创建集合 '{new_coll.name}'，移入 {moved_count} 个对象")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects


class MMY_OT_GenerateCollectionTemplate(bpy.types.Operator):
    """应用模板生成集合架构"""
    bl_idname = "mmy.generate_collection_template"
    bl_label = "生成集合架构"
    bl_description = "根据模板创建集合层级结构"
    bl_options = {'REGISTER', 'UNDO'}

    template_name: StringProperty(name="模板名称", default="")

    def execute(self, context):
        from .collection_templates import get_template, set_recent_template

        if not self.template_name:
            self.report({'WARNING'}, "请选择模板")
            return {'CANCELLED'}

        template = get_template(self.template_name)
        root_name = template.get("root_name", "Assets")
        children = template.get("children", [])
        auto_lod = template.get("auto_lod", False)
        lod_suffixes = template.get("lod_suffixes", ["_high", "_low"])

        # 创建根集合
        root_coll = bpy.data.collections.new(root_name)
        context.scene.collection.children.link(root_coll)

        # 创建子集合
        created_count = 1
        for child_name in children:
            child_coll = bpy.data.collections.new(child_name)
            root_coll.children.link(child_coll)
            created_count += 1

            # 自动创建 LOD 子集合
            if auto_lod:
                for suffix in lod_suffixes:
                    lod_coll = bpy.data.collections.new(f"{child_name}{suffix}")
                    child_coll.children.link(lod_coll)
                    created_count += 1

        # 记录最近使用的模板
        set_recent_template(self.template_name)

        self.report({'INFO'}, f"已创建 {created_count} 个集合")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return True


class MMY_OT_QuickGenerateCollections(bpy.types.Operator):
    """快速生成集合架构"""
    bl_idname = "mmy.quick_generate_collections"
    bl_label = "快速生成集合"
    bl_description = "自定义输入快速创建集合层级"
    bl_options = {'REGISTER', 'UNDO'}

    root_name: StringProperty(name="父集合名称", default="Assets")
    children_names: StringProperty(name="子集合列表", default="Char,Prop,Set", description="用逗号分隔多个名称")
    auto_lod: BoolProperty(name="自动创建高低模容器", default=True)
    batch_mode: BoolProperty(name="批量模式", default=False, description="子集合名作为资产名，批量生成完整结构")
    batch_assets: StringProperty(name="批量资产名", default="Hero,Enemy,Boss", description="用逗号分隔多个资产名")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "root_name")
        layout.prop(self, "children_names")

        row = layout.row()
        row.prop(self, "auto_lod")

        layout.separator()

        row = layout.row()
        row.prop(self, "batch_mode")
        if self.batch_mode:
            layout.prop(self, "batch_assets")

    def execute(self, context):
        # 解析名称列表
        children = [n.strip() for n in self.children_names.split(",") if n.strip()]

        if not children:
            self.report({'WARNING'}, "请输入子集合名称")
            return {'CANCELLED'}

        lod_suffixes = ["_high", "_low"]
        created_count = 0

        if self.batch_mode:
            # 批量模式：每个资产名生成完整结构
            batch_assets = [n.strip() for n in self.batch_assets.split(",") if n.strip()]
            if not batch_assets:
                self.report({'WARNING'}, "请输入批量资产名")
                return {'CANCELLED'}

            # 创建根集合
            root_coll = bpy.data.collections.new(self.root_name)
            context.scene.collection.children.link(root_coll)
            created_count += 1

            # 每个资产创建完整结构
            for asset_name in batch_assets:
                asset_coll = bpy.data.collections.new(asset_name)
                root_coll.children.link(asset_coll)
                created_count += 1

                if self.auto_lod:
                    for suffix in lod_suffixes:
                        lod_coll = bpy.data.collections.new(f"{asset_name}{suffix}")
                        asset_coll.children.link(lod_coll)
                        created_count += 1
        else:
            # 普通模式：创建标准层级
            root_coll = bpy.data.collections.new(self.root_name)
            context.scene.collection.children.link(root_coll)
            created_count += 1

            for child_name in children:
                child_coll = bpy.data.collections.new(child_name)
                root_coll.children.link(child_coll)
                created_count += 1

                if self.auto_lod:
                    for suffix in lod_suffixes:
                        lod_coll = bpy.data.collections.new(f"{child_name}{suffix}")
                        child_coll.children.link(lod_coll)
                        created_count += 1

        self.report({'INFO'}, f"已创建 {created_count} 个集合")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return True


_classes = (
    MMY_OT_SmartDuplicateCollection,
    MMY_OT_SmartDuplicateObject,
    MMY_OT_BatchRename,
    MMY_OT_RenameSingle,
    MMY_OT_AddPrefixPreset,
    MMY_OT_RemovePrefixPreset,
    MMY_OT_AddSuffixPreset,
    MMY_OT_RemoveSuffixPreset,
    MMY_OT_CreateLODCollections,
    MMY_OT_GroupSelectedObjects,
    MMY_OT_GenerateCollectionTemplate,
    MMY_OT_QuickGenerateCollections,
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