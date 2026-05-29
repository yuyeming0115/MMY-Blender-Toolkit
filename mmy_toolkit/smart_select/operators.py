"""智能选择操作符"""

import bpy
import time
from bpy.props import EnumProperty
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
    """选中相同材质的面"""
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


class MMY_OT_SmartSelectDialog(bpy.types.Operator):
    """智能选择 - 弹出确认面板"""
    bl_idname = "mmy.smart_select_dialog"
    bl_label = "智能选择"
    bl_options = {'REGISTER', 'UNDO'}

    select_type: EnumProperty(
        name="选择类型",
        description="选择要执行的智能选择类型",
        items=[
            ('ISLAND', "UV 孤岛", "选中整个 UV 孤岛"),
            ('MATERIAL', "相同材质", "选中所有相同材质的面"),
            ('SEAM', "缝合边", "选中所有缝合边"),
        ],
        default='ISLAND'
    )

    _mouse_x = 0
    _mouse_y = 0

    def execute(self, context):
        # 执行选择
        if self.select_type == 'ISLAND':
            if select_uv_island(context, self._mouse_x, self._mouse_y):
                self.report({'INFO'}, "已选中 UV 孤岛")
            else:
                self.report({'WARNING'}, "无法选中 UV 孤岛")
        elif self.select_type == 'MATERIAL':
            success, count = select_faces_by_material(context, 0, 0)
            if success:
                self.report({'INFO'}, f"已选中 {count} 个相同材质的面")
            else:
                self.report({'WARNING'}, "没有选中面")
        elif self.select_type == 'SEAM':
            if select_uv_seams(context):
                self.report({'INFO'}, "已选中缝合边")
            else:
                self.report({'WARNING'}, "没有缝合边")

        return {'FINISHED'}

    def invoke(self, context, event):
        self._mouse_x = event.mouse_region_x if hasattr(event, 'mouse_region_x') else event.mouse_x
        self._mouse_y = event.mouse_region_y if hasattr(event, 'mouse_region_y') else event.mouse_y

        # 尝试读取上次的选择类型（使用场景属性存储）
        try:
            last_type = context.scene.get("mmy_smart_select_last_type", 'ISLAND')
            self.select_type = last_type
        except:
            pass

        # 使用 invoke_props_popup 在鼠标位置弹出（比 invoke_props_dialog 更轻量）
        return context.window_manager.invoke_props_popup(self, event)


# ============ 双击检测监听器 ============

class MMY_OT_SmartSelectHandler(bpy.types.Operator):
    """智能选择处理器 - 持续监听双击事件"""
    bl_idname = "mmy.smart_select_handler"
    bl_label = "智能选择处理器"
    bl_options = {'REGISTER'}

    _running = False

    def modal(self, context, event):
        # 调试：检查 modal 是否收到任何事件
        if event.type == 'LEFTMOUSE':
            print(f"[Smart Select] Modal 收到 LEFTMOUSE: value={event.value}, area={context.area.type if context.area else 'None'}")

        # 只处理左键点击
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # context.area 在窗口级别 modal 中可能为 None
            # 需要从鼠标位置找到实际区域
            mouse_x = event.mouse_x
            mouse_y = event.mouse_y

            # 从窗口找到鼠标所在的区域
            window = context.window
            area = None
            if window:
                screen = window.screen
                if screen:
                    for a in screen.areas:
                        if (a.x <= mouse_x <= a.x + a.width and
                            a.y <= mouse_y <= a.y + a.height):
                            area = a
                            break

            if area is None:
                return {'PASS_THROUGH'}

            # 调试：打印区域信息
            print(f"[Smart Select] 区域检查: type={area.type}")

            # 只在 VIEW_3D 和 IMAGE_EDITOR（UV模式）中触发
            if area.type not in ('VIEW_3D', 'IMAGE_EDITOR'):
                return {'PASS_THROUGH'}

            # IMAGE_EDITOR 需要检查是否是 UV 模式
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                if space:
                    print(f"[Smart Select] UV空间模式: {space.mode if hasattr(space, 'mode') else 'N/A'}")
                    # UV 编辑器 mode 为 'VIEW' 时是 UV 编辑模式
                    if hasattr(space, 'mode') and space.mode != 'VIEW':
                        return {'PASS_THROUGH'}

            # 检查是否启用
            addon = context.preferences.addons.get("mmy_toolkit")
            if not addon or not getattr(addon.preferences, "smart_select_enabled", True):
                return {'PASS_THROUGH'}

            interval = getattr(addon.preferences, "smart_select_double_click_interval", DOUBLE_CLICK_INTERVAL)

            current_time = time.time()

            global _last_click_time, _last_click_x, _last_click_y

            # 调试：打印每次点击
            print(f"[Smart Select] 点击检测: time_diff={current_time - _last_click_time:.2f}")

            if current_time - _last_click_time < interval:
                dx = abs(mouse_x - _last_click_x)
                dy = abs(mouse_y - _last_click_y)
                if dx < CLICK_POS_TOLERANCE and dy < CLICK_POS_TOLERANCE:
                    # 双击触发！
                    print("[Smart Select] 双击检测成功！")
                    _last_click_time = 0
                    try:
                        bpy.ops.mmy.smart_select_dialog('INVOKE_DEFAULT')
                    except Exception as e:
                        print(f"[Smart Select] 弹出面板失败: {e}")
                    return {'PASS_THROUGH'}

            # 记录点击
            _last_click_time = current_time
            _last_click_x = mouse_x
            _last_click_y = mouse_y

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if self._running:
            return {'PASS_THROUGH'}

        self._running = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def _start_handler_delayed():
    """延迟启动监听器"""
    try:
        bpy.ops.mmy.smart_select_handler('INVOKE_DEFAULT')
        print("[Smart Select] 监听器已启动")
    except Exception as e:
        print(f"[Smart Select] 启动失败: {e}")
    return None


_classes = (
    MMY_OT_SmartSelectUVIsland,
    MMY_OT_SmartSelectUVSeams,
    MMY_OT_SmartSelectMaterial,
    MMY_OT_SmartSelectDialog,
    MMY_OT_SmartSelectHandler,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.app.timers.register(_start_handler_delayed, first_interval=1.0)


def unregister():
    MMY_OT_SmartSelectHandler._running = False

    try:
        bpy.app.timers.unregister(_start_handler_delayed)
    except:
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass