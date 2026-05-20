import bpy
import bmesh
from mathutils import Vector
import math


def calc_max_style_normals(mesh):
    """
    智能平滑组算法。

    逻辑（尊重模型原有状态）：

    对于 Group 0（未设置）的面：
      - 保持原有的 face.smooth 状态
      - 原本 Flat 的面保持 Flat
      - 原本 Smooth 的面保持 Smooth

    对于 Group 1-32（已设置）的面：
      - Group 0 + Group X = 硬边（分隔效果）
      - Group X + Group X = 平滑（同组）
      - Group X + Group Y = 硬边（不同组，且 X&Y==0）
    """
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    sg_layer = bm.faces.layers.int.get("smoothing_groups")
    if not sg_layer:
        sg_layer = bm.faces.layers.int.new("smoothing_groups")

    face_smooth_state = {}
    for f in bm.faces:
        face_smooth_state[f.index] = f.smooth

    loop_normals = [None] * len(mesh.loops)

    for v in bm.verts:
        if not v.link_faces:
            continue

        link_faces = v.link_faces

        if len(link_faces) == 1:
            f = link_faces[0]
            for loop in v.link_loops:
                loop_normals[loop.index] = f.normal
            continue

        connected_data = []
        for f in link_faces:
            connected_data.append((
                f[sg_layer],
                f.normal,
                face_smooth_state[f.index]
            ))

        for loop in v.link_loops:
            current_face = loop.face
            current_sg = current_face[sg_layer]
            current_normal = current_face.normal
            current_smooth = face_smooth_state[current_face.index]

            avg_x, avg_y, avg_z = 0.0, 0.0, 0.0

            for other_sg, other_n, other_smooth in connected_data:
                is_compatible = False

                if current_sg == 0 and other_sg == 0:
                    if current_smooth and other_smooth:
                        is_compatible = True
                elif current_sg == 0 or other_sg == 0:
                    is_compatible = False
                elif (current_sg & other_sg) != 0:
                    is_compatible = True

                if is_compatible:
                    avg_x += other_n.x
                    avg_y += other_n.y
                    avg_z += other_n.z

            length_sq = avg_x*avg_x + avg_y*avg_y + avg_z*avg_z
            if length_sq < 0.0001:
                loop_normals[loop.index] = current_normal
            else:
                inv_len = 1.0 / math.sqrt(length_sq)
                loop_normals[loop.index] = Vector((avg_x * inv_len, avg_y * inv_len, avg_z * inv_len))

    bm.to_mesh(mesh)
    bm.free()

    for i in range(len(loop_normals)):
        if loop_normals[i] is None:
            loop_normals[i] = Vector((0, 0, 1))

    if bpy.app.version < (4, 1, 0):
        mesh.use_auto_smooth = True

    mesh.normals_split_custom_set(loop_normals)


def hide_sharp_edge_overlay():
    """隐藏所有 3D 视图中的锐边青色显示"""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.overlay.show_edge_sharp = False
    except:
        pass


def show_sharp_edge_overlay():
    """显示所有 3D 视图中的锐边青色显示"""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.overlay.show_edge_sharp = True
    except:
        pass