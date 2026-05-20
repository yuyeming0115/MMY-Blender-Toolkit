import bpy


class MMY_UL_PreviewFileList(bpy.types.UIList):
    """刷新预览图文件列表（带勾选框）"""
    bl_idname = "MMY_UL_preview_file_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        props = context.scene.mmy_asset_creator

        # 检查是否被排除
        is_excluded = item.filename in props.excluded_files

        row = layout.row(align=True)
        row.prop(item, "is_selected", text="")

        if is_excluded:
            row.label(text=item.filename, icon='CANCEL')
            row.label(text="已排除")
        elif item.has_preview:
            row.label(text=item.filename, icon='FILE_BLEND')
            row.label(text="✓")
        else:
            row.alert = True
            row.label(text=item.filename, icon='FILE_BLEND')
            row.alert = False


class MMY_MT_FavoritePathMenu(bpy.types.Menu):
    """收藏路径下拉菜单"""
    bl_idname = "MMY_MT_favorite_path_menu"
    bl_label = "收藏路径"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mmy_asset_creator
        if not hasattr(context.scene, 'mmy_asset_creator'):
            return
        try:
            if len(props.favorite_paths) == 0:
                layout.label(text="暂无收藏路径")
                layout.label(text="点击 + 添加")
                return
            for item in props.favorite_paths:
                display_text = item.alias if item.alias else item.path
                op = layout.operator("mmy.set_path_from_history", text=display_text)
                op.path = item.path
        except:
            layout.label(text="加载失败")


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

        # 对象模式：导入工具 + 资产创建
        if mode == 'OBJECT':
            # 导入工具
            box = layout.box()
            box.label(text="导入工具", icon='IMPORT')
            row = box.row(align=True)
            row.operator("mmy.import_fbx", text="导入FBX")
            row.prop(context.scene, "mmy_import_anim", text="动画")
            # 第二行：材质引用 + 清零变换
            row2 = box.row(align=True)
            row2.prop(context.scene, "mmy_reuse_materials", text="引用材质")
            row2.prop(context.scene, "mmy_clear_transforms", text="清零变换")

            # Better FBX按钮
            has_better_fbx = hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx')
            if has_better_fbx:
                row2 = box.row()
                row2.operator("mmy.better_import_fbx", text="Better Import FBX")

            # 查找缺失文件
            box.operator("file.find_missing_files", text="查找缺失文件", icon='FILE_REFRESH')

            # 资产创建工具
            try:
                self._draw_asset_creator(layout, context)
            except Exception as e:
                # 如果出错，显示简单提示
                box2 = layout.box()
                box2.label(text="资产创建", icon='ASSET_MANAGER')
                box2.label(text=f"加载错误: {str(e)}", icon='ERROR')

        # 编辑模式：缝合边工具 + 拆出工具
        if mode == 'EDIT' and obj and obj.type == 'MESH':
            box = layout.box()
            box.label(text="缝合边工具", icon='SNAP_EDGE')
            row = box.row()
            row.operator("mmy.mark_uv_island_seams")
            row.scale_y = 1.5

            # 拆出工具
            box = layout.box()
            box.label(text="拆出工具", icon='MESH_DATA')
            row = box.row(align=True)
            row.operator("mmy.detach_selection", text="拆出")
            row.operator("mmy.duplicate_detach", text="复制拆出")
            row.scale_y = 1.5
            row = box.row(align=True)
            row.operator("mmy.separate_by_material", text="按材质拆")
            row.operator("mmy.separate_by_loose", text="按松散块拆")
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
        # asset_path 的 subtype="DIR_PATH" 会自动显示文件夹按钮
        row = box.row(align=True)
        row.prop(props, "asset_path", text="")
        # ➕ 快速收藏按钮（在文件夹按钮后、书签按钮前）
        row.operator("mmy.add_favorite_path", text="", icon='ADD')
        # 🔖 收藏路径菜单
        row.menu("MMY_MT_favorite_path_menu", text="", icon='BOOKMARKS')

        # === 资产信息：名称 + 分类（一行）===
        row = box.row(align=True)
        row.prop(props, "asset_name", text="名称")
        row.prop(props, "catalog_enum", text="分类")

        # === 预览图 + 压缩选项（一行）===
        row = box.row(align=True)
        row.prop(props, "auto_preview", text="自动缩略图")
        row.prop(props, "compress", text="压缩")

        # === 创建按钮 ===
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("mmy.create_asset", text="建立资产", icon='ASSET_MANAGER')

        # === 批量刷新预览图 ===
        if props.asset_path:
            layout.separator(factor=0.5)
            box = layout.box()
            box.label(text="刷新预览图", icon='FILE_REFRESH')

            # 扫描按钮
            row = box.row(align=True)
            row.operator("mmy.scan_preview_files", text="扫描目录", icon='VIEWZOOM')
            if len(props.refresh_preview_files) > 0:
                row.operator("mmy.clear_preview_list", text="清空", icon='X')

            # 文件列表（可滚动，默认显示10行）
            if len(props.refresh_preview_files) > 0:
                # 快捷选择按钮
                row = box.row(align=True)
                row.operator("mmy.select_all_preview_files", text="全选", icon='CHECKMARK')
                row.operator("mmy.select_with_preview", text="有预览", icon='FILE_IMAGE')
                row.operator("mmy.select_none_preview", text="无预览", icon='ERROR')
                row.operator("mmy.manage_excluded_files", text="排除", icon='CANCEL')

                # 使用 template_list 显示可滚动列表
                box.template_list(
                    "MMY_UL_preview_file_list", "",
                    props, "refresh_preview_files",
                    props, "refresh_preview_index",
                    rows=10
                )

                # 统计选中数量（排除已排除的文件）
                selected_with_preview = sum(
                    1 for item in props.refresh_preview_files
                    if item.is_selected and item.has_preview
                    and item.filename not in props.excluded_files
                )

                # 刷新按钮
                row = box.row()
                row.scale_y = 1.2
                if selected_with_preview > 0:
                    row.operator("mmy.refresh_selected_previews",
                                 text=f"刷新选中 ({selected_with_preview})", icon='PLAY')
                else:
                    row.label(text="请选中有预览图的文件", icon='ERROR')

        # 显示选中对象数量
        selected_count = len(context.selected_objects)
        if selected_count > 0:
            layout.label(text=f"已选中 {selected_count} 个对象", icon='CHECKMARK')
        else:
            layout.label(text="请选择要转为资产的对象", icon='ERROR')

        # 材质替换区块
        try:
            self._draw_mat_replacer(layout, context)
        except Exception as e:
            box3 = layout.box()
            box3.label(text="材质替换", icon='MATERIAL')
            box3.label(text=f"加载错误: {str(e)}", icon='ERROR')

        # 动画关联区块
        try:
            self._draw_anim_linker(layout, context)
        except Exception as e:
            box4 = layout.box()
            box4.label(text="关联动画", icon='ANIM_DATA')
            box4.label(text=f"加载错误: {str(e)}", icon='ERROR')

        # 骨骼缩放控制区块
        try:
            self._draw_armature_scale(layout, context)
        except Exception as e:
            box5 = layout.box()
            box5.label(text="骨骼缩放", icon='ARMATURE_DATA')
            box5.label(text=f"加载错误: {str(e)}", icon='ERROR')

    def _draw_armature_scale(self, layout, context):
        """绘制骨骼缩放控制区块"""
        if not hasattr(context.scene, 'mmy_mat_replacer'):
            return

        props = context.scene.mmy_mat_replacer

        layout.separator()
        box = layout.box()
        box.label(text="骨骼缩放", icon='ARMATURE_DATA')

        # 选择目标骨骼 + 创建约束 + 启用开关
        row = box.row(align=True)
        row.prop(props, "target_armature_enum", text="骨骼")

        # 创建约束按钮
        if props.target_armature_enum != "none":
            row.operator("mmy.create_scale_constraint", text="创建约束", icon='CONSTRAINT')

            # 如果约束已存在，显示启用开关
            armature_name = props.target_armature_enum
            if armature_name != "none":
                # 解码骨骼名
                from ..mat_replacer.properties import decode_armature_id
                real_name = decode_armature_id(armature_name)
                armature = bpy.data.objects.get(real_name) if real_name else None
                if armature:
                    has_constraint = any(c.name == "MMY_Copy_Scale" for c in armature.constraints)
                    if has_constraint:
                        row.prop(props, "constraint_enabled", text="", icon='CHECKMARK' if props.constraint_enabled else 'X')

        # 缩放控制（如果Scale物体存在）
        scale_obj = bpy.data.objects.get("Scale")
        if scale_obj:
            layout.separator(factor=0.3)
            row = box.row(align=True)
            row.prop(props, "scale_value", text="缩放", slider=True)
            row.label(text=f"({scale_obj.scale.x:.2f})")

            # 偏移选项
            row = box.row(align=True)
            row.prop(props, "use_offset", text="偏移")
            row.label(text="叠加原有缩放", icon='INFO')

    def _draw_anim_linker(self, layout, context):
        """绘制动画关联区块"""
        if not hasattr(context.scene, 'mmy_mat_replacer'):
            return

        props = context.scene.mmy_mat_replacer

        layout.separator()
        box = layout.box()
        box.label(text="关联动画", icon='ANIM_DATA')

        # 选择动画文件
        row = box.row(align=True)
        row.operator("mmy.select_anim_file", text="选择动画文件", icon='FILE_FOLDER')

        if props.anim_file:
            import os
            filename = os.path.basename(props.anim_file)
            row.label(text=filename)

            # 显示状态和关联按钮
            if props.has_ani_collection:
                row = box.row(align=True)
                row.operator("mmy.link_animation", text="关联 Ani 集合", icon='LINK_BLEND')
                row.label(text="✓ 找到 Ani", icon='CHECKMARK')
            else:
                box.label(text="文件中未找到 Ani 集合", icon='ERROR')

    def _draw_mat_replacer(self, layout, context):
        """绘制材质替换区块"""
        if not hasattr(context.scene, 'mmy_mat_replacer'):
            return

        props = context.scene.mmy_mat_replacer

        layout.separator()
        box = layout.box()
        box.label(text="材质替换", icon='MATERIAL')

        # Step 1: 选择外部文件
        row = box.row(align=True)
        row.operator("mmy.select_external_file", text="选择外部文件", icon='FILE_FOLDER')
        if props.external_file:
            import os
            filename = os.path.basename(props.external_file)
            row.label(text=filename)

        # Step 2: Link按钮 + 替换按钮（同一行）
        if len(props.external_materials) > 0:
            row = box.row(align=True)
            row.operator("mmy.link_materials", text="Link并生成映射", icon='LINK_BLEND')
            if len(props.mappings) > 0:
                row.operator("mmy.execute_replace", text="替换", icon='PLAY')
            row.operator("mmy.clear_all", text="清除", icon='X')

        # 双列布局：外部材质勾选 + 映射列表
        if len(props.external_materials) > 0:
            split = box.split(factor=0.35)

            # 左列：外部材质勾选
            left = split.column()
            left.label(text="外部材质:", icon='LINKED')
            for item in props.external_materials:
                row = left.row(align=True)
                row.prop(item, "is_selected", text="")
                short = item.name[:18] + ".." if len(item.name) > 18 else item.name
                row.label(text=short)

            # 右列：映射列表
            right = split.column()
            right.label(text="映射:", icon='MATERIAL')

            if len(props.mappings) > 0:
                for mapping in props.mappings:
                    row = right.row(align=True)
                    src_short = mapping.source_mat_name[:12] + ".." if len(mapping.source_mat_name) > 12 else mapping.source_mat_name
                    row.label(text=src_short)
                    row.prop(mapping, "target_mat_id", text="")


_classes = (
    MMY_UL_PreviewFileList,
    MMY_MT_FavoritePathMenu,
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
