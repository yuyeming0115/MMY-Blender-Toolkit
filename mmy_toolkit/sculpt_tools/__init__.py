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


# ============ HUD Modal 管理器（单一 Timer） ============

_HUD_TIMER_NAME = "mmy_sculpt_hud_timer"


def _hud_modal_manager():
    """单一 Timer：管理 HUD Modal 生命周期"""
    # 检查是否启用
    if not _HUD_STATE["enabled"]:
        return None  # 停止 Timer

    context = bpy.context
    if context is None:
        return 2.0

    wm = getattr(context, "window_manager", None)
    if wm is None or len(wm.windows) == 0:
        return 2.0

    # 检查每个窗口
    for window in wm.windows:
        window_id = window.as_pointer()

        # 如果这个窗口已有 Modal 运行，跳过
        if window_id in _HUD_STATE["modal_windows"]:
            continue

        screen = getattr(window, "screen", None)
        if screen is None:
            continue

        # 查找 3D 视图区域
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue

            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region is None:
                continue

            # 尝试启动 Modal
            try:
                with context.temp_override(window=window, area=area, region=region):
                    result = bpy.ops.view3d.mmy_sculpt_hud_modal('INVOKE_DEFAULT')
                    print(f"[MMY Sculpt] Modal 启动: {result}, 窗口: {window_id}")
            except Exception as e:
                print(f"[MMY Sculpt] Modal 启动失败: {e}")
            break

    return 2.0  # 每 2 秒检查一次


def _start_hud_timer():
    """启动 HUD Timer"""
    # 使用标志避免重复注册
    if _HUD_STATE.get("timer_active"):
        return

    try:
        bpy.app.timers.register(_hud_modal_manager, first_interval=0.5, persistent=True)
        _HUD_STATE["timer_active"] = True
        print("[MMY Sculpt] Timer 已注册")
    except Exception as e:
        print(f"[MMY Sculpt] Timer 注册失败: {e}")


def _stop_hud_timer():
    """停止 HUD Timer"""
    try:
        bpy.app.timers.unregister(_hud_modal_manager)
        _HUD_STATE["timer_active"] = False
        print("[MMY Sculpt] Timer 已注销")
    except Exception as e:
        # Timer 可能已被 Blender 清除（文件加载后）
        _HUD_STATE["timer_active"] = False
        print(f"[MMY Sculpt] Timer 注销: {e}")


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

    # 启动持久 Timer
    _start_hud_timer()

    # 添加文件加载后处理
    if _on_file_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_file_loaded)

    print("[MMY Sculpt] 悬浮按钮系统已启用")


def _on_file_loaded(dummy):
    """文件加载后重新启动 HUD"""
    print("[MMY Sculpt] 文件加载完成，重新初始化 HUD")

    # 重置运行状态（保持 enabled）
    _HUD_STATE["modal_windows"].clear()
    _HUD_STATE["hover"] = None

    # Blender 文件加载会清除所有 Timer（包括 persistent）
    # 需要重置标志并重新启动
    _HUD_STATE["timer_active"] = False

    # 确保 draw handler 还在
    if _HUD_STATE["draw_handler"] is None:
        try:
            _HUD_STATE["draw_handler"] = bpy.types.SpaceView3D.draw_handler_add(
                draw_sculpt_hud_callback,
                (),
                "WINDOW",
                "POST_PIXEL",
            )
            print("[MMY Sculpt] 重新挂载 draw_handler")
        except Exception as e:
            print(f"[MMY Sculpt] 挂载绘制回调失败: {e}")

    # 重新启动 Timer
    _start_hud_timer()


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

    # 停止 Timer
    _stop_hud_timer()

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