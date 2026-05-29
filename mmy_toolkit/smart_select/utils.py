"""智能选择工具函数"""

import bpy
import bmesh


def select_uv_island(context, mouse_x, mouse_y):
    """在 UV 编辑器中选中鼠标位置的 UV 孤岛"""
    # 找到 UV 编辑器区域
    for area in context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            space = area.spaces.active
            if space and hasattr(space, 'mode') and space.mode == 'VIEW':
                # 找到区域内的鼠标坐标
                for region in area.regions:
                    if region.type == 'WINDOW':
                        # 转换为区域坐标
                        region_mouse_x = mouse_x - region.x
                        region_mouse_y = mouse_y - region.y

                        # 使用 select_linked_pick
                        try:
                            # 临时切换到 UV 编辑器上下文
                            with context.temp_override(area=area, region=region):
                                bpy.ops.uv.select_linked_pick(
                                    extend=False,
                                    location=(region_mouse_x, region_mouse_y)
                                )
                            print(f"[Smart Select] UV孤岛选中成功")
                            return True
                        except Exception as e:
                            print(f"[Smart Select] UV孤岛选中失败: {e}")
                            # 备用：选中所有 UV（简单的全选）
                            try:
                                with context.temp_override(area=area, region=region):
                                    bpy.ops.uv.select_all(action='SELECT')
                                return True
                            except:
                                return False
    return False


def select_uv_seams(context):
    """选中所有 UV 缝合边"""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        print("[Smart Select] 没有活动网格对象")
        return False

    # 需要在编辑模式
    if obj.mode != 'EDIT':
        print("[Smart Select] 不在编辑模式")
        return False

    bm = bmesh.from_edit_mesh(obj.data)
    if not bm:
        return False

    # 清除当前选择
    bpy.ops.mesh.select_all(action='DESELECT')

    # 选中所有缝合边
    count = 0
    for edge in bm.edges:
        if edge.seam:
            edge.select = True
            count += 1

    bmesh.update_edit_mesh(obj.data)

    # 切换到边选择模式
    context.tool_settings.mesh_select_mode = (False, True, False)

    print(f"[Smart Select] 选中 {count} 条缝合边")
    return count > 0


def select_faces_by_material(context, mouse_x, mouse_y):
    """选中所有与点击面相同材质的面"""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        print("[Smart Select] 没有活动网格对象")
        return False, 0

    # 需要在编辑模式
    if obj.mode != 'EDIT':
        print("[Smart Select] 不在编辑模式")
        return False, 0

    # 确保面选择模式
    context.tool_settings.mesh_select_mode = (False, False, True)

    # 获取当前选中的面（双击前用户可能已选中某个面）
    bm = bmesh.from_edit_mesh(obj.data)
    if not bm:
        return False, 0

    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        # 没有选中面，尝试使用 raycast 找到点击位置的面
        # 或者简单地返回 False，让用户先选中一个面
        print("[Smart Select] 没有选中面，请先点击选中一个面")
        return False, 0

    # 取第一个选中面的材质索引
    target_material_index = selected_faces[0].material_index
    print(f"[Smart Select] 目标材质索引: {target_material_index}")

    # 清除当前选择
    for face in bm.faces:
        face.select = False

    # 选中所有相同材质的面
    count = 0
    for face in bm.faces:
        if face.material_index == target_material_index:
            face.select = True
            count += 1

    bmesh.update_edit_mesh(obj.data)

    print(f"[Smart Select] 选中 {count} 个相同材质的面")
    return True, count


def get_context_type_from_mouse(context, mouse_x, mouse_y):
    """从鼠标位置获取上下文类型"""
    window = context.window
    if window:
        screen = window.screen
        if screen:
            for area in screen.areas:
                if (area.x <= mouse_x <= area.x + area.width and
                    area.y <= mouse_y <= area.y + area.height):
                    if area.type == 'IMAGE_EDITOR':
                        space = area.spaces.active
                        if space and hasattr(space, 'mode') and space.mode == 'VIEW':
                            return 'UV_EDITOR'
                    elif area.type == 'VIEW_3D':
                        if context.mode == 'EDIT_MESH':
                            return 'VIEW_3D_EDIT'
    return None