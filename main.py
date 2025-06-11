#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Copy Channel Telegram
Entry point để chạy bot
"""

import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.core import TelegramBot

def main():
    """Main function để chạy bot"""
    print("🚀 Khởi động Bot Copy Channel Telegram...")
    print("📋 Kiểm tra cấu hình...")
    
    try:
        # Tạo và chạy bot
        bot = TelegramBot()
        print("✅ Bot được khởi tạo thành công!")
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot đã được dừng bởi người dùng")
    except Exception as e:
        print(f"❌ Lỗi chạy bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 