# 修改器工具操作符

import bpy


class MMY_OT_HideAllModifiers(bpy.types.Operator):
    """隐藏所有修改器并记住显隐状态（支持多选）"""
    bl_idname = "mmy.hide_all_modifiers"
    bl_label = "隐藏所有修改器"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中对象且有修改器
        for obj in context.selected_objects:
            if obj.modifiers and len(obj.modifiers) > 0:
                return True
        return False

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}

        count = 0
        for obj in objects:
            if not obj.modifiers:
                continue

            # 保存当前状态
            state = {}
            for mod in obj.modifiers:
                state[mod.name] = mod.show_viewport
                mod.show_viewport = False

            obj["mmy_modifier_visibility"] = str(state)
            count += 1

        self.report({'INFO'}, f"已隐藏 {count} 个对象的修改器")
        return {'FINISHED'}


class MMY_OT_RestoreModifierVisibility(bpy.types.Operator):
    """恢复修改器显隐状态（支持多选）"""
    bl_idname = "mmy.restore_modifier_visibility"
    bl_label = "恢复修改器显隐"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中对象有保存的状态
        for obj in context.selected_objects:
            if "mmy_modifier_visibility" in obj:
                return True
        return False

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}

        count = 0
        for obj in objects:
            if "mmy_modifier_visibility" not in obj:
                continue

            try:
                import ast
                state = ast.literal_eval(obj["mmy_modifier_visibility"])
                for mod in obj.modifiers:
                    if mod.name in state:
                        mod.show_viewport = state[mod.name]
                del obj["mmy_modifier_visibility"]
                count += 1
            except:
                continue

        self.report({'INFO'}, f"已恢复 {count} 个对象的修改器显隐状态")
        return {'FINISHED'}


class MMY_OT_DeleteAllModifiers(bpy.types.Operator):
    """删除所有修改器（支持多选）"""
    bl_idname = "mmy.delete_all_modifiers"
    bl_label = "删除所有修改器"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中对象且有修改器
        for obj in context.selected_objects:
            if obj.modifiers and len(obj.modifiers) > 0:
                return True
        return False

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}

        total_count = 0
        obj_count = 0
        for obj in objects:
            if not obj.modifiers:
                continue

            mod_count = len(obj.modifiers)
            while obj.modifiers:
                obj.modifiers.remove(obj.modifiers[0])

            # 清除保存的显隐状态
            if "mmy_modifier_visibility" in obj:
                del obj["mmy_modifier_visibility"]

            total_count += mod_count
            obj_count += 1

        self.report({'INFO'}, f"已删除 {obj_count} 个对象的 {total_count} 个修改器")
        return {'FINISHED'}


class MMY_OT_ExpandAllModifiers(bpy.types.Operator):
    """展开所有修改器面板（支持多选）"""
    bl_idname = "mmy.expand_all_modifiers"
    bl_label = "展开所有修改器"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中对象且有修改器
        for obj in context.selected_objects:
            if obj.modifiers and len(obj.modifiers) > 0:
                return True
        return False

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}

        count = 0
        for obj in objects:
            if not obj.modifiers:
                continue

            for mod in obj.modifiers:
                mod.show_expanded = True
            count += 1

        self.report({'INFO'}, f"已展开 {count} 个对象的修改器")
        return {'FINISHED'}


class MMY_OT_CollapseAllModifiers(bpy.types.Operator):
    """折叠所有修改器面板（支持多选）"""
    bl_idname = "mmy.collapse_all_modifiers"
    bl_label = "折叠所有修改器"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # 至少有一个选中对象且有修改器
        for obj in context.selected_objects:
            if obj.modifiers and len(obj.modifiers) > 0:
                return True
        return False

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}

        count = 0
        for obj in objects:
            if not obj.modifiers:
                continue

            for mod in obj.modifiers:
                mod.show_expanded = False
            count += 1

        self.report({'INFO'}, f"已折叠 {count} 个对象的修改器")
        return {'FINISHED'}


class MMY_OT_AddGeometryNodesAsset(bpy.types.Operator):
    """从资产库添加几何节点修改器"""
    bl_idname = "mmy.add_geometry_nodes_asset"
    bl_label = "添加几何节点资产"
    bl_options = {'REGISTER', 'UNDO'}

    asset_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        # 从偏好设置获取资产库路径
        addon = bpy.context.preferences.addons.get("mmy_toolkit")
        asset_path = ""
        if addon and addon.preferences:
            asset_path = getattr(addon.preferences, "geometry_nodes_asset_path", "")

        if not asset_path:
            self.report({'ERROR'}, "未配置几何节点资产库路径")
            return {'CANCELLED'}

        # Append node group from asset library
        try:
            with bpy.data.libraries.load(asset_path, link=False) as (data_from, data_to):
                if self.asset_name in data_from.node_groups:
                    data_to.node_groups.append(self.asset_name)
                else:
                    self.report({'ERROR'}, f"资产 '{self.asset_name}' 不存在")
                    return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载资产库失败: {e}")
            return {'CANCELLED'}

        # Get the node group
        node_group = bpy.data.node_groups.get(self.asset_name)
        if not node_group:
            self.report({'ERROR'}, "节点组导入失败")
            return {'CANCELLED'}

        # Add Geometry Nodes modifier
        obj = context.active_object
        mod = obj.modifiers.new(name=self.asset_name, type='NODES')
        mod.node_group = node_group

        self.report({'INFO'}, f"已添加几何节点修改器: {self.asset_name}")
        return {'FINISHED'}


_classes = (
    MMY_OT_HideAllModifiers,
    MMY_OT_RestoreModifierVisibility,
    MMY_OT_DeleteAllModifiers,
    MMY_OT_ExpandAllModifiers,
    MMY_OT_CollapseAllModifiers,
    MMY_OT_AddGeometryNodesAsset,
)