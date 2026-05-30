# -*- coding: utf-8 -*-
"""贴图处理工具"""

import bpy
import os
import shutil


def resize_image(src_path, dest_path, target_size, file_format='PNG'):
    """缩放贴图到目标尺寸"""
    try:
        img = bpy.data.images.load(src_path, check_existing=True)
        orig_w, orig_h = img.size

        if orig_w >= orig_h:
            new_w = target_size
            new_h = max(1, round(orig_h * target_size / orig_w))
        else:
            new_h = target_size
            new_w = max(1, round(orig_w * target_size / orig_h))

        img.scale(new_w, new_h)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.filepath_raw = dest_path
        img.file_format = file_format
        img.save()
        print(f"贴图已缩放: {orig_w}x{orig_h} -> {new_w}x{new_h}")
        return True
    except Exception as e:
        print(f"贴图缩放错误: {e}")
        return False


def get_texture_suffix_from_filename(filename):
    """从文件名判断贴图类型"""
    name_lower = filename.lower()
    words = name_lower.replace('.', ' ').replace('_', ' ').replace('-', ' ').split()

    has_normal_keyword = any(w in ('normal', 'nrm', 'norm') for w in words)
    has_color_keyword = any(w in ('albedo', 'diffuse', 'color', 'col', 'basecolor', 'base',
                                   'map', 'texture', 'tex') for w in words)

    if has_normal_keyword and not has_color_keyword or '法线' in filename:
        return '_Normal'
    elif 'albedo' in name_lower or 'diffuse' in name_lower or 'basecolor' in name_lower:
        return '_Albedo'
    elif ('color' in name_lower or '颜色' in filename) and 'normal' not in name_lower:
        return '_Albedo'
    elif 'metallic' in name_lower or '金属' in filename:
        return '_Metallic'
    elif 'roughness' in name_lower or '粗糙' in filename:
        return '_Roughness'
    elif 'ao' in name_lower or 'ambient' in name_lower:
        return '_AO'
    elif 'emission' in name_lower or 'emissive' in name_lower:
        return '_Emission'
    return ''


def get_texture_suffix(socket_name, node_label="", node_type=None):
    """根据 socket 名称返回贴图后缀"""
    socket_lower = socket_name.lower()
    label_lower = node_label.lower()

    if node_type == 'NORMAL_MAP' or node_type == 'SHADER_NODE_NORMAL_MAP':
        return '_Normal'

    if '法线' in node_label or label_lower == 'normal':
        return '_Normal'

    if socket_lower in ('normal',):
        return '_Normal'

    if socket_lower in ('base color', 'albedo', 'diffuse', 'basecolor') or '基础色' in socket_name:
        return '_Albedo'

    if socket_lower == 'color' and 'normal' not in label_lower and '法线' not in node_label \
       and node_type not in ('NORMAL_MAP', 'SHADER_NODE_NORMAL_MAP'):
        if '颜色' in socket_name:
            return '_Albedo'

    if 'metallic' in socket_lower or '金属' in socket_name:
        return '_Metallic'
    elif 'roughness' in socket_lower or '粗糙' in socket_name:
        return '_Roughness'
    elif 'specular' in socket_lower:
        return '_Specular'
    elif 'emission' in socket_lower:
        return '_Emission'
    elif 'ambient occlusion' in socket_lower or socket_lower == 'ao':
        return '_AO'
    elif socket_lower == 'alpha':
        return '_Alpha'

    return ''


def copy_and_rename_texture(obj, target_dir, target_size=0, keep_original_names=True):
    """复制并重命名贴图"""
    if not obj.data or not hasattr(obj.data, 'materials'):
        return

    clean_obj_name = bpy.path.clean_name(obj.name)
    total_mats = len([m for m in obj.data.materials if m and m.use_nodes])

    for mat_index, mat in enumerate(obj.data.materials):
        if not mat or not mat.use_nodes:
            continue

        if total_mats == 1:
            mat_suffix = ""
        else:
            mat_suffix = f"_Mat{mat_index + 1}"

        nodes = mat.node_tree.nodes
        processed_images = set()

        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image = node.image

                if image.name in processed_images:
                    continue
                processed_images.add(image.name)

                has_valid_link = False
                texture_suffix = ''

                if image.filepath:
                    filename = os.path.basename(image.filepath)
                    texture_suffix = get_texture_suffix_from_filename(filename)
                    if texture_suffix:
                        has_valid_link = any(output.links for output in node.outputs)

                if not texture_suffix:
                    for output in node.outputs:
                        for link in output.links:
                            socket_name = link.to_socket.name
                            target_node = link.to_node
                            node_label = target_node.label if target_node else ""
                            node_type = target_node.type if target_node else ""
                            suffix = get_texture_suffix(socket_name, node_label, node_type)
                            if suffix:
                                has_valid_link = True
                                texture_suffix = suffix
                                break
                        if has_valid_link:
                            break

                if not has_valid_link:
                    for output in node.outputs:
                        if output.links:
                            has_valid_link = True
                            texture_suffix = '_Texture'
                            break

                if has_valid_link:
                    src_path = bpy.path.abspath(image.filepath)
                    ext = os.path.splitext(src_path)[1]
                    if not ext:
                        ext = ".png"

                    if image.filepath:
                        original_filename = os.path.basename(image.filepath)
                    else:
                        original_filename = bpy.path.clean_name(image.name)

                    if keep_original_names:
                        new_file_name = original_filename
                        dest_path = os.path.join(target_dir, new_file_name)
                        counter = 1
                        while os.path.exists(dest_path):
                            name_without_ext, cur_ext = os.path.splitext(new_file_name)
                            new_file_name = f"{name_without_ext}_{counter}{cur_ext}"
                            dest_path = os.path.join(target_dir, new_file_name)
                            if counter > 20:
                                break
                            counter += 1
                    else:
                        new_file_name = clean_obj_name + mat_suffix + texture_suffix + ext
                        dest_path = os.path.join(target_dir, new_file_name)

                    resize_info = f" -> {target_size}px" if target_size > 0 else ""
                    name_mode = "原名" if keep_original_names else "重命名"
                    print(f"[贴图] {original_filename} -> {new_file_name} ({name_mode}{resize_info})")

                    try:
                        os.makedirs(target_dir, exist_ok=True)

                        if os.path.exists(src_path) and not image.packed_file:
                            if target_size > 0:
                                resize_image(src_path, dest_path, target_size)
                            else:
                                shutil.copy2(src_path, dest_path)
                                print(f"贴图已复制: {new_file_name}")
                        else:
                            print(f"提取打包贴图: {image.name} -> {new_file_name}")
                            old_filepath = image.filepath
                            try:
                                image.filepath_raw = dest_path
                                image.file_format = 'PNG'

                                if target_size > 0:
                                    temp_path = dest_path + ".temp"
                                    image.filepath_raw = temp_path
                                    image.save()
                                    resize_image(temp_path, dest_path, target_size)
                                    if os.path.exists(temp_path):
                                        os.remove(temp_path)
                                else:
                                    image.save()
                            except Exception as e:
                                print(f"保存错误: {e}")
                            finally:
                                image.filepath_raw = old_filepath

                    except Exception as e:
                        print(f"贴图同步错误: {e}")