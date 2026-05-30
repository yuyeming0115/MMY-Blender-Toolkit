# -*- coding: utf-8 -*-
"""NLA 轨道管理工具"""

import bpy


def gather_export_nla_tracks(context, selected_objects_only):
    """收集导出范围内的 NLA 轨道"""
    candidates = list(context.selected_objects) if selected_objects_only else list(context.view_layer.objects)
    items = []
    seen = set()

    for obj in candidates:
        anim_data = getattr(obj, "animation_data", None)
        if not anim_data:
            continue

        for track in anim_data.nla_tracks:
            key = (obj.name, track.name)
            if key in seen:
                continue
            seen.add(key)
            items.append((obj.name, track.name, f"{obj.name} / {track.name}"))

    return items


def sync_nla_items(operator, context):
    """同步操作符的 NLA 条目"""
    desired_items = gather_export_nla_tracks(context, operator.selected_objects)
    desired_keys = [(object_name, track_name) for object_name, track_name, _label in desired_items]
    current_keys = [(item.object_name, item.track_name) for item in operator.nla_items]

    if desired_keys == current_keys:
        return

    previous_states = {
        (item.object_name, item.track_name): item.enabled
        for item in operator.nla_items
    }

    operator.nla_items.clear()
    for object_name, track_name, label in desired_items:
        entry = operator.nla_items.add()
        entry.object_name = object_name
        entry.track_name = track_name
        entry.label = label
        entry.enabled = previous_states.get((object_name, track_name), True)


def apply_nla_selection(context, selected_objects_only, nla_items):
    """应用 NLA 轨道选择"""
    enabled_lookup = {
        (item.object_name, item.track_name): item.enabled
        for item in nla_items
    }
    track_state = {}
    candidates = list(context.selected_objects) if selected_objects_only else list(context.view_layer.objects)

    for obj in candidates:
        anim_data = getattr(obj, "animation_data", None)
        if not anim_data:
            continue

        for track in anim_data.nla_tracks:
            key = (obj.name, track.name)
            if key not in enabled_lookup:
                continue
            track_state[key] = track.mute
            track.mute = not enabled_lookup[key]

    return track_state


def restore_nla_selection(context, selected_objects_only, track_state):
    """恢复 NLA 轨道状态"""
    if not track_state:
        return

    candidates = list(context.selected_objects) if selected_objects_only else list(context.view_layer.objects)
    for obj in candidates:
        anim_data = getattr(obj, "animation_data", None)
        if not anim_data:
            continue

        for track in anim_data.nla_tracks:
            key = (obj.name, track.name)
            if key in track_state:
                track.mute = track_state[key]