# EnumProperty 中文显示乱码：完整修复记录

**日期**：2026-05-17
**状态**：已修复
**涉及文件**：`mmy_toolkit/asset_browser/properties.py`

## 问题描述

在"创建资产"面板中，"Catalog分类"下拉列表（`catalog_enum`）显示乱码（如 `@اس`、`Pاس` 等异常字符），而不是中文分类名。多次排查文件读取编码、尝试不同方案均未能解决。

## 问题根因（三个层面）

### 1. identifier 不支持中文

Blender 的 `EnumProperty` 的 `identifier` 字段**只允许 ASCII 字符**（字母、数字、下划线）。直接使用中文作为 identifier 会导致显示异常。

### 2. description 字段传入中文导致乱码

Blender 在 Windows 上以系统代码页（GBK/CP936）渲染 description 字段。当 description 传入含中文的路径字符串时，UTF-8 字节被错误解释为其他编码（如 Windows-1256 阿拉伯字符）。

`name` 字段不受影响，因为 Blender 对其有正确的 Unicode 处理。

### 3. items 列表缺少模块级持久引用（最终根因）

这是最隐蔽也最关键的一个。Blender 的 C 端要求 Python 端保持对 `items` 列表的持久引用（keep-alive）。如果 `items` 回调函数每次都返回一个新创建的列表对象，Python 的 GC 会回收旧列表，导致 Blender C 端持有的中文 display_name 指针失效，最终显示乱码。

## 修复方案（三步）

### 第一步：identifier 使用 UTF-8 hex 编码

```python
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
```

| 原始中文名 | 编码后 identifier |
|-----------|-------------------|
| `"未分类"` | `"ce69caaae58886e7b1bb"` |
| `"Game/轿跑钥匙"` | `"c47616d652fe8b7fe8b791e8b7a5e992a5"` |

### 第二步：description 字段使用空字符串

不再将 `catalog_path` 等含中文的字符串作为 description 传入，避免 Blender 以错误编码渲染。

```python
# 错误写法
items.append((safe_id, catalog_simple, catalog_path))  # description 含中文 → 乱码

# 正确写法
items.append((safe_id, catalog_simple, ""))  # description 留空
```

### 第三步：使用模块级缓存列表（关键修复）

```python
# 模块级缓存，Blender C 端需要 Python 端保持对 items 的持久引用
_CATALOG_ITEMS_CACHE = []

def get_catalog_enum_items(self, context):
    _CATALOG_ITEMS_CACHE.clear()
    _CATALOG_ITEMS_CACHE.append(("", "未分类", "不分配到任何Catalog"))
    # ... 解析 catalog 数据 ...
    _CATALOG_ITEMS_CACHE.append((safe_id, catalog_simple, ""))
    # ...
    return _CATALOG_ITEMS_CACHE  # 返回同一个列表对象
```

**对比错误写法**：

```python
# 错误：每次都创建新列表，GC 后中文丢失
def get_catalog_enum_items(self, context):
    items = [("", "未分类", "不分配到任何Catalog")]
    items.append((safe_id, catalog_simple, ""))
    return items  # 函数返回后列表被 GC 回收
```

### 读取时还原中文

```python
def _update_catalog_id(self, context):
    """当 catalog_enum 改变时，同步 catalog_id（解码 safe_enum_id）"""
    self.catalog_id = _unsafe_enum_id(self.catalog_enum)
```

## 完整流程

| 阶段 | identifier | display_name | 说明 |
|------|------------|--------------|------|
| 定义 items | `"ce69caaae58886e7b1bb"` | `"未分类"` | 编码存储，中文作 display_name |
| 用户选择 | 存储 `"ce69caaae58886e7b1bb"` | 显示 `"未分类"` | 属性值是编码后的 identifier |
| 读取使用 | → 解码 `"未分类"` | — | `_update_catalog_id` 还原 UUID |

## 关键教训

1. **Blender EnumProperty 的 items 回调必须返回持久引用的列表**，否则非 ASCII 字符会因 GC 而丢失。这是最容易被忽视的一点，也是本次乱码的最终根因。
2. **identifier 只接受 ASCII**，中文、连字符、空格等必须编码转换。
3. **description 字段在 Windows 上存在编码问题**，避免传入含中文的字符串，留空最安全。
4. 这三个问题叠加在一起，使得排查过程容易遗漏某一个，导致"修了还是乱码"。

## 相关文件

- 编码/解码函数：`mmy_toolkit/asset_browser/properties.py:18-30`
- 模块级缓存：`mmy_toolkit/asset_browser/properties.py:44`
- items 回调：`mmy_toolkit/asset_browser/properties.py:49-101`
- 属性定义：`mmy_toolkit/asset_browser/properties.py:188-193`
- 方案文档：`开发文档/EnumProperty中文显示方案.md`
