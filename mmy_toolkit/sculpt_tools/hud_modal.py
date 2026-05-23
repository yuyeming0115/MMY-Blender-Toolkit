"""雕刻 HUD Modal Operator"""

import bpy
from .hud_state import _HUD_STATE
from .hud_draw import HUD_BUTTON_WIDTH, HUD_BUTTON_HEIGHT, HUD_BUTTON_GAP, HUD_MARGIN


def get_region_key(window, area, region):
    """获取 region 唯一标识"""
    return (window.as_pointer(), area.as_pointer(), region.as_pointer())


def find_button_at_point(window, mouse_x, mouse_y):
    """查找鼠标位置对应的按钮"""
    context = bpy.context
    area = getattr(context, "area", None)
    region = getattr(context, "region", None)
    space = getattr(context, "space_data", None)
    obj = getattr(context, "active_object", None)

    if area is None or region is None or space is None or obj is None:
        return None, None, None, None

    if obj.mode != 'SCULPT':
        return None, None, None, None

    # 获取偏好设置计算位置
    addon = context.preferences.addons.get("mmy_toolkit")
    prefs = addon.preferences if addon else None

    layout_mode = getattr(prefs, "sculpt_hud_layout", "horizontal") if prefs else "horizontal"
    offset_x = getattr(prefs, "sculpt_hud_offset_x", 0) if prefs else 0
    offset_y = getattr(prefs, "sculpt_hud_offset_y", 0) if prefs else 0

    from .hud_state import _DEFAULT_BUTTONS
    buttons = _DEFAULT_BUTTONS

    if layout_mode == "horizontal":
        total_width = len(buttons) * HUD_BUTTON_WIDTH + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        total_height = HUD_BUTTON_HEIGHT + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5
    else:
        total_width = HUD_BUTTON_WIDTH + HUD_MARGIN * 2
        total_height = len(buttons) * HUD_BUTTON_HEIGHT + (len(buttons) - 1) * HUD_BUTTON_GAP + HUD_MARGIN * 2
        start_x = region.width * 0.5 + offset_x * region.width - total_width * 0.5
        start_y = region.height * 0.5 + offset_y * region.height - total_height * 0.5

    # 转换鼠标坐标（region 相对）
    region_mouse_x = mouse_x - region.x
    region_mouse_y = mouse_y - region.y

    # 检查是否在 HUD 区域内
    if not (start_x <= region_mouse_x <= start_x + total_width and
            start_y <= region_mouse_y <= start_y + total_height):
        return None, None, None, None

    # 查找具体按钮
    for i, button_id in enumerate(buttons):
        if layout_mode == "horizontal":
            btn_x = start_x + HUD_MARGIN + i * (HUD_BUTTON_WIDTH + HUD_BUTTON_GAP)
            btn_y = start_y + HUD_MARGIN
        else:
            btn_x = start_x + HUD_MARGIN
            btn_y = start_y + HUD_MARGIN + i * (HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP)

        if (btn_x <= region_mouse_x <= btn_x + HUD_BUTTON_WIDTH and
            btn_y <= region_mouse_y <= btn_y + HUD_BUTTON_HEIGHT):
            return area, region, space, button_id

    # 在 HUD 区域内但没有点击到按钮
    return area, region, space, "HUD_AREA"


class VIEW3D_OT_mmy_sculpt_hud_modal(bpy.types.Operator):
    """雕刻 HUD Modal Operator"""
    bl_idname = "view3d.mmy_sculpt_hud_modal"
    bl_label = "MMY Sculpt HUD Modal"
    bl_description = "雕刻模式悬浮按钮事件处理"
    bl_options = {"INTERNAL"}

    _window_id = None

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

        window = getattr(context, "window", None)
        if window is None or window.as_pointer() != self._window_id:
            return self._finish()

        if event.type == 'MOUSEMOVE':
            self._update_hover(window, event.mouse_x, event.mouse_y)
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            area, region, space, button_id = find_button_at_point(window, event.mouse_x, event.mouse_y)

            if button_id is None or button_id == "HUD_AREA":
                return {'PASS_THROUGH'}

            if area and region and space:
                result = self._activate_button(context, space, button_id)
                if result:
                    return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            # 右键菜单（布局切换等）
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    def _update_hover(self, window, mouse_x, mouse_y):
        area, region, space, button_id = find_button_at_point(window, mouse_x, mouse_y)

        if button_id is None or area is None or region is None:
            if _HUD_STATE["hover"] is not None:
                _HUD_STATE["hover"] = None
                self._redraw(area)
            return

        region_key = get_region_key(window, area, region)
        hover_value = (region_key, button_id) if button_id != "HUD_AREA" else None

        if _HUD_STATE["hover"] != hover_value:
            _HUD_STATE["hover"] = hover_value
            self._redraw(area)

    def _activate_button(self, context, space, button_id):
        """激活按钮功能"""
        obj = context.active_object
        overlay = space.overlay if space else None

        if button_id == "face_sets":
            if overlay:
                overlay.sculpt_show_face_sets = not overlay.sculpt_show_face_sets
            return True
        elif button_id == "mask":
            # 切换遮罩显示
            if overlay:
                overlay.show_mode_face_sets = not overlay.show_mode_face_sets
            return True
        elif button_id == "wireframe":
            if obj:
                obj.show_wire = not obj.show_wire
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


_classes = (VIEW3D_OT_mmy_sculpt_hud_modal,)


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