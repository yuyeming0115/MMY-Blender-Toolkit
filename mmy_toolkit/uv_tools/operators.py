# -*- coding: utf-8 -*-
"""UV 工具操作符"""

import os
import subprocess
import time
import tempfile
import functools

import bpy
import blf


OVERLAP_TIMER_INTERVAL = 0.4
_overlap_timer_running = False
_ruv_timer_running = False


def _set_attr_if_exists(target, attr_name, value):
    if target is None or not hasattr(target, attr_name):
        return False
    try:
        setattr(target, attr_name, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def update_uv_stretch_display(self, context):
    """更新 UV 拉伸显示设置"""
    if context is None:
        return

    scene = context.scene
    window_manager = getattr(context, "window_manager", None)
    if scene is None or window_manager is None:
        return

    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type != 'IMAGE_EDITOR':
                continue

            space = area.spaces.active
            if space is None or getattr(space, "mode", None) != 'UV':
                continue

            uv_editor = getattr(space, "uv_editor", None)
            overlay = getattr(space, "overlay", None)

            _set_attr_if_exists(uv_editor, "show_stretch", scene.uv_show_stretch) or _set_attr_if_exists(
                overlay, "show_stretch", scene.uv_show_stretch
            )
            _set_attr_if_exists(uv_editor, "display_stretch_type", scene.uv_stretch_type) or _set_attr_if_exists(
                overlay, "stretch_type", scene.uv_stretch_type
            )

            if scene.uv_show_stretch:
                _set_attr_if_exists(uv_editor, "show_faces", True) or _set_attr_if_exists(
                    overlay, "show_faces", True
                )

            area.tag_redraw()


def _start_overlap_timer():
    global _overlap_timer_running
    if _overlap_timer_running:
        return

    _overlap_timer_running = True
    if not bpy.app.timers.is_registered(_overlap_timer_callback):
        bpy.app.timers.register(_overlap_timer_callback, first_interval=0.1)


def _stop_overlap_timer():
    global _overlap_timer_running
    _overlap_timer_running = False
    if bpy.app.timers.is_registered(_overlap_timer_callback):
        try:
            bpy.app.timers.unregister(_overlap_timer_callback)
        except ValueError:
            pass


def _stop_ruv_timers():
    """停止所有 RizomUV 相关定时器"""
    global _ruv_timer_running
    _ruv_timer_running = False


def stop_all_timers():
    """停止所有定时器（模块卸载时调用）"""
    _stop_overlap_timer()
    _stop_ruv_timers()


def _overlap_timer_callback():
    global _overlap_timer_running

    if not _overlap_timer_running:
        return None

    scene = getattr(bpy.context, "scene", None)
    if scene is None or not getattr(scene, "uv_show_overlap", False):
        _overlap_timer_running = False
        return None

    if getattr(scene, "uv_overlap_selection_mode", 'REPLACE') != 'REPLACE':
        return OVERLAP_TIMER_INTERVAL

    try:
        bpy.ops.uv.detect_overlap_highlight('EXEC_DEFAULT', silent=True)
    except Exception:
        pass

    return OVERLAP_TIMER_INTERVAL


def update_uv_overlap_display(self, context):
    """更新 UV 重叠检测自动刷新状态"""
    if context is None or context.scene is None:
        return

    scene = context.scene
    if scene.uv_show_overlap:
        _start_overlap_timer()
        try:
            bpy.ops.uv.detect_overlap_highlight('EXEC_DEFAULT', silent=True)
        except Exception:
            pass
    else:
        _stop_overlap_timer()
        scene.uv_overlap_face_count = 0


def _get_uv_preferences(context):
    """获取 UV 工具偏好设置"""
    from . import get_uv_preferences
    return get_uv_preferences(context)


def _get_photoshop_path(context):
    preferences = _get_uv_preferences(context)
    if preferences is None or not preferences.photoshop_path:
        return ""
    return bpy.path.abspath(preferences.photoshop_path)


def _find_uv_editor_override(context):
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None:
        return None

    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type != 'IMAGE_EDITOR':
                continue

            space = area.spaces.active
            if space is None or getattr(space, "mode", None) != 'UV':
                continue

            region = next((region for region in area.regions if region.type == 'WINDOW'), None)
            if region is None:
                continue

            override = {
                "window": window,
                "screen": screen,
                "area": area,
                "region": region,
            }
            if getattr(window, "scene", None) is not None:
                override["scene"] = window.scene
            if getattr(window, "view_layer", None) is not None:
                override["view_layer"] = window.view_layer
            return override

    return None


def _count_selected_uv_faces(obj, tool_settings):
    obj.update_from_editmode()
    mesh = obj.data

    if getattr(tool_settings, "use_uv_select_sync", False):
        return sum(1 for face in mesh.polygons if face.select)

    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return 0

    uv_data = uv_layer.data
    if len(uv_data) == 0:
        return 0

    selected_count = 0
    for face in mesh.polygons:
        if all(uv_data[loop_index].select for loop_index in face.loop_indices if loop_index < len(uv_data)):
            selected_count += 1
    return selected_count


def _detect_overlap_on_active_object(context, replace_selection=True):
    override = _find_uv_editor_override(context)
    if override is None:
        return False, 0, "未找到可用的UV编辑器窗口"

    with bpy.context.temp_override(**override):
        obj = bpy.context.active_object
        if obj is None or obj.type != 'MESH':
            return False, 0, "当前活动对象不是mesh对象"
        if obj.mode != 'EDIT':
            return False, 0, "请在Mesh编辑模式下检测重叠"
        if not obj.data.uv_layers or not obj.data.uv_layers.active:
            return False, 0, "当前对象没有可用UV层"

        try:
            if replace_selection:
                bpy.ops.uv.select_all(action='DESELECT')
            result = bpy.ops.uv.select_overlap()
        except Exception as exc:
            return False, 0, f"UV重叠检测失败: {exc}"

        if result != {'FINISHED'}:
            return False, 0, "UV重叠检测未完成"

        overlap_count = _count_selected_uv_faces(obj, bpy.context.tool_settings)

        obj.update_from_editmode()
        mesh = obj.data
        overlap_indices = [i for i, face in enumerate(mesh.polygons) if face.select]
        context.scene.uv_cached_overlap_faces = ",".join(map(str, overlap_indices))

        return True, overlap_count, ""


class UV_OT_detect_overlap_highlight(bpy.types.Operator):
    bl_idname = "uv.mmy_detect_overlap_highlight"
    bl_label = "立即检测重叠"
    bl_description = "检测活动对象UV重叠并高亮重叠面"

    silent: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        replace_selection = context.scene.uv_overlap_selection_mode == 'REPLACE'
        success, overlap_count, message = _detect_overlap_on_active_object(context, replace_selection)

        if success:
            context.scene.uv_overlap_face_count = overlap_count
            if not self.silent:
                self.report({'INFO'}, f"检测完成，重叠面数量: {overlap_count}")
            return {'FINISHED'}

        context.scene.uv_overlap_face_count = 0
        if not self.silent:
            self.report({'WARNING'}, message)
        return {'CANCELLED'}


class UV_OT_invert_overlap_selection(bpy.types.Operator):
    bl_idname = "uv.mmy_invert_overlap_selection"
    bl_label = "反选重叠面"
    bl_description = "在重叠面集合内反选"

    def execute(self, context):
        cached_str = context.scene.uv_cached_overlap_faces
        if not cached_str:
            self.report({'WARNING'}, "请先检测重叠")
            return {'CANCELLED'}

        try:
            cached_indices = [int(x) for x in cached_str.split(",") if x]
        except ValueError:
            self.report({'ERROR'}, "缓存数据损坏")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            self.report({'ERROR'}, "请在Mesh编辑模式下使用")
            return {'CANCELLED'}

        obj.update_from_editmode()
        mesh = obj.data

        for idx in cached_indices:
            if idx < len(mesh.polygons):
                mesh.polygons[idx].select = not mesh.polygons[idx].select

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, "已反选重叠面")
        return {'FINISHED'}


class OBJECT_OT_transfer_uv(bpy.types.Operator):
    bl_idname = "object.mmy_transfer_uv"
    bl_label = "传递UV"
    bl_description = "将UV数据从新UV对象传递到绑定对象（基于拓扑匹配）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source_obj = context.scene.uv_source_object
        target_obj = context.scene.uv_target_object

        if not source_obj:
            self.report({'ERROR'}, "请选择新UV对象")
            return {'CANCELLED'}

        if not target_obj:
            self.report({'ERROR'}, "请选择绑定对象")
            return {'CANCELLED'}

        if source_obj.type != 'MESH' or target_obj.type != 'MESH':
            self.report({'ERROR'}, "新UV对象和绑定对象必须是mesh对象")
            return {'CANCELLED'}

        source_mesh = source_obj.data
        target_mesh = target_obj.data

        if not source_mesh.uv_layers.active:
            self.report({'ERROR'}, "新UV对象没有UV数据")
            return {'CANCELLED'}

        if len(source_mesh.polygons) != len(target_mesh.polygons):
            self.report({'ERROR'}, "面数不匹配，无法传递UV")
            return {'CANCELLED'}

        if len(source_mesh.loops) != len(target_mesh.loops):
            self.report({'ERROR'}, "Loop数量不匹配，无法传递UV")
            return {'CANCELLED'}

        if not target_mesh.uv_layers.active:
            target_mesh.uv_layers.new(name="UVMap")

        source_uv = source_mesh.uv_layers.active.data
        target_uv = target_mesh.uv_layers.active.data

        transfer_count = 0
        for i in range(len(target_mesh.loops)):
            if i < len(source_uv):
                target_uv[i].uv = source_uv[i].uv.copy()
                transfer_count += 1

        self.report({'INFO'}, f"UV传递完成：{transfer_count}个loop")
        return {'FINISHED'}


class UV_OT_test_photoshop_path(bpy.types.Operator):
    bl_idname = "uv.mmy_test_photoshop_path"
    bl_label = "测试 Photoshop 路径"
    bl_description = "测试偏好设置中的 Photoshop 路径并尝试启动"

    def execute(self, context):
        photoshop_path = _get_photoshop_path(context)
        if not photoshop_path:
            self.report({'ERROR'}, "请先在插件偏好设置中配置 Photoshop 路径")
            return {'CANCELLED'}

        if not os.path.isfile(photoshop_path):
            self.report({'ERROR'}, f"Photoshop 文件不存在: {photoshop_path}")
            return {'CANCELLED'}

        try:
            subprocess.Popen([photoshop_path])
        except Exception as exc:
            self.report({'ERROR'}, f"启动 Photoshop 失败: {exc}")
            return {'CANCELLED'}

        self.report({'INFO'}, "Photoshop 已启动")
        return {'FINISHED'}


class UV_OT_quick_export_layout(bpy.types.Operator):
    bl_idname = "uv.mmy_quick_export_layout"
    bl_label = "快速导出UV"
    bl_description = "将当前UV导出为PNG文件"

    target_size: bpy.props.IntProperty(default=1024)

    def execute(self, context):
        space = context.space_data
        if not space or space.type != 'IMAGE_EDITOR' or space.mode != 'UV':
            self.report({'ERROR'}, "该功能仅可在UV编辑模式下使用")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "当前活动对象必须是mesh对象")
            return {'CANCELLED'}

        if not obj.data.uv_layers:
            self.report({'ERROR'}, "当前mesh对象没有UV数据")
            return {'CANCELLED'}

        blend_filepath = bpy.data.filepath
        if not blend_filepath:
            self.report({'ERROR'}, "请先保存 .blend 文件")
            return {'CANCELLED'}

        blend_name = os.path.splitext(os.path.basename(blend_filepath))[0]
        blend_dir = os.path.dirname(blend_filepath)
        output_name = f"{blend_name}_uv_{self.target_size}.png"
        output_path = os.path.join(blend_dir, output_name)

        try:
            result = bpy.ops.uv.export_layout(
                'EXEC_DEFAULT',
                filepath=output_path,
                check_existing=False,
                export_all=False,
                modified=False,
                mode='PNG',
                size=(self.target_size, self.target_size),
                opacity=0.25,
            )
        except Exception as exc:
            self.report({'ERROR'}, f"导出UV失败: {exc}")
            return {'CANCELLED'}

        if result != {'FINISHED'}:
            self.report({'ERROR'}, "导出UV失败")
            return {'CANCELLED'}

        if not os.path.exists(output_path):
            self.report({'ERROR'}, "导出结果文件不存在")
            return {'CANCELLED'}

        context.scene.uv_last_export_path = output_path
        self.report({'INFO'}, f"UV已导出: {output_name}")
        return {'FINISHED'}


class UV_OT_open_last_export_in_photoshop(bpy.types.Operator):
    bl_idname = "uv.mmy_open_last_export_in_photoshop"
    bl_label = "发送到 Photoshop"
    bl_description = "将最近导出的UV图片发送到 Photoshop"

    def execute(self, context):
        image_path = context.scene.uv_last_export_path
        if not image_path:
            self.report({'ERROR'}, "当前没有最近导出的UV文件")
            return {'CANCELLED'}

        image_path = bpy.path.abspath(image_path)
        if not os.path.isfile(image_path):
            self.report({'ERROR'}, "最近导出的文件不存在")
            return {'CANCELLED'}

        photoshop_path = _get_photoshop_path(context)
        if not photoshop_path:
            self.report({'ERROR'}, "请先配置 Photoshop 路径")
            return {'CANCELLED'}

        if not os.path.isfile(photoshop_path):
            self.report({'ERROR'}, f"Photoshop 文件不存在")
            return {'CANCELLED'}

        try:
            subprocess.Popen([photoshop_path, image_path])
        except Exception as exc:
            self.report({'ERROR'}, f"启动 Photoshop 失败: {exc}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"已发送: {os.path.basename(image_path)}")
        return {'FINISHED'}


class OBJECT_OT_unify_uvmap_name(bpy.types.Operator):
    bl_idname = "object.mmy_unify_uvmap_name"
    bl_label = "统一UVMap名称"
    bl_description = "将选中对象的活动UVMap重命名为指定名称"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_name = context.scene.uv_unified_name.strip()
        if not target_name:
            self.report({'ERROR'}, "请输入目标UVMap名称")
            return {'CANCELLED'}

        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_meshes:
            self.report({'ERROR'}, "未选中mesh对象")
            return {'CANCELLED'}

        renamed_count = 0
        for obj in selected_meshes:
            if obj.data.uv_layers.active:
                obj.data.uv_layers.active.name = target_name
                renamed_count += 1

        self.report({'INFO'}, f"已统一 {renamed_count} 个对象的UVMap名称")
        return {'FINISHED'}


# ═══════════════════════════════════════════════════════════════
# RizomUV 桥接
# ═══════════════════════════════════════════════════════════════

def _ruv_get_temp_paths():
    """获取 RizomUV 桥接使用的临时文件路径"""
    path = tempfile.gettempdir().replace("\\", "/")
    return (
        path + "/mmy_ruv_tmp.fbx",
        path + "/mmy_ruv_tmp_out.fbx",
        path + "/mmy_ruv_new.lua",
        path + "/mmy_ruv_edit.lua",
    )


def _ruv_join_uvs():
    """在所有 3D 视图中执行 object.join_uvs()"""
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                context_override = {'window': window, 'screen': screen, 'area': area}
                with bpy.context.temp_override(**context_override):
                    bpy.ops.object.join_uvs()


def _ruv_write_lua_settings(f, prefs):
    """将偏好设置中的 Unwrap/Layout 参数写入 Lua 文件"""
    if prefs.rizomuv_unwrap_tab:
        f.write("U3dSet({Path=\"Prefs.UnfoldIte\", Value=%d})\n" % prefs.rizomuv_unwrap_unfold_itr)
        f.write("U3dSet({Path=\"Prefs.Optimize.Iterations\", Value=%d})\n" % prefs.rizomuv_unwrap_optimize_itr)
        f.write("U3dSet({Path=\"Prefs.TriangleFlipsOn\", Value=%s})\n" % str(prefs.rizomuv_unwrap_tflips).lower())
        f.write("U3dSet({Path=\"Prefs.OverlapsOn\", Value=%s})\n" % str(prefs.rizomuv_unwrap_overlaps).lower())
        f.write("U3dSet({Path=\"Prefs.RoomSpace\", Value=%.3f})\n" % prefs.rizomuv_unwrap_overlaps_dist)
        f.write("U3dSet({Path=\"Vars.Unwrap.FreeSelectionBorder\", Value=%s})\n" % str(prefs.rizomuv_unwrap_free).lower())
        f.write("U3dSet({Path=\"Vars.Unwrap.FillHoles\", Value=%s})\n" % str(prefs.rizomuv_unwrap_fill).lower())
        f.write("U3dSet({Path=\"Vars.Optimize.KeepMetric\", Value=%s})\n" % str(prefs.rizomuv_unwrap_keep_metric).lower())
    if prefs.rizomuv_layout_tab:
        f.write("U3dIslandGroups({Mode=\"SetGroupsProperties\", GroupPaths={ \"RootGroup\" }, Properties={Pack={MarginSize=%.3f}}})\n" % prefs.rizomuv_layout_margin)
        f.write("U3dIslandGroups({Mode=\"SetGroupsProperties\", GroupPaths={ \"RootGroup\" }, Properties={Pack={SpacingSize=%.3f}}})\n" % prefs.rizomuv_layout_spacing)
        f.write("ZomIslandGroups({Mode=\"SetGroupsProperties\", WorkingSet=\"Visible\", GroupPath=\"RootGroup\", Properties={Pack={MapResolution=%d}}})\n" % prefs.rizomuv_layout_map_size)


def _ruv_bridge_io(prefs, scene, ruv_path, multi_channel, temp_file, temp_file_out, lua_new, lua_edit):
    """RizomUV 桥接核心导出函数"""
    if os.path.exists(temp_file_out):
        os.remove(temp_file_out)

    exp_objs = []
    exp_meshes = []
    source_names = []

    uv_map = scene.uv_ruv_map
    uv_mode = scene.uv_ruv_mode

    for ob in bpy.context.selected_objects:
        if ob.type != 'MESH':
            continue

        if not multi_channel:
            if len(ob.data.uv_layers) < uv_map:
                for _ in range(uv_map - len(ob.data.uv_layers)):
                    ob.data.uv_layers.new()
            ob.data.uv_layers.active_index = uv_map - 1
            uv_name = ob.data.uv_layers[uv_map - 1].name
            if '.' in uv_name:
                ob.data.uv_layers[uv_map - 1].name = '_'.join(uv_name.split('.'))
        else:
            for l in ob.data.uv_layers:
                if '.' in l.name:
                    l.name = '_'.join(l.name.split('.'))
            for c in range(len(ob.data.uv_layers)):
                uv_name = ob.data.uv_layers[c].name
                prefix = "ch" + str(c + 1) + "_"
                alt_name = "ch" + str(c + 1)
                if prefix not in uv_name and alt_name != uv_name:
                    ob.data.uv_layers[c].name = prefix + uv_name

        source_names.append(ob.name)

    if not source_names:
        return None, []

    for ob in bpy.context.selected_objects:
        if ob.type != 'MESH':
            continue
        new_obj = ob.copy()
        new_obj.data = ob.data.copy()
        new_obj.animation_data_clear()
        new_obj.name = ob.name + "__RUV"
        bpy.context.scene.collection.objects.link(new_obj)
        exp_objs.append(new_obj)
        exp_meshes.append(new_obj.data)

    if not multi_channel:
        for mesh in exp_meshes:
            active_idx = uv_map - 1
            target_name = mesh.uv_layers[active_idx].name
            layers_to_remove = [l.name for l in mesh.uv_layers if l.name != target_name]
            for name in layers_to_remove:
                mesh.uv_layers.remove(mesh.uv_layers[name])

    bpy.ops.object.select_all(action='DESELECT')
    for ob in exp_objs:
        bpy.data.objects[ob.name].select_set(True)

    view = bpy.context.space_data
    if view and view.local_view:
        bpy.ops.view3d.localview(frame_selected=False)

    bpy.ops.export_scene.fbx(
        filepath=temp_file,
        check_existing=True,
        filter_glob="*.fbx",
        use_selection=True,
        use_active_collection=False,
        global_scale=1,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=True,
        object_types={'MESH'},
        use_mesh_modifiers=False,
        use_mesh_modifiers_render=False,
        mesh_smooth_type='OFF',
        use_mesh_edges=False,
        use_tspace=False,
        use_custom_props=False,
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_armature_deform_only=False,
        armature_nodetype='NULL',
        bake_anim=False,
        path_mode='AUTO',
        embed_textures=False,
        batch_mode='OFF',
        use_batch_own_dir=True,
        use_metadata=True,
        axis_forward='-Z',
        axis_up='Y',
    )

    for mesh in exp_meshes:
        bpy.data.meshes.remove(mesh, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')

    temp_file_escaped = "\"" + temp_file + "\""

    if uv_mode == 'New':
        with open(lua_new, "w+", encoding='utf-8') as f:
            if multi_channel:
                f.write("ZomLoad({File={Path=%s, ImportGroups=true, XYZUVW=true, UVWProps=true}})\nZomSet({Path=\"Prefs.FileSuffix\", Value=\"_out\"})" % temp_file_escaped)
            else:
                f.write("ZomLoad({File={Path=%s, ImportGroups=true, XYZ=true}, NormalizeUVW=true})\nU3dSet({Path=\"Prefs.FileSuffix\", Value=\"_out\"})" % temp_file_escaped)
            _ruv_write_lua_settings(f, prefs)
        return lua_new, source_names

    elif uv_mode == 'Edit':
        with open(lua_edit, "w+", encoding='utf-8') as f:
            f.write("ZomLoad({File={Path=%s, ImportGroups=true, XYZUVW=true, UVWProps=true}})\nZomSet({Path=\"Prefs.FileSuffix\", Value=\"_out\"})" % temp_file_escaped)
            _ruv_write_lua_settings(f, prefs)
        return lua_edit, source_names

    return None, source_names


def _ruv_launcher(ruv_path, lua_file):
    """启动 RizomUV 进程"""
    exe = os.path.join(ruv_path, "rizomuv.exe")
    proc = subprocess.Popen([exe, "-cfi" + lua_file], shell=True)
    return proc


def _ruv_transfer_uvs(uvl_objs, source_names, multi_channel, uv_map):
    """将导入物体的 UV 传递到原始物体"""
    for ob in uvl_objs:
        ref_name = ob.name.split("__RUV")[0]
        if ref_name not in bpy.data.objects:
            print(f"MMY-UV: 原始物体 \"{ref_name}\" 已被删除或重命名")
            try:
                bpy.data.meshes.remove(ob.data, do_unlink=True)
            except Exception:
                pass
            continue

        src_obj = bpy.data.objects[ref_name]

        if not multi_channel:
            active_idx = uv_map - 1
            src_obj.select_set(True)
            bpy.context.view_layer.objects.active = ob
            ob.data.uv_layers.active_index = 0
            src_obj.data.uv_layers.active_index = active_idx
            src_obj.data.uv_layers.active.name = ob.data.uv_layers.active.name
            _ruv_join_uvs()
            bpy.ops.object.select_all(action='DESELECT')
        else:
            src_count = len(src_obj.data.uv_layers)
            uvl_count = len(ob.data.uv_layers)
            if uvl_count > 8:
                uvl_count = 8

            src_obj.select_set(True)
            bpy.context.view_layer.objects.active = ob

            if src_count == 0:
                for n in range(uvl_count):
                    src_obj.data.uv_layers.new(name=ob.data.uv_layers[n].name)
            elif src_count < uvl_count:
                for n in range(src_count, uvl_count):
                    src_obj.data.uv_layers.new(name=ob.data.uv_layers[n].name)

            for i in range(min(uvl_count, len(ob.data.uv_layers))):
                ob.data.uv_layers.active_index = i
                src_obj.data.uv_layers.active_index = i
                src_obj.data.uv_layers.active.name = ob.data.uv_layers.active.name
                _ruv_join_uvs()
            bpy.ops.object.select_all(action='DESELECT')


def _ruv_process_timer(proc):
    """检测 RizomUV 进程是否仍在运行"""
    if proc.poll() is None:
        scene = getattr(bpy.context, "scene", None)
        if scene is not None and hasattr(scene, "uv_ruv_toggle"):
            scene.uv_ruv_toggle = True
        return 1.0
    else:
        scene = getattr(bpy.context, "scene", None)
        if scene is not None and hasattr(scene, "uv_ruv_toggle"):
            scene.uv_ruv_toggle = False
        return None


def _ruv_import_timer(temp_file_out, lua_file, multi_channel, uv_map, source_names, prefs, handler):
    """异步检测 RizomUV 输出文件并回导 UV"""
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return None

    if not getattr(scene, "uv_ruv_toggle", False):
        print("MMY-UV: RizomUV 未保存已关闭")
        try:
            bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        except Exception:
            pass
        return None

    if not os.path.isfile(temp_file_out):
        return 1.0

    fsize = os.stat(temp_file_out).st_size
    time.sleep(0.1)
    while fsize != os.stat(temp_file_out).st_size:
        fsize = os.stat(temp_file_out).st_size
        time.sleep(0.1)

    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

    bpy.ops.import_scene.fbx(
        filepath=temp_file_out,
        directory="",
        filter_glob="*.fbx",
        use_manual_orientation=False,
        global_scale=1,
        bake_space_transform=False,
        use_custom_normals=True,
        use_image_search=False,
        use_alpha_decals=False,
        decal_offset=0,
        use_anim=False,
        anim_offset=1,
        use_custom_props=False,
        use_custom_props_enum_as_string=False,
        ignore_leaf_bones=False,
        force_connect_children=False,
        automatic_bone_orientation=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_prepost_rot=True,
        axis_forward='-Z',
        axis_up='Y',
    )

    uvl_objs = [ob for ob in bpy.data.objects if ob.select_get()]
    bpy.ops.object.select_all(action='DESELECT')

    _ruv_transfer_uvs(uvl_objs, source_names, multi_channel, uv_map)

    bpy.ops.object.select_all(action='DESELECT')
    for name in source_names:
        if name not in bpy.data.objects:
            continue
        ob = bpy.data.objects[name]
        try:
            for uv in ob.data.uv_layers:
                if uv.active_render:
                    ob.data.uv_layers.active_index = ob.data.uv_layers[:].index(uv)
            bpy.context.view_layer.objects.active = ob
            ob.select_set(True)
        except Exception:
            continue

    bpy.ops.object.select_all(action='DESELECT')

    for ob in uvl_objs:
        try:
            bpy.data.meshes.remove(ob.data, do_unlink=True)
        except Exception:
            pass

    try:
        bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
    except Exception:
        pass

    if prefs.rizomuv_exit_after_save:
        try:
            with open(lua_file, "w+", encoding='utf-8') as f:
                f.write('ZomSet({Path="Prefs.FileSuffix", Value=""})')
                f.write("ZomQuit()")
        except Exception:
            pass

    return None


def _ruv_retake(temp_file_out, multi_channel, uv_map):
    """手动回取：从已有的输出文件重新导入 UV"""
    if not os.path.isfile(temp_file_out):
        return False, "输出文件不存在，请先发送到 RizomUV 并保存"

    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

    bpy.ops.import_scene.fbx(
        filepath=temp_file_out,
        directory="",
        filter_glob="*.fbx",
        use_manual_orientation=False,
        global_scale=1,
        bake_space_transform=False,
        use_custom_normals=True,
        use_image_search=False,
        use_alpha_decals=False,
        decal_offset=0,
        use_anim=False,
        anim_offset=1,
        use_custom_props=False,
        use_custom_props_enum_as_string=False,
        ignore_leaf_bones=False,
        force_connect_children=False,
        automatic_bone_orientation=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_prepost_rot=True,
        axis_forward='-Z',
        axis_up='Y',
    )

    uvl_objs = [ob for ob in bpy.data.objects if ob.select_get()]
    bpy.ops.object.select_all(action='DESELECT')

    source_names = []
    for ob in uvl_objs:
        ref = ob.name.split("__RUV")[0]
        if ref:
            source_names.append(ref)

    _ruv_transfer_uvs(uvl_objs, source_names, multi_channel, uv_map)

    bpy.ops.object.select_all(action='DESELECT')
    for ob in uvl_objs:
        try:
            bpy.data.meshes.remove(ob.data, do_unlink=True)
        except Exception:
            pass

    return True, "UV 回取完成"


def _draw_rizomuv_text():
    """在 3D 视口绘制 RizomUV 等待提示"""
    font_id = 0
    try:
        width = bpy.context.area.width
        blf.color(font_id, 1, 1, 1, 1)
        blf.position(font_id, width / 2 - 300, 150, 0)
        blf.size(font_id, 24)
        blf.draw(font_id, "RizomUV: 按 'CTRL+S' 保存以传回 UV...")
    except Exception:
        pass


class RUV_OT_send_to_rizomuv(bpy.types.Operator):
    bl_idname = "uv.mmy_send_to_rizomuv"
    bl_label = "发送到 RizomUV"
    bl_description = "导出选中网格到 RizomUV 进行 UV 展开"
    bl_options = {'REGISTER', 'UNDO'}

    _handle = None

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.mode == 'OBJECT'

    def execute(self, context):
        if not context.selected_objects:
            self.report({'INFO'}, "未选中任何对象")
            return {'FINISHED'}

        prefs = _get_uv_preferences(context)
        if prefs is None:
            self.report({'ERROR'}, "无法获取插件偏好设置")
            return {'CANCELLED'}

        ruv_path = prefs.rizomuv_app_path
        if not ruv_path:
            self.report({'ERROR'}, "请先在偏好设置中配置 RizomUV 路径")
            return {'CANCELLED'}

        exe = os.path.join(ruv_path, "rizomuv.exe")
        if not os.path.isfile(exe):
            self.report({'ERROR'}, f"RizomUV 可执行文件不存在")
            return {'CANCELLED'}

        multi_channel = prefs.rizomuv_multi_uv
        temp_file, temp_file_out, lua_new, lua_edit = _ruv_get_temp_paths()

        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_rizomuv_text, (), 'WINDOW', 'POST_PIXEL'
        )

        lua_file, source_names = _ruv_bridge_io(
            prefs, context.scene, ruv_path, multi_channel,
            temp_file, temp_file_out, lua_new, lua_edit,
        )

        if lua_file is None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except Exception:
                pass
            self.report({'WARNING'}, "没有可导出的网格对象")
            return {'CANCELLED'}

        uv_map = context.scene.uv_ruv_map

        if not context.scene.uv_ruv_toggle:
            proc = _ruv_launcher(ruv_path, lua_file)
            bpy.app.timers.register(
                functools.partial(_ruv_process_timer, proc),
                first_interval=1.0, persistent=True,
            )
            bpy.app.timers.register(
                functools.partial(
                    _ruv_import_timer,
                    temp_file_out, lua_file, multi_channel,
                    uv_map, source_names, prefs, self._handle,
                ),
                first_interval=1.0,
            )
        else:
            bpy.app.timers.register(
                functools.partial(
                    _ruv_import_timer,
                    temp_file_out, lua_file, multi_channel,
                    uv_map, source_names, prefs, self._handle,
                ),
                first_interval=1.0,
            )

        return {'FINISHED'}


class RUV_OT_retake_rizomuv(bpy.types.Operator):
    bl_idname = "uv.mmy_retake_rizomuv"
    bl_label = "手动回取 RizomUV"
    bl_description = "从 RizomUV 输出文件重新导入 UV"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.mode == 'OBJECT'

    def execute(self, context):
        if not context.selected_objects:
            self.report({'INFO'}, "未选中任何对象")
            return {'FINISHED'}

        prefs = _get_uv_preferences(context)
        multi_channel = prefs.rizomuv_multi_uv if prefs else False
        temp_file_out = _ruv_get_temp_paths()[1]
        uv_map = context.scene.uv_ruv_map

        success, message = _ruv_retake(temp_file_out, multi_channel, uv_map)
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, message)
            return {'CANCELLED'}


classes = (
    UV_OT_detect_overlap_highlight,
    UV_OT_invert_overlap_selection,
    OBJECT_OT_transfer_uv,
    UV_OT_test_photoshop_path,
    UV_OT_quick_export_layout,
    UV_OT_open_last_export_in_photoshop,
    OBJECT_OT_unify_uvmap_name,
    RUV_OT_send_to_rizomuv,
    RUV_OT_retake_rizomuv,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    stop_all_timers()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)