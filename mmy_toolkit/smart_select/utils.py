"""智能选择工具函数"""

import bpy
import bmesh


def select_uv_island(context, mouse_x, mouse_y):
    """在 UV 编辑器中选中鼠标位置的 UV 孤岛"""
    # 使用 Blender 内置的 select_linked_pick
    # 需要在 UV 编辑器上下文
    try:
        # 尝试使用 select_linked_pick（Blender 4.0+）
        bpy.ops.uv.select_linked_pick(
            'INVOKE_DEFAULT',
            extend=False,
            location=(mouse_x, mouse_y)
        )
        return True
    except:
        # 备用方案：先选中点击位置的元素，再 select_linked
        try:
            bpy.ops.uv.select(extend=False, location=(mouse_x, mouse_y))
            bpy.ops.uv.select_linked()
            return True
        except:
            return False


def select_uv_seams(context):
    """选中所有 UV 缝合边"""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return False

    # 需要在编辑模式
    if obj.mode != 'EDIT':
        return False

    bm = bmesh.from_edit_mesh(obj.data)
    if not bm:
        return False

    # 清除当前选择
    for edge in bm.edges:
        edge.select = False

    # 选中所有缝合边
    count = 0
    for edge in bm.edges:
        if edge.seam:
            edge.select = True
            count += 1

    bmesh.update_edit_mesh(obj.data)

    # 切换到边选择模式
    bpy.context.tool_settings.mesh_select_mode = (False, True, False)

    return count > 0


def select_faces_by_material(context, mouse_x, mouse_y):
    """选中所有与点击面相同材质的面"""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return False, 0

    # 需要在编辑模式
    if obj.mode != 'EDIT':
        return False, 0

    bm = bmesh.from_edit_mesh(obj.data)
    if not bm:
        return False, 0

    # 确保面选择模式
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    # 获取点击位置的面（通过视图射线检测）
    # 由于 Blender API 限制，我们使用当前选中的面作为基准
    # 如果没有选中面，先尝试选中一个

    # 获取当前选中的面的材质索引
    selected_faces = [f for f in bm.faces if f.select]
    if not selected_faces:
        # 没有选中面，无法确定材质
        return False, 0

    # 取第一个选中面的材质索引
    target_material_index = selected_faces[0].material_index

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

    return True, count


def get_context_type(context):
    """获取当前上下文类型"""
    area = context.area
    if area:
        if area.type == 'IMAGE_EDITOR':
            # UV 编辑器
            space = area.spaces.active
            if space and space.mode == 'VIEW':
                return 'UV_EDITOR'
        elif area.type == 'VIEW_3D':
            if context.mode == 'EDIT_MESH':
                return 'VIEW_3D_EDIT'
    return None