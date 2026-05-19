# EnumProperty 中文显示方案

## 问题背景

Blender 的 `EnumProperty` 的 `identifier` 字段**只允许 ASCII 字符**（字母、数字、下划线）。如果直接把中文名作为 identifier，会导致乱码或显示异常。

## 解决方案：双编码策略

### 核心原理

- `identifier`：使用 UTF-8 hex 编码后的 ASCII 安全字符串
- `display_name`：使用原始中文名（用户看到的显示名）
- 读取时通过解码还原中文

### 编码/解码函数

```python
def safe_id(name: str) -> str:
    '''将任意字符串转为 Blender EnumProperty 安全的 identifier。'''
    # UTF-8 字节序列转十六进制字符串，前缀 'p' 确保以字母开头
    return 'p' + name.encode('utf-8').hex()

def unsafe_id(identifier: str) -> str:
    '''将编码后的 identifier 还原为原始名字。'''
    if isinstance(identifier, str) and identifier.startswith('p') and len(identifier) > 1:
        try:
            return bytes.fromhex(identifier[1:]).decode('utf-8')
        except Exception:
            pass
    return identifier  # 回退：原样返回（兼容旧版数据）
```

### 示例转换

| 原始中文名 | 编码后 identifier |
|-----------|-------------------|
| `"测试预设"` | `"pe6b58be895e8aebe"` |
| `"默认配置"` | `"pe9bb9e8aebee9858d"` |

## 关键实现步骤

### 1. 模块级缓存（最关键）

Blender 的 C 端要求 Python 端保持对 items 列表的持久引用（keep-alive），否则非 ASCII 字符会因引用丢失而显示乱码。

```python
# 必须使用模块级列表，不能每次返回新列表
_MY_ITEMS_CACHE = []
```

### 2. EnumProperty items 回调

```python
def get_my_items(self, context):
    _MY_ITEMS_CACHE.clear()
    for chinese_name in ["选项一", "选项二", "选项三"]:
        # (identifier, display_name, description)
        _MY_ITEMS_CACHE.append((safe_id(chinese_name), chinese_name, ''))
    return _MY_ITEMS_CACHE
```

### 3. 属性定义

```python
class MySettings(bpy.types.PropertyGroup):
    my_enum: bpy.props.EnumProperty(
        name='我的选项',
        items=get_my_items,  # 使用回调函数
    )
```

### 4. 读取时解码还原

```python
def some_function(props):
    raw = props.my_enum  # 这是编码后的 identifier
    real_name = unsafe_id(raw)  # 解码回原始中文名
    # 使用 real_name 进行后续操作...
```

## 完整流程示意

| 阶段 | identifier | display_name | 说明 |
|------|------------|--------------|------|
| 定义 items | `"pe6b58be895e8aebe"` | `"测试预设"` | 编码存储 |
| 用户选择 | 存储 `"pe6b58be895e8aebe"` | — | 属性值是编码后的 |
| 读取使用 | → 解码 `"测试预设"` | — |还原中文名 |

## 常见错误

### ❌ 错误写法

```python
def get_items(self, context):
    # 每次返回新列表，没有持久引用 → 中文乱码
    return [(safe_id(n), n, '') for n in names]

# 或直接用中文作为 identifier → 更严重的乱码
return [("测试", "测试", '')]  # identifier 不允许非 ASCII
```

### ✓ 正确写法

```python
_ITEMS_CACHE = []  # 模块级缓存

def get_items(self, context):
    _ITEMS_CACHE.clear()
    for n in names:
        _ITEMS_CACHE.append((safe_id(n), n, ''))
    return _ITEMS_CACHE
```

## 本项目实际应用位置

- 编码函数定义：`services/preset_service.py` 第 17-29 行
- 预设 Enum 实现：`props/render_props.py` 第 17-52 行
- 预设管理操作：`operators/preset_ops.py`

---

**变更记录**

| 日期 | 内容 |
|------|------|
| 2026-05-17 | 从代码分析提取方案，整理成文档 |