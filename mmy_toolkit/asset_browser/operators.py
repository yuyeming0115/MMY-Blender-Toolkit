import bpy
import os
from bpy_extras.io_utils import ExportHelper

from ..config import (
    add_recent_asset_path,
    add_favorite_path,
    remove_favorite_path,
    get_recent_asset_paths,
    get_favorite_paths,
)
from ..asset_browser.properties import _unsafe_enum_id


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
            # 4. 收集需要导出的数据块
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

            # 5. 打开新文件并设置资产属性
            bpy.ops.wm.open_mainfile(filepath=filepath)

            # 6. 创建资产集合
            asset_collection = bpy.data.collections.new(asset_name)
            bpy.context.scene.collection.children.link(asset_collection)

            # 7. 将所有导出的对象链接到资产集合
            # 注意：不从 scene 中移除对象，否则对象会因无 scene 引用而被 Blender
            # 视为未使用数据块，保存后再次打开时文件内容为空
            for obj_name in exported_obj_names:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    asset_collection.objects.link(obj)

            # 8. 标记集合为资产
            asset_collection.asset_mark()
            if catalog_id:
                asset_collection.asset_data.catalog_id = catalog_id
                print(f"[MMY] Catalog ID 设置为: {catalog_id}")

            # 9. 查找并设置预览图
            if auto_preview:
                preview_path = None
                for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                    test_path = os.path.join(asset_path, f"{asset_name}{ext}")
                    if os.path.exists(test_path):
                        preview_path = test_path
                        break

                if preview_path:
                    self._set_preview(preview_path, asset_collection)

            # 10. 保存文件
            bpy.ops.wm.save_mainfile(filepath=filepath, compress=compress)

            # 11. 记录最近路径
            add_recent_asset_path(asset_path)

            # 12. 返回原文件
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
        try:
            # 加载图片
            img = bpy.data.images.load(preview_path, check_existing=True)

            # 尝试使用操作符设置预览
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type in ['OUTLINER', 'VIEW_3D', 'ASSETS']:
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                try:
                                    with bpy.context.temp_override(window=window, area=area, region=region):
                                        bpy.ops.ed.lib_id_load_custom_preview(filepath=preview_path)
                                        print(f"[MMY] 预览图设置成功: {preview_path}")
                                        return
                                except:
                                    continue

            print(f"[MMY] 预览图需手动设置: {preview_path}")

        except Exception as e:
            print(f"[MMY] 预览图处理出错: {e}")

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

    def invoke(self, context, event):
        props = context.scene.mmy_asset_creator
        if not props.asset_path:
            self.report({'WARNING'}, "请先选择路径")
            return {'CANCELLED'}

        # 使用路径名作为默认别名
        self.alias = os.path.basename(props.asset_path) or props.asset_path
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        props = context.scene.mmy_asset_creator

        if add_favorite_path(props.asset_path, self.alias):
            # 同步到场景属性
            props.favorite_paths.clear()
            favorites = get_favorite_paths()
            for fav in favorites:
                item = props.favorite_paths.add()
                item.path = fav.get("path", "")
                item.alias = fav.get("alias", "")

            self.report({'INFO'}, f"已收藏: {self.alias}")
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


_classes = (
    MMY_OT_CreateAsset,
    MMY_OT_SelectAssetPath,
    MMY_OT_AddFavoritePath,
    MMY_OT_RemoveFavoritePath,
    MMY_OT_SetPathFromHistory,
    MMY_OT_RefreshRecentPaths,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)