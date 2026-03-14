# -*- coding: utf-8 -*-
"""
桌面宠物打包脚本
用法: python build.py
"""
import subprocess
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_SOURCE = os.path.join(PROJECT_DIR, "resources", "animations", "idle", "cat", "stand.png")
ICON_OUTPUT = os.path.join(PROJECT_DIR, "app_icon.ico")
SPEC_FILE = os.path.join(PROJECT_DIR, "desktop_pet.spec")


def check_dependencies():
    """检查构建依赖"""
    missing = []
    try:
        import PyInstaller
    except ImportError:
        missing.append("pyinstaller")
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print(f"[错误] 缺少构建依赖: {', '.join(missing)}")
        print(f"请运行: pip install {' '.join(missing)}")
        return False

    print("[OK] 构建依赖已就绪")
    return True


def generate_icon():
    """将 stand.png 转换为多分辨率 .ico 文件"""
    from PIL import Image

    if not os.path.exists(ICON_SOURCE):
        print(f"[警告] 图标源文件不存在: {ICON_SOURCE}，将使用默认图标")
        return False

    print(f"[生成图标] {ICON_SOURCE} -> {ICON_OUTPUT}")

    img = Image.open(ICON_SOURCE)

    # 如果图片有透明通道，保持 RGBA；否则转换
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 生成多种分辨率
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_images = []
    for size in sizes:
        resized = img.resize(size, Image.LANCZOS)
        icon_images.append(resized)

    # 保存为 .ico（第一个图片调用 save，其余通过 append_images 传入）
    icon_images[0].save(
        ICON_OUTPUT,
        format="ICO",
        append_images=icon_images[1:],
        sizes=[s for s in sizes],
    )

    print(f"[OK] 图标已生成: {ICON_OUTPUT}")
    return True


def run_pyinstaller():
    """运行 PyInstaller 打包"""
    print("[打包] 开始 PyInstaller 构建...")

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", SPEC_FILE]

    result = subprocess.run(cmd, cwd=PROJECT_DIR)

    if result.returncode != 0:
        print("[错误] PyInstaller 构建失败")
        return False

    print("[OK] PyInstaller 构建完成")
    return True


def print_summary():
    """打印构建摘要"""
    dist_dir = os.path.join(PROJECT_DIR, "dist", "desktop_pet")
    exe_path = os.path.join(dist_dir, "desktop_pet.exe")

    if os.path.exists(exe_path):
        exe_size_mb = os.path.getsize(exe_path) / (1024 * 1024)

        # 计算整个目录大小
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(dist_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        total_size_mb = total_size / (1024 * 1024)

        print("\n" + "=" * 50)
        print("  构建成功!")
        print("=" * 50)
        print(f"  输出目录: {dist_dir}")
        print(f"  EXE 文件: {exe_path}")
        print(f"  EXE 大小: {exe_size_mb:.1f} MB")
        print(f"  总大小:   {total_size_mb:.1f} MB")
        print("=" * 50)
        print("  分发方式: 将整个 desktop_pet 文件夹发给对方即可")
        print("  运行方式: 双击 desktop_pet.exe")
        print("=" * 50)
    else:
        print("[错误] 未找到输出文件，构建可能失败")


def main():
    os.chdir(PROJECT_DIR)

    print("=" * 50)
    print("  桌面宠物 - EXE 打包工具")
    print("=" * 50)

    # 1. 检查依赖
    if not check_dependencies():
        return 1

    # 2. 生成图标
    generate_icon()

    # 3. 运行 PyInstaller
    if not run_pyinstaller():
        return 1

    # 4. 输出摘要
    print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
