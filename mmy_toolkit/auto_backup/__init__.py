"""自动备份模块入口"""

import bpy
import time
from . import properties
from . import backup_manager


# 模块级变量
_timer_handle = None


def _backup_timer_callback():
    """定时器回调函数 - 无条件运行，在回调中检查条件"""
    global _timer_handle

    # 获取偏好设置
    prefs = properties.get_backup_prefs()

    if not prefs:
        return 120  # 继续运行

    try:
        enabled = bool(prefs.enabled_backup)
        minor_interval = int(prefs.minor_interval_backup)
        major_interval = int(prefs.major_interval_backup)
        daily_max = int(prefs.daily_max_backups)
    except Exception as e:
        print(f"[MMY备份] 偏好设置读取失败: {e}")
        return 120

    # 如果用户禁用了，停止定时器
    if not enabled:
        _timer_handle = None
        return None

    # 尝试获取 filepath
    filepath = ""
    try:
        filepath = bpy.data.filepath
    except:
        pass

    # 更新下次保存时间
    backup_manager.update_next_save_time(minor_interval)

    # 检查文件是否有名
    if not filepath:
        # 未命名文件，跳过本次备份，继续定时
        return minor_interval * 60

    # 文件有名，执行备份逻辑
    current_time = time.time()
    scene = bpy.context.scene

    # 判断是否需要大版本备份
    last_major = getattr(scene, 'mmy_backup_last_major', 0.0)
    time_since_major = current_time - last_major
    need_major = time_since_major >= major_interval * 60

    if need_major:
        backup_path = backup_manager.create_backup(is_major=True)
        if backup_path:
            scene.mmy_backup_last_major = current_time
            backup_manager.cleanup_old_backups(
                backup_manager.get_today_dir(),
                daily_max,
                is_major=True
            )
            print(f"[MMY备份] 大版本备份: {backup_path}")

    # 判断是否需要小版本备份
    last_minor = getattr(scene, 'mmy_backup_last_minor', 0.0)
    time_since_minor = current_time - last_minor
    need_minor = time_since_minor >= minor_interval * 60

    if need_minor:
        backup_path = backup_manager.create_backup(is_major=False)
        if backup_path:
            scene.mmy_backup_last_minor = current_time
            backup_manager.cleanup_old_backups(
                backup_manager.get_today_dir(),
                daily_max,
                is_major=False
            )
            print(f"[MMY备份] 小版本备份: {backup_path}")

    # 清理旧日期文件夹（偶尔执行）
    if need_minor:
        backup_manager.cleanup_old_date_folders()

    # 计算容量
    backup_manager.calculate_capacity()

    # 返回下次触发时间（秒）
    return minor_interval * 60


def start_backup_timer():
    """启动备份定时器（无条件启动）"""
    global _timer_handle

    # 如果定时器已注册，先注销
    if _timer_handle:
        try:
            bpy.app.timers.unregister(_timer_handle)
        except:
            pass
        _timer_handle = None

    prefs = properties.get_backup_prefs()
    minor_interval = 2  # 默认值
    if prefs:
        try:
            minor_interval = int(prefs.minor_interval_backup)
        except:
            pass

    # 注册定时器（首次 1 分钟后触发）
    _timer_handle = bpy.app.timers.register(
        _backup_timer_callback,
        first_interval=60.0,  # 首次 1 分钟后触发
        persistent=True
    )

    # 初始化下次保存时间
    backup_manager.update_next_save_time(minor_interval)

    print(f"[MMY备份] 定时器已启动")


def _stop_timer():
    """停止定时器"""
    global _timer_handle

    if _timer_handle:
        try:
            bpy.app.timers.unregister(_timer_handle)
        except:
            pass
        _timer_handle = None


def _on_file_load(dummy):
    """文件加载后更新状态"""
    # 重置时间戳，确保新文件能触发备份
    scene = bpy.context.scene
    scene.mmy_backup_last_minor = time.time()
    scene.mmy_backup_last_major = time.time()


def _on_file_save(dummy):
    """文件保存后更新状态"""
    # 重置时间戳
    scene = bpy.context.scene
    scene.mmy_backup_last_minor = time.time()
    scene.mmy_backup_last_major = time.time()


def register():
    # 注册运行时状态属性
    properties.register_backup_prefs()

    # 添加文件加载处理器
    if _on_file_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_file_load)

    # 添加文件保存处理器
    if _on_file_save not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(_on_file_save)


def unregister():
    # 停止定时器
    _stop_timer()

    # 移除处理器
    if _on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_file_load)
    if _on_file_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_on_file_save)

    # 注销偏好设置属性
    properties.unregister_backup_prefs()


def start_backup_if_enabled():
    """启动备份定时器（在主模块类注册后调用）"""
    start_backup_timer()


# 导出状态缓存供状态栏使用
def get_status():
    """获取备份状态（供状态栏显示）"""
    return backup_manager.get_status_cache()

def get_next_save_time():
    """获取下次保存时间字符串"""
    return backup_manager.get_next_save_time_str()