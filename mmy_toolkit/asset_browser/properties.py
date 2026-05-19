import bpy
import os
from bpy.props import (
    StringProperty,
    BoolProperty,
    CollectionProperty,
    IntProperty,
    EnumProperty,
)


# ── EnumProperty ASCII-safe 标识符工具 ────────────────────────
# Blender 的 EnumProperty identifier 只允许字母、数字和下划线。
# 中文、连字符、空格等非 ASCII 字符都会导致显示乱码或截断。
# 方案：将原始字符串 UTF-8 字节序列转为十六进制字符串（只含 0-9a-f），
# 前缀 'c' 确保 identifier 始终以字母开头（Blender 要求）。

def _safe_enum_id(name: str) -> str:
    """将任意字符串转为 Blender EnumProperty 安全的 identifier。"""
    return 'c' + name.encode('utf-8').hex()


def _unsafe_enum_id(identifier: str) -> str:
    """将 _safe_enum_id 的结果还原为原始字符串。"""
    if isinstance(identifier, str) and identifier.startswith('c') and len(identifier) > 1:
        try:
            return bytes.fromhex(identifier[1:]).decode('utf-8')
        except Exception:
            pass
    return identifier


class MMY_RecentPath(bpy.types.PropertyGroup):
    """最近使用路径项"""
    path: StringProperty(name="路径", default="")


class MMY_FavoritePath(bpy.types.PropertyGroup):
    """收藏路径项"""
    path: StringProperty(name="路径", default="")
    alias: StringProperty(name="别名", default="")


class MMY_RefreshPreviewFileItem(bpy.types.PropertyGroup):
    """刷新预览图文件项"""
    filepath: StringProperty(name="文件路径", default="")
    filename: StringProperty(name="文件名", default="")
    has_preview: BoolProperty(name="有预览图", default=False)
    preview_path: StringProperty(name="预览图路径", default="")
    is_selected: BoolProperty(name="选中", default=True)  # 默认选中


# ── 模块级缓存：Blender C 端要求 Python 端保持对 items 列表的持久引用，
# 否则非 ASCII 字符会因引用丢失而显示乱码。
_CATALOG_ITEMS_CACHE = []


def _update_catalog_id(self, context):
    """当catalog_enum改变时，同步catalog_id（解码 safe_enum_id）"""
    self.catalog_id = _unsafe_enum_id(self.catalog_enum)


def get_catalog_enum_items(self, context):
    """动态获取Catalog枚举项 - 优先使用 Blender 内置 Catalog API"""
    _CATALOG_ITEMS_CACHE.clear()
    _CATALOG_ITEMS_CACHE.append(("", "未分类", "不分配到任何Catalog"))
    seen_ids = set()

    # 直接解析 cats.txt，内置 API 返回的 display_name 在 Windows 上编码错误
    prefs = context.preferences
    if prefs:
        asset_libraries = prefs.filepaths.asset_libraries
        for lib in asset_libraries:
            lib_path = lib.path
            if lib_path and os.path.exists(lib_path):
                catalog_file = os.path.join(lib_path, "blender_assets.cats.txt")
                if os.path.exists(catalog_file):
                    try:
                        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']
                        file_content = None
                        for encoding in encodings:
                            try:
                                with open(catalog_file, "r", encoding=encoding) as f:
                                    file_content = f.read()
                                break
                            except:
                                continue

                        if file_content:
                            for line in file_content.split('\n'):
                                line = line.strip()
                                if not line or line.startswith("#") or line.startswith("VERSION"):
                                    continue
                                parts = line.split(":", 2)
                                if len(parts) == 3:
                                    catalog_uuid = parts[0].strip()
                                    catalog_path = parts[1].strip()
                                    catalog_simple = parts[2].strip()

                                    if (
                                        catalog_uuid and catalog_simple
                                        and len(catalog_uuid) >= 4
                                        and catalog_uuid not in seen_ids
                                    ):
                                        seen_ids.add(catalog_uuid)
                                        safe_id = _safe_enum_id(catalog_uuid)
                                        _CATALOG_ITEMS_CACHE.append((safe_id, catalog_simple, ""))
                    except Exception as e:
                        print(f"[MMY] 读取catalog文件失败: {catalog_file}, 错误: {e}")

    print(f"[MMY] 最终Catalog列表: {len(_CATALOG_ITEMS_CACHE)} 项")
    return _CATALOG_ITEMS_CACHE


def _try_get_builtin_catalog_tree(context):
    """尝试通过 Blender 内置 API 获取 AssetCatalogTree。
    
    与 Blender 自带资产浏览器（标注2）使用同一数据源，
    彻底避免手动解析文件时的编码乱码问题。
    """
    # ── 尝试 A：从当前窗口的 FILE_BROWSER 空间获取 ──
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'FILE_BROWSER':
                for space in area.spaces:
                    if space.type == 'FILE_BROWSER' and hasattr(space, 'params'):
                        params = getattr(space, 'params', None)
                        if params and hasattr(params, 'asset_library_catalogs'):
                            tree = params.asset_library_catalogs
                            if tree is not None:
                                print(f"[MMY] 从FILE_BROWSER空间获取到CatalogTree")
                                return tree

    # ── 尝试 B：通过 bpy.asset 模块获取全局 catalog tree ──
    if hasattr(bpy, 'asset'):
        asset_mod = bpy.asset
        # Blender 4.2+: bpy.asset.catalogs.catalog_tree
        for attr_chain in [
            ('catalogs', 'catalog_tree'),
            ('catalogs', 'tree'),
            ('catalog_tree',),
        ]:
            obj = asset_mod
            found = True
            for attr in attr_chain:
                if hasattr(obj, attr):
                    obj = getattr(obj, attr)
                else:
                    found = False
                    break
            if found and obj is not None:
                print(f"[MMY] 从bpy.asset.{ '.'.join(attr_chain) }获取到CatalogTree")
                return obj

    # ── 尝试 C：通过 AssetLibraryService 获取 ──
    if hasattr(bpy, 'asset_utils'):
        try:
            from blender_asset import AssetLibraryService  # 某些版本的导入路径
        except ImportError:
            pass

    print(f"[MMY] 所有内置API均不可用")
    return None


class MMY_AssetCreatorProps(bpy.types.PropertyGroup):
    """资产创建器属性组"""

    # === 路径相关 ===
    asset_path: StringProperty(
        name="资产路径",
        description="资产保存的目录路径",
        subtype="DIR_PATH",
        default=""
    )

    recent_paths: CollectionProperty(
        type=MMY_RecentPath,
        name="最近使用路径"
    )

    favorite_paths: CollectionProperty(
        type=MMY_FavoritePath,
        name="收藏路径"
    )

    selected_favorite_index: IntProperty(default=0)

    # === 资产信息 ===
    asset_name: StringProperty(
        name="资产名称",
        description="资产名称，将作为集合名和文件名",
        default=""
    )

    # === Catalog相关 ===
    catalog_id: StringProperty(
        name="Catalog ID",
        description="资产所属的Catalog UUID",
        default=""
    )

    catalog_enum: EnumProperty(
        name="Catalog分类",
        description="选择资产所属的Catalog分类（从资产库读取）",
        items=get_catalog_enum_items,
        update=_update_catalog_id,
    )

    # === 预览图 ===
    auto_preview: BoolProperty(
        name="自动预览",
        description="自动使用同目录下的同名图片作为预览",
        default=True
    )

    # === 操作选项 ===
    compress: BoolProperty(
        name="压缩",
        description="压缩保存文件",
        default=True
    )

    # === 刷新预览图 ===
    refresh_preview_files: CollectionProperty(
        type=MMY_RefreshPreviewFileItem,
        name="刷新预览图文件列表"
    )
    refresh_preview_index: IntProperty(default=0)

    # === 排除文件列表（持久化存储）===
    excluded_files: CollectionProperty(
        type=MMY_RecentPath,  # 复用 MMY_RecentPath 作为简单字符串存储
        name="排除刷新的文件"
    )


_classes = (
    MMY_RecentPath,
    MMY_FavoritePath,
    MMY_RefreshPreviewFileItem,
    MMY_AssetCreatorProps,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mmy_asset_creator = bpy.props.PointerProperty(
        type=MMY_AssetCreatorProps
    )


def unregister():
    del bpy.types.Scene.mmy_asset_creator

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)