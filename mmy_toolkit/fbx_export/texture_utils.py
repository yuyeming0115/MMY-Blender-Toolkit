# -*- coding: utf-8 -*-
"""贴图处理工具"""

import bpy
import os
import shutil
import hashlib


def get_file_hash(filepath):
    """计算文件哈希值用于比较"""
    try:
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


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


def copy_and_rename_texture(obj, target_dir, target_size=0, keep_original_names=True, global_processed_images=None):
    """复制并重命名贴图

    Args:
        obj: 目标对象
        target_dir: 导出目录
        target_size: 缩放尺寸（0表示不缩放）
        keep_original_names: 是否保持原文件名
        global_processed_images: 全局已处理贴图字典 {image_name: dest_path}，用于跨材质去重
    """
    if not obj.data or not hasattr(obj.data, 'materials'):
        return

    # 初始化全局去重字典
    if global_processed_images is None:
        global_processed_images = {}

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
        # 当前材质内的去重（用于同一材质内多个节点使用同一贴图）
        local_processed_images = set()

        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image = node.image

                # 跨材质去重检查：如果这个贴图已经被处理过，跳过
                if image.name in global_processed_images:
                    print(f"[贴图] '{image.name}' 已在全局处理过，跳过")
                    continue

                # 材质内去重检查
                if image.name in local_processed_images:
                    continue
                local_processed_images.add(image.name)

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
                    # 获取原始文件路径
                    if image.filepath:
                        src_path = bpy.path.abspath(image.filepath)
                    elif image.packed_file:
                        # 打包贴图没有外部路径，使用临时路径
                        src_path = ""
                    else:
                        src_path = ""

                    ext = os.path.splitext(src_path)[1] if src_path else ""
                    if not ext:
                        # 从 image.name 获取扩展名，或默认使用 .png
                        name_ext = os.path.splitext(image.name)[1]
                        ext = name_ext if name_ext in ('.png', '.jpg', '.jpeg', '.tga', '.bmp', '.exr', '.hdr') else ".png"

                    # 获取原始文件名
                    original_filename = ""
                    if image.filepath:
                        abs_path = bpy.path.abspath(image.filepath)
                        original_filename = os.path.basename(abs_path)
                    elif image.name:
                        original_filename = image.name

                    # 清理文件名
                    if original_filename:
                        name_base, name_ext = os.path.splitext(original_filename)
                        # 去除 Blender 可能添加的数字后缀如 ".001"
                        if '.' in name_base:
                            parts = name_base.split('.')
                            if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) <= 3:
                                name_base = parts[0]
                        original_filename = name_base + (name_ext if name_ext else ext)

                    # 如果 original_filename 看起来像 Blender 自动生成的名称或为空，使用更合理的名称
                    is_bad_name = (
                        not original_filename or
                        original_filename.strip() == "" or
                        (original_filename.startswith('_') and original_filename.replace('_', '').replace('.', '').isdigit()) or
                        original_filename.lower().startswith('untitled')
                    )

                    if is_bad_name:
                        original_filename = clean_obj_name + mat_suffix + texture_suffix + ext

                    if keep_original_names:
                        new_file_name = original_filename
                    else:
                        new_file_name = clean_obj_name + mat_suffix + texture_suffix + ext

                    dest_path = os.path.join(target_dir, new_file_name)

                    # 检查文件是否已存在，如果是相同内容则跳过
                    need_copy = True
                    if os.path.exists(dest_path):
                        # 比较文件内容
                        existing_hash = get_file_hash(dest_path)

                        # 获取源文件哈希（如果有外部文件）
                        if src_path and os.path.exists(src_path):
                            src_hash = get_file_hash(src_path)
                            if src_hash and existing_hash and src_hash == existing_hash:
                                print(f"[贴图] '{new_file_name}' 已存在且内容相同，跳过复制")
                                need_copy = False
                        else:
                            # 内容可能不同或打包贴图，需要添加后缀
                            counter = 1
                            while os.path.exists(dest_path) and counter <= 20:
                                name_without_ext, cur_ext = os.path.splitext(new_file_name)
                                new_file_name = f"{name_without_ext}_{counter}{cur_ext}"
                                dest_path = os.path.join(target_dir, new_file_name)
                                counter += 1

                    resize_info = f" -> {target_size}px" if target_size > 0 else ""
                    name_mode = "原名" if keep_original_names else "重命名"
                    print(f"[贴图] {original_filename} -> {new_file_name} ({name_mode}{resize_info})")

                    # 记录到全局已处理字典
                    global_processed_images[image.name] = dest_path

                    if need_copy:
                        try:
                            os.makedirs(target_dir, exist_ok=True)

                            if src_path and os.path.exists(src_path) and not image.packed_file:
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