#!/usr/bin/env python3
"""
MMY Blender Toolkit 自动打包脚本
打包插件目录为 zip，命名包含版本号和时间戳
"""

import os
import zipfile
import re
from datetime import datetime


def get_version():
    """从 __init__.py 读取版本号"""
    init_path = os.path.join(os.path.dirname(__file__), 'mmy_toolkit', '__init__.py')

    with open(init_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 version: (x, y, z)
    match = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', content)
    if match:
        return f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"
    return "v0.0.0"


def pack_plugin():
    """打包插件"""
    # 获取版本和时间戳
    version = get_version()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # 输出目录
    output_dir = os.path.join(os.path.dirname(__file__), 'releases')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 压缩包名称
    zip_name = f"MMY_Blender_Toolkit_{version}_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    # 源目录
    source_dir = os.path.join(os.path.dirname(__file__), 'mmy_toolkit')

    # 排除文件
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.git',
        'presets/user_',  # 用户自定义预设
    ]

    # 创建压缩包
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            # 排除目录
            dirs[:] = [d for d in dirs if not any(
                pattern in d for pattern in exclude_patterns
            )]

            for file in files:
                # 排除文件
                if any(pattern in file for pattern in exclude_patterns):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zf.write(file_path, arcname)

    print(f"[OK] 打包完成: {zip_path}")
    print(f"     版本: {version}")
    print(f"     时间: {timestamp}")

    return zip_path


if __name__ == '__main__':
    pack_plugin()