
<!-- MMY-INJECT:START -->
## 模型信息（由 MMYCodeSwitch-API 自动管理）

> 当前使用的模型为 **glm-5**，通过 **阿里云百炼-glm5** 提供服务。
> 此段内容由 `<!-- MMY-INJECT:START -->` 和 `<!-- MMY-INJECT:END -->` 包裹，
> 切换供应商或解绑项目时会自动更新，请勿手动编辑此区域。

<!-- MMY-INJECT:END -->

## 项目开发规则

### UI 挂载位置原则

功能 UI 应挂载在"最方便使用的地方"，避免冗余副本：

| 功能类型 | 推荐位置 | 示例 |
|----------|----------|------|
| 文件操作 | 文件浏览器 Header | 后缀保存 |
| 材质/节点操作 | Shader Editor 右键菜单/Header | 颜色空间切换 |
| 视图操作 | 3D 视图 Header | 相机焦距 |
| 通用工具 | N 面板页签 | 资产创建、缝合边 |

**原则**：原生位置优先，页签面板只放需要集中管理的工具，不在两处重复。

### EnumProperty 中文显示规范

Blender 的 `EnumProperty` 在处理中文时有三个坑点：

| 问题 | 解决方案 |
|------|----------|
| identifier 只接受 ASCII | 中文用 UTF-8 hex 编码：`'c' + name.encode('utf-8').hex()` |
| description 字段中文乱码（Windows） | description 留空，不要传入含中文的字符串 |
| items 列表被 GC 回收导致乱码 | 使用**模块级缓存列表**，回调函数返回同一个对象 |

**正确写法**：
```python
_ITEMS_CACHE = []  # 模块级缓存（关键）

def get_items(self, context):
    _ITEMS_CACHE.clear()
    for name in ["选项一", "选项二"]:
        safe_id = 'c' + name.encode('utf-8').hex()
        _ITEMS_CACHE.append((safe_id, name, ""))  # description 留空
    return _ITEMS_CACHE  # 返回同一个列表对象
```

详见：`开发文档/EnumProperty中文显示修复记录.md`