import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils.keyboards import Keyboards
from bot.utils.states import WAITING_EXTRACT_PATTERN

class ConfigHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.temp_data = bot_instance.temp_data
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode='Markdown'):
        """Safely edit message with error handling"""
        return await self.bot.safe_edit_message(query, text, reply_markup, parse_mode)
    
    async def show_config_menu(self, query):
        """Hiển thị menu cấu hình"""
        user_id = query.from_user.id
        
        # Kiểm tra đăng nhập
        user = self.db.get_user(user_id)
        if not user or not user['is_authenticated']:
            await self.safe_edit_message(
                query,
                "❌ **Bạn cần đăng nhập trước!**\n\nVui lòng đăng nhập tài khoản Telegram để tiếp tục.",
                reply_markup=Keyboards.back_to_main()
            )
            return
        
        # Hiển thị cấu hình hiện tại
        current_config = self.temp_data.get(user_id, {})
        
        # Format thông tin channel với ID
        source_info = "Chưa chọn"
        if current_config.get('source_channel_name') and current_config.get('source_channel_id'):
            source_info = f"{current_config['source_channel_name']}\n    `ID: {current_config['source_channel_id']}`"
        
        target_info = "Chưa chọn"
        if current_config.get('target_channel_name') and current_config.get('target_channel_id'):
            target_info = f"{current_config['target_channel_name']}\n    `ID: {current_config['target_channel_id']}`"
        
        text = f"""
⚙️ **CẤU HÌNH COPY CHANNEL**

📥 **Channel nguồn:** 
{source_info}

📤 **Channel đích:** 
{target_info}

🎯 **Pattern lọc:** {current_config.get('extract_pattern', 'Không có')}
📄 **Header:** {current_config.get('header_text', 'Không có')[:30]}{'...' if len(current_config.get('header_text', '')) > 30 else ''}
📄 **Footer:** {current_config.get('footer_text', 'Không có')[:30]}{'...' if len(current_config.get('footer_text', '')) > 30 else ''}
🔘 **Button:** {current_config.get('button_text', 'Không có')}

📝 **Chọn mục cần cấu hình:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.config_menu()
        )
    
    async def handle_extract_pattern(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý pattern extraction được nhập"""
        pattern = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id]['extract_pattern'] = pattern
        
        await update.message.reply_text(
            f"✅ **Đã lưu pattern:** `{pattern}`\n\n🔙 Quay lại menu cấu hình để tiếp tục.",
            reply_markup=Keyboards.back_to_main(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def show_user_configs(self, query):
        """Hiển thị danh sách cấu hình của user"""
        user_id = query.from_user.id
        configs = self.db.get_all_user_configs(user_id)  # Lấy tất cả configs bao gồm inactive
        
        if not configs:
            await self.safe_edit_message(
                query,
                """
📋 **DANH SÁCH CẤU HÌNH**

❌ **Bạn chưa có cấu hình nào!**

Hãy tạo cấu hình mới bằng cách chọn "Cấu hình Copy Channel" ở menu chính.
                """,
                reply_markup=Keyboards.back_to_main()
            )
            return
        
        # Tách configs theo trạng thái
        active_configs = [c for c in configs if c['is_active']]
        inactive_configs = [c for c in configs if not c['is_active']]
        
        text = f"""
📋 **DANH SÁCH CẤU HÌNH** ({len(configs)} cấu hình)

🟢 **Đang chạy:** {len(active_configs)} cấu hình
⚪ **Đã dừng:** {len(inactive_configs)} cấu hình

👇 **Chọn cấu hình để xem chi tiết:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.config_list_buttons(configs)
        )
    
    async def show_help(self, query):
        """Hiển thị hướng dẫn sử dụng"""
        help_text = """
❓ **HƯỚNG DẪN SỬ DỤNG BOT**

🎯 **Mục đích:** Copy tin nhắn từ channel Telegram khác về channel của bạn

📋 **Các bước sử dụng:**

**1. 🔐 Đăng nhập tài khoản**
   • Cần API_ID và API_HASH từ my.telegram.org
   • Nhập số điện thoại và mã xác thực

**2. ⚙️ Cấu hình Copy Channel**
   • Chọn channel nguồn (để copy từ đó)
   • Chọn channel đích (để gửi tin nhắn đến)
   • Thiết lập filter text (tùy chọn)
   • Thêm header/footer (tùy chọn)
   • Thêm button tùy chỉnh (tùy chọn)

**3. 🚀 Bắt đầu Copy**
   • Lưu cấu hình và bắt đầu
   • Bot sẽ tự động copy tin nhắn mới

**🔧 Tính năng nâng cao:**
   • Lọc tin nhắn theo pattern (RegEx)
   • Thêm text đầu/cuối tin nhắn
   • Button với link tùy chỉnh
   • Hỗ trợ hình ảnh, video, file

**📱 Các lệnh hữu ích:**
   • `/start` - Mở menu chính
   • `/status` - Kiểm tra trạng thái đăng nhập
   • `/recover` - Khôi phục session nếu bị lỗi
   • `/logout` - Đăng xuất tài khoản

**⚠️ Lưu ý:**
   • Cần quyền admin hoặc member của channel nguồn
   • Cần quyền gửi tin nhắn ở channel đích
   • Bot chỉ copy tin nhắn mới, không copy tin nhắn cũ
   • Nếu gặp lỗi session, thử `/recover` trước khi đăng nhập lại
        """
        
        await self.safe_edit_message(
            query,
            help_text,
            reply_markup=Keyboards.back_to_main()
        ) 