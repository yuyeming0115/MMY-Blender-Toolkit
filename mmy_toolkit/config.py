import bpy

DEFAULT_SUFFIXES = [
    "_Mesh",
    "_Mat",
    "_Rig",
    "_Ani",
    "_Render",
]


def get_suffixes() -> list[str]:
    prefs = bpy.context.preferences.addons.get("mmy_toolkit")
    if prefs and prefs.preferences.custom_suffixes.strip():
        return [s.strip() for s in prefs.preferences.custom_suffixes.split(",") if s.strip()]
    return DEFAULT_SUFFIXES
