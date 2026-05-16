import bpy
import bmesh


class MMY_OT_MarkUVIslandSeams(bpy.types.Operator):
    """沿UV孤岛边界标记缝合边"""
    bl_idname = "mmy.mark_uv_island_seams"
    bl_label = "沿UV孤岛边界标记缝合边"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        me = obj.data

        bm = bmesh.from_edit_mesh(me)
        if bm is None:
            self.report({'ERROR'}, "无法获取网格数据")
            return {'CANCELLED'}

        uv_layer = bm.loops.layers.uv.verify()
        if uv_layer is None:
            self.report({'WARNING'}, "该对象没有UV数据，请先展开UV")
            return {'CANCELLED'}

        new_seams_count = 0

        for edge in bm.edges:
            # 跳过已有缝合边
            if edge.seam:
                continue

            # 获取关联面
            faces = edge.link_faces
            if len(faces) < 2:
                # 网格边界边，跳过
                continue

            # 检查UV连续性
            if not self._check_uv_continuity(edge, faces, uv_layer):
                edge.seam = True
                new_seams_count += 1

        bmesh.update_edit_mesh(me)

        if new_seams_count > 0:
            self.report({'INFO'}, f"已标记 {new_seams_count} 条缝合边")
        else:
            self.report({'INFO'}, "没有发现新的UV孤岛边界")

        return {'FINISHED'}

    def _check_uv_continuity(self, edge, faces, uv_layer):
        """
        检查边在两个面上的UV是否连续
        返回True表示连续（同一UV孤岛），False表示不连续（UV孤岛边界）

        方法：边的两个顶点在UV空间中形成一条UV边。
        如果两个面在这条边的UV位置相同（可能方向相反），则UV连续。
        """
        if len(faces) != 2:
            return True

        face_a, face_b = faces
        verts = edge.verts
        v1, v2 = verts[0], verts[1]

        tolerance = 0.001

        def get_uv_for_vert(face, vert):
            """在指定面上找到指定顶点的UV坐标"""
            for loop in face.loops:
                if loop.vert == vert:
                    return loop[uv_layer].uv.copy()
            return None

        # 获取两个顶点在face_a上的UV坐标
        uv_a1 = get_uv_for_vert(face_a, v1)
        uv_a2 = get_uv_for_vert(face_a, v2)

        # 获取两个顶点在face_b上的UV坐标
        uv_b1 = get_uv_for_vert(face_b, v1)
        uv_b2 = get_uv_for_vert(face_b, v2)

        if uv_a1 is None or uv_a2 is None or uv_b1 is None or uv_b2 is None:
            return True

        # 检查UV边是否匹配（两个面在同一UV边位置，可能方向相反）
        # 情况1: v1的UV在两个面上相同，v2的UV在两个面上相同
        if self._uv_close(uv_a1, uv_b1, tolerance) and self._uv_close(uv_a2, uv_b2, tolerance):
            return True
        # 情况2: 方向相反，v1在face_a的UV等于v2在face_b的UV
        if self._uv_close(uv_a1, uv_b2, tolerance) and self._uv_close(uv_a2, uv_b1, tolerance):
            return True

        return False

    def _uv_close(self, uv1, uv2, tolerance):
        """检查两个UV坐标是否接近"""
        return abs(uv1.x - uv2.x) < tolerance and abs(uv1.y - uv2.y) < tolerance


class MMY_OT_ImportFBX(bpy.types.Operator):
    """导入FBX模型"""
    bl_idname = "mmy.import_fbx"
    bl_label = "导入FBX"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        use_anim = context.scene.mmy_import_anim
        try:
            bpy.ops.import_scene.fbx(filepath=self.filepath, use_anim=use_anim)
            self.report({'INFO'}, f"已导入: {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class MMY_OT_BetterImportFBX(bpy.types.Operator):
    """使用Better FBX插件导入"""
    bl_idname = "mmy.better_import_fbx"
    bl_label = "Better Import FBX"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        # 检查Better FBX插件是否已安装
        return "better_fbx" in bpy.context.preferences.addons

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        try:
            # 调用Better FBX的导入功能
            bpy.ops.better_fbx.import_fbx(filepath=self.filepath)
            self.report({'INFO'}, f"已导入(Better FBX): {self.filepath}")
        except AttributeError:
            self.report({'ERROR'}, "Better FBX插件未安装或版本不兼容")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}