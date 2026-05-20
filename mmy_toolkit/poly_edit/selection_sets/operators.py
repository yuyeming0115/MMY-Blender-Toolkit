"""选择集操作符"""

import bpy
import bmesh
import time
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty

from ..ui.lang import get_text, get_text_formatted


class StringItem(PropertyGroup):
    value: StringProperty()


class IntItem(PropertyGroup):
    value: IntProperty()


class ElementSelection(PropertyGroup):
    object_name: StringProperty()
    verts: CollectionProperty(type=IntItem)
    edges: CollectionProperty(type=IntItem)
    faces: CollectionProperty(type=IntItem)


class SelectionSetItem(PropertyGroup):
    name: StringProperty(name="Name", default="New Set")
    objects: CollectionProperty(type=StringItem)
    elements: CollectionProperty(type=ElementSelection)


def save_element_selection(elem_data, obj):
    """保存元素选择"""
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        elem_data.verts.clear()
        elem_data.edges.clear()
        elem_data.faces.clear()

        for v in bm.verts:
            if v.select:
                elem = elem_data.verts.add()
                elem.value = v.index
        for e in bm.edges:
            if e.select:
                elem = elem_data.edges.add()
                elem.value = e.index
        for f in bm.faces:
            if f.select:
                elem = elem_data.faces.add()
                elem.value = f.index


def load_element_selection(elem_data, obj, mode):
    """加载元素选择"""
    if obj.type != 'MESH':
        return False
    prev_mode = obj.mode
    if prev_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    if not bm:
        return False
    has_selection = False

    if mode == 'REPLACE':
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

    for v_item in elem_data.verts:
        try:
            v = bm.verts[v_item.value]
            if mode == 'ADD':
                v.select = v.select or True
            elif mode == 'SUBTRACT':
                v.select = False
            else:
                v.select = True
        except IndexError:
            pass

    for e_item in elem_data.edges:
        try:
            e = bm.edges[e_item.value]
            if mode == 'ADD':
                e.select = e.select or True
            elif mode == 'SUBTRACT':
                e.select = False
            else:
                e.select = True
        except IndexError:
            pass

    for f_item in elem_data.faces:
        try:
            f = bm.faces[f_item.value]
            if mode == 'ADD':
                f.select = f.select or True
            elif mode == 'SUBTRACT':
                f.select = False
            else:
                f.select = True
        except IndexError:
            pass

    has_selection = any(v.select for v in bm.verts) or any(e.select for e in bm.edges) or any(f.select for f in bm.faces)

    bmesh.update_edit_mesh(obj.data)
    if prev_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')
    return has_selection


class MMY_OT_SaveSelectionSet(Operator):
    bl_idname = "mmy.save_selection_set"
    bl_label = "保存选择集"
    bl_options = {'REGISTER', 'UNDO'}

    set_name: StringProperty(name="名称")
    use_elements: BoolProperty(name="存储元素", default=True)

    def execute(self, context):
        if not self.set_name:
            self.report({'ERROR'}, get_text("name_cannot_be_empty"))
            return {'CANCELLED'}

        original_name = self.set_name.strip('-')
        if context.mode == 'EDIT_MESH':
            self.set_name = f"-{original_name}-"

        if self.set_name in [s.name for s in context.scene.mmy_poly_edit_selection_sets]:
            self.report({'ERROR'}, get_text("name_already_exists"))
            return {'CANCELLED'}

        new_set = context.scene.mmy_poly_edit_selection_sets.add()
        new_set.name = self.set_name

        if context.mode == 'OBJECT':
            for obj in context.selected_objects:
                item = new_set.objects.add()
                item.value = obj.name
        if self.use_elements and context.mode == 'EDIT_MESH':
            obj = context.active_object
            if obj and obj.type == 'MESH':
                elem_data = new_set.elements.add()
                elem_data.object_name = obj.name
                save_element_selection(elem_data, obj)

        return {'FINISHED'}

    def invoke(self, context, event):
        if context.mode == 'OBJECT':
            if context.selected_objects:
                active_obj = context.active_object
                if active_obj:
                    base_name = f"{active_obj.name}_collection"
                else:
                    base_name = f"ObjectSet_{len(context.scene.mmy_poly_edit_selection_sets)+1}"
            else:
                base_name = f"ObjectSet_{len(context.scene.mmy_poly_edit_selection_sets)+1}"
            self.set_name = base_name
        else:
            obj = context.active_object
            if obj and hasattr(obj, 'face_select_mode'):
                if obj.face_select_mode:
                    elem_type = "Faces"
                elif obj.edge_select_mode:
                    elem_type = "Edges"
                else:
                    elem_type = "Vertices"
            else:
                elem_type = "Elements"
            base_name = f"{elem_type}_Selection_{len(context.scene.mmy_poly_edit_selection_sets)+1}"
            self.set_name = f"-{base_name}-"

        return context.window_manager.invoke_props_dialog(self)


class MMY_OT_LoadSelectionSet(Operator):
    bl_idname = "mmy.load_selection_set"
    bl_label = "加载选择集"

    set_name: StringProperty()
    mode: StringProperty(default='REPLACE')

    def execute(self, context):
        try:
            set_data = next(s for s in context.scene.mmy_poly_edit_selection_sets if s.name == self.set_name)
        except StopIteration:
            self.report({'ERROR'}, get_text("selection_set_not_found"))
            return {'CANCELLED'}

        is_edit_set = set_data.name.startswith('-') and set_data.name.endswith('-')

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if is_edit_set:
            if not set_data.elements:
                self.report({'ERROR'}, get_text("invalid_edit_set"))
                return {'CANCELLED'}

            objects_to_check = []
            for elem_data in set_data.elements:
                target_obj = bpy.data.objects.get(elem_data.object_name)
                if not target_obj:
                    self.report({'ERROR'}, get_text_formatted("object_not_found", object=elem_data.object_name))
                    continue
                objects_to_check.append(target_obj)

                if self.mode == 'REPLACE':
                    bpy.ops.object.select_all(action='DESELECT')
                    target_obj.select_set(True)
                    context.view_layer.objects.active = target_obj
                    load_element_selection(elem_data, target_obj, 'REPLACE')
                elif self.mode == 'ADD':
                    target_obj.select_set(True)
                    context.view_layer.objects.active = target_obj
                    load_element_selection(elem_data, target_obj, 'ADD')
                elif self.mode == 'SUBTRACT':
                    if target_obj.mode != 'EDIT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                        target_obj.select_set(True)
                        context.view_layer.objects.active = target_obj
                        bpy.ops.object.mode_set(mode='EDIT')
                    has_selection = load_element_selection(elem_data, target_obj, 'SUBTRACT')
                    if not has_selection:
                        target_obj.select_set(False)

            remaining_objects = [obj for obj in objects_to_check if obj.select_get()]
            if remaining_objects:
                context.view_layer.objects.active = remaining_objects[0]
                for obj in remaining_objects:
                    obj.select_set(True)
                bpy.ops.object.mode_set(mode='EDIT')

                final_selected = []
                for obj in context.selected_objects:
                    if obj.type != 'MESH':
                        continue
                    bpy.ops.object.mode_set(mode='OBJECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bm = bmesh.from_edit_mesh(obj.data)
                    if bm:
                        any_selected = any(v.select for v in bm.verts) or any(e.select for e in bm.edges) or any(f.select for f in bm.faces)
                        if not any_selected:
                            obj.select_set(False)
                        else:
                            final_selected.append(obj)
                    bpy.ops.object.mode_set(mode='OBJECT')

                bpy.ops.object.select_all(action='DESELECT')
                for obj in final_selected:
                    obj.select_set(True)
                if final_selected:
                    context.view_layer.objects.active = final_selected[0]
                    bpy.ops.object.mode_set(mode='EDIT')
                else:
                    bpy.ops.object.mode_set(mode='OBJECT')
            else:
                bpy.ops.object.mode_set(mode='OBJECT')
        else:
            if self.mode == 'REPLACE':
                bpy.ops.object.select_all(action='DESELECT')
                for obj_ref in set_data.objects:
                    obj = bpy.data.objects.get(obj_ref.value)
                    if obj:
                        obj.select_set(True)
                if set_data.objects:
                    context.view_layer.objects.active = bpy.data.objects[set_data.objects[0].value]

            elif self.mode == 'ADD':
                for obj_ref in set_data.objects:
                    obj = bpy.data.objects.get(obj_ref.value)
                    if obj:
                        obj.select_set(True)

            elif self.mode == 'SUBTRACT':
                for obj_ref in set_data.objects:
                    obj = bpy.data.objects.get(obj_ref.value)
                    if obj:
                        obj.select_set(False)

        return {'FINISHED'}

    def invoke(self, context, event):
        self.mode = 'REPLACE'
        if event.shift:
            self.mode = 'ADD'
        elif event.ctrl:
            self.mode = 'SUBTRACT'
        return self.execute(context)


class MMY_OT_DeleteSelectionSet(Operator):
    bl_idname = "mmy.delete_selection_set"
    bl_label = "删除选择集"

    set_index: IntProperty()

    def execute(self, context):
        context.scene.mmy_poly_edit_selection_sets.remove(self.set_index)
        return {'FINISHED'}


class MMY_OT_RenameSelectionSet(Operator):
    bl_idname = "mmy.rename_selection_set"
    bl_label = "重命名选择集"

    set_index: IntProperty()
    new_name: StringProperty(name="新名称")

    def execute(self, context):
        if not self.new_name:
            self.report({'ERROR'}, get_text("name_cannot_be_empty"))
            return {'CANCELLED'}

        sel_set = context.scene.mmy_poly_edit_selection_sets[self.set_index]
        if self.new_name in [s.name for s in context.scene.mmy_poly_edit_selection_sets]:
            self.report({'ERROR'}, get_text("name_already_exists"))
            return {'CANCELLED'}

        sel_set.name = self.new_name
        return {'FINISHED'}

    def invoke(self, context, event):
        self.new_name = context.scene.mmy_poly_edit_selection_sets[self.set_index].name
        return context.window_manager.invoke_props_dialog(self)


class MMY_OT_UpdateSelectionSet(Operator):
    bl_idname = "mmy.update_selection_set"
    bl_label = "更新选择集"

    set_index: IntProperty()
    start_time = None

    def check_selection(self, context):
        if context.mode == 'OBJECT':
            return bool(context.selected_objects)
        elif context.mode == 'EDIT_MESH':
            obj = context.active_object
            if obj and obj.type == 'MESH':
                bm = bmesh.from_edit_mesh(obj.data)
                if bm:
                    return any(v.select for v in bm.verts) or any(e.select for e in bm.edges) or any(f.select for f in bm.faces)
            return False
        return False

    def execute(self, context):
        if self.start_time is not None:
            if time.time() - self.start_time >= 2:
                self.start_time = None
                return {'FINISHED'}
            return {'PASS_THROUGH'}

        if not self.check_selection(context):
            self.start_time = time.time()
            self.report({'INFO'}, get_text("no_selection"))
            return {'RUNNING_MODAL'}

        sel_set = context.scene.mmy_poly_edit_selection_sets[self.set_index]
        sel_set.objects.clear()
        sel_set.elements.clear()

        if context.mode == 'OBJECT':
            for obj in context.selected_objects:
                item = sel_set.objects.add()
                item.value = obj.name
        elif context.mode == 'EDIT_MESH':
            obj = context.active_object
            if obj and obj.type == 'MESH':
                elem_data = sel_set.elements.add()
                elem_data.object_name = obj.name
                save_element_selection(elem_data, obj)

        return {'FINISHED'}

    def modal(self, context, event):
        if self.start_time is not None:
            if time.time() - self.start_time >= 2:
                self.start_time = None
                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if not self.check_selection(context):
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return self.execute(context)


_classes = (
    StringItem,
    IntItem,
    ElementSelection,
    SelectionSetItem,
    MMY_OT_SaveSelectionSet,
    MMY_OT_LoadSelectionSet,
    MMY_OT_DeleteSelectionSet,
    MMY_OT_RenameSelectionSet,
    MMY_OT_UpdateSelectionSet,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mmy_poly_edit_selection_sets = bpy.props.CollectionProperty(type=SelectionSetItem)


def unregister():
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    try:
        del bpy.types.Scene.mmy_poly_edit_selection_sets
    except:
        pass