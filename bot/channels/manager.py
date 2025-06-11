import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils.keyboards import Keyboards

class ChannelManager:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.temp_data = bot_instance.temp_data
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode='Markdown'):
        """Safely edit message with error handling"""
        return await self.bot.safe_edit_message(query, text, reply_markup, parse_mode)
    
    async def show_channel_selection(self, query, channel_type):
        """Hiển thị danh sách channel để chọn"""
        user_id = query.from_user.id
        
        try:
            # Lấy hoặc khôi phục client của user
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    "❌ **Không tìm thấy phiên đăng nhập!**\n\nVui lòng đăng nhập lại tài khoản Telegram.",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            print(f"Getting dialogs for user {user_id}...")
            dialogs = await client.get_dialogs()
            
            if not dialogs:
                # Check if user is authenticated
                user = self.db.get_user(user_id)
                auth_status = "đã xác thực" if user and user['is_authenticated'] else "chưa xác thực"
                
                await self.safe_edit_message(
                    query,
                    f"""
❌ **Không tìm thấy channel/group nào!**

🔍 **Nguyên nhân có thể:**
• Tài khoản chưa tham gia channel/group nào
• Session đã hết hạn (trạng thái: {auth_status})
• Lỗi kết nối Telegram

💡 **Giải pháp:**
1. Tham gia ít nhất một channel hoặc group
2. Thử đăng xuất và đăng nhập lại
3. Kiểm tra kết nối internet

🔧 **Debug:** Kiểm tra console để xem thông tin chi tiết
                    """,
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Lưu dữ liệu để sử dụng cho pagination
            if user_id not in self.temp_data:
                self.temp_data[user_id] = {}
            
            self.temp_data[user_id]['selecting_channel_type'] = channel_type
            self.temp_data[user_id]['available_channels'] = dialogs
            
            # Hiển thị trang đầu tiên
            await self._show_channel_page(query, dialogs, channel_type, page=0)
            
        except Exception as e:
            print(f"Error in show_channel_selection: {e}")
            import traceback
            traceback.print_exc()
            
            await self.safe_edit_message(
                query,
                f"""
❌ **Lỗi khi lấy danh sách channel:**

🔍 **Chi tiết lỗi:** {str(e)}

💡 **Giải pháp:**
1. Thử đăng xuất và đăng nhập lại
2. Kiểm tra kết nối internet
3. Liên hệ admin nếu lỗi vẫn tiếp tục

🔧 **Debug:** Kiểm tra console để xem thông tin chi tiết
                """,
                reply_markup=Keyboards.back_to_main()
            )
    
    async def show_channel_selection_page(self, query, page):
        """Hiển thị trang channel selection theo số trang"""
        user_id = query.from_user.id
        
        if user_id not in self.temp_data:
            await self.safe_edit_message(
                query,
                "❌ **Phiên đã hết hạn!**\n\nVui lòng thử lại.",
                reply_markup=Keyboards.back_to_main()
            )
            return
        
        dialogs = self.temp_data[user_id].get('available_channels', [])
        channel_type = self.temp_data[user_id].get('selecting_channel_type', 'source')
        
        await self._show_channel_page(query, dialogs, channel_type, page)
    
    async def _show_channel_page(self, query, dialogs, channel_type, page=0):
        """Helper method để hiển thị một trang channels"""
        channel_text = "nguồn (để copy từ đó)" if channel_type == "source" else "đích (để gửi tin nhắn đến)"
        
        # Đếm số lượng channel theo loại
        channels_count = len(dialogs)
        supergroups = len([d for d in dialogs if d.get('type') == 'supergroup'])
        channels = len([d for d in dialogs if d.get('type') == 'channel'])
        groups = len([d for d in dialogs if d.get('type') == 'group'])
        private_chats = len([d for d in dialogs if d.get('type') == 'private'])
        
        # Tính toán pagination info
        per_page = 15
        total_pages = (len(dialogs) + per_page - 1) // per_page
        start_idx = page * per_page + 1
        end_idx = min((page + 1) * per_page, len(dialogs))
        
        text = f"""
📺 **CHỌN CHANNEL {channel_text.upper()}**

📊 **Thống kê:**
• 📺 Channels: {channels}
• 👥 Supergroups: {supergroups} 
• 👫 Groups: {groups}
• 💬 Private chats: {private_chats}
• 📋 **Tổng cộng: {channels_count}**

📄 **Trang {page+1}/{total_pages}** (Hiển thị {start_idx}-{end_idx})

💡 **Hướng dẫn:**
• Nhấn vào channel để chọn
• Sử dụng nút ◀️▶️ để xem thêm
• Channel type: 📺=Channel, 👥=Supergroup, 👫=Group

👇 **Chọn channel {channel_text}:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.channel_selection_buttons(dialogs, page)
        )
    
    async def handle_channel_selection(self, query, data):
        """Xử lý khi user chọn channel"""
        user_id = query.from_user.id
        channel_id = data.split("_")[2]
        
        try:
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    "❌ **Phiên đăng nhập đã hết hạn!**\n\nVui lòng đăng nhập lại tài khoản Telegram.",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            chat = await client.client.get_chat(int(channel_id))
            
            channel_type = self.temp_data[user_id].get('selecting_channel_type', 'source')
            
            # Lấy thông tin chi tiết về channel
            type_text = "📺 Channel"
            if chat.type.name.lower() == 'supergroup':
                type_text = "👥 Supergroup"
            elif chat.type.name.lower() == 'group':
                type_text = "👫 Group"
            elif chat.type.name.lower() == 'private':
                type_text = "💬 Private Chat"
            
            channel_info = f"""
**Tên:** {chat.title if hasattr(chat, 'title') else 'N/A'}
**ID:** `{channel_id}`
**Loại:** {type_text}"""
            
            if hasattr(chat, 'username') and chat.username:
                channel_info += f"\n**Username:** @{chat.username}"
            
            if hasattr(chat, 'members_count') and chat.members_count:
                channel_info += f"\n**Thành viên:** {chat.members_count:,}"
            
            if hasattr(chat, 'description') and chat.description:
                desc = chat.description[:100] + "..." if len(chat.description) > 100 else chat.description
                channel_info += f"\n**Mô tả:** {desc}"
            
            if channel_type == "source":
                self.temp_data[user_id]['source_channel_id'] = str(channel_id)
                self.temp_data[user_id]['source_channel_name'] = getattr(chat, 'title', 'Unknown')
                success_text = f"""
✅ **Đã chọn channel nguồn thành công!**

{channel_info}

🔄 **Channel này sẽ được sử dụng để copy tin nhắn từ đó.**

⏱️ *Đang chuyển về menu cấu hình...*
                """
            else:
                self.temp_data[user_id]['target_channel_id'] = str(channel_id)
                self.temp_data[user_id]['target_channel_name'] = getattr(chat, 'title', 'Unknown')
                success_text = f"""
✅ **Đã chọn channel đích thành công!**

{channel_info}

📤 **Tin nhắn sẽ được gửi đến channel này.**

⏱️ *Đang chuyển về menu cấu hình...*
                """
            
            # Hiển thị thông báo thành công
            await self.safe_edit_message(
                query,
                success_text,
                reply_markup=Keyboards.back_to_main()
            )
            
            # Tự động chuyển về menu cấu hình sau 3 giây
            await asyncio.sleep(3)
            await self.bot.show_config_menu(query)
            
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi chọn channel:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            ) 