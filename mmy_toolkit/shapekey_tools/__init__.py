"""形态键工具模块"""

import bpy
from . import operators
from . import menu


_classes = (
    *operators._classes,
    *menu._classes,
)


def register():
    # 注册类
    for cls in _classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            try:
                bpy.utils.unregister_class(cls)
                bpy.utils.register_class(cls)
            except:
                pass

    # 挂载菜单到 3D视口 Object 主菜单
    try:
        bpy.types.VIEW3D_MT_object.append(menu._append_to_object_menu)
        print("[MMY] 形态键菜单已挂载到 VIEW3D_MT_object")
    except Exception as e:
        print(f"[MMY] 挂载 VIEW3D_MT_object 失败: {e}")

    # 挂载菜单到 Object 右键上下文菜单
    try:
        bpy.types.VIEW3D_MT_object_context_menu.append(menu._append_to_object_menu)
        print("[MMY] 形态键菜单已挂载到 VIEW3D_MT_object_context_menu")
    except Exception as e:
        print(f"[MMY] 挂载 VIEW3D_MT_object_context_menu 失败: {e}")


def unregister():
    # 移除菜单挂载
    try:
        bpy.types.VIEW3D_MT_object.remove(menu._append_to_object_menu)
    except:
        pass
    try:
        bpy.types.VIEW3D_MT_object_context_menu.remove(menu._append_to_object_menu)
    except:
        pass

    # 注销类
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass