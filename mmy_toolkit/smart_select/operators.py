"""智能选择操作符"""

import bpy
import time
from .utils import select_uv_island, select_uv_seams, select_faces_by_material, get_context_type


# 双击检测常量
DOUBLE_CLICK_INTERVAL = 0.3  # 秒
CLICK_POS_TOLERANCE = 10     # 像素

# 全局状态（跨调用保持）
_last_click_time = 0
_last_click_x = 0
_last_click_y = 0


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
        self._mouse_x = event.mouse_region_x
        self._mouse_y = event.mouse_region_y
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


# ============ 双击检测监听器（持续运行） ============

class MMY_OT_SmartSelectHandler(bpy.types.Operator):
    """智能选择处理器 - 持续监听双击事件"""
    bl_idname = "mmy.smart_select_handler"
    bl_label = "智能选择处理器"
    bl_options = {'REGISTER'}

    _running = False

    def modal(self, context, event):
        # 检查是否启用
        addon = context.preferences.addons.get("mmy_toolkit")
        if not addon or not getattr(addon.preferences, "smart_select_enabled", True):
            self._running = False
            return {'CANCELLED'}

        # 只处理左键点击
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # 获取双击间隔
            interval = getattr(addon.preferences, "smart_select_double_click_interval", DOUBLE_CLICK_INTERVAL)

            current_time = time.time()
            mouse_x = event.mouse_x
            mouse_y = event.mouse_y

            # 检测双击
            global _last_click_time, _last_click_x, _last_click_y

            if current_time - _last_click_time < interval:
                dx = abs(mouse_x - _last_click_x)
                dy = abs(mouse_y - _last_click_y)
                if dx < CLICK_POS_TOLERANCE and dy < CLICK_POS_TOLERANCE:
                    # 双击触发！
                    self._execute_smart_select(context, event)
                    # 重置状态
                    _last_click_time = 0
                    return {'PASS_THROUGH'}

            # 记录点击
            _last_click_time = current_time
            _last_click_x = mouse_x
            _last_click_y = mouse_y

        return {'PASS_THROUGH'}

    def _execute_smart_select(self, context, event):
        """根据上下文执行智能选择"""
        context_type = get_context_type(context)

        if context_type == 'UV_EDITOR':
            # UV 编辑器 - 选中孤岛
            select_uv_island(context, event.mouse_region_x, event.mouse_region_y)
        elif context_type == 'VIEW_3D_EDIT':
            # 3D 视图编辑模式 - 选中相同材质
            success, count = select_faces_by_material(context, event.mouse_x, event.mouse_y)
            if success:
                print(f"[Smart Select] 已选中 {count} 个相同材质的面")

    def invoke(self, context, event):
        if self._running:
            return {'PASS_THROUGH'}

        self._running = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def _start_handler_delayed():
    """延迟启动监听器（确保有窗口上下文）"""
    try:
        bpy.ops.mmy.smart_select_handler('INVOKE_DEFAULT')
        print("[Smart Select] 监听器已启动")
    except Exception as e:
        print(f"[Smart Select] 启动失败: {e}")
    return None  # 停止定时器


_classes = (
    MMY_OT_SmartSelectUVIsland,
    MMY_OT_SmartSelectUVSeams,
    MMY_OT_SmartSelectMaterial,
    MMY_OT_SmartSelectHandler,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 延迟启动监听器（等待窗口上下文可用）
    bpy.app.timers.register(_start_handler_delayed, first_interval=1.0)


def unregister():
    # 停止监听器
    MMY_OT_SmartSelectHandler._running = False

    # 取消定时器
    try:
        bpy.app.timers.unregister(_start_handler_delayed)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass