"""自动备份模块 - 备份管理核心逻辑"""

import bpy
import os
import time
import shutil
from datetime import datetime
from pathlib import Path
from .properties import get_backup_prefs


# 模块级缓存（状态栏显示）
_status_cache = {
    "capacity_mb": 0.0,
    "backup_count": 0,
    "next_save_time": 0.0,
    "warning": False
}


def get_backup_base_dir():
    """获取备份根目录（Blender 临时目录下的 MMY_Backups）"""
    # 读取 Blender 偏好设置的临时目录
    temp_dir = bpy.context.preferences.filepaths.temporary_directory

    # 如果未设置临时目录，使用系统临时目录
    if not temp_dir:
        temp_dir = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')))

    # 在临时目录下创建 MMY_Backups 子目录
    backup_dir = os.path.join(temp_dir, "MMY_Backups")

    # 确保目录存在
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    return backup_dir


def get_today_dir():
    """获取今日备份目录"""
    base_dir = get_backup_base_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(base_dir, today)

    if not os.path.exists(today_dir):
        os.makedirs(today_dir)

    return today_dir


def get_backup_filename(is_major=False):
    """生成备份文件名

    Args:
        is_major: 是否为大版本备份

    Returns:
        文件名字符串（不含路径）
    """
    # 获取当前 blend 文件名
    filepath = bpy.data.filepath
    if not filepath:
        return None

    # 提取文件名（不含扩展名）
    filename = os.path.splitext(os.path.basename(filepath))[0]

    # 时间戳（时分）
    time_str = datetime.now().strftime("%H%M")

    # 大版本添加 _MAJOR 标识
    suffix = "_MAJOR" if is_major else ""

    return f"{filename}_{time_str}{suffix}.blend"


def create_backup(is_major=False):
    """执行备份操作

    Args:
        is_major: 是否为大版本备份

    Returns:
        备份文件路径，失败返回 None
    """
    # 检查文件是否有名
    filepath = bpy.data.filepath
    if not filepath:
        # 未命名文件，不备份
        return None

    # 获取今日目录和文件名
    today_dir = get_today_dir()
    backup_name = get_backup_filename(is_major)

    if not backup_name:
        return None

    backup_path = os.path.join(today_dir, backup_name)

    # 执行保存（copy=True 不影响当前文件）
    try:
        bpy.ops.wm.save_as_mainfile(
            filepath=backup_path,
            copy=True,
            compress=False
        )
        return backup_path
    except Exception as e:
        print(f"[MMY备份] 备份失败: {e}")
        return None


def cleanup_old_backups(today_dir, max_count, is_major=False):
    """清理超出数量的旧备份

    Args:
        today_dir: 今日备份目录
        max_count: 最大保留数量
        is_major: 是否处理大版本文件
    """
    # 获取对应类型的备份文件
    suffix = "_MAJOR.blend" if is_major else ".blend"
    exclude_suffix = "_MAJOR.blend"

    files = []
    for f in os.listdir(today_dir):
        if f.endswith(suffix):
            # 小版本时排除大版本文件
            if not is_major and f.endswith(exclude_suffix):
                continue
            files.append(os.path.join(today_dir, f))

    # 按修改时间排序（最旧在前）
    files.sort(key=lambda x: os.path.getmtime(x))

    # 删除超出数量的文件
    while len(files) > max_count:
        oldest = files.pop(0)
        try:
            os.remove(oldest)
            print(f"[MMY备份] 删除旧备份: {oldest}")
        except Exception as e:
            print(f"[MMY备份] 删除失败: {e}")


def cleanup_old_date_folders():
    """清理超出保留天数的日期文件夹"""
    base_dir = get_backup_base_dir()

    # 获取偏好设置中的保留天数
    keep_days = 7  # 默认值
    prefs = get_backup_prefs()
    if prefs:
        try:
            keep_days = int(prefs.keep_days_backup)
        except:
            keep_days = 7

    # 获取所有日期文件夹
    date_folders = []
    for f in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, f)
        if os.path.isdir(folder_path) and f.count('-') == 2:  # 格式: YYYY-MM-DD
            date_folders.append(folder_path)

    # 按日期排序（最旧在前）
    date_folders.sort()

    # 删除超出数量的文件夹
    while len(date_folders) > keep_days:
        oldest = date_folders.pop(0)
        try:
            shutil.rmtree(oldest)
            print(f"[MMY备份] 删除旧日期文件夹: {oldest}")
        except Exception as e:
            print(f"[MMY备份] 删除文件夹失败: {e}")


def calculate_capacity():
    """计算备份总容量和数量，更新缓存"""
    base_dir = get_backup_base_dir()
    total_size = 0
    total_count = 0

    try:
        for root, dirs, files in os.walk(base_dir):
            for f in files:
                if f.endswith('.blend'):
                    filepath = os.path.join(root, f)
                    total_size += os.path.getsize(filepath)
                    total_count += 1
    except Exception:
        pass

    # 转换为 MB
    capacity_mb = total_size / (1024 * 1024)

    # 更新缓存
    _status_cache["capacity_mb"] = capacity_mb
    _status_cache["backup_count"] = total_count

    # 检查是否超过阈值
    threshold = 500  # 默认值
    prefs = get_backup_prefs()
    if prefs:
        try:
            threshold = int(prefs.capacity_threshold_mb)
        except:
            threshold = 500

    _status_cache["warning"] = capacity_mb > threshold

    return capacity_mb, total_count


def get_status_cache():
    """获取状态缓存（供状态栏显示使用）"""
    return _status_cache


def update_next_save_time(interval_minutes):
    """更新下次保存时间"""
    _status_cache["next_save_time"] = time.time() + interval_minutes * 60


def get_next_save_time_str():
    """获取下次保存时间的字符串表示"""
    next_time = _status_cache.get("next_save_time", 0)
    if next_time > 0:
        dt = datetime.fromtimestamp(next_time)
        return dt.strftime("%H:%M")
    return "--:--"