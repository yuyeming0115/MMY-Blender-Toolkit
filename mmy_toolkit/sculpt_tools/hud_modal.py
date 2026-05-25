"""雕刻 HUD Modal Operator"""

import bpy
from .hud_state import _HUD_STATE, _AVAILABLE_BUTTONS, get_user_buttons, get_global_offset
from .hud_draw import HUD_BUTTON_WIDTH, HUD_BUTTON_HEIGHT, HUD_BUTTON_GAP, HUD_MARGIN, HUD_HANDLE_WIDTH


# ============ 添加按钮菜单 ============

class MMY_MT_HUDAddButtonMenu(bpy.types.Menu):
    """添加按钮菜单"""
    bl_idname = "MMY_MT_hud_add_button_menu"
    bl_label = "添加按钮"

    def draw(self, context):
        layout = self.layout
        user_buttons = get_user_buttons()

        for button_id, info in _AVAILABLE_BUTTONS.items():
            if button_id not in user_buttons:
                symbol = info.get("symbol", "?")
                label = info.get("label", "?")
                layout.operator("mmy.hud_add_button", text=f"{symbol} {label}").button_id = button_id

        layout.separator()
        layout.operator("mmy.hud_reset_buttons", text="重置默认")


class MMY_OT_HUDAddButton(bpy.types.Operator):
    """添加 HUD 按钮"""
    bl_idname = "mmy.hud_add_button"
    bl_label = "添加按钮"
    bl_options = {'INTERNAL'}

    button_id: bpy.props.StringProperty()

    def execute(self, context):
        from .hud_state import add_user_button
        add_user_button(self.button_id)
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        return {'FINISHED'}


class MMY_MT_HUDManageButtonsMenu(bpy.types.Menu):
    """管理按钮菜单"""
    bl_idname = "MMY_MT_hud_manage_buttons_menu"
    bl_label = "管理按钮"

    def draw(self, context):
        layout = self.layout
        user_buttons = get_user_buttons()

        for button_id in user_buttons:
            info = _AVAILABLE_BUTTONS.get(button_id, {})
            symbol = info.get("symbol", "?")
            label = info.get("label", "?")
            layout.operator("mmy.hud_remove_button", text=f"移除 {symbol} {label}").button_id = button_id

        layout.separator()
        layout.operator("mmy.hud_reset_buttons", text="重置默认")


class MMY_OT_HUDRemoveButton(bpy.types.Operator):
    """移除 HUD 按钮"""
    bl_idname = "mmy.hud_remove_button"
    bl_label = "移除按钮"
    bl_options = {'INTERNAL'}

    button_id: bpy.props.StringProperty()

    def execute(self, context):
        from .hud_state import remove_user_button
        remove_user_button(self.button_id)
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        return {'FINISHED'}


class MMY_OT_HUDResetButtons(bpy.types.Operator):
    """重置为默认按钮配置"""
    bl_idname = "mmy.hud_reset_buttons"
    bl_label = "重置默认"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        from .hud_state import reset_user_buttons
        reset_user_buttons()
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        return {'FINISHED'}


# ============ 布局切换菜单 ============

class MMY_MT_HUDLayoutMenu(bpy.types.Menu):
    """HUD 布局切换菜单"""
    bl_idname = "MMY_MT_hud_layout_menu"
    bl_label = "HUD 布局"

    def draw(self, context):
        layout = self.layout
        layout.operator("mmy.hud_layout_horizontal", text="水平布局").layout_mode = "horizontal"
        layout.operator("mmy.hud_layout_vertical", text="垂直布局").layout_mode = "vertical"
        layout.separator()
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
        from .hud_state import reset_global_offset
        reset_global_offset()
        for window in context.window_manager.windows:
            screen = getattr(window, "screen", None)
            if screen:
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()
        return {'FINISHED'}


# ============ 位置检测 ============

def get_region_key(window, area, region):
    """获取 region 唯一标识"""
    return (window.as_pointer(), area.as_pointer(), region.as_pointer())


def find_button_at_point(window, mouse_x, mouse_y, area_id=None, region_id=None):
    """查找鼠标位置对应的按钮或把手"""
    context = bpy.context
    area, region = None, None

    screen = getattr(window, "screen", None)
    if screen:
        for a in screen.areas:
            if (a.x <= mouse_x <= a.x + a.width and a.y <= mouse_y <= a.y + a.height):
                area = a
                for r in a.regions:
                    if (r.x <= mouse_x <= r.x + r.width and r.y <= mouse_y <= r.y + r.height):
                        region = r
                        break
                break

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

    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None
    layout_mode = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"

    offset_x, offset_y = get_global_offset()

    user_buttons = get_user_buttons()
    buttons = user_buttons + ["add"]
    button_count = len(buttons)

    if layout_mode == "horizontal":
        total_width = HUD_HANDLE_WIDTH + button_count * HUD_BUTTON_WIDTH + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = HUD_HANDLE_WIDTH + button_count * HUD_BUTTON_HEIGHT + (button_count - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5

    region_mouse_x = mouse_x - region.x
    region_mouse_y = mouse_y - region.y

    if not (start_x <= region_mouse_x <= start_x + total_width and start_y <= region_mouse_y <= start_y + total_height):
        return None, None, None, None

    # 检查把手
    if layout_mode == "horizontal":
        handle_x, handle_y = start_x, start_y
        handle_w, handle_h = HUD_HANDLE_WIDTH, total_height
    else:
        handle_x = start_x
        handle_y = start_y + total_height - HUD_HANDLE_WIDTH
        handle_w, handle_h = total_width, HUD_HANDLE_WIDTH

    if (handle_x <= region_mouse_x <= handle_x + handle_w and handle_y <= region_mouse_y <= handle_y + handle_h):
        return area, region, space, "handle"

    # 检查按钮
    button_order = buttons if layout_mode == "horizontal" else list(reversed(buttons))
    for i, button_id in enumerate(button_order):
        if layout_mode == "horizontal":
            btn_x = start_x + HUD_HANDLE_WIDTH + HUD_MARGIN + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            btn_y = start_y + HUD_MARGIN
        else:
            btn_x = start_x + HUD_MARGIN
            btn_y = start_y + HUD_MARGIN + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)

        if (btn_x <= region_mouse_x <= btn_x + HUD_BUTTON_WIDTH and btn_y <= region_mouse_y <= btn_y + HUD_BUTTON_HEIGHT):
            return area, region, space, button_id

    return area, region, space, "HUD_AREA"


# ============ Modal Operator ============

class VIEW3D_OT_mmy_sculpt_hud_modal(bpy.types.Operator):
    """雕刻 HUD Modal Operator"""
    bl_idname = "view3d.mmy_sculpt_hud_modal"
    bl_label = "MMY Sculpt HUD Modal"
    bl_description = "雕刻模式悬浮按钮事件处理"
    bl_options = {"INTERNAL"}

    _window_id = None
    _dragging = False
    _drag_start_x = 0
    _drag_start_y = 0
    _drag_start_offset_x = 0
    _drag_start_offset_y = 0

    def invoke(self, context, event):
        if not _HUD_STATE["enabled"]:
            return {'CANCELLED'}

        window = getattr(context, "window", None)
        area = getattr(context, "area", None)
        if window is None or area is None or area.type != "VIEW_3D":
            return {'CANCELLED'}

        self._window_id = window.as_pointer()
        if self._window_id in _HUD_STATE["modal_windows"]:
            return {'CANCELLED'}

        _HUD_STATE["modal_windows"].add(self._window_id)
        _HUD_STATE["modal_running"] = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not _HUD_STATE["enabled"]:
            return self._finish()
        if self._window_id not in _HUD_STATE["modal_windows"]:
            return self._finish()

        window = getattr(context, "window", None)
        if window is None:
            return {'PASS_THROUGH'}

        # 拖拽处理
        if self._dragging:
            if event.type == 'MOUSEMOVE':
                self._update_drag_position(context, event.mouse_x, event.mouse_y)
                return {'RUNNING_MODAL'}
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self._dragging = False
                return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self._update_hover(window, event.mouse_x, event.mouse_y)
            return {'PASS_THROUGH'}

        # 左键点击
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            area, region, space, button_id = find_button_at_point(window, event.mouse_x, event.mouse_y)
            print(f"[MMY Sculpt] 左键点击: button_id={button_id}")

            if button_id is None or button_id == "HUD_AREA":
                return {'PASS_THROUGH'}

            if button_id == "handle":
                self._start_drag(context, event.mouse_x, event.mouse_y)
                return {'RUNNING_MODAL'}

            if button_id == "add":
                # 左键点击 +按钮：弹出添加菜单
                bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="MMY_MT_hud_add_button_menu")
                return {'RUNNING_MODAL'}

            if area and region and space:
                result = self._activate_button(context, space, button_id)
                if result:
                    return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        # 右键点击
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            area, region, space, button_id = find_button_at_point(window, event.mouse_x, event.mouse_y)

            if button_id == "handle":
                bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="MMY_MT_hud_layout_menu")
                return {'RUNNING_MODAL'}

            if button_id == "add":
                # 右键点击 +按钮：弹出管理菜单
                bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="MMY_MT_hud_manage_buttons_menu")
                return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _start_drag(self, context, mouse_x, mouse_y):
        offset_x, offset_y = get_global_offset()
        self._dragging = True
        self._drag_start_x = mouse_x
        self._drag_start_y = mouse_y
        self._drag_start_offset_x = offset_x
        self._drag_start_offset_y = offset_y

    def _update_drag_position(self, context, mouse_x, mouse_y):
        from .hud_state import set_global_offset
        window = getattr(context, "window", None)
        if not window:
            return

        area, region = None, None
        screen = getattr(window, "screen", None)
        if screen:
            for a in screen.areas:
                if (a.x <= mouse_x <= a.x + a.width and a.y <= mouse_y <= a.y + a.height):
                    area = a
                    for r in a.regions:
                        if (r.x <= mouse_x <= r.x + r.width and r.y <= mouse_y <= r.y + r.height):
                            region = r
                            break
                    break

        if not area or not region or area.type != "VIEW_3D":
            return

        delta_x = (mouse_x - self._drag_start_x) / region.width
        delta_y = (mouse_y - self._drag_start_y) / region.height
        set_global_offset(self._drag_start_offset_x + delta_x, self._drag_start_offset_y + delta_y)

        screen = getattr(window, "screen", None)
        if screen:
            for a in screen.areas:
                if a.type == "VIEW_3D":
                    a.tag_redraw()

    def _update_hover(self, window, mouse_x, mouse_y):
        area, region, space, button_id = find_button_at_point(window, mouse_x, mouse_y)
        if button_id is None or area is None or region is None:
            if _HUD_STATE["hover"] is not None:
                _HUD_STATE["hover"] = None
                if area:
                    area.tag_redraw()
            return

        region_key = get_region_key(window, area, region)
        hover_value = (region_key, button_id) if button_id not in ("HUD_AREA", None) else None
        if _HUD_STATE["hover"] != hover_value:
            _HUD_STATE["hover"] = hover_value
            area.tag_redraw()

    def _activate_button(self, context, space, button_id):
        """激活按钮功能"""
        obj = context.active_object
        overlay = space.overlay if space else None
        shading = space.shading if space else None

        if button_id == "face_sets":
            if overlay:
                overlay.show_sculpt_face_sets = not overlay.show_sculpt_face_sets
            return True
        elif button_id == "mask":
            if overlay:
                overlay.show_sculpt_mask = not overlay.show_sculpt_mask
            return True
        elif button_id == "wireframe":
            if overlay:
                overlay.show_wireframes = not overlay.show_wireframes
            return True
        elif button_id == "backface_culling":
            # 背面遮罩
            if shading:
                shading.backface_culling = not shading.backface_culling
            return True
        elif button_id == "symmetry":
            # 雕刻对称
            if obj and obj.type == 'MESH' and obj.data:
                obj.data.use_sculpt_symmetry = not obj.data.use_sculpt_symmetry
            return True
        elif button_id == "dynamic_topology":
            # 动态拓扑
            if obj and obj.type == 'MESH':
                if obj.data.use_dynamic_topology_sculpting:
                    bpy.ops.sculpt.dynamic_topology_toggle()
                else:
                    bpy.ops.sculpt.dynamic_topology_toggle()
            return True

        return False

    def _finish(self):
        if self._window_id in _HUD_STATE["modal_windows"]:
            _HUD_STATE["modal_windows"].discard(self._window_id)
        _HUD_STATE["modal_running"] = bool(_HUD_STATE["modal_windows"])
        if not _HUD_STATE["modal_windows"]:
            _HUD_STATE["hover"] = None
        return {'CANCELLED'}


_classes = (
    MMY_MT_HUDAddButtonMenu,
    MMY_OT_HUDAddButton,
    MMY_MT_HUDManageButtonsMenu,
    MMY_OT_HUDRemoveButton,
    MMY_OT_HUDResetButtons,
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