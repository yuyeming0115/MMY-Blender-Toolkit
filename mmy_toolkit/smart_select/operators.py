"""智能选择操作符"""

import bpy
import time
from .utils import select_uv_island, select_uv_seams, select_faces_by_material, get_context_type


# 双击检测常量
DOUBLE_CLICK_INTERVAL = 0.25  # 秒
CLICK_POS_TOLERANCE = 5       # 像素


class MMY_OT_SmartSelectUVIsland(bpy.types.Operator):
    """双击选中 UV 孤岛"""
    bl_idname = "mmy.smart_select_uv_island"
    bl_label = "选中 UV 孤岛"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取鼠标位置（在 invoke 中设置）
        mouse_x = getattr(self, '_mouse_x', 0)
        mouse_y = getattr(self, '_mouse_y', 0)

        if select_uv_island(context, mouse_x, mouse_y):
            self.report({'INFO'}, "已选中 UV 孤岛")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "无法选中 UV 孤岛")
            return {'CANCELLED'}

    def invoke(self, context, event):
        self._mouse_x = event.mouse_x
        self._mouse_y = event.mouse_y
        return self.execute(context)


class MMY_OT_SmartSelectUVSeams(bpy.types.Operator):
    """选中所有缝合边"""
    bl_idname = "mmy.smart_select_uv_seams"
    bl_label = "选中缝合边"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if select_uv_seams(context):
            self.report({'INFO'}, "已选中缝合边")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "没有缝合边或不在编辑模式")
            return {'CANCELLED'}


class MMY_OT_SmartSelectMaterial(bpy.types.Operator):
    """双击选中相同材质的面"""
    bl_idname = "mmy.smart_select_material"
    bl_label = "选中相同材质"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        success, count = select_faces_by_material(context, 0, 0)
        if success:
            self.report({'INFO'}, f"已选中 {count} 个相同材质的面")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "没有选中面或不在编辑模式")
            return {'CANCELLED'}


# ============ 双击检测监听器 ============

class MMY_OT_SmartSelectListener(bpy.types.Operator):
    """智能选择监听器 - 检测双击并执行智能选择"""
    bl_idname = "mmy.smart_select_listener"
    bl_label = "智能选择监听器"
    bl_options = {'REGISTER'}

    _last_click_time = 0
    _last_click_x = 0
    _last_click_y = 0
    _timer = None

    def invoke(self, context, event):
        # 获取偏好设置中的双击间隔
        addon = context.preferences.addons.get("mmy_toolkit")
        interval = DOUBLE_CLICK_INTERVAL
        if addon and addon.preferences:
            interval = getattr(addon.preferences, "smart_select_double_click_interval", DOUBLE_CLICK_INTERVAL)

        current_time = time.time()
        mouse_x = event.mouse_x
        mouse_y = event.mouse_y

        # 检测双击
        is_double_click = False
        if current_time - self._last_click_time < interval:
            # 检查位置是否相近
            dx = abs(mouse_x - self._last_click_x)
            dy = abs(mouse_y - self._last_click_y)
            if dx < CLICK_POS_TOLERANCE and dy < CLICK_POS_TOLERANCE:
                is_double_click = True

        if is_double_click:
            # 执行智能选择
            self._execute_smart_select(context, event)
            # 重置状态
            self._last_click_time = 0
            return {'FINISHED'}
        else:
            # 记录首次点击
            self._last_click_time = current_time
            self._last_click_x = mouse_x
            self._last_click_y = mouse_y
            return {'PASS_THROUGH'}

    def _execute_smart_select(self, context, event):
        """根据上下文执行智能选择"""
        context_type = get_context_type(context)

        # 获取选择模式偏好
        addon = context.preferences.addons.get("mmy_toolkit")
        mode = 'auto'  # 默认自动
        if addon and addon.preferences:
            mode = getattr(addon.preferences, "smart_select_mode", 'auto')

        if context_type == 'UV_EDITOR':
            # UV 编辑器
            if mode == 'auto' or mode == 'island':
                # 尝试选中孤岛
                select_uv_island(context, event.mouse_x, event.mouse_y)
        elif context_type == 'VIEW_3D_EDIT':
            # 3D 视图编辑模式
            if mode == 'auto' or mode == 'material':
                # 选中相同材质的面
                success, count = select_faces_by_material(context, event.mouse_x, event.mouse_y)
                if success:
                    self.report({'INFO'}, f"已选中 {count} 个相同材质的面")


_classes = (
    MMY_OT_SmartSelectUVIsland,
    MMY_OT_SmartSelectUVSeams,
    MMY_OT_SmartSelectMaterial,
    MMY_OT_SmartSelectListener,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass