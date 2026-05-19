import bpy
import os
import subprocess
import sys

from bpy.props import BoolProperty, StringProperty, EnumProperty


# ── 模块级缓存：EnumProperty items 列表需要持久引用 ──
_TEMP_SUFFIX_MODE_CACHE = []


def get_temp_suffix_mode_items(self, context):
    """动态获取临时后缀处理模式选项"""
    _TEMP_SUFFIX_MODE_CACHE.clear()
    _TEMP_SUFFIX_MODE_CACHE.append(('default', "使用配置", "使用偏好设置中的后缀去除列表"))
    _TEMP_SUFFIX_MODE_CACHE.append(('none', "不去除", "保留原始文件名，不去除任何后缀"))
    _TEMP_SUFFIX_MODE_CACHE.append(('custom', "自定义", "指定要去除的后缀"))
    return _TEMP_SUFFIX_MODE_CACHE


class MMY_OT_RenderPreview(bpy.types.Operator):
    """渲染预览图到 Render 文件夹"""
    bl_idname = "mmy.render_preview"
    bl_label = "渲染预览图"
    bl_options = {'REGISTER'}

    auto_open_folder: BoolProperty(
        name="自动打开文件夹",
        description="渲染完成后自动打开 Render 文件夹",
        default=True
    )

    # 临时后缀处理模式（用于下拉菜单选项）
    temp_suffix_mode: EnumProperty(
        name="后缀处理",
        items=get_temp_suffix_mode_items,
        default='default'
    )

    custom_suffix: StringProperty(
        name="自定义后缀",
        description="指定要去除的后缀",
        default="_Render"
    )

    @classmethod
    def poll(cls, context):
        # 必须有保存过的文件
        return bpy.data.filepath != ""

    def execute(self, context):
        blend_path = bpy.data.filepath

        if not blend_path:
            self.report({'ERROR'}, "请先保存文件")
            return {'CANCELLED'}

        # 获取文件名和目录
        blend_dir = os.path.dirname(blend_path)
        blend_name = os.path.splitext(os.path.basename(blend_path))[0]

        # 根据模式处理后缀去除
        output_name = self._process_suffix(blend_name, context)

        # 构建 Render 目录
        render_dir = os.path.join(blend_dir, "Render")
        if not os.path.exists(render_dir):
            os.makedirs(render_dir)

        output_path = os.path.join(render_dir, f"{output_name}.png")

        # 设置渲染参数
        scene = context.scene
        original_filepath = scene.render.filepath
        original_color_mode = scene.render.image_settings.color_mode

        # Blender 5.x: file_format 在 image_settings 下
        try:
            original_format = scene.render.image_settings.file_format
        except AttributeError:
            original_format = None

        # 保存原始帧号
        original_frame = scene.frame_current

        try:
            # 设置帧号为 1
            scene.frame_set(1)

            # 设置输出参数
            scene.render.filepath = output_path
            scene.render.image_settings.file_format = 'PNG'
            scene.render.image_settings.color_mode = 'RGBA'

            # 执行渲染
            bpy.ops.render.render(write_still=True)

            # 裁剪透明边缘
            self._crop_transparent_border(output_path)

            self.report({'INFO'}, f"预览图已保存: {output_path}")

            # 自动打开文件夹
            if self.auto_open_folder:
                self._open_folder(render_dir)

        finally:
            # 恢复原始设置
            scene.render.filepath = original_filepath
            if original_format:
                scene.render.image_settings.file_format = original_format
            scene.render.image_settings.color_mode = original_color_mode
            scene.frame_set(original_frame)

        return {'FINISHED'}

    def _process_suffix(self, blend_name, context):
        """根据配置处理文件名后缀"""
        if self.temp_suffix_mode == 'none':
            # 不去除任何后缀
            return blend_name

        elif self.temp_suffix_mode == 'custom':
            # 使用自定义后缀
            if blend_name.endswith(self.custom_suffix):
                return blend_name[:-len(self.custom_suffix)]
            return blend_name

        else:  # 'default' - 使用偏好设置中的列表
            addon = context.preferences.addons.get("mmy_toolkit")
            if addon and addon.preferences:
                suffixes = [item.name for item in addon.preferences.render_remove_suffixes]
                for suffix in suffixes:
                    if blend_name.endswith(suffix):
                        return blend_name[:-len(suffix)]
            return blend_name

    def _crop_transparent_border(self, image_path):
        """裁剪图片的透明边缘"""
        try:
            # 尝试使用 Pillow
            from PIL import Image

            img = Image.open(image_path)
            if img.mode == 'RGBA':
                bbox = img.getbbox()
                if bbox:
                    cropped = img.crop(bbox)
                    cropped.save(image_path)
                    print(f"[MMY] 已裁剪透明边缘: {bbox}")
                else:
                    print("[MMY] 图片全透明，不裁剪")
            else:
                print("[MMY] 图片无透明通道，不裁剪")

        except ImportError:
            # Pillow 未安装，使用 Blender 内置 API
            print("[MMY] Pillow 未安装，尝试使用 Blender API")
            self._crop_with_blender(image_path)

    def _crop_with_blender(self, image_path):
        """使用 Blender API 裁剪"""
        try:
            # 加载图片到 Blender
            img = bpy.data.images.load(image_path)

            # 获取像素数据
            pixels = list(img.pixels)
            width = img.size[0]
            height = img.size[1]

            # 查找非透明边界
            min_x, max_x = width, 0
            min_y, max_y = height, 0

            for y in range(height):
                for x in range(width):
                    idx = (y * width + x) * 4
                    alpha = pixels[idx + 3]
                    if alpha > 0.01:  # 非透明像素
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

            # 如果找到有效区域
            if min_x < max_x and min_y < max_y:
                # 创建裁剪后的图片
                new_width = max_x - min_x + 1
                new_height = max_y - min_y + 1
                new_img = bpy.data.images.new(
                    f"{img.name}_cropped",
                    new_width,
                    new_height,
                    alpha=True
                )

                # 复制像素
                new_pixels = []
                for y in range(min_y, max_y + 1):
                    for x in range(min_x, max_x + 1):
                        idx = (y * width + x) * 4
                        new_pixels.extend([
                            pixels[idx],     # R
                            pixels[idx + 1], # G
                            pixels[idx + 2], # B
                            pixels[idx + 3], # A
                        ])

                new_img.pixels = new_pixels

                # 保存裁剪后的图片
                new_img.filepath_raw = image_path
                new_img.file_format = 'PNG'
                new_img.save()

                # 清理
                bpy.data.images.remove(img)
                bpy.data.images.remove(new_img)

                print(f"[MMY] Blender API 裁剪完成: ({min_x}, {min_y}) - ({max_x}, {max_y})")
            else:
                print("[MMY] 图片全透明，不裁剪")
                bpy.data.images.remove(img)

        except Exception as e:
            print(f"[MMY] Blender API 裁剪失败: {e}")

    def _open_folder(self, path):
        """打开文件夹"""
        try:
            if sys.platform == 'win32':
                subprocess.run(['explorer', path])
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            print(f"[MMY] 打开文件夹失败: {e}")


class MMY_OT_RenderPreviewNoSuffix(bpy.types.Operator):
    """渲染预览图（不去除后缀）"""
    bl_idname = "mmy.render_preview_no_suffix"
    bl_label = "不去除后缀"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # 调用主 Operator，设置模式为 'none'
        bpy.ops.mmy.render_preview(temp_suffix_mode='none')
        return {'FINISHED'}


class MMY_OT_RenderPreviewCustomSuffix(bpy.types.Operator):
    """渲染预览图（自定义后缀）"""
    bl_idname = "mmy.render_preview_custom_suffix"
    bl_label = "自定义后缀"
    bl_options = {'REGISTER'}

    custom_suffix: StringProperty(
        name="要去除的后缀",
        default="_Render"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "custom_suffix")

    def execute(self, context):
        bpy.ops.mmy.render_preview(temp_suffix_mode='custom', custom_suffix=self.custom_suffix)
        return {'FINISHED'}


class MMY_MT_RenderPreviewMenu(bpy.types.Menu):
    """渲染预览图下拉菜单"""
    bl_idname = "MMY_MT_render_preview_menu"
    bl_label = "渲染预览图选项"

    def draw(self, context):
        layout = self.layout

        # 默认：使用配置
        layout.operator("mmy.render_preview", text="使用配置", icon='CHECKMARK').temp_suffix_mode = 'default'

        # 不去除后缀
        layout.operator("mmy.render_preview_no_suffix", text="不去除后缀", icon='X')

        # 自定义后缀
        layout.operator("mmy.render_preview_custom_suffix", text="自定义后缀...", icon='EDIT')

        layout.separator()

        # 显示当前配置的后缀列表
        addon = context.preferences.addons.get("mmy_toolkit")
        if addon and addon.preferences:
            suffixes = [item.name for item in addon.preferences.render_remove_suffixes]
            if suffixes:
                layout.label(text="当前去除列表:")
                for suffix in suffixes:
                    layout.label(text=f"  {suffix}", icon='DOT')


_classes = (
    MMY_OT_RenderPreview,
    MMY_OT_RenderPreviewNoSuffix,
    MMY_OT_RenderPreviewCustomSuffix,
    MMY_MT_RenderPreviewMenu,
)


def _append_render_button(self, context):
    """在 3D 视图 Header 添加渲染按钮和下拉菜单"""
    layout = self.layout
    # 只在对象模式下显示
    if context.mode == 'OBJECT':
        layout.separator()
        # 主按钮 + 下拉菜单
        row = layout.row(align=True)
        row.operator("mmy.render_preview", text="", icon='RENDER_STILL')
        row.menu("MMY_MT_render_preview_menu", text="", icon='DOWNARROW_HLT')


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    # 添加 Header 按钮
    try:
        bpy.types.VIEW3D_HT_header.append(_append_render_button)
    except Exception as e:
        print(f"[MMY] 添加 Header 按钮失败: {e}")


def unregister():
    # 移除 Header 按钮
    try:
        bpy.types.VIEW3D_HT_header.remove(_append_render_button)
    except:
        pass

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)