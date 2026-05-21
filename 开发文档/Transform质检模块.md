# Transform 质检模块开发记录

## 功能概述

从 MMY_Transform_QA 插件整合，检测和修复对象的 Transform 问题：
- 旋转非零
- 缩放非 1
- 负缩放
- 位移非零
- 父级变换异常

## 核心功能

| 功能 | 操作 | 说明 |
|------|------|------|
| 扫描 | 检测所有问题 | 支持选定/可见/整个场景范围 |
| 修复 | 应用 Transform | 跳过风险对象（Shape Keys、动画、约束等） |
| 选择 | 选中问题对象 | 便于手动处理 |
| Alert | 按钮警示 | 选中对象有问题时高亮 |

## 风险检测

| 风险类型 | 说明 |
|----------|------|
| Shape Keys | 有形态键的对象 |
| 动画数据 | 有动画的对象 |
| 约束 | 有约束器的对象 |
| 骨架修改器 | 有 Armature 修改器 |
| 链接/Override | 来自外部库的对象 |

## 模块结构

```
mmy_toolkit/transform_check/
├── __init__.py          # 模块入口
├── operators.py         # 操作符实现
├── properties.py        # 属性定义
└── utils.py             # 工具函数
```

## UI 位置

- **按钮位置**：顶栏（TOPBAR）右侧
- **交互方式**：点击按钮弹出 popup 窗口

## Alert 特性

选中对象有 Transform 问题时，按钮高亮警示：
```python
row.alert = selection_has_transform_issue(context)
```

## 变更记录

| 日期 | 内容 |
|------|------|
| 2026-05-21 | 从 MMY_Transform_QA 整合到 MMY Toolkit |
| 2026-05-21 | 移到顶栏（TOPBAR）右侧 |