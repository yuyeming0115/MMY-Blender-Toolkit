"""雕刻工具模块 - 悬浮按钮 + 右键菜单"""

import bpy
from .hud_state import _HUD_STATE, reset_hud_runtime_state
from .hud_draw import draw_sculpt_hud_callback
from .hud_modal import register as register_modal, unregister as unregister_modal


# ============ 面组右键菜单 ============

class MMY_MT_SculptFaceSets(bpy.types.Menu):
    """面组菜单"""
    bl_idname = "MMY_MT_sculpt_face_sets"
    bl_label = "面组"

    def draw(self, context):
        layout = self.layout

        # 创建面组
        layout.label(text="创建")
        layout.operator("sculpt.face_sets_create", text="从遮罩创建").mode = 'MASKED'
        layout.operator("sculpt.face_sets_create", text="从可见面创建").mode = 'VISIBLE'
        layout.operator("sculpt.face_sets_create", text="全部").mode = 'ALL'

        layout.separator()

        # 可见性控制
        layout.label(text="可见性")
        layout.operator("sculpt.face_set_change_visibility", text="切换显示")
        layout.operator("sculpt.face_set_invert_visibility", text="反转可见性")

        layout.separator()

        # 全局控制
        layout.label(text="全局")
        layout.operator("sculpt.face_set_hide_all", text="隐藏全部")
        layout.operator("sculpt.face_set_show_all", text="显示全部")

        layout.separator()

        # 编辑功能
        layout.label(text="编辑")
        layout.operator("sculpt.face_set_edit", text="填充面组").mode = 'GROW'
        layout.operator("sculpt.face_set_edit", text="收缩面组").mode = 'SHRINK'


_classes = (MMY_MT_SculptFaceSets,)


def _draw_sculpt_context_menu(self, context):
    """扩展雕刻模式右键菜单（Panel）"""
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'SCULPT':
        return

    layout = self.layout
    layout.separator()

    # 添加面组菜单
    layout.menu("MMY_MT_sculpt_face_sets", text="面组", icon='GROUP_VERTEX')


# ============ HUD Modal Timer ============

def _ensure_hud_modal_running():
    """确保 HUD Modal Operator 在所有窗口运行"""
    print(f"[MMY Sculpt] Timer 触发: enabled={_HUD_STATE['enabled']}")

    if not _HUD_STATE["enabled"]:
        _HUD_STATE["timer_registered"] = False
        return None

    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        print(f"[MMY Sculpt] window_manager 为 None")
        return 0.5

    print(f"[MMY Sculpt] 检查窗口数量: {len(wm.windows)}")

    for window in wm.windows:
        window_id = window.as_pointer()
        if window_id in _HUD_STATE["modal_windows"]:
            print(f"[MMY Sculpt] 窗口 {window_id} 已有 Modal 运行")
            continue

        screen = getattr(window, "screen", None)
        if screen is None:
            print(f"[MMY Sculpt] 窗口 {window_id} 无 screen")
            continue

        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue

            # 使用 invoke 方式启动 modal
            try:
                with bpy.context.temp_override(window=window, area=area, region=region):
                    result = bpy.ops.view3d.mmy_sculpt_hud_modal('INVOKE_DEFAULT')
                    print(f"[MMY Sculpt] Modal 启动结果: {result}, 窗口: {window_id}")
            except Exception as e:
                print(f"[MMY Sculpt] Modal 启动失败: {e}")
            break

    return 1.0


def register_hud_modal_timer():
    if _HUD_STATE["timer_registered"]:
        return
    bpy.app.timers.register(_ensure_hud_modal_running, first_interval=0.2)
    _HUD_STATE["timer_registered"] = True


def unregister_hud_modal_timer():
    try:
        bpy.app.timers.unregister(_ensure_hud_modal_running)
    except:
        pass
    _HUD_STATE["timer_registered"] = False


# ============ 注册/注销 ============

def register():
    """注册模块"""
    # 启用 HUD
    _HUD_STATE["enabled"] = True
    reset_hud_runtime_state()

    # 注册菜单类
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)

    # 注册 Modal Operator（必须先注册）
    register_modal()

    # 挂载绘制回调
    try:
        _HUD_STATE["draw_handler"] = bpy.types.SpaceView3D.draw_handler_add(
            draw_sculpt_hud_callback,
            (),
            "WINDOW",
            "POST_PIXEL",
        )
    except Exception as e:
        print(f"[MMY Sculpt] 挂载绘制回调失败: {e}")

    # 挂载右键菜单
    try:
        bpy.types.VIEW3D_PT_sculpt_context_menu.append(_draw_sculpt_context_menu)
    except Exception as e:
        print(f"[MMY Sculpt] 挂载右键菜单失败: {e}")

    # 启动 Modal Timer（延迟启动，确保操作符已注册）
    bpy.app.timers.register(_delayed_start_modal, first_interval=0.5)

    # 添加文件加载后处理（重新启动 Modal）
    if _on_file_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_file_loaded)

    print("[MMY Sculpt] 悬浮按钮系统已启用")


def _on_file_loaded(dummy):
    """文件加载后重新启动 HUD Modal"""
    print(f"[MMY Sculpt] 文件加载完成，重新初始化 HUD")

    # 完全重置状态
    reset_hud_runtime_state()

    # 确保 draw handler 还在
    if _HUD_STATE["draw_handler"] is None:
        try:
            _HUD_STATE["draw_handler"] = bpy.types.SpaceView3D.draw_handler_add(
                draw_sculpt_hud_callback,
                (),
                "WINDOW",
                "POST_PIXEL",
            )
            print(f"[MMY Sculpt] 重新挂载 draw_handler")
        except Exception as e:
            print(f"[MMY Sculpt] 挂载绘制回调失败: {e}")

    # Blender 文件加载会清除所有 Timer，需要重新注册
    # 使用稍长的延迟确保 Blender 完全加载完
    try:
        bpy.app.timers.register(_ensure_hud_modal_running, first_interval=1.0)
        _HUD_STATE["timer_registered"] = True
        print(f"[MMY Sculpt] 文件加载后重新启动 Timer")
    except Exception as e:
        print(f"[MMY Sculpt] 启动 Timer 失败: {e}")


def _periodic_hud_check():
    """定期检查 HUD 是否正常运行（备用机制）"""
    # 检查是否在雕刻模式
    obj = getattr(bpy.context, "active_object", None)
    if obj and obj.mode == 'SCULPT':
        # 确保 Modal 在运行
        wm = getattr(bpy.context, "window_manager", None)
        if wm:
            for window in wm.windows:
                window_id = window.as_pointer()
                if window_id not in _HUD_STATE["modal_windows"]:
                    screen = getattr(window, "screen", None)
                    if screen:
                        for area in screen.areas:
                            if area.type == "VIEW_3D":
                                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                                if region:
                                    try:
                                        with bpy.context.temp_override(window=window, area=area, region=region):
                                            bpy.ops.view3d.mmy_sculpt_hud_modal('INVOKE_DEFAULT')
                                    except:
                                        pass
                                break
    return 5.0  # 每5秒检查一次


def _delayed_start_modal():
    """延迟启动 Modal"""
    register_hud_modal_timer()

    # 启动定期检查 Timer（备用机制）
    try:
        bpy.app.timers.register(_periodic_hud_check, first_interval=5.0, persistent=True)
    except:
        pass

    return None  # 一次性 timer


def unregister():
    """注销模块"""
    # 禁用 HUD
    _HUD_STATE["enabled"] = False
    reset_hud_runtime_state()

    # 移除文件加载 handler
    try:
        bpy.app.handlers.load_post.remove(_on_file_loaded)
    except:
        pass

    # 停止 Modal Timer
    unregister_hud_modal_timer()

    # 移除绘制回调
    if _HUD_STATE["draw_handler"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_HUD_STATE["draw_handler"], "WINDOW")
        except:
            pass
        _HUD_STATE["draw_handler"] = None

    # 移除右键菜单
    try:
        bpy.types.VIEW3D_PT_sculpt_context_menu.remove(_draw_sculpt_context_menu)
    except:
        pass

    # 注销 Modal Operator
    unregister_modal()

    # 注销菜单类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    print("[MMY Sculpt] 悬浮按钮系统已禁用")