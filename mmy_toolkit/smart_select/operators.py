"""智能选择操作符

使用 Blender 原生操作符实现双击选择。
"""

import bpy
import bmesh
from mathutils import Vector
from .hud_tip import show_tip


class MMY_OT_SmartSelectUVIsland(bpy.types.Operator):
    """双击选中 UV 孤岛"""
    bl_idname = "mmy.smart_select_uv_island"
    bl_label = "选中 UV 孤岛"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "没有活动网格对象")
            return {'CANCELLED'}

        if context.scene.tool_settings.use_uv_select_sync:
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

        try:
            bpy.ops.uv.select_linked_pick('INVOKE_DEFAULT')
            show_tip("uv_island")
            return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f"选择失败: {e}")
            return {'CANCELLED'}


class MMY_OT_SmartSelectMeshLinked(bpy.types.Operator):
    """双击选中相连网格元素"""
    bl_idname = "mmy.smart_select_mesh_linked"
    bl_label = "选中相连元素"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "没有活动网格对象")
            return {'CANCELLED'}

        ts = context.tool_settings
        if ts.mesh_select_mode[0]:
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT')
        elif ts.mesh_select_mode[1]:
            bpy.ops.mesh.loop_select('INVOKE_DEFAULT', extend=True)
        elif ts.mesh_select_mode[2]:
            bpy.ops.mesh.select_linked_pick('INVOKE_DEFAULT')

        show_tip("mesh_linked")
        return {'FINISHED'}


class MMY_OT_SmartSelectUVSeams(bpy.types.Operator):
    """Ctrl+双击选中所有缝合边"""
    bl_idname = "mmy.smart_select_uv_seams"
    bl_label = "选中缝合边"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "没有活动网格对象")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "需要在编辑模式")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return {'CANCELLED'}

        bpy.ops.mesh.select_all(action='DESELECT')

        count = 0
        for edge in bm.edges:
            if edge.seam:
                edge.select = True
                count += 1

        bmesh.update_edit_mesh(obj.data)
        context.tool_settings.mesh_select_mode = (False, True, False)

        show_tip("seam")
        return {'FINISHED'}


class MMY_OT_SmartSelectMaterial(bpy.types.Operator):
    """Shift+双击选中相同材质的面"""
    bl_idname = "mmy.smart_select_material"
    bl_label = "选中相同材质"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        # 使用窗口坐标（不是区域坐标）
        self._mouse_x = event.mouse_x
        self._mouse_y = event.mouse_y
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "没有活动网格对象")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "需要在编辑模式")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            return {'CANCELLED'}

        # 先取消所有选择
        for face in bm.faces:
            face.select = False

        # 射线检测找到点击位置的面
        hit_face = self._raycast_face(context, obj)

        if hit_face is None:
            self.report({'WARNING'}, "未检测到点击的面")
            return {'CANCELLED'}

        target_material_index = hit_face.material_index

        # 选中所有相同材质的面
        count = 0
        for face in bm.faces:
            if face.material_index == target_material_index:
                face.select = True
                count += 1

        bmesh.update_edit_mesh(obj.data)
        context.tool_settings.mesh_select_mode = (False, False, True)

        show_tip("material")
        return {'FINISHED'}

    def _raycast_face(self, context, obj):
        """射线检测找到鼠标位置的面"""
        try:
            from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

            mouse_x, mouse_y = self._mouse_x, self._mouse_y

            # 找到鼠标所在的 3D 视图区域
            region = None
            rv3d = None

            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        if (area.x <= mouse_x < area.x + area.width and
                            area.y <= mouse_y < area.y + area.height):
                            space = area.spaces.active
                            for r in area.regions:
                                if r.type == 'WINDOW':
                                    region = r
                                    break
                            if space:
                                rv3d = space.region_3d
                            break
                if region:
                    break

            if region is None or rv3d is None:
                return None

            # 计算区域内的坐标
            region_x = mouse_x - area.x
            region_y = mouse_y - area.y

            # 获取世界空间的射线
            ray_origin = region_2d_to_origin_3d(region, rv3d, (region_x, region_y))
            ray_dir = region_2d_to_vector_3d(region, rv3d, (region_x, region_y))

            # 使用 scene.ray_cast 做世界空间检测
            depsgraph = context.evaluated_depsgraph_get()
            result, location, normal, face_index, hit_obj, matrix = context.scene.ray_cast(
                depsgraph, ray_origin, ray_dir
            )

            if result and hit_obj == obj and face_index >= 0:
                bm = bmesh.from_edit_mesh(obj.data)
                if face_index < len(bm.faces):
                    return bm.faces[face_index]

        except Exception as e:
            print(f"[Smart Select Material] 射线检测失败: {e}")

        return None


_classes = (
    MMY_OT_SmartSelectUVIsland,
    MMY_OT_SmartSelectMeshLinked,
    MMY_OT_SmartSelectUVSeams,
    MMY_OT_SmartSelectMaterial,
)


def register():
    from .hud_tip import register as hud_register
    hud_register()
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    from .hud_tip import unregister as hud_unregister
    hud_unregister()
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass