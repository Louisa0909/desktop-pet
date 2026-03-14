#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
桌面宠物 - 程序入口
"""
import sys
from PyQt5.QtWidgets import QApplication

from core.pet import DesktopPet
from utils.userdata import UserDataManager
from ui.name_dialog import NameDialog


def get_pet_name(user_data: UserDataManager) -> str:
    """获取宠物名称，首次启动时询问"""
    # 如果已有保存的名字，直接使用
    saved_name = user_data.pet_name
    if saved_name and saved_name != "我的小宠物":
        print(f"[用户数据] 使用保存的宠物名: {saved_name}")
        return saved_name
    
    # 首次启动或使用默认名时询问
    dialog = NameDialog(saved_name)
    dialog.show_center()
    
    if dialog.result() != NameDialog.Accepted:
        return ""
    
    name = dialog.get_name()
    
    # 保存名字
    user_data.pet_name = name
    user_data.save()
    
    return name


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("桌面宠物")
    
    # 初始化用户数据
    user_data = UserDataManager()
    user_data.start_session()
    
    # 获取宠物名称
    pet_name = get_pet_name(user_data)
    if not pet_name:
        user_data.end_session()
        return 0
    
    # 创建宠物实例
    pet = DesktopPet(pet_name, user_data)
    
    # 注册清理函数
    def on_quit():
        pet.cleanup()
        user_data.end_session()
    
    app.aboutToQuit.connect(on_quit)
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())