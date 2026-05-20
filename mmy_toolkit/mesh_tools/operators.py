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
        reuse_materials = context.scene.mmy_reuse_materials
        clear_transforms = context.scene.mmy_clear_transforms

        try:
            # 导入前记录当前场景中的对象
            before_objs = set(context.scene.objects)

            bpy.ops.import_scene.fbx(filepath=self.filepath, use_anim=use_anim)

            # 导入后获取新导入的对象
            after_objs = set(context.scene.objects)
            new_objs = after_objs - before_objs

            # 如果勾选了引用已有材质
            if reuse_materials and new_objs:
                self._reuse_existing_materials(new_objs)

            # 如果勾选了清零变换
            if clear_transforms and new_objs:
                self._clear_transforms(new_objs)

            self.report({'INFO'}, f"已导入: {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}

    def _reuse_existing_materials(self, new_objects):
        """替换导入对象的材质为场景中已有的同名材质"""
        import re
        replaced_count = 0
        for obj in new_objects:
            if hasattr(obj.data, 'materials'):
                for i, mat_slot in enumerate(obj.material_slots):
                    mat = mat_slot.material
                    if mat:
                        # 处理材质名称（可能带有 .001、.002 等后缀）
                        mat_name = mat.name
                        # 去掉 Blender 自动添加的数字后缀
                        base_name = re.sub(r'\.\d+$', '', mat_name)
                        # 查找场景中已有的同名材质
                        existing = bpy.data.materials.get(base_name)
                        if existing and existing != mat:
                            obj.material_slots[i].material = existing
                            if mat.users == 0:
                                bpy.data.materials.remove(mat)
                            replaced_count += 1
        if replaced_count > 0:
            self.report({'INFO'}, f"已替换 {replaced_count} 个同名材质")

    def _clear_transforms(self, new_objects):
        """应用变换：将物体的变换结构应用为自身数据"""
        # set 转 list
        obj_list = list(new_objects)
        if not obj_list:
            return

        # 先选中所有新导入的对象
        bpy.ops.object.select_all(action='DESELECT')
        for obj in obj_list:
            obj.select_set(True)

        # 设置第一个对象为活动对象
        bpy.context.view_layer.objects.active = obj_list[0]

        # 应用变换（位移、旋转、缩放）
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        self.report({'INFO'}, f"已应用 {len(obj_list)} 个对象的变换")


class MMY_OT_BetterImportFBX(bpy.types.Operator):
    """调用Better FBX导入功能"""
    bl_idname = "mmy.better_import_fbx"
    bl_label = "Better Import FBX"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx')

    def execute(self, context):
        # 直接调用 Better FBX，让它打开自己的文件选择器
        # 这样可以使用 Better FBX 的所有设置
        bpy.ops.better_import.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}


class MMY_OT_DetachSelection(bpy.types.Operator):
    """拆出选中部分为新物体，退出编辑模式并选中新物体"""
    bl_idname = "mmy.detach_selection"
    bl_label = "拆出"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        obj_name = obj.name

        # 分离选中部分
        bpy.ops.mesh.separate(type='SELECTED')

        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')

        # 取消选择原物体
        obj.select_set(False)

        # 找到新分离出的物体并选中
        new_obj = None
        for o in context.scene.objects:
            if o.type == 'MESH' and o.name.startswith(obj_name) and o != obj:
                if new_obj is None or o.name > new_obj.name:
                    new_obj = o

        if new_obj:
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            self.report({'INFO'}, f"已拆出: {new_obj.name}")
        else:
            self.report({'WARNING'}, "未找到分离的物体")

        return {'FINISHED'}


class MMY_OT_DuplicateDetach(bpy.types.Operator):
    """复制选中部分并拆出新物体，退出编辑模式并选中新物体"""
    bl_idname = "mmy.duplicate_detach"
    bl_label = "复制拆出"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        obj_name = obj.name

        # 复制选中部分
        bpy.ops.mesh.duplicate_move(MESH_OT_duplicate={"mode": 1})

        # 分离复制部分
        bpy.ops.mesh.separate(type='SELECTED')

        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')

        # 取消选择原物体
        obj.select_set(False)

        # 找到新分离出的物体并选中
        new_obj = None
        for o in context.scene.objects:
            if o.type == 'MESH' and o.name.startswith(obj_name) and o != obj:
                if new_obj is None or o.name > new_obj.name:
                    new_obj = o

        if new_obj:
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            self.report({'INFO'}, f"已复制拆出: {new_obj.name}")
        else:
            self.report({'WARNING'}, "未找到分离的物体")

        return {'FINISHED'}


class MMY_OT_SeparateByMaterial(bpy.types.Operator):
    """按材质分离网格，退出编辑模式并选中所有新物体"""
    bl_idname = "mmy.separate_by_material"
    bl_label = "按材质拆"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        obj_name = obj.name

        # 按材质分离
        bpy.ops.mesh.separate(type='MATERIAL')

        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')

        # 取消选择原物体
        obj.select_set(False)

        # 选中新分离出的所有物体
        new_objs = []
        for o in context.scene.objects:
            if o.type == 'MESH' and o.name.startswith(obj_name) and o != obj:
                new_objs.append(o)
                o.select_set(True)

        if new_objs:
            context.view_layer.objects.active = new_objs[0]
            self.report({'INFO'}, f"已按材质拆出 {len(new_objs)} 个物体")
        else:
            self.report({'WARNING'}, "未分离出新物体（可能只有一个材质）")

        return {'FINISHED'}


class MMY_OT_SeparateByLoose(bpy.types.Operator):
    """按松散块分离网格，退出编辑模式并选中所有新物体"""
    bl_idname = "mmy.separate_by_loose"
    bl_label = "按松散块拆"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        obj_name = obj.name

        # 按松散块分离
        bpy.ops.mesh.separate(type='LOOSE')

        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')

        # 取消选择原物体
        obj.select_set(False)

        # 选中新分离出的所有物体
        new_objs = []
        for o in context.scene.objects:
            if o.type == 'MESH' and o.name.startswith(obj_name) and o != obj:
                new_objs.append(o)
                o.select_set(True)

        if new_objs:
            context.view_layer.objects.active = new_objs[0]
            self.report({'INFO'}, f"已按松散块拆出 {len(new_objs)} 个物体")
        else:
            self.report({'WARNING'}, "未分离出新物体（可能已是整体）")

        return {'FINISHED'}