import bpy


class VIEW3D_PT_MMYMeshTools(bpy.types.Panel):
    """MMY网格工具面板"""
    bl_label = "MMY工具"
    bl_idname = "VIEW3D_PT_MMY_mesh_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMY工具"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        mode = obj.mode if obj else 'OBJECT'

        # 对象模式：导入工具
        if mode == 'OBJECT':
            box = layout.box()
            box.label(text="导入工具")
            row = box.row(align=True)
            row.operator("mmy.import_fbx", text="导入FBX")
            row.prop(context.scene, "mmy_import_anim", text="动画")
            row.prop(context.scene, "mmy_reuse_materials", text="引用已有材质")

            # Better FBX按钮
            has_better_fbx = hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx')
            if has_better_fbx:
                row2 = box.row()
                row2.operator("mmy.better_import_fbx", text="Better Import FBX")

            # 资产创建工具
            try:
                self._draw_asset_creator(layout, context)
            except Exception as e:
                # 如果出错，显示简单提示
                box2 = layout.box()
                box2.label(text="资产创建", icon='ASSET_MANAGER')
                box2.label(text=f"加载错误: {str(e)}", icon='ERROR')

        # 编辑模式：缝合边工具
        if mode == 'EDIT' and obj and obj.type == 'MESH':
            box = layout.box()
            box.label(text="缝合边工具")
            row = box.row()
            row.operator("mmy.mark_uv_island_seams")
            row.scale_y = 1.5

    def _draw_asset_creator(self, layout, context):
        """绘制资产创建区块"""
        # 安全检查属性是否存在
        if not hasattr(context.scene, 'mmy_asset_creator'):
            box = layout.box()
            box.label(text="资产创建", icon='ASSET_MANAGER')
            box.label(text="请刷新插件", icon='ERROR')
            return

        props = context.scene.mmy_asset_creator

        box = layout.box()
        box.label(text="资产创建", icon='ASSET_MANAGER')

        # === 路径设置 ===
        row = box.row(align=True)
        row.prop(props, "asset_path", text="")
        row.operator("mmy.select_asset_path", text="", icon='FILE_FOLDER')

        # 最近使用路径
        try:
            if len(props.recent_paths) > 0:
                col = box.column()
                col.label(text="最近:", icon='HISTORY')
                for item in props.recent_paths[:5]:
                    row = col.row(align=True)
                    op = row.operator("mmy.set_path_from_history", text=item.path, translate=False)
                    op.path = item.path
        except:
            pass

        # 收藏路径
        try:
            if len(props.favorite_paths) > 0:
                col = box.column()
                col.label(text="收藏:", icon='STAR')
                for item in props.favorite_paths:
                    row = col.row(align=True)
                    display_text = item.alias if item.alias else item.path
                    op = row.operator("mmy.set_path_from_history", text=display_text)
                    op.path = item.path
                    rm_op = row.operator("mmy.remove_favorite_path", text="", icon='X')
                    rm_op.path = item.path
        except:
            pass

        # 添加收藏按钮
        if props.asset_path:
            box.operator("mmy.add_favorite_path", text="收藏当前路径", icon='ADD')

        # === 资产信息 ===
        box.prop(props, "asset_name", text="名称")

        # === Catalog选择 ===
        row = box.row()
        row.prop(props, "catalog_enum", text="分类")

        # === 预览图选项 ===
        box.prop(props, "auto_preview", text="自动预览图")

        # === 保存选项 ===
        box.prop(props, "compress", text="压缩")

        # === 创建按钮 ===
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("mmy.create_asset", text="建立资产", icon='ASSET_MANAGER')

        # 显示选中对象数量
        selected_count = len(context.selected_objects)
        if selected_count > 0:
            layout.label(text=f"已选中 {selected_count} 个对象", icon='CHECKMARK')
        else:
            layout.label(text="请选择要转为资产的对象", icon='ERROR')


_classes = (
    VIEW3D_PT_MMYMeshTools,
)


def register():
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

    # 添加右键菜单项
    try:
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(_append_context_menu)
    except:
        pass


def unregister():
    # 移除右键菜单项
    try:
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(_append_context_menu)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


def _append_context_menu(self, context):
    """在编辑模式右键菜单中添加缝合边操作"""
    layout = self.layout
    obj = context.active_object
    if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
        layout.separator()
        layout.operator("mmy.mark_uv_island_seams", icon='MESH_DATA')