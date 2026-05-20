"""简体中文界面"""

TRANSLATIONS = {
    # 面板标题
    "panel_title": "Poly @ Edit",
    "smooth_groups_title": "平滑组",
    "selection_sets_title": "选择集",

    # 模式提示
    "enter_edit_mode": "请进入编辑模式",

    # 显示 ID
    "show_ids": "显示 ID",
    "sel_only": "仅选中",

    # 交互模式
    "interaction_mode": "交互模式：",
    "mode_set": "设定 / 切换",
    "mode_select": "选择面",

    # 按钮提示
    "click_to_select": "点击 ID 以选择面",

    # 清除按钮
    "clear_selected": "清除选中面的组",

    # 修正按钮
    "fix_shading": "着色错误修正",

    # 锐边显示
    "hide_sharp": "隐藏锐边显示",

    # 报告消息
    "msg_selected_faces": "已选中平滑组 {group} 的 {count} 个面",
    "msg_no_faces": "平滑组 {group} 中没有找到面",
    "msg_deselected_faces": "从选区移除平滑组 {group} 的 {count} 个面",
    "msg_no_faces_to_deselect": "选区中没有平滑组 {group} 的面可移除",
    "msg_added_faces": "将平滑组 {group} 的 {count} 个面加入选区",
    "msg_fix_done": "着色已修正。插件数据已清除。",

    # 选择模式提示
    "select_mode_hint": "Shift：加选 | Ctrl：减选",

    # 选择集相关
    "quick_operations": "快捷操作：",
    "click_normal": "普通点击 = 替换",
    "click_shift": "Shift = 加选",
    "click_ctrl": "Ctrl = 减选",
    "no_selection_sets": "暂无选择集",
    "edit_mode": "编辑模式",
    "object_mode": "物体模式",
    "load_label": "加载:",
    "new_selection_set": "新建选择集",
    "update_selection_set": "更新",
    "rename_selection_set": "重命名",
    "delete_selection_set": "删除",

    # 错误提示
    "name_cannot_be_empty": "名称不能为空!",
    "name_already_exists": "名称已存在!",
    "selection_set_not_found": "选择集不存在!",
    "invalid_edit_set": "无效的编辑模式选择集!",
    "object_not_found": "关联物体 {object} 不存在!",
    "no_selection": "未选择任何对象",
}


def get_text(key):
    """获取翻译文本"""
    return TRANSLATIONS.get(key, key)


def get_text_formatted(key, **kwargs):
    """获取翻译文本并格式化"""
    text = get_text(key)
    return text.format(**kwargs)