# 修改器面板按钮绘制

import bpy


# ============ 修改器分类定义 ============
# 按类别分组，便于快速查找

MODIFIER_CATEGORIES = {
    "生成": [
        ('ARRAY', "阵列", 'MOD_ARRAY'),
        ('BEVEL', "倒角", 'MOD_BEVEL'),
        ('BOOLEAN', "布尔", 'MOD_BOOLEAN'),
        ('BUILD', "构建", 'MOD_BUILD'),
        ('DECIMATE', "精简", 'MOD_DECIM'),
        ('EDGE_SPLIT', "拆边", 'MOD_EDGESPLIT'),
        ('MASK', "遮罩", 'MOD_MASK'),
        ('MIRROR', "镜像", 'MOD_MIRROR'),
        ('MULTIRES', "多级精度", 'MOD_MULTIRES'),
        ('NODES', "几何节点", 'NODETREE'),
        ('REMESH', "重构网格", 'MOD_REMESH'),
        ('SCREW', "螺旋", 'MOD_SCREW'),
        ('SKIN', "蒙皮", 'MOD_SKIN'),
        ('SOLIDIFY', "实体化", 'MOD_SOLIDIFY'),
        ('SUBSURF', "细分", 'MOD_SUBSURF'),
        ('TRIANGULATE', "三角化", 'MOD_TRIANGULATE'),
        ('VOLUME_TO_MESH', "体积转网格", 'VOLUME_DATA'),
        ('WELD', "焊接", 'AUTOMERGE_OFF'),
        ('WIREFRAME', "线框", 'MOD_WIREFRAME'),
    ],
    "变形": [
        ('ARMATURE', "骨架", 'MOD_ARMATURE'),
        ('CAST', "投射", 'MOD_CAST'),
        ('CURVE', "曲线", 'MOD_CURVE'),
        ('DISPLACE', "置换", 'MOD_DISPLACE'),
        ('HOOK', "钩子", 'HOOK'),
        ('LAPLACIANDEFORM', "拉普拉斯变形", 'MOD_MESHDEFORM'),
        ('LAPLACIANSMOOTH', "拉普拉斯平滑", 'MOD_SMOOTH'),
        ('LATTICE', "晶格", 'MOD_LATTICE'),
        ('MESH_DEFORM', "网格变形", 'MOD_MESHDEFORM'),
        ('SHRINKWRAP', "收缩包裹", 'MOD_SHRINKWRAP'),
        ('SIMPLE_DEFORM', "简易变形", 'MOD_SIMPLEDEFORM'),
        ('SMOOTH', "平滑", 'MOD_SMOOTH'),
        ('CORRECTIVE_SMOOTH', "矫正平滑", 'MOD_SMOOTH'),
        ('SURFACE_DEFORM', "表面变形", 'MOD_MESHDEFORM'),
        ('WARP', "扭曲", 'MOD_WARP'),
        ('WAVE', "波浪", 'MOD_WAVE'),
    ],
    "修改": [
        ('DATA_TRANSFER', "数据传递", 'MOD_DATATRANSFER'),
        ('MESH_CACHE', "网格缓存", 'FILE'),
        ('MESH_SEQUENCE_CACHE', "网格序列缓存", 'FILE'),
        ('NORMAL_EDIT', "编辑法向", 'MOD_NORMALEDIT'),
        ('WEIGHTED_NORMAL', "加权法向", 'MOD_NORMALEDIT'),
        ('UV_PROJECT', "UV投射", 'MOD_UVPROJECT'),
        ('UV_WARP', "UV扭曲", 'MOD_UVWARP'),
        ('VERTEX_WEIGHT_EDIT', "顶点权重编辑", 'MOD_VERTEX_WEIGHT'),
        ('VERTEX_WEIGHT_MIX', "顶点权重混合", 'MOD_VERTEX_WEIGHT'),
        ('VERTEX_WEIGHT_PROXIMITY', "顶点权重邻近", 'MOD_VERTEX_WEIGHT'),
    ],
    "物理": [
        ('CLOTH', "布料", 'MOD_CLOTH'),
        ('COLLISION', "碰撞", 'MOD_COLLISION'),
        ('DYNAMIC_PAINT', "动态绘画", 'MOD_DYNAMICPAINT'),
        ('EXPLODE', "爆炸", 'MOD_EXPLODE'),
        ('FLUID', "流体", 'MOD_FLUIDSIM'),
        ('OCEAN', "海洋", 'MOD_OCEAN'),
        ('PARTICLE_INSTANCE', "粒子实例", 'MOD_PARTICLE_INSTANCE'),
        ('PARTICLE_SYSTEM', "粒子系统", 'MOD_PARTICLES'),
        ('SOFT_BODY', "软体", 'MOD_SOFT'),
    ],
}


# 存储每个修改器的显隐状态（使用对象自定义属性）
def _save_modifier_visibility(obj):
    """保存修改器显隐状态到对象属性"""
    if not obj:
        return
    state = {}
    for mod in obj.modifiers:
        state[mod.name] = mod.show_viewport
    obj["mmy_modifier_visibility"] = str(state)


def _restore_modifier_visibility(obj):
    """从对象属性恢复修改器显隐状态"""
    if not obj or "mmy_modifier_visibility" not in obj:
        return False
    try:
        import ast
        state = ast.literal_eval(obj["mmy_modifier_visibility"])
        for mod in obj.modifiers:
            if mod.name in state:
                mod.show_viewport = state[mod.name]
        del obj["mmy_modifier_visibility"]
        return True
    except:
        return False


def _has_saved_visibility(obj):
    """检查是否有保存的显隐状态"""
    return obj and "mmy_modifier_visibility" in obj


# ============ 自定义修改器菜单 ============

class MMY_MT_AddModifierMenu(bpy.types.Menu):
    """自定义添加修改器菜单（按类别分组，多列显示）"""
    bl_idname = "MMY_MT_add_modifier"
    bl_label = "添加修改器"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            layout.label(text="仅网格对象可用")
            return

        # 使用 column_flow 实现4列布局
        flow = layout.column_flow(columns=4)

        for category, modifiers in MODIFIER_CATEGORIES.items():
            col = flow.column()

            # 类别标题
            col.label(text=category)

            # 修改器列表
            for mod_type, mod_name, mod_icon in modifiers:
                op = col.operator("object.modifier_add", text=mod_name, icon=mod_icon)
                op.type = mod_type


# ============ 工具按钮行 ============

def draw_modifier_buttons_panel(self, context):
    """绘制修改器面板工具按钮行"""
    layout = self.layout
    obj = context.active_object

    # 仅对网格对象显示
    if not obj or obj.type != 'MESH':
        return

    has_modifiers = bool(obj.modifiers)

    # 工具按钮行（带背景框，自适应宽度）
    box = layout.box()
    row = box.row(align=True)
    row.scale_y = 1.5

    # 1. 添加修改器（始终可用）
    row.menu("MMY_MT_add_modifier", text="添加", icon='ADD')

    # 以下按钮始终显示，无修改器时禁用
    sub = row.row(align=True)
    sub.active = has_modifiers  # 无修改器时禁用

    # 2. 显隐开关
    if has_modifiers and _has_saved_visibility(obj):
        sub.operator("mmy.restore_modifier_visibility", text="显隐", icon='HIDE_OFF')
    else:
        sub.operator("mmy.hide_all_modifiers", text="显隐", icon='HIDE_ON')

    # 3. 应用修改器
    sub.operator("mmy.apply_all_modifiers_with_shapekeys", text="应用", icon='CHECKMARK')

    # 4. 删除所有修改器
    sub.operator("mmy.delete_all_modifiers", text="删除", icon='X')

    # 5. 展开/折叠
    if has_modifiers:
        all_expanded = all(mod.show_expanded for mod in obj.modifiers)
        if all_expanded:
            sub.operator("mmy.collapse_all_modifiers", text="折叠", icon='DISCLOSURE_TRI_DOWN')
        else:
            sub.operator("mmy.expand_all_modifiers", text="展开", icon='DISCLOSURE_TRI_RIGHT')
    else:
        # 无修改器时显示占位按钮（禁用状态）
        sub.label(text="展开", icon='DISCLOSURE_TRI_RIGHT')

    layout.separator(factor=0.3)


def draw_modifier_buttons_header(self, context):
    """Header 绘制（备用位置）"""
    layout = self.layout
    obj = context.active_object

    if not obj or not obj.modifiers:
        return

    row = layout.row(align=True)
    if _has_saved_visibility(obj):
        row.operator("mmy.restore_modifier_visibility", text="", icon='HIDE_OFF')
    else:
        row.operator("mmy.hide_all_modifiers", text="", icon='HIDE_ON')


# 挂载位置配置（延迟初始化）
HEADER_LOCATIONS = None


def _init_header_locations():
    """初始化挂载位置配置（在 register 时调用）"""
    global HEADER_LOCATIONS
    HEADER_LOCATIONS = []

    # 优先：DATA_PT_modifiers Panel
    if hasattr(bpy.types, 'DATA_PT_modifiers'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.DATA_PT_modifiers,
            'attr': 'modifier_panel',
            'drawing_func': draw_modifier_buttons_panel,
            'default_show': True,
            'use_prepend': True
        })

    # 备用：PROPERTIES_HT_header
    if hasattr(bpy.types, 'PROPERTIES_HT_header'):
        HEADER_LOCATIONS.append({
            'menu': bpy.types.PROPERTIES_HT_header,
            'attr': 'modifier_properties_header',
            'drawing_func': draw_modifier_buttons_header,
            'default_show': False,
            'use_append': True
        })

    return HEADER_LOCATIONS


def update_visual_settings(menu, attr, drawing_func, default_show=True, use_prepend=False, use_append=False, unregister=False):
    """更新按钮显示"""
    if unregister:
        try:
            menu.remove(drawing_func)
        except:
            pass
        return

    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if not addon or not addon.preferences:
        if default_show:
            try:
                if use_prepend:
                    menu.prepend(drawing_func)
                elif use_append:
                    menu.append(drawing_func)
                else:
                    menu.append(drawing_func)
            except:
                pass
        return

    show = getattr(addon.preferences, attr, default_show)
    if show is None:
        show = default_show

    if not show:
        try:
            menu.remove(drawing_func)
        except:
            pass
    else:
        try:
            menu.remove(drawing_func)
        except:
            pass
        if use_prepend:
            menu.prepend(drawing_func)
        elif use_append:
            menu.append(drawing_func)
        else:
            menu.append(drawing_func)


def update_modifier_buttons(self, context):
    """偏好设置变化时更新所有按钮"""
    if HEADER_LOCATIONS is None:
        return
    for loc in HEADER_LOCATIONS:
        update_visual_settings(
            loc['menu'], loc['attr'], loc['drawing_func'],
            default_show=loc.get('default_show', True),
            use_prepend=loc.get('use_prepend', False),
            use_append=loc.get('use_append', False)
        )


# 模块级菜单类
_classes_ui = (
    MMY_MT_AddModifierMenu,
)