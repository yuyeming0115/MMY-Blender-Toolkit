import bpy
from . import properties
from . import operators

from ..config import (
    get_recent_asset_paths,
    get_favorite_paths,
    get_last_used_asset_path,
)


_classes = (
    properties.MMY_RecentPath,
    properties.MMY_FavoritePath,
    properties.MMY_AssetCreatorProps,
    operators.MMY_OT_CreateAsset,
    operators.MMY_OT_SelectAssetPath,
    operators.MMY_OT_AddFavoritePath,
    operators.MMY_OT_RemoveFavoritePath,
    operators.MMY_OT_SetPathFromHistory,
    operators.MMY_OT_RefreshRecentPaths,
    operators.MMY_OT_RefreshAllPreviews,
)


@bpy.app.handlers.persistent
def _on_load_post(dummy):
    """文件加载后初始化场景属性"""
    _sync_scene_props()


def _sync_scene_props():
    """同步场景属性中的历史和收藏路径"""
    scene = bpy.context.scene
    if not scene:
        return

    # 检查属性是否存在
    if not hasattr(scene, 'mmy_asset_creator'):
        return

    props = scene.mmy_asset_creator

    # 设置最后使用的路径
    last_path = get_last_used_asset_path()
    if last_path:
        props.asset_path = last_path

    # 加载最近使用路径
    props.recent_paths.clear()
    recent = get_recent_asset_paths()
    for path in recent:
        item = props.recent_paths.add()
        item.path = path

    # 加载收藏路径
    props.favorite_paths.clear()
    favorites = get_favorite_paths()
    for fav in favorites:
        item = props.favorite_paths.add()
        item.path = fav.get("path", "")
        item.alias = fav.get("alias", "")


def register():
    # 注册属性组和操作符
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

    # 注册场景属性
    bpy.types.Scene.mmy_asset_creator = bpy.props.PointerProperty(
        type=properties.MMY_AssetCreatorProps
    )

    # 添加文件加载后的处理器（延迟初始化）
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)


def unregister():
    # 移除处理器
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)

    # 删除场景属性
    try:
        del bpy.types.Scene.mmy_asset_creator
    except:
        pass

    # 注销类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass