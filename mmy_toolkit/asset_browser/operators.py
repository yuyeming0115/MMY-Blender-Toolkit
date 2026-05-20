import bpy
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, EnumProperty

from ..config import (
    add_recent_asset_path,
    add_favorite_path,
    remove_favorite_path,
    get_recent_asset_paths,
    get_favorite_paths,
)
from ..asset_browser.properties import _unsafe_enum_id, MMY_RefreshPreviewFileItem


class MMY_OT_CreateAsset(bpy.types.Operator):
    """创建资产文件"""
    bl_idname = "mmy.create_asset"
    bl_label = "建立资产"
    bl_options = {'REGISTER'}

    # 用于记录原文件路径（返回时使用）
    original_filepath = ""

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        # 1. 验证输入
        asset_path = props.asset_path
        asset_name = props.asset_name

        if not asset_path:
            self.report({'ERROR'}, "请设置资产路径")
            return {'CANCELLED'}

        if not asset_name:
            self.report({'ERROR'}, "请输入资产名称")
            return {'CANCELLED'}

        if not os.path.exists(asset_path):
            self.report({'ERROR'}, f"路径不存在: {asset_path}")
            return {'CANCELLED'}

        # 2. 获取选中对象
        selected_objects = list(context.selected_objects)
        if not selected_objects:
            self.report({'ERROR'}, "请选择要转为资产的对象")
            return {'CANCELLED'}

        # 记录原始文件路径
        original_filepath = bpy.data.filepath

        # 获取catalog设置（解码 safe_enum_id 还原真实 UUID）
        catalog_id = _unsafe_enum_id(props.catalog_enum)

        # 3. 先保存当前文件（如果有修改且已保存过）
        if original_filepath and os.path.exists(original_filepath):
            if bpy.data.is_dirty:
                bpy.ops.wm.save_mainfile()

        try:
            # 4. 先在原文件中打包所有外部数据（贴图、材质节点图片等）
            # 这样导出时贴图已经嵌入blend文件，新文件会自动携带贴图
            print("[MMY] 正在打包原文件的外部数据...")
            try:
                bpy.ops.file.pack_all()
                print("[MMY] 原文件外部数据打包完成")
            except Exception as e:
                print(f"[MMY] 打包外部数据出错（部分贴图可能未找到）: {e}")

            # 5. 收集需要导出的数据块
            # 先保存对象名称（打开新文件后原引用会失效）
            exported_obj_names = [obj.name for obj in selected_objects]

            # 在 open_mainfile 之前保存需要的属性值（之后 scene 会被替换）
            auto_preview = props.auto_preview
            compress = props.compress

            datablocks = set()

            for obj in selected_objects:
                datablocks.add(obj)
                if obj.data:
                    datablocks.add(obj.data)
                # 收集材质
                if hasattr(obj, 'material_slots'):
                    for slot in obj.material_slots:
                        if slot.material:
                            datablocks.add(slot.material)

            # 导出到新文件
            filepath = os.path.join(asset_path, f"{asset_name}.blend")
            bpy.data.libraries.write(filepath, datablocks)

            print(f"[MMY] 数据已导出到: {filepath}")
            print(f"[MMY] 导出的数据块数量: {len(datablocks)}")

            # 6. 打开新文件并设置资产属性
            bpy.ops.wm.open_mainfile(filepath=filepath)

            # 启用自动打包（确保后续新增的外部资源也会自动打包）
            # Blender 5.x API 可能变化，失败不影响主流程
            try:
                # Blender 4.x 及之前版本
                bpy.data.use_auto_pack = True
            except AttributeError:
                try:
                    # 尝试 Blender 5.x 的新 API
                    if hasattr(bpy.context.preferences.filepaths, 'use_file_auto_pack'):
                        bpy.context.preferences.filepaths.use_file_auto_pack = True
                except Exception:
                    pass
            print("[MMY] 已启用自动打包")

            # 7. 创建资产集合
            asset_collection = bpy.data.collections.new(asset_name)
            bpy.context.scene.collection.children.link(asset_collection)

            # 8. 将所有导出的对象链接到资产集合
            # 注意：不从 scene 中移除对象，否则对象会因无 scene 引用而被 Blender
            # 视为未使用数据块，保存后再次打开时文件内容为空
            for obj_name in exported_obj_names:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    asset_collection.objects.link(obj)

            # 9. 标记集合为资产
            asset_collection.asset_mark()
            if catalog_id:
                asset_collection.asset_data.catalog_id = catalog_id
                print(f"[MMY] Catalog ID 设置为: {catalog_id}")

            # 10. 查找并设置预览图
            if auto_preview:
                preview_path = None
                for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                    test_path = os.path.join(asset_path, f"{asset_name}{ext}")
                    if os.path.exists(test_path):
                        preview_path = test_path
                        break

                if preview_path:
                    self._set_preview(preview_path, asset_collection)

            # 11. 保存文件
            bpy.ops.wm.save_mainfile(filepath=filepath, compress=compress)
            print("[MMY] 资产文件已保存")

            # 12. 记录最近路径
            add_recent_asset_path(asset_path)

            # 13. 返回原文件
            if original_filepath and os.path.exists(original_filepath):
                bpy.ops.wm.open_mainfile(filepath=original_filepath)
            else:
                bpy.ops.wm.read_homefile()

            self.report({'INFO'}, f"资产已创建: {filepath}")

        except Exception as e:
            import traceback
            print(f"[MMY] 错误详情:\n{traceback.format_exc()}")
            self.report({'ERROR'}, f"创建失败: {str(e)}")

            # 尝试返回原文件
            if original_filepath and os.path.exists(original_filepath):
                try:
                    bpy.ops.wm.open_mainfile(filepath=original_filepath)
                except:
                    pass

            return {'CANCELLED'}

        return {'FINISHED'}

    def _set_preview(self, preview_path, collection):
        """设置资产预览图"""
        if self._set_preview_correct(collection, preview_path):
            print(f"[MMY] 预览图设置成功: {preview_path}")
        else:
            print(f"[MMY] 预览图需手动设置: {preview_path}")

    def _sync_favorites_to_props(self, context):
        """同步收藏路径到场景属性"""
        props = context.scene.mmy_asset_creator

        # 清空现有收藏
        props.favorite_paths.clear()

        # 从配置文件加载
        favorites = get_favorite_paths()
        for fav in favorites:
            item = props.favorite_paths.add()
            item.path = fav.get("path", "")
            item.alias = fav.get("alias", "")


class MMY_OT_SelectAssetPath(bpy.types.Operator, ExportHelper):
    """选择资产保存路径"""
    bl_idname = "mmy.select_asset_path"
    bl_label = "选择路径"

    filename_ext = ""

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        # 获取目录路径
        directory = os.path.dirname(self.filepath)
        props.asset_path = directory
        return {'FINISHED'}


class MMY_OT_AddFavoritePath(bpy.types.Operator):
    """添加当前路径到收藏夹"""
    bl_idname = "mmy.add_favorite_path"
    bl_label = "收藏当前路径"

    alias: bpy.props.StringProperty(name="别名", default="")

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        if not props.asset_path:
            self.report({'WARNING'}, "请先选择路径")
            return {'CANCELLED'}

        # 自动使用路径名作为别名
        alias = self.alias or os.path.basename(props.asset_path) or props.asset_path

        if add_favorite_path(props.asset_path, alias):
            # 同步到场景属性
            props.favorite_paths.clear()
            favorites = get_favorite_paths()
            for fav in favorites:
                item = props.favorite_paths.add()
                item.path = fav.get("path", "")
                item.alias = fav.get("alias", "")

            self.report({'INFO'}, f"已收藏: {alias}")
        else:
            self.report({'WARNING'}, "该路径已在收藏夹中")

        return {'FINISHED'}


class MMY_OT_RemoveFavoritePath(bpy.types.Operator):
    """从收藏夹移除路径"""
    bl_idname = "mmy.remove_favorite_path"
    bl_label = "移除收藏"

    path: bpy.props.StringProperty()

    def execute(self, context):
        remove_favorite_path(self.path)

        # 同步到场景属性
        props = context.scene.mmy_asset_creator
        props.favorite_paths.clear()
        favorites = get_favorite_paths()
        for fav in favorites:
            item = props.favorite_paths.add()
            item.path = fav.get("path", "")
            item.alias = fav.get("alias", "")

        self.report({'INFO'}, "已移除收藏")
        return {'FINISHED'}


class MMY_OT_SetPathFromHistory(bpy.types.Operator):
    """从历史设置路径"""
    bl_idname = "mmy.set_path_from_history"
    bl_label = "设置路径"

    path: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        props.asset_path = self.path
        return {'FINISHED'}


class MMY_OT_RefreshAllPreviews(bpy.types.Operator):
    """批量刷新目录下所有资产的预览图"""
    bl_idname = "mmy.refresh_all_previews"
    bl_label = "批量刷新预览图"
    bl_options = {'REGISTER'}

    # 用于 timer 链式执行的状态
    _blend_files = []
    _preview_paths = {}
    _target_dir = ""
    _original_filepath = ""
    _current_index = 0
    _success_count = 0
    _skip_count = 0
    _fail_count = 0
    _error_details = []

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_asset_creator
        return bool(props.asset_path)

    def invoke(self, context, event):
        props = context.scene.mmy_asset_creator
        return context.window_manager.invoke_confirm(
            self,
            event,
            title="批量刷新预览图",
            message=f"将刷新目录 {props.asset_path} 下所有资产的预览图，确认继续？"
        )

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        target_dir = props.asset_path

        if not os.path.exists(target_dir):
            self.report({'ERROR'}, f"目录不存在: {target_dir}")
            return {'CANCELLED'}

        # 收集所有 .blend 文件及其预览图路径
        try:
            blend_files = [
                f for f in os.listdir(target_dir)
                if f.lower().endswith('.blend')
            ]
        except PermissionError:
            self.report({'ERROR'}, f"无法访问目录: {target_dir}")
            return {'CANCELLED'}

        if not blend_files:
            self.report({'WARNING'}, f"目录下没有 .blend 文件: {target_dir}")
            return {'CANCELLED'}

        # 初始化状态
        MMY_OT_RefreshAllPreviews._blend_files = blend_files
        MMY_OT_RefreshAllPreviews._preview_paths = {}
        MMY_OT_RefreshAllPreviews._target_dir = target_dir
        MMY_OT_RefreshAllPreviews._original_filepath = bpy.data.filepath
        MMY_OT_RefreshAllPreviews._current_index = 0
        MMY_OT_RefreshAllPreviews._success_count = 0
        MMY_OT_RefreshAllPreviews._skip_count = 0
        MMY_OT_RefreshAllPreviews._fail_count = 0
        MMY_OT_RefreshAllPreviews._error_details = []

        # 预先查找所有预览图
        for blend_name in blend_files:
            asset_name = os.path.splitext(blend_name)[0]
            preview_path = None
            for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                test_path = os.path.join(target_dir, f"{asset_name}{ext}")
                if os.path.exists(test_path):
                    preview_path = test_path
                    break
            MMY_OT_RefreshAllPreviews._preview_paths[blend_name] = preview_path

        # 启动第一个文件的处理
        self._process_next_file()

        return {'RUNNING_MODAL'}

    def _process_next_file(self):
        """处理下一个文件（打开并设置预览图，然后用 timer 延迟保存）"""
        cls = MMY_OT_RefreshAllPreviews

        if cls._current_index >= len(cls._blend_files):
            # 所有文件处理完毕，返回原文件并报告
            self._finish_processing()
            return

        blend_name = cls._blend_files[cls._current_index]
        blend_path = os.path.join(cls._target_dir, blend_name)
        preview_path = cls._preview_paths.get(blend_name)

        if not preview_path:
            cls._skip_count += 1
            print(f"[MMY] 跳过 {blend_name}: 未找到预览图")
            cls._current_index += 1
            self._process_next_file()
            return

        try:
            # 打开目标 .blend 文件
            bpy.ops.wm.open_mainfile(filepath=blend_path)

            # 刷新 UI
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
                window.screen.areas.update()

            # 查找被标记为资产的数据块
            asset_id = None
            for collection in bpy.data.collections:
                if collection.asset_data is not None:
                    asset_id = collection
                    break
            if asset_id is None:
                for obj in bpy.data.objects:
                    if obj.asset_data is not None:
                        asset_id = obj
                        break

            if asset_id is None:
                cls._skip_count += 1
                print(f"[MMY] 跳过 {blend_name}: 未找到已标记的资产")
                cls._current_index += 1
                self._process_next_file()
                return

            # 设置资产预览图
            if not self._set_preview_correct(asset_id, preview_path):
                cls._fail_count += 1
                cls._error_details.append(f"{blend_name}: 预览图设置失败")
                cls._current_index += 1
                self._process_next_file()
                return

            # 切换 3D 视窗到材质预览模式
            self._setup_viewport_for_preview()

            # 注册 timer，延迟保存（等待界面渲染）
            bpy.app.timers.register(
                self._delayed_save,
                first_interval=0.5  # 等待 0.5 秒让界面渲染
            )

        except Exception as e:
            import traceback
            cls._fail_count += 1
            cls._error_details.append(f"{blend_name}: {e}")
            print(f"[MMY] 处理失败 {blend_name}: {traceback.format_exc()}")
            cls._current_index += 1
            self._process_next_file()

    def _delayed_save(self):
        """timer 回调：保存当前文件并继续处理下一个"""
        cls = MMY_OT_RefreshAllPreviews

        blend_name = cls._blend_files[cls._current_index]
        blend_path = os.path.join(cls._target_dir, blend_name)

        try:
            # 保存文件（此时界面已渲染，文件预览图会正确生成）
            bpy.ops.wm.save_mainfile(filepath=blend_path)
            cls._success_count += 1
            print(f"[MMY] 已刷新: {blend_name}")
        except Exception as e:
            cls._fail_count += 1
            cls._error_details.append(f"{blend_name}: 保存失败 {e}")
            print(f"[MMY] 保存失败 {blend_name}: {e}")

        cls._current_index += 1

        # 继续处理下一个文件（等待额外时间让下一个文件加载）
        if cls._current_index < len(cls._blend_files):
            bpy.app.timers.register(
                self._process_next_file_wrapper,
                first_interval=0.2
            )
        else:
            self._finish_processing()

        return None  # timer 不再重复执行

    def _process_next_file_wrapper(self):
        """timer 包装器：处理下一个文件"""
        self._process_next_file()
        return None

    def _finish_processing(self):
        """完成所有处理，返回原文件并报告结果"""
        cls = MMY_OT_RefreshAllPreviews

        # 返回原文件
        original_filepath = cls._original_filepath
        if original_filepath and os.path.exists(original_filepath):
            bpy.ops.wm.open_mainfile(filepath=original_filepath)
        else:
            bpy.ops.wm.read_homefile()

        # 汇总报告
        msg = f"完成: {cls._success_count} 成功, {cls._skip_count} 跳过, {cls._fail_count} 失败"
        if cls._error_details:
            msg += " | " + "; ".join(cls._error_details[:3])  # 只显示前3个错误
        print(f"[MMY] {msg}")

        # 清理状态
        cls._blend_files = []
        cls._preview_paths = {}
        cls._current_index = 0

    def _setup_viewport_for_preview(self):
        """切换 3D 视窗到材质预览模式，全选模型并最大化显示"""
        try:
            # 先切换到对象模式
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
                print(f"[MMY] 已切换到对象模式")

            # 全选所有对象
            for obj in bpy.data.objects:
                if obj.visible_get():
                    obj.select_set(True)
            # 设置活动对象（确保有选中）
            visible_objs = [obj for obj in bpy.data.objects if obj.visible_get()]
            if visible_objs:
                bpy.context.view_layer.objects.active = visible_objs[0]
            print(f"[MMY] 已全选所有可见对象: {len(visible_objs)} 个")

            # 查找 3D 视窗
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        space = area.spaces.active
                        region = None
                        for r in area.regions:
                            if r.type == 'WINDOW':
                                region = r
                                break

                        # 切换到材质预览模式
                        if space and hasattr(space, 'shading'):
                            space.shading.type = 'MATERIAL'
                            print(f"[MMY] 已切换到材质预览模式")

                        if space and region:
                            # 使用正确的上下文执行操作
                            with bpy.context.temp_override(window=window, area=area, region=region, space_data=space):
                                # 框显所选对象
                                bpy.ops.view3d.view_selected()
                                print(f"[MMY] 已框显所选模型")

                                # 最大最大化 3D 视窗
                                bpy.ops.screen.screen_full_area(use_hide_panels=True)
                                print(f"[MMY] 已最大化 3D 视窗")

                        # 刷新渲染
                        for r in area.regions:
                            r.tag_redraw()
                        return

            print(f"[MMY] 未找到 3D 视窗")

        except Exception as e:
            print(f"[MMY] 切换视窗模式失败: {e}")
            import traceback
            print(traceback.format_exc())

    def _set_preview_correct(self, asset_id, preview_path):
        """使用正确的 API 设置资产预览图"""
        try:
            # 检查文件存在
            if not os.path.exists(preview_path):
                print(f"[MMY] 预览图文件不存在: {preview_path}")
                return False

            # 方法1: 使用 temp_override 并传入 id 参数
            try:
                with bpy.context.temp_override(id=asset_id):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=preview_path)
                print(f"[MMY] 预览图设置成功 (temp_override): {preview_path}")
                return True
            except Exception as e1:
                print(f"[MMY] temp_override 方式失败: {e1}")

            print(f"[MMY] 无法设置预览图")
            return False

        except Exception as e:
            print(f"[MMY] 设置预览图失败: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def _return_to_original(self, original_filepath):
        """返回到原始文件"""
        if original_filepath and os.path.exists(original_filepath):
            bpy.ops.wm.open_mainfile(filepath=original_filepath)
        else:
            bpy.ops.wm.read_homefile()


class MMY_OT_RefreshRecentPaths(bpy.types.Operator):
    """刷新最近使用路径"""
    bl_idname = "mmy.refresh_recent_paths"
    bl_label = "刷新历史"

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        # 清空现有历史
        props.recent_paths.clear()

        # 从配置文件加载
        recent = get_recent_asset_paths()
        for path in recent:
            item = props.recent_paths.add()
            item.path = path

        return {'FINISHED'}


class MMY_OT_ScanPreviewFiles(bpy.types.Operator):
    """扫描目录下的 .blend 文件"""
    bl_idname = "mmy.scan_preview_files"
    bl_label = "扫描目录"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_asset_creator
        return bool(props.asset_path)

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        target_dir = props.asset_path

        if not os.path.exists(target_dir):
            self.report({'ERROR'}, f"目录不存在: {target_dir}")
            return {'CANCELLED'}

        # 清空现有列表
        props.refresh_preview_files.clear()

        # 收集所有 .blend 文件
        try:
            blend_files = [
                f for f in os.listdir(target_dir)
                if f.lower().endswith('.blend')
            ]
        except PermissionError:
            self.report({'ERROR'}, f"无法访问目录: {target_dir}")
            return {'CANCELLED'}

        if not blend_files:
            self.report({'WARNING'}, f"目录下没有 .blend 文件")
            return {'CANCELLED'}

        # 添加到列表
        for blend_name in sorted(blend_files):
            asset_name = os.path.splitext(blend_name)[0]
            blend_path = os.path.join(target_dir, blend_name)

            # 查找预览图
            preview_path = None
            for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                test_path = os.path.join(target_dir, f"{asset_name}{ext}")
                if os.path.exists(test_path):
                    preview_path = test_path
                    break

            item = props.refresh_preview_files.add()
            item.filepath = blend_path
            item.filename = blend_name
            item.has_preview = preview_path is not None
            item.preview_path = preview_path or ""
            item.is_selected = True  # 默认选中

        self.report({'INFO'}, f"找到 {len(blend_files)} 个文件")
        return {'FINISHED'}


class MMY_OT_ClearPreviewList(bpy.types.Operator):
    """清空预览图文件列表"""
    bl_idname = "mmy.clear_preview_list"
    bl_label = "清空列表"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        props.refresh_preview_files.clear()
        return {'FINISHED'}


class MMY_OT_SelectAllPreviewFiles(bpy.types.Operator):
    """全选/取消全选"""
    bl_idname = "mmy.select_all_preview_files"
    bl_label = "全选"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        # 检查当前是否全部选中
        all_selected = all(item.is_selected for item in props.refresh_preview_files)

        # 切换：全选则取消，不全选则全选
        new_state = not all_selected
        for item in props.refresh_preview_files:
            item.is_selected = new_state

        return {'FINISHED'}


class MMY_OT_SelectWithPreview(bpy.types.Operator):
    """只选中有预览图的文件"""
    bl_idname = "mmy.select_with_preview"
    bl_label = "有预览"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        for item in props.refresh_preview_files:
            item.is_selected = item.has_preview
        return {'FINISHED'}


class MMY_OT_SelectNonePreview(bpy.types.Operator):
    """只选中无预览图的文件"""
    bl_idname = "mmy.select_none_preview"
    bl_label = "无预览"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.mmy_asset_creator
        for item in props.refresh_preview_files:
            item.is_selected = not item.has_preview
        return {'FINISHED'}


class MMY_OT_ManageExcludedFiles(bpy.types.Operator):
    """管理排除文件列表"""
    bl_idname = "mmy.manage_excluded_files"
    bl_label = "管理排除文件"
    bl_options = {'REGISTER'}

    filename: StringProperty(name="文件名", default="")
    action: EnumProperty(
        name="操作",
        items=[
            ('add', "添加到排除列表", ""),
            ('remove', "从排除列表移除", ""),
            ('clear', "清空排除列表", ""),
            ('show', "显示排除列表", ""),
        ],
        default='show'
    )

    def invoke(self, context, event):
        if self.action == 'show':
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        props = context.scene.mmy_asset_creator

        if self.action == 'show':
            layout.label(text="当前排除列表:")
            if len(props.excluded_files) == 0:
                layout.label(text="  (空)")
            else:
                for item in props.excluded_files:
                    row = layout.row(align=True)
                    row.label(text=item.path)
                    op = row.operator("mmy.manage_excluded_files", text="", icon='X')
                    op.action = 'remove'
                    op.filename = item.path

            layout.separator()
            # 添加当前选中的文件到排除列表
            selected_not_excluded = [
                item.filename for item in props.refresh_preview_files
                if item.is_selected and item.filename not in props.excluded_files
            ]
            if selected_not_excluded:
                row = layout.row()
                row.label(text=f"将选中 ({len(selected_not_excluded)}) 个文件加入排除:")
            else:
                layout.label(text="勾选文件后可加入排除列表")

            # 清空按钮
            if len(props.excluded_files) > 0:
                layout.separator()
                layout.operator("mmy.manage_excluded_files", text="清空排除列表").action = 'clear'

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        if self.action == 'add':
            # 添加当前选中的文件到排除列表
            for item in props.refresh_preview_files:
                if item.is_selected and item.filename not in props.excluded_files:
                    excluded_item = props.excluded_files.add()
                    excluded_item.path = item.filename
            # 自动取消选中已排除的文件
            for item in props.refresh_preview_files:
                if item.filename in props.excluded_files:
                    item.is_selected = False
            self.report({'INFO'}, f"已添加到排除列表")

        elif self.action == 'remove':
            # 从排除列表移除
            for i, item in enumerate(props.excluded_files):
                if item.path == self.filename:
                    props.excluded_files.remove(i)
                    break
            self.report({'INFO'}, f"已移除: {self.filename}")

        elif self.action == 'clear':
            props.excluded_files.clear()
            self.report({'INFO'}, "排除列表已清空")

        elif self.action == 'show':
            # 添加所有选中文件到排除列表
            for item in props.refresh_preview_files:
                if item.is_selected and item.filename not in props.excluded_files:
                    excluded_item = props.excluded_files.add()
                    excluded_item.path = item.filename
            # 自动取消选中已排除的文件
            for item in props.refresh_preview_files:
                if item.filename in props.excluded_files:
                    item.is_selected = False
            if len(props.excluded_files) > 0:
                self.report({'INFO'}, f"排除列表已更新，共 {len(props.excluded_files)} 个文件")

        return {'FINISHED'}


class MMY_OT_RefreshSelectedPreviews(bpy.types.Operator):
    """刷新选中资产的预览图"""
    bl_idname = "mmy.refresh_selected_previews"
    bl_label = "刷新选中预览图"
    bl_options = {'REGISTER'}

    # 用于 timer 链式执行的状态
    _selected_files = []
    _original_filepath = ""
    _current_index = 0
    _success_count = 0
    _skip_count = 0
    _fail_count = 0
    _error_details = []

    @classmethod
    def poll(cls, context):
        props = context.scene.mmy_asset_creator
        # 检查是否有选中的文件
        for item in props.refresh_preview_files:
            if item.is_selected and item.has_preview:
                return True
        return False

    def invoke(self, context, event):
        # 统计选中数量
        selected_count = sum(
            1 for item in context.scene.mmy_asset_creator.refresh_preview_files
            if item.is_selected
        )
        return context.window_manager.invoke_confirm(
            self,
            event,
            title="刷新选中预览图",
            message=f"将刷新 {selected_count} 个选中资产的预览图，确认继续？"
        )

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        # 收集选中的、有预览图的文件
        selected_files = []
        for item in props.refresh_preview_files:
            if item.is_selected and item.has_preview:
                selected_files.append({
                    'filepath': item.filepath,
                    'filename': item.filename,
                    'preview_path': item.preview_path,
                })

        if not selected_files:
            self.report({'WARNING'}, "没有选中任何有预览图的文件")
            return {'CANCELLED'}

        # 初始化状态
        MMY_OT_RefreshSelectedPreviews._selected_files = selected_files
        MMY_OT_RefreshSelectedPreviews._original_filepath = bpy.data.filepath
        MMY_OT_RefreshSelectedPreviews._current_index = 0
        MMY_OT_RefreshSelectedPreviews._success_count = 0
        MMY_OT_RefreshSelectedPreviews._skip_count = 0
        MMY_OT_RefreshSelectedPreviews._fail_count = 0
        MMY_OT_RefreshSelectedPreviews._error_details = []

        # 启动处理
        self._process_next_file()

        return {'RUNNING_MODAL'}

    def _process_next_file(self):
        """处理下一个文件"""
        cls = MMY_OT_RefreshSelectedPreviews

        if cls._current_index >= len(cls._selected_files):
            self._finish_processing()
            return

        file_info = cls._selected_files[cls._current_index]
        blend_path = file_info['filepath']
        blend_name = file_info['filename']
        preview_path = file_info['preview_path']

        try:
            # 打开目标 .blend 文件
            bpy.ops.wm.open_mainfile(filepath=blend_path)

            # 刷新 UI
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
                window.screen.areas.update()

            # 查找被标记为资产的数据块
            asset_id = None
            for collection in bpy.data.collections:
                if collection.asset_data is not None:
                    asset_id = collection
                    break
            if asset_id is None:
                for obj in bpy.data.objects:
                    if obj.asset_data is not None:
                        asset_id = obj
                        break

            if asset_id is None:
                cls._skip_count += 1
                print(f"[MMY] 跳过 {blend_name}: 未找到已标记的资产")
                cls._current_index += 1
                self._process_next_file()
                return

            # 设置资产预览图
            if not self._set_preview_correct(asset_id, preview_path):
                cls._fail_count += 1
                cls._error_details.append(f"{blend_name}: 预览图设置失败")
                cls._current_index += 1
                self._process_next_file()
                return

            # 切换 3D 视窗到材质预览模式
            self._setup_viewport_for_preview()

            # 注册 timer，延迟保存
            bpy.app.timers.register(
                self._delayed_save,
                first_interval=0.5
            )

        except Exception as e:
            import traceback
            cls._fail_count += 1
            cls._error_details.append(f"{blend_name}: {e}")
            print(f"[MMY] 处理失败 {blend_name}: {traceback.format_exc()}")
            cls._current_index += 1
            self._process_next_file()

    def _delayed_save(self):
        """timer 回调：保存当前文件并继续"""
        cls = MMY_OT_RefreshSelectedPreviews

        file_info = cls._selected_files[cls._current_index]
        blend_path = file_info['filepath']
        blend_name = file_info['filename']

        try:
            bpy.ops.wm.save_mainfile(filepath=blend_path)
            cls._success_count += 1
            print(f"[MMY] 已刷新: {blend_name}")
        except Exception as e:
            cls._fail_count += 1
            cls._error_details.append(f"{blend_name}: 保存失败 {e}")

        cls._current_index += 1

        if cls._current_index < len(cls._selected_files):
            bpy.app.timers.register(
                self._process_next_file_wrapper,
                first_interval=0.2
            )
        else:
            self._finish_processing()

        return None

    def _process_next_file_wrapper(self):
        self._process_next_file()
        return None

    def _finish_processing(self):
        """完成处理，返回原文件"""
        cls = MMY_OT_RefreshSelectedPreviews

        original_filepath = cls._original_filepath
        if original_filepath and os.path.exists(original_filepath):
            bpy.ops.wm.open_mainfile(filepath=original_filepath)
        else:
            bpy.ops.wm.read_homefile()

        msg = f"完成: {cls._success_count} 成功, {cls._skip_count} 跳过, {cls._fail_count} 失败"
        if cls._error_details:
            msg += " | " + "; ".join(cls._error_details[:3])
        print(f"[MMY] {msg}")

        cls._selected_files = []
        cls._current_index = 0

    def _setup_viewport_for_preview(self):
        """切换 3D 视窗到材质预览模式"""
        try:
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            for obj in bpy.data.objects:
                if obj.visible_get():
                    obj.select_set(True)
            visible_objs = [obj for obj in bpy.data.objects if obj.visible_get()]
            if visible_objs:
                bpy.context.view_layer.objects.active = visible_objs[0]

            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        space = area.spaces.active
                        region = None
                        for r in area.regions:
                            if r.type == 'WINDOW':
                                region = r
                                break

                        if space and hasattr(space, 'shading'):
                            space.shading.type = 'MATERIAL'

                        if space and region:
                            with bpy.context.temp_override(window=window, area=area, region=region, space_data=space):
                                bpy.ops.view3d.view_selected()
                                bpy.ops.screen.screen_full_area(use_hide_panels=True)

                        for r in area.regions:
                            r.tag_redraw()
                        return

        except Exception as e:
            print(f"[MMY] 切换视窗失败: {e}")

    def _set_preview_correct(self, asset_id, preview_path):
        """设置资产预览图"""
        try:
            if not os.path.exists(preview_path):
                return False

            with bpy.context.temp_override(id=asset_id):
                bpy.ops.ed.lib_id_load_custom_preview(filepath=preview_path)
            return True
        except Exception as e:
            print(f"[MMY] 设置预览图失败: {e}")
            return False


_classes = (
    MMY_OT_CreateAsset,
    MMY_OT_SelectAssetPath,
    MMY_OT_AddFavoritePath,
    MMY_OT_RemoveFavoritePath,
    MMY_OT_SetPathFromHistory,
    MMY_OT_RefreshRecentPaths,
    MMY_OT_ScanPreviewFiles,
    MMY_OT_ClearPreviewList,
    MMY_OT_RefreshSelectedPreviews,
    MMY_OT_RefreshAllPreviews,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)