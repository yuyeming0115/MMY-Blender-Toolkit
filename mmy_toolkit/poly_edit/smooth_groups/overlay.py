import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
import bmesh
import colorsys
from collections import deque
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

# 全局变量
draw_handler_2d = None
draw_handler_3d = None

_overlay_data = {
    "cluster_centers": [],
}

# 颜色表
COLORS = {}
EDGE_COLORS = {}
for i in range(1, 33):
    hue = (i * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    COLORS[i] = (r, g, b, 0.4)
    r2, g2, b2 = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    EDGE_COLORS[i] = (r2, g2, b2, 1.0)

MULTI_COLOR = (0.8, 0.4, 1.0, 0.5)
MULTI_EDGE_COLOR = (1.0, 0.5, 1.0, 1.0)


def to_unsigned(val):
    """将有符号 32 位整数转换为无符号表示"""
    if val < 0:
        return val + 0x100000000
    return val


def get_group_ids(val):
    """从位掩码中提取所有组 ID"""
    uval = to_unsigned(val)
    ids = []
    for i in range(32):
        if uval & (1 << i):
            ids.append(i + 1)
    return ids


def get_lowest_group(val):
    """获取最低位的组 ID"""
    if val == 0:
        return 0
    uval = to_unsigned(val)
    for i in range(32):
        if uval & (1 << i):
            return i + 1
    return 0


def is_multi_group(val):
    """检查是否属于多个组"""
    if val == 0:
        return False
    uval = to_unsigned(val)
    return (uval & (uval - 1)) != 0


def draw_3d(self, context):
    global _overlay_data
    _overlay_data["cluster_centers"] = []

    if not context.scene.mmy_poly_edit_show_overlay:
        return

    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return

    try:
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        sg_layer = bm.faces.layers.int.get("smoothing_groups")
        if not sg_layer:
            return

        only_selected = context.scene.mmy_poly_edit_overlay_selected_only
        mat_world = obj.matrix_world

        face_batches = {}
        edge_batches = {}
        multi_faces = []
        multi_edges = []

        OFFSET = 0.003

        face_groups = {}
        multi_face_set = set()

        for f in bm.faces:
            if f.hide: continue
            if only_selected and not f.select: continue
            val = f[sg_layer]
            if val == 0: continue

            if is_multi_group(val):
                multi_face_set.add(f.index)
            else:
                gid = get_lowest_group(val)
                if gid > 0:
                    if gid not in face_groups:
                        face_groups[gid] = set()
                    face_groups[gid].add(f.index)

        visited = set()

        for f in bm.faces:
            if f.hide: continue
            if only_selected and not f.select: continue
            val = f[sg_layer]
            if val == 0: continue
            if f.index in visited: continue
            if f.index in multi_face_set: continue

            gid = get_lowest_group(val)
            if gid == 0:
                continue
            group_faces = face_groups.get(gid, set())

            cluster = []
            queue = deque([f])
            visited.add(f.index)

            while queue:
                cf = queue.popleft()
                cluster.append(cf)

                for e in cf.edges:
                    for nf in e.link_faces:
                        if nf.index in visited: continue
                        if nf.index not in group_faces: continue
                        visited.add(nf.index)
                        queue.append(nf)

            center = Vector((0, 0, 0))
            for cf in cluster:
                center += cf.calc_center_median()
            center /= len(cluster)
            center_world = mat_world @ center

            _overlay_data["cluster_centers"].append((gid, center_world.copy(), False))

            cluster_set = set(cf.index for cf in cluster)

            for cf in cluster:
                f_normal = cf.normal
                verts = cf.verts

                if gid not in face_batches:
                    face_batches[gid] = []

                if len(verts) == 3:
                    v0 = mat_world @ verts[0].co + (f_normal * OFFSET)
                    v1 = mat_world @ verts[1].co + (f_normal * OFFSET)
                    v2 = mat_world @ verts[2].co + (f_normal * OFFSET)
                    face_batches[gid].extend([v0, v1, v2])
                else:
                    poly_points = [v.co for v in verts]
                    tris = tessellate_polygon([poly_points])
                    for tri in tris:
                        v0 = mat_world @ verts[tri[0]].co + (f_normal * OFFSET)
                        v1 = mat_world @ verts[tri[1]].co + (f_normal * OFFSET)
                        v2 = mat_world @ verts[tri[2]].co + (f_normal * OFFSET)
                        face_batches[gid].extend([v0, v1, v2])

                for e in cf.edges:
                    is_boundary = False
                    if len(e.link_faces) == 1:
                        is_boundary = True
                    else:
                        for lf in e.link_faces:
                            if lf.index not in cluster_set:
                                is_boundary = True
                                break

                    if is_boundary:
                        if gid not in edge_batches:
                            edge_batches[gid] = []
                        ev1 = mat_world @ e.verts[0].co + (f_normal * OFFSET * 2)
                        ev2 = mat_world @ e.verts[1].co + (f_normal * OFFSET * 2)
                        edge_batches[gid].extend([ev1, ev2])

        if multi_face_set:
            multi_center = Vector((0, 0, 0))
            multi_count = 0
            all_gids = set()

            for f in bm.faces:
                if f.index not in multi_face_set: continue

                val = f[sg_layer]
                gids = get_group_ids(val)
                all_gids.update(gids)

                f_normal = f.normal
                verts = f.verts

                multi_center += f.calc_center_median()
                multi_count += 1

                if len(verts) == 3:
                    v0 = mat_world @ verts[0].co + (f_normal * OFFSET)
                    v1 = mat_world @ verts[1].co + (f_normal * OFFSET)
                    v2 = mat_world @ verts[2].co + (f_normal * OFFSET)
                    multi_faces.extend([v0, v1, v2])
                else:
                    poly_points = [v.co for v in verts]
                    tris = tessellate_polygon([poly_points])
                    for tri in tris:
                        v0 = mat_world @ verts[tri[0]].co + (f_normal * OFFSET)
                        v1 = mat_world @ verts[tri[1]].co + (f_normal * OFFSET)
                        v2 = mat_world @ verts[tri[2]].co + (f_normal * OFFSET)
                        multi_faces.extend([v0, v1, v2])

                for e in f.edges:
                    is_boundary = False
                    if len(e.link_faces) == 1:
                        is_boundary = True
                    else:
                        for lf in e.link_faces:
                            if lf.index not in multi_face_set:
                                is_boundary = True
                                break

                    if is_boundary:
                        ev1 = mat_world @ e.verts[0].co + (f_normal * OFFSET * 2)
                        ev2 = mat_world @ e.verts[1].co + (f_normal * OFFSET * 2)
                        multi_edges.extend([ev1, ev2])

            if multi_count > 0:
                multi_center /= multi_count
                multi_center_world = mat_world @ multi_center
                gid_str = ",".join(str(g) for g in sorted(all_gids))
                _overlay_data["cluster_centers"].append((gid_str, multi_center_world.copy(), True))

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        shader.bind()

        for gid, coords in face_batches.items():
            if not coords: continue
            color = COLORS.get(gid, (1, 1, 1, 0.4))
            shader.uniform_float("color", color)
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords})
            batch.draw(shader)

        if multi_faces:
            shader.uniform_float("color", MULTI_COLOR)
            batch = batch_for_shader(shader, 'TRIS', {"pos": multi_faces})
            batch.draw(shader)

        gpu.state.line_width_set(4.0)
        for gid, coords in edge_batches.items():
            if not coords: continue
            color = EDGE_COLORS.get(gid, (1, 1, 1, 1.0))
            shader.uniform_float("color", color)
            batch = batch_for_shader(shader, 'LINES', {"pos": coords})
            batch.draw(shader)

        if multi_edges:
            shader.uniform_float("color", MULTI_EDGE_COLOR)
            batch = batch_for_shader(shader, 'LINES', {"pos": multi_edges})
            batch.draw(shader)

        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')

    except Exception as e:
        print(f"Overlay 3D Error: {e}")


def draw_2d(self, context):
    if not context.scene.mmy_poly_edit_show_overlay:
        return

    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return

    region = context.region
    rv3d = context.region_data

    font_id = 0
    blf.size(font_id, 28)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 5, 0, 0, 0, 1)

    try:
        for item in _overlay_data.get("cluster_centers", []):
            gid, center, is_multi = item

            coord_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, center)

            if coord_2d:
                x, y = int(coord_2d[0]), int(coord_2d[1])
                if x < 0 or x > region.width or y < 0 or y > region.height:
                    continue

                if is_multi:
                    txt = str(gid)
                    blf.color(font_id, 1.0, 0.6, 1.0, 1.0)
                else:
                    txt = str(gid)
                    blf.color(font_id, 1, 1, 1, 1)

                w, h = blf.dimensions(font_id, txt)
                blf.position(font_id, x - w/2, y - h/2, 0)
                blf.draw(font_id, txt)

    except Exception as e:
        print(f"Overlay 2D Error: {e}")


def register_overlay():
    global draw_handler_2d, draw_handler_3d
    if draw_handler_2d is None:
        draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(draw_2d, (None, bpy.context), 'WINDOW', 'POST_PIXEL')
        draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(draw_3d, (None, bpy.context), 'WINDOW', 'POST_VIEW')
        _redraw()


def unregister_overlay():
    global draw_handler_2d, draw_handler_3d, _overlay_data
    if draw_handler_2d is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler_2d, 'WINDOW')
        draw_handler_2d = None
    if draw_handler_3d is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler_3d, 'WINDOW')
        draw_handler_3d = None
    _overlay_data = {"cluster_centers": []}
    _redraw()


def _redraw():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()