import bpy
from importlib import import_module

bl_info = {
    "name": "MMY Blender Toolkit",
    "blender": (4, 5, 0),
    "version": (0, 1, 0),
    "category": "Pipeline",
    "description": "MMY 系列 Blender 效率优化工具集",
}

_modules = [
    ".save_helper",
]

_prefs_cls = None


def register():
    global _prefs_cls
    from . import config

    package = __package__

    class MMY_Preferences(bpy.types.AddonPreferences):
        bl_idname = "mmy_toolkit"

        custom_suffixes: bpy.props.StringProperty(
            name="后缀列表",
            description="逗号分隔的后缀列表",
            default=", ".join(config.DEFAULT_SUFFIXES),
        )

        def draw(self, context):
            layout = self.layout
            layout.prop(self, "custom_suffixes")
            layout.label(text="默认: " + ", ".join(config.DEFAULT_SUFFIXES))

    _prefs_cls = MMY_Preferences
    # 先尝试注销（防止重载时残留）
    try:
        bpy.utils.unregister_class(MMY_Preferences)
    except (ValueError, RuntimeError):
        pass
    try:
        bpy.utils.register_class(MMY_Preferences)
    except ValueError:
        pass

    for mod in _modules:
        import_module(mod, package).register()


def unregister():
    global _prefs_cls
    from importlib import import_module

    package = __package__

    for mod in reversed(_modules):
        import_module(mod, package).unregister()

    if _prefs_cls is not None:
        try:
            bpy.utils.unregister_class(_prefs_cls)
        except ValueError:
            pass
        _prefs_cls = None


if __name__ == "__main__":
    register()
