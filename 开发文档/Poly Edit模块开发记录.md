# Poly @ Edit 模块开发记录

## 功能概述

整合 `MMY Poly @Edit` 插件的平滑组和选择集功能到 MMY Toolkit，提供建模工具增强。

---

## 一、平滑组模块

### 功能说明

为模型面分配平滑组 ID（1-32），通过自定义法线控制模型着色效果，实现类似 3ds Max 的平滑组功能。

### 核心算法逻辑

| 条件 | 效果 |
|------|------|
| Group 0 + Group 0 | 根据原始 `face.smooth` 状态 |
| Group 0 + Group X | 硬边（分隔效果） |
| Group X + Group X | 平滑（同组） |
| Group X + Group Y | 硬边（不同组，且 X&Y==0） |

### 数据存储

使用 `bm.faces.layers.int["smoothing_groups"]` 位掩码存储，每个面可属于多个组。

### 关键 API

```python
# 位掩码操作
bit_mask = 1 << (group_id - 1)  # Group 1 = bit 0

# 自定义法线
mesh.normals_split_custom_set(loop_normals)

# GPU Overlay 绘制
gpu.shader.from_builtin('UNIFORM_COLOR')
batch_for_shader(shader, 'TRIS', {"pos": coords})
```

### 交互模式

| 模式 | 操作 |
|------|------|
| SET（设定） | 点击数字为选中面分配/切换平滑组 |
| SELECT（选择） | 点击数字选中属于该组的所有面 |

**修饰键支持**：
- Shift + 点击：加选
- Ctrl + 点击：减选

---

## 二、选择集模块

### 功能说明

保存和加载选择状态，支持物体模式和编辑模式两种类型。

### 命名规则

| 模式 | 格式 | 示例 |
|------|------|------|
| 物体模式 | 普通名称 | `ObjectSet_1` |
| 编辑模式 | `-名称-` | `-Faces_Selection_1-` |

### 加载模式

| 模式 | 操作 |
|------|------|
| REPLACE | 清除当前选择，加载选择集 |
| ADD | 将选择集内容加入当前选择 |
| SUBTRACT | 将选择集内容从当前选择移除 |

### 数据结构

```python
class SelectionSetItem(PropertyGroup):
    name: StringProperty()
    objects: CollectionProperty(type=StringItem)     # 物体名称列表
    elements: CollectionProperty(type=ElementSelection)  # 编辑模式元素
```

---

## 三、模块结构

```
mmy_toolkit/poly_edit/
├── __init__.py              # 模块入口
├── smooth_groups/
│   ├── __init__.py
│   ├── algo.py              # 法线算法
│   ├── overlay.py           # GPU Overlay 绘制
│   └── operators.py         # 平滑组操作符 + 属性注册
├── selection_sets/
│   ├── __init__.py
│   └── operators.py         # 选择集操作符 + 数据结构
└── ui/
    ├── __init__.py
    ├── lang.py              # 中文翻译
    └── panels.py            # N 面板绘制
```

---

## 四、关键技术

### 位掩码处理 Group 32 溢出

```python
def safe_bit_mask(group_id):
    bit_mask = 1 << (group_id - 1)
    # Group 32 超出有符号 32 位整数正数范围
    if bit_mask > 0x7FFFFFFF:
        bit_mask = bit_mask - 0x100000000
    return bit_mask
```

### GPU Overlay 3D/2D 绘制

```python
# 3D 绘制：彩色区域 + 边界线
bpy.types.SpaceView3D.draw_handler_add(draw_3d, ..., 'WINDOW', 'POST_VIEW')

# 2D 绘制：标签文字
bpy.types.SpaceView3D.draw_handler_add(draw_2d, ..., 'WINDOW', 'POST_PIXEL')

# 文字绘制
blf.size(font_id, 28)
blf.position(font_id, x - w/2, y - h/2, 0)
blf.draw(font_id, txt)
```

### BFS 聚类计算标签位置

```python
# 从一个面开始，BFS 遍历相邻同组面
queue = deque([f])
while queue:
    cf = queue.popleft()
    for e in cf.edges:
        for nf in e.link_faces:
            if nf.index not in visited and nf.index in group_faces:
                queue.append(nf)
# 计算聚类中心作为标签位置
center = sum(f.calc_center_median() for f in cluster) / len(cluster)
```

---

## 五、变更记录

| 日期 | 内容 |
|------|------|
| 2026-05-20 | 从 MMY Poly @Edit 插件合并平滑组和选择集功能 |