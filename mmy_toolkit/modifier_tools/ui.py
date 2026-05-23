# 修改器面板按钮绘制

import bpy


# ============ 存储每个修改器的显隐状态（使用对象自定义属性）============

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


# ============ 图标名称映射（Blender 5.1 验证可用） ============

# 修改器类型 -> 图标名称（使用 Blender 5.1 实际可用的名称）
MODIFIER_ICON_NAMES = {
    # 生成类
    'ARRAY': 'MOD_ARRAY',
    'BEVEL': 'MOD_BEVEL',
    'BOOLEAN': 'MOD_BOOLEAN',
    'BUILD': 'MOD_BUILD',
    'DECIMATE': 'MOD_DECIM',  # 注意：不是 MOD_DECIMATE
    'EDGE_SPLIT': 'MOD_EDGESPLIT',
    'MASK': 'MOD_MASK',
    'MIRROR': 'MOD_MIRROR',
    'MULTIRES': 'MOD_MULTIRES',
    'NODES': 'NODETREE',  # 几何节点使用 NODETREE 图标
    'REMESH': 'MOD_REMESH',
    'SCREW': 'MOD_SCREW',
    'SKIN': 'MOD_SKIN',
    'SOLIDIFY': 'MOD_SOLIDIFY',
    'SUBSURF': 'MOD_SUBSURF',
    'TRIANGULATE': 'MOD_TRIANGULATE',
    'VOLUME_TO_MESH': 'VOLUME_DATA',
    'WELD': 'AUTOMERGE_ON',
    'WIREFRAME': 'MOD_WIREFRAME',
    # 变形类
    'ARMATURE': 'MOD_ARMATURE',
    'CAST': 'MOD_CAST',
    'CURVE': 'MOD_CURVE',
    'DISPLACE': 'MOD_DISPLACE',
    'HOOK': 'HOOK',
    'LAPLACIANDEFORM': 'MOD_MESHDEFORM',
    'LAPLACIANSMOOTH': 'MOD_SMOOTH',
    'LATTICE': 'MOD_LATTICE',
    'MESH_DEFORM': 'MOD_MESHDEFORM',
    'SHRINKWRAP': 'MOD_SHRINKWRAP',
    'SIMPLE_DEFORM': 'MOD_SIMPLEDEFORM',
    'SMOOTH': 'MOD_SMOOTH',
    'CORRECTIVE_SMOOTH': 'MOD_SMOOTH',
    'SURFACE_DEFORM': 'MOD_MESHDEFORM',
    'WARP': 'MOD_WARP',
    'WAVE': 'MOD_WAVE',
    # 修改类
    'DATA_TRANSFER': 'MOD_DATA_TRANSFER',
    'MESH_CACHE': 'FILE',
    'MESH_SEQUENCE_CACHE': 'FILE',
    'NORMAL_EDIT': 'MOD_NORMALEDIT',
    'WEIGHTED_NORMAL': 'MOD_NORMALEDIT',
    'UV_PROJECT': 'MOD_UVPROJECT',
    'UV_WARP': 'MOD_UVPROJECT',
    'VERTEX_WEIGHT_EDIT': 'MOD_VERTEX_WEIGHT',
    'VERTEX_WEIGHT_MIX': 'MOD_VERTEX_WEIGHT',
    'VERTEX_WEIGHT_PROXIMITY': 'MOD_VERTEX_WEIGHT',
    # 物理类
    'CLOTH': 'MOD_CLOTH',
    'COLLISION': 'MOD_PHYSICS',
    'DYNAMIC_PAINT': 'MOD_DYNAMICPAINT',
    'EXPLODE': 'MOD_EXPLODE',
    'FLUID': 'MOD_FLUIDSIM',
    'OCEAN': 'MOD_OCEAN',
    'PARTICLE_INSTANCE': 'MOD_PARTICLE_INSTANCE',
    'PARTICLE_SYSTEM': 'MOD_PARTICLES',
    'SOFT_BODY': 'MOD_SOFT',
    # 蜡笔修改器
    'GREASE_PENCIL_ARRAY': 'MOD_ARRAY',
    'GREASE_PENCIL_BUILD': 'MOD_BUILD',
    'GREASE_PENCIL_LENGTH': 'MOD_LENGTH',
    'GREASE_PENCIL_MIRROR': 'MOD_MIRROR',
    'GREASE_PENCIL_MULTIPLY': 'MOD_ARRAY',
    'GREASE_PENCIL_SIMPLIFY': 'MOD_SIMPLIFY',
    'GREASE_PENCIL_SUBDIV': 'MOD_SUBSURF',
    'GREASE_PENCIL_ENVELOPE': 'MOD_ENVELOPE',
    'GREASE_PENCIL_OUTLINE': 'MOD_OUTLINE',
    'GREASE_PENCIL_DASH': 'MOD_DASH',
    'GREASE_PENCIL_HOOK': 'HOOK',
    'GREASE_PENCIL_NOISE': 'MOD_NOISE',
    'GREASE_PENCIL_OFFSET': 'MOD_OFFSET',
    'GREASE_PENCIL_SMOOTH': 'MOD_SMOOTH',
    'GREASE_PENCIL_THICKNESS': 'MOD_THICKNESS',
    'GREASE_PENCIL_LATTICE': 'MOD_LATTICE',
    'GREASE_PENCIL_ARMATURE': 'MOD_ARMATURE',
    'GREASE_PENCIL_SHRINKWRAP': 'MOD_SHRINKWRAP',
    'GREASE_PENCIL_COLOR': 'MOD_HUE_SATURATION',
    'GREASE_PENCIL_TINT': 'MOD_TINT',
    'GREASE_PENCIL_OPACITY': 'MOD_OPACITY',
    'GREASE_PENCIL_VERTEX_WEIGHT_ANGLE': 'MOD_VERTEX_WEIGHT',
    'GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY': 'MOD_VERTEX_WEIGHT',
    'GREASE_PENCIL_TIME': 'MOD_TIME',
    'LINEART': 'MOD_LINEART',
    'GREASE_PENCIL_TEXTURE': 'TEXTURE',
}

# 修改器分类定义（与 Blender 5.1 原生分类一致）
MODIFIER_CATEGORIES = {
    "生成": [
        ('ARRAY', "阵列"),
        ('BEVEL', "倒角"),
        ('BOOLEAN', "布尔"),
        ('BUILD', "构建"),
        ('DECIMATE', "精简"),
        ('EDGE_SPLIT', "拆边"),
        ('MASK', "遮罩"),
        ('MIRROR', "镜像"),
        ('MULTIRES', "多级精度"),
        ('NODES', "几何节点"),
        ('REMESH', "重构网格"),
        ('SCREW', "螺旋"),
        ('SKIN', "蒙皮"),
        ('SOLIDIFY', "实体化"),
        ('SUBSURF', "细分"),
        ('TRIANGULATE', "三角化"),
        ('VOLUME_TO_MESH', "体积转网格"),
        ('WELD', "焊接"),
        ('WIREFRAME', "线框"),
    ],
    "变形": [
        ('ARMATURE', "骨架"),
        ('CAST', "投射"),
        ('CURVE', "曲线"),
        ('DISPLACE', "置换"),
        ('HOOK', "钩子"),
        ('LAPLACIANDEFORM', "拉普拉斯变形"),
        ('LAPLACIANSMOOTH', "拉普拉斯平滑"),
        ('LATTICE', "晶格"),
        ('MESH_DEFORM', "网格变形"),
        ('SHRINKWRAP', "收缩包裹"),
        ('SIMPLE_DEFORM', "简易变形"),
        ('SMOOTH', "平滑"),
        ('CORRECTIVE_SMOOTH', "矫正平滑"),
        ('SURFACE_DEFORM', "表面变形"),
        ('WARP', "扭曲"),
        ('WAVE', "波浪"),
    ],
    "修改": [
        ('DATA_TRANSFER', "数据传递"),
        ('MESH_CACHE', "网格缓存"),
        ('MESH_SEQUENCE_CACHE', "网格序列缓存"),
        ('UV_PROJECT', "UV投射"),
        ('UV_WARP', "UV扭曲"),
        ('VERTEX_WEIGHT_EDIT', "顶点权重编辑"),
        ('VERTEX_WEIGHT_MIX', "顶点权重混合"),
        ('VERTEX_WEIGHT_PROXIMITY', "顶点权重邻近"),
    ],
    "法向": [
        ('NORMAL_EDIT', "编辑法向"),
        ('WEIGHTED_NORMAL', "加权法向"),
    ],
    "物理": [
        ('CLOTH', "布料"),
        ('COLLISION', "碰撞"),
        ('DYNAMIC_PAINT', "动态绘画"),
        ('EXPLODE', "爆炸"),
        ('FLUID', "流体"),
        ('OCEAN', "海洋"),
        ('PARTICLE_INSTANCE', "粒子实例"),
        ('PARTICLE_SYSTEM', "粒子系统"),
        ('SOFT_BODY', "软体"),
    ],
}

# 蜡笔修改器分类定义
GPENCIL_MODIFIER_CATEGORIES = {
    "生成": [
        ('GREASE_PENCIL_ARRAY', "阵列"),
        ('GREASE_PENCIL_BUILD', "构建"),
        ('GREASE_PENCIL_LENGTH', "长度"),
        ('GREASE_PENCIL_MIRROR', "镜像"),
        ('GREASE_PENCIL_MULTIPLY', "多笔触"),
        ('GREASE_PENCIL_SIMPLIFY', "简化"),
        ('GREASE_PENCIL_SUBDIV', "细分"),
        ('GREASE_PENCIL_ENVELOPE', "包络"),
        ('GREASE_PENCIL_OUTLINE', "轮廓"),
        ('GREASE_PENCIL_DASH', "点划线"),
    ],
    "变形": [
        ('GREASE_PENCIL_HOOK', "钩子"),
        ('GREASE_PENCIL_NOISE', "噪波"),
        ('GREASE_PENCIL_OFFSET', "偏移"),
        ('GREASE_PENCIL_SMOOTH', "平滑"),
        ('GREASE_PENCIL_THICKNESS', "厚度"),
        ('GREASE_PENCIL_LATTICE', "晶格"),
        ('GREASE_PENCIL_ARMATURE', "骨架"),
        ('GREASE_PENCIL_SHRINKWRAP', "收缩包裹"),
    ],
    "颜色": [
        ('GREASE_PENCIL_COLOR', "色调饱和"),
        ('GREASE_PENCIL_TINT', "着色"),
        ('GREASE_PENCIL_OPACITY', "透明度"),
    ],
    "权重": [
        ('GREASE_PENCIL_VERTEX_WEIGHT_ANGLE', "角度权重"),
        ('GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY', "邻近权重"),
    ],
    "时间": [
        ('GREASE_PENCIL_TIME', "时间偏移"),
    ],
    "线画": [
        ('LINEART', "线画"),
        ('GREASE_PENCIL_TEXTURE', "纹理映射"),
    ],
}


# ============ 资产库扫描 ============

def get_geometry_nodes_assets():
    """获取资产库中的几何节点资产列表"""
    addon = bpy.context.preferences.addons.get("mmy_toolkit")
    if not addon or not addon.preferences:
        return []

    asset_path = getattr(addon.preferences, "geometry_nodes_asset_path", "")
    if not asset_path:
        return []

    assets = []
    try:
        with bpy.data.libraries.load(asset_path, link=False) as (data_from, _):
            for ng_name in data_from.node_groups:
                # 过滤掉以 '.' 开头的隐藏节点组
                if not ng_name.startswith('.'):
                    assets.append(ng_name)
    except:
        pass

    return assets


# ============ 自定义修改器菜单（智能切换 + 多列布局） ============

class MMY_MT_AddModifierMenu(bpy.types.Menu):
    """自定义添加修改器菜单（智能切换：网格/蜡笔）"""
    bl_idname = "MMY_MT_add_modifier"
    bl_label = "添加修改器"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj:
            layout.label(text="请选择对象")
            return

        if obj.type == 'MESH':
            self.draw_mesh_modifiers(layout, obj)
        elif obj.type == 'GREASE_PENCIL':
            self.draw_gpencil_modifiers(layout, obj)
        else:
            layout.label(text="仅网格和蜡笔对象可用")

    def draw_mesh_modifiers(self, layout, obj):
        """绘制网格修改器菜单（5列 + 资产库）"""
        # 获取几何节点资产
        assets = get_geometry_nodes_assets()

        # 计算列数（5列原生 + 1列资产库）
        num_cols = 6 if assets else 5
        factor = 1.0 / num_cols

        split = layout.split(factor=factor)

        # 绘制5列原生分类
        for category, modifiers in MODIFIER_CATEGORIES.items():
            col = split.column()
            col.label(text=category)

            for mod_type, mod_name in modifiers:
                icon_name = MODIFIER_ICON_NAMES.get(mod_type, 'MODIFIER_DATA')
                op = col.operator("object.modifier_add", text=mod_name, icon=icon_name)
                op.type = mod_type

        # 绘制资产库列（如果有资产）
        if assets:
            col = split.column()
            col.label(text="资产库")

            for asset_name in assets[:15]:  # 限制显示数量
                op = col.operator("mmy.add_geometry_nodes_asset", text=asset_name, icon='NODETREE')
                op.asset_name = asset_name

            if len(assets) > 15:
                col.label(text=f"... 还有 {len(assets) - 15} 个")

    def draw_gpencil_modifiers(self, layout, obj):
        """绘制蜡笔修改器菜单（6列）"""
        split = layout.split(factor=1.0 / 6)

        for category, modifiers in GPENCIL_MODIFIER_CATEGORIES.items():
            col = split.column()
            col.label(text=category)

            for mod_type, mod_name in modifiers:
                icon_name = MODIFIER_ICON_NAMES.get(mod_type, 'MODIFIER_DATA')
                op = col.operator("object.modifier_add", text=mod_name, icon=icon_name)
                op.type = mod_type


# ============ 工具按钮行 ============

def draw_modifier_buttons_panel(self, context):
    """绘制修改器面板工具按钮行（支持网格和蜡笔）"""
    layout = self.layout
    obj = context.active_object

    # 仅对网格和蜡笔对象显示
    if not obj or obj.type not in ('MESH', 'GREASE_PENCIL'):
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

    # 3. 应用修改器（仅网格对象）
    if obj.type == 'MESH':
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