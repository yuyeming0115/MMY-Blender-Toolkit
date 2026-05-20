import re
import bpy


PURPLE_COLOR = (0.7490196, 0.1490196, 0.7490196, 1.0)


def clean_name(name: str) -> str:
    """去除 Blender 自动追加的数字后缀，如 .001 .002 .010 等"""
    return re.sub(r'\.\d{3}$', '', name)


def is_purple_material(mat) -> bool:
    """
    判断材质是否为 FBX 导入后丢失贴图产生的紫色默认材质。
    检查条件：
    - 使用 Principled BSDF 着色器
    - Base Color 为默认紫色 (#BF26BF)
    """
    if not mat or not mat.use_nodes:
        return False

    bsdf = None
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf = node
            break

    if not bsdf:
        return False

    base_color = bsdf.inputs["Base Color"].default_value
    if abs(base_color[0] - PURPLE_COLOR[0]) < 0.01 and \
       abs(base_color[1] - PURPLE_COLOR[1]) < 0.01 and \
       abs(base_color[2] - PURPLE_COLOR[2]) < 0.01:
        return True

    return False


def reassign_material(old_mat, new_mat):
    """将所有引用 old_mat 的物体替换为 new_mat，并删除 old_mat（如果安全）"""
    for obj in bpy.data.objects:
        for i, slot in enumerate(obj.material_slots):
            if slot.material == old_mat:
                obj.material_slots[i].material = new_mat

    if old_mat.users == 0:
        bpy.data.materials.remove(old_mat)


def reassign_image_textures(old_img, new_img):
    """将材质节点中引用 old_img 的 Image 节点替换为 new_img"""
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image == old_img:
                node.image = new_img

    if old_img.users == 0:
        bpy.data.images.remove(old_img)


def is_empty_collection(coll) -> bool:
    """检查 Collection 是否为空（无任何对象）"""
    return len(coll.objects) == 0 and len(coll.children) == 0


def find_node_groups_to_clean() -> list:
    """查找未被引用的节点组"""
    return [ng for ng in bpy.data.node_groups if ng.users == 0 and not ng.is_registered_nodetree]