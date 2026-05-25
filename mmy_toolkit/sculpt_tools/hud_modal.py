"""雕刻 HUD Modal Operator"""

import bpy
from .hud_state import _HUD_STATE
from .hud_draw import HUD_BUTTON_WIDTH, HUD_BUTTON_HEIGHT, HUD_BUTTON_GAP, HUD_MARGIN, HUD_HANDLE_WIDTH


# ============ 布局切换菜单 ============

class MMY_MT_HUDLayoutMenu(bpy.types.Menu):
    """HUD 布局切换菜单"""
    bl_idname = "MMY_MT_hud_layout_menu"
    bl_label = "HUD 布局"

    def draw(self, context):
        layout = self.layout
        addon = context.preferences.addons.get("mmy_toolkit")
        prefs = addon.preferences if addon else None
        current_layout = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"

        layout.operator("mmy.hud_layout_horizontal", text="水平布局").layout_mode = "horizontal"
        layout.operator("mmy.hud_layout_vertical", text="垂直布局").layout_mode = "vertical"

        layout.separator()

        # 重置位置
        layout.operator("mmy.hud_layout_reset", text="重置位置")


class MMY_OT_HUDLayoutHorizontal(bpy.types.Operator):
    """切换为水平布局"""
    bl_idname = "mmy.hud_layout_horizontal"
    bl_label = "水平布局"
    bl_options = {'INTERNAL'}

    layout_mode: bpy.props.StringProperty(default="horizontal")

    def execute(self, context):
        addon = context.preferences.addons.get("mmy_toolkit")
        prefs = addon.preferences if addon else None
        if prefs:
            prefs.sculpt_hud_layout = self.layout_mode
        return {'FINISHED'}


class MMY_OT_HUDLayoutVertical(bpy.types.Operator):
    """切换为垂直布局"""
    bl_idname = "mmy.hud_layout_vertical"
    bl_label = "垂直布局"
    bl_options = {'INTERNAL'}

    layout_mode: bpy.props.StringProperty(default="vertical")

    def execute(self, context):
        addon = context.preferences.addons.get("mmy_toolkit")
        prefs = addon.preferences if addon else None
        if prefs:
            prefs.sculpt_hud_layout = self.layout_mode
        return {'FINISHED'}


class MMY_OT_HUDLayoutReset(bpy.types.Operator):
    """重置 HUD 位置"""
    bl_idname = "mmy.hud_layout_reset"
    bl_label = "重置位置"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        from .hud_state import _HUD_STATE
        # 重置所有视窗的偏移值
        _HUD_STATE["window_offsets"].clear()
        return {'FINISHED'}


def get_region_key(window, area, region):
    """获取 region 唯一标识"""
    return (window.as_pointer(), area.as_pointer(), region.as_pointer())


def find_button_at_point(window, mouse_x, mouse_y, area_id=None, region_id=None):
    """查找鼠标位置对应的按钮或把手"""
    context = bpy.context

    # 使用鼠标坐标查找 area 和 region（更可靠）
    area = None
    region = None

    screen = getattr(window, "screen", None)
    if screen:
        for a in screen.areas:
            # 检查鼠标是否在这个 area 内（使用全局坐标）
            if (a.x <= mouse_x <= a.x + a.width and
                a.y <= mouse_y <= a.y + a.height):
                area = a
                # 在这个 area 内查找具体的 region
                for r in a.regions:
                    if (r.x <= mouse_x <= r.x + r.width and
                        r.y <= mouse_y <= r.y + r.height):
                        region = r
                        break
                break

    # 如果没找到，尝试从 context 获取
    if area is None:
        area = getattr(context, "area", None)
    if region is None:
        region = getattr(context, "region", None)

    space = getattr(area, "spaces", None)
    if space:
        space = space.active if hasattr(space, 'active') else space[0] if len(space) > 0 else None
    else:
        space = getattr(context, "space_data", None)

    obj = getattr(context, "active_object", None)

    if area is None or region is None or space is None or obj is None:
        return None, None, None, None

    if obj.mode != 'SCULPT':
        return None, None, None, None

    # 获取偏好设置（布局模式）
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    layout_mode = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"

    # 使用视窗特定的偏移值（与 HUD 绘制保持一致）
    window_id = window.as_pointer()
    from .hud_state import get_window_offset
    offset_x, offset_y = get_window_offset(window_id)

    from .hud_state import _DEFAULT_BUTTONS
    buttons = _DEFAULT_BUTTONS
    handle_width = HUD_HANDLE_WIDTH

    if layout_mode == "horizontal":
        total_width = handle_width + len(buttons) * HUD_BUTTON_WIDTH + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = handle_width + len(buttons) * HUD_BUTTON_HEIGHT + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5

    # 转换鼠标坐标（region 相对）
    region_mouse_x = mouse_x - region.x
    region_mouse_y = mouse_y - region.y

    # 计算 HUD 位置
    from .hud_state import _DEFAULT_BUTTONS
    buttons = _DEFAULT_BUTTONS
    handle_width = HUD_HANDLE_WIDTH

    if layout_mode == "horizontal":
        total_width = handle_width + len(buttons) * HUD_BUTTON_WIDTH + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = handle_width + len(buttons) * HUD_BUTTON_HEIGHT + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5

    # 调试输出（仅在点击时）
    # print(f"[MMY Sculpt] HUD位置: start_x={start_x:.1f}, start_y={start_y:.1f}, 鼠标: ({region_mouse_x:.1f}, {region_mouse_y:.1f})")

    # 检查是否在 HUD 区域内
    if not (start_x <= region_mouse_x <= start_x + total_width and
            start_y <= region_mouse_y <= start_y + total_height):
        return None, None, None, None

    # 先检查把手
    if layout_mode == "horizontal":
        # 水平布局：把手在左边
        handle_x = start_x
        handle_y = start_y
        handle_w = handle_width
        handle_h = total_height
    else:
        # 垂直布局：把手在底部
        handle_x = start_x
        handle_y = start_y + total_height - handle_width
        handle_w = total_width
        handle_h = handle_width

    if (handle_x <= region_mouse_x <= handle_x + handle_w and
        handle_y <= region_mouse_y <= handle_y + handle_h):
        return area, region, space, "handle"

    # 查找具体按钮（垂直布局时反转顺序）
    if layout_mode == "horizontal":
        button_order = buttons
    else:
        button_order = list(reversed(buttons))  # 反转：+, 线框, 遮罩, 面组

    for i, button_id in enumerate(button_order):
        if layout_mode == "horizontal":
            btn_x = start_x + handle_width + HUD_MARGIN + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            btn_y = start_y + HUD_MARGIN
        else:
            # 垂直布局：按钮从上往下，把手在底部
            btn_x = start_x + HUD_MARGIN
            btn_y = start_y + HUD_MARGIN + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)

        if (btn_x <= region_mouse_x <= btn_x + HUD_BUTTON_WIDTH and
            btn_y <= region_mouse_y <= btn_y + HUD_BUTTON_HEIGHT):
            return area, region, space, button_id

    # 在 HUD 区域内但没有点击到按钮或把手
    return area, region, space, "HUD_AREA"


class VIEW3D_OT_mmy_sculpt_hud_modal(bpy.types.Operator):
    """雕刻 HUD Modal Operator"""
    bl_idname = "view3d.mmy_sculpt_hud_modal"
    bl_label = "MMY Sculpt HUD Modal"
    bl_description = "雕刻模式悬浮按钮事件处理"
    bl_options = {"INTERNAL"}

    _window_id = None
    _area_id = None
    _region_id = None
    _dragging = False
    _drag_start_x = 0
    _drag_start_y = 0
    _drag_start_offset_x = 0
    _drag_start_offset_y = 0
    _drag_window_id = None  # 拖拽时记录的视窗 ID

    def invoke(self, context, event):
        if not _HUD_STATE["enabled"]:
            return {'CANCELLED'}

        window = getattr(context, "window", None)
        area = getattr(context, "area", None)
        region = getattr(context, "region", None)
        if window is None or area is None or area.type != "VIEW_3D":
            return {'CANCELLED'}

        self._window_id = window.as_pointer()
        self._area_id = area.as_pointer()
        self._region_id = region.as_pointer() if region else None

        if self._window_id in _HUD_STATE["modal_windows"]:
            return {'CANCELLED'}

        _HUD_STATE["modal_windows"].add(self._window_id)
        _HUD_STATE["modal_running"] = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not _HUD_STATE["enabled"]:
            return self._finish()

        # 不使用指针比较，因为 Blender 可能重新创建对象导致指针变化
        # 只检查 enabled 状态和 modal_windows 中是否有记录
        if self._window_id not in _HUD_STATE["modal_windows"]:
            return self._finish()

        window = getattr(context, "window", None)
        if window is None:
            return {'PASS_THROUGH'}

        # 处理拖拽
        if self._dragging:
            if event.type == 'MOUSEMOVE':
                self._update_drag_position(context, event.mouse_x, event.mouse_y)
                return {'RUNNING_MODAL'}
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self._end_drag()
                return {'RUNNING_MODAL'}

        # 鼠标移动时更新 hover（每 10 次打印一次避免日志过多）
        if event.type == 'MOUSEMOVE':
            self._update_hover(window, event.mouse_x, event.mouse_y)
            return {'PASS_THROUGH'}

        # 点击事件
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            area, region, space, button_id = find_button_at_point(window, event.mouse_x, event.mouse_y, self._area_id, self._region_id)

            # 详细调试
            if area and region:
                hud_x = event.mouse_x - region.x
                hud_y = event.mouse_y - region.y
                print(f"[MMY Sculpt] 点击坐标: 全局({event.mouse_x}, {event.mouse_y}) -> region内({hud_x:.0f}, {hud_y:.0f}), region尺寸({region.width}, {region.height})")
            print(f"[MMY Sculpt] 左键点击: button_id={button_id}")

            if button_id is None or button_id == "HUD_AREA":
                return {'PASS_THROUGH'}

            # 处理把手拖拽
            if button_id == "handle":
                self._start_drag(context, event.mouse_x, event.mouse_y)
                return {'RUNNING_MODAL'}

            if area and region and space:
                result = self._activate_button(context, space, button_id)
                if result:
                    return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            area, region, space, button_id = find_button_at_point(window, event.mouse_x, event.mouse_y, self._area_id, self._region_id)

            # 右键点击把手弹出布局菜单
            if button_id == "handle":
                bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="MMY_MT_hud_layout_menu")
                return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _start_drag(self, context, mouse_x, mouse_y):
        """开始拖拽"""
        from .hud_state import get_window_offset

        window = getattr(context, "window", None)
        if window:
            self._drag_window_id = window.as_pointer()
            offset_x, offset_y = get_window_offset(self._drag_window_id)
        else:
            self._drag_window_id = None
            offset_x, offset_y = 0.0, 0.0

        self._dragging = True
        self._drag_start_x = mouse_x
        self._drag_start_y = mouse_y
        self._drag_start_offset_x = offset_x
        self._drag_start_offset_y = offset_y

    def _update_drag_position(self, context, mouse_x, mouse_y):
        """更新拖拽位置"""
        from .hud_state import set_window_offset

        window = getattr(context, "window", None)
        if not window:
            return

        # 使用鼠标坐标查找 area 和 region
        area, region = None, None
        screen = getattr(window, "screen", None)
        if screen:
            for a in screen.areas:
                if a.type == "VIEW_3D":
                    for r in a.regions:
                        if r.type == "WINDOW":
                            area = a
                            region = r
                            break
                    if area:
                        break

        if not area or not region:
            return

        # 计算偏移变化（相对于 region 尺寸的比例）
        delta_x = (mouse_x - self._drag_start_x) / region.width
        delta_y = (mouse_y - self._drag_start_y) / region.height

        # 更新视窗特定的偏移值（使用开始拖拽时记录的窗口 ID）
        new_offset_x = self._drag_start_offset_x + delta_x
        new_offset_y = self._drag_start_offset_y + delta_y
        set_window_offset(self._drag_window_id, new_offset_x, new_offset_y)

        # 刷新视图
        area.tag_redraw()

    def _end_drag(self):
        """结束拖拽"""
        self._dragging = False

    def _update_hover(self, window, mouse_x, mouse_y):
        area, region, space, button_id = find_button_at_point(window, mouse_x, mouse_y, self._area_id, self._region_id)

        if button_id is None or area is None or region is None:
            if _HUD_STATE["hover"] is not None:
                _HUD_STATE["hover"] = None
                self._redraw(area)
            return

        region_key = get_region_key(window, area, region)
        # 包含 handle 的 hover 值
        hover_value = (region_key, button_id) if button_id not in ("HUD_AREA", None) else None

        if _HUD_STATE["hover"] != hover_value:
            _HUD_STATE["hover"] = hover_value
            self._redraw(area)

    def _activate_button(self, context, space, button_id):
        """激活按钮功能"""
        obj = context.active_object
        overlay = space.overlay if space else None

        if button_id == "face_sets":
            if overlay:
                overlay.show_sculpt_face_sets = not overlay.show_sculpt_face_sets
            return True
        elif button_id == "mask":
            # 切换遮罩显示
            if overlay:
                overlay.show_sculpt_mask = not overlay.show_sculpt_mask
            return True
        elif button_id == "wireframe":
            # 雕刻模式线框显示需要使用 overlay 属性
            if overlay:
                overlay.show_wireframes = not overlay.show_wireframes
                # 刷新视图
                window = getattr(context, "window", None)
                if window:
                    screen = getattr(window, "screen", None)
                    if screen:
                        for a in screen.areas:
                            if a.type == 'VIEW_3D':
                                a.tag_redraw()
            return True
        elif button_id == "add":
            # 添加自定义按钮（暂时不做）
            return False

        return False

    def _redraw(self, area):
        if area:
            area.tag_redraw()

    def _finish(self):
        if self._window_id in _HUD_STATE["modal_windows"]:
            _HUD_STATE["modal_windows"].discard(self._window_id)
        _HUD_STATE["modal_running"] = bool(_HUD_STATE["modal_windows"])
        if not _HUD_STATE["modal_windows"]:
            _HUD_STATE["hover"] = None
        return {'CANCELLED'}


_classes = (
    MMY_MT_HUDLayoutMenu,
    MMY_OT_HUDLayoutHorizontal,
    MMY_OT_HUDLayoutVertical,
    MMY_OT_HUDLayoutReset,
    VIEW3D_OT_mmy_sculpt_hud_modal,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


__all__ = [
    'VIEW3D_OT_mmy_sculpt_hud_modal',
    'find_button_at_point',
    'get_region_key',
]