import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils.keyboards import Keyboards

class BotHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.temp_data = bot_instance.temp_data
        self.user_clients = bot_instance.user_clients
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode='Markdown'):
        """Wrapper for safe message editing"""
        return await self.bot.safe_edit_message(query, text, reply_markup, parse_mode)
    
    async def request_extract_pattern(self, query):
        """Yêu cầu nhập pattern extraction"""
        text = """
🎯 **THIẾT LẬP PATTERN LỌC TEXT**

Nhập pattern (regex) để lọc nội dung từ tin nhắn:

📝 **Ví dụ:**
• `\d+` - Lấy tất cả số
• `https?://[^\s]+` - Lấy tất cả link
• `#\w+` - Lấy tất cả hashtag
• `@\w+` - Lấy tất cả mention

⚠️ **Để trống** nếu muốn copy toàn bộ tin nhắn
        """
        await self.safe_edit_message(query, text)
    
    async def show_header_footer_menu(self, query):
        """Hiển thị menu thiết lập header/footer"""
        user_id = query.from_user.id
        current_config = self.temp_data.get(user_id, {})
        
        text = f"""
📄 **THIẾT LẬP HEADER/FOOTER**

📝 **Header hiện tại:** 
{current_config.get('header_text', 'Không có')[:100]}{'...' if len(current_config.get('header_text', '')) > 100 else ''}

📝 **Footer hiện tại:** 
{current_config.get('footer_text', 'Không có')[:100]}{'...' if len(current_config.get('footer_text', '')) > 100 else ''}

👇 **Chọn mục cần thiết lập:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.header_footer_menu()
        )
    
    async def request_header_text(self, query):
        """Yêu cầu nhập header text"""
        text = """
📝 **THIẾT LẬP HEADER**

Nhập văn bản sẽ được thêm vào **đầu** mỗi tin nhắn copy:

📝 **Ví dụ:**
• `🔥 Tin nóng từ kênh ABC`
• `📢 Thông báo quan trọng:`
• `💎 Nội dung VIP:`

⚠️ **Để trống** nếu không muốn thêm header
        """
        await self.safe_edit_message(query, text)
    
    async def request_footer_text(self, query):
        """Yêu cầu nhập footer text"""
        text = """
📝 **THIẾT LẬP FOOTER**

Nhập văn bản sẽ được thêm vào **cuối** mỗi tin nhắn copy:

📝 **Ví dụ:**
• `📱 Theo dõi kênh chính: @mychannel`
• `🔗 Website: https://example.com`
• `💌 Liên hệ: @admin`

⚠️ **Để trống** nếu không muốn thêm footer
        """
        await self.safe_edit_message(query, text)
    
    async def show_button_menu(self, query):
        """Hiển thị menu thiết lập button"""
        user_id = query.from_user.id
        current_config = self.temp_data.get(user_id, {})
        
        text = f"""
🔘 **THIẾT LẬP BUTTON**

📝 **Text button:** {current_config.get('button_text', 'Không có')}
🔗 **URL button:** {current_config.get('button_url', 'Không có')}

**Button sẽ được thêm vào cuối mỗi tin nhắn copy**

👇 **Chọn mục cần thiết lập:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.button_menu()
        )
    
    async def request_button_text(self, query):
        """Yêu cầu nhập text button"""
        text = """
📝 **THIẾT LẬP TEXT BUTTON**

Nhập văn bản hiển thị trên button:

📝 **Ví dụ:**
• `📱 Tham gia ngay`
• `🔗 Xem thêm`
• `💎 Nhận ưu đãi`

⚠️ **Để trống** nếu không muốn thêm button
        """
        await self.safe_edit_message(query, text)
    
    async def request_button_url(self, query):
        """Yêu cầu nhập URL button"""
        text = """
🔗 **THIẾT LẬP URL BUTTON**

Nhập link sẽ được mở khi nhấn button:

📝 **Ví dụ:**
• `https://t.me/yourchannel`
• `https://yourwebsite.com`
• `https://t.me/yourbot?start=ref`

⚠️ **Lưu ý:** Phải là link hợp lệ (bắt đầu với http/https)
        """
        await self.safe_edit_message(query, text)
    
    async def handle_header_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý header text được nhập"""
        header_text = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id]['header_text'] = header_text
        
        await update.message.reply_text(
            f"✅ **Đã lưu header:**\n\n{header_text}\n\n🔙 Quay lại menu cấu hình để tiếp tục.",
            reply_markup=Keyboards.back_to_main(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def handle_footer_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý footer text được nhập"""
        footer_text = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id]['footer_text'] = footer_text
        
        await update.message.reply_text(
            f"✅ **Đã lưu footer:**\n\n{footer_text}\n\n🔙 Quay lại menu cấu hình để tiếp tục.",
            reply_markup=Keyboards.back_to_main(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def handle_button_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý button text được nhập"""
        button_text = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id]['button_text'] = button_text
        
        await update.message.reply_text(
            f"✅ **Đã lưu text button:** {button_text}\n\n🔙 Quay lại menu cấu hình để tiếp tục.",
            reply_markup=Keyboards.back_to_main(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def handle_button_url_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý button URL được nhập"""
        button_url = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Validate URL
        if not button_url.startswith(('http://', 'https://', 'tg://')):
            await update.message.reply_text(
                "❌ **URL không hợp lệ!**\n\nVui lòng nhập URL bắt đầu với http://, https:// hoặc tg://"
            )
            return
        
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        
        self.temp_data[user_id]['button_url'] = button_url
        
        await update.message.reply_text(
            f"✅ **Đã lưu URL button:** {button_url}\n\n🔙 Quay lại menu cấu hình để tiếp tục.",
            reply_markup=Keyboards.back_to_main(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def save_configuration(self, query):
        """Lưu cấu hình copy channel"""
        user_id = query.from_user.id
        config_data = self.temp_data.get(user_id, {})
        
        # Kiểm tra các thông tin bắt buộc
        if not config_data.get('source_channel_id') or not config_data.get('target_channel_id'):
            await query.edit_message_text(
                "❌ **Thiếu thông tin!**\n\nVui lòng chọn cả channel nguồn và channel đích.",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
            return
        
        try:
            # Config mới tạo sẽ ở trạng thái ACTIVE để user có thể sử dụng ngay
            config_data['is_active'] = True
            
            # Lưu vào database
            self.db.save_channel_config(user_id, config_data)
            
            # Xóa dữ liệu tạm thời
            self.temp_data[user_id] = {}
            
            await query.edit_message_text(
                f"""
✅ **CẤU HÌNH ĐÃ ĐƯỢC LƯU VÀ KÍCH HOẠT!**

🎉 **Cấu hình copy channel đã sẵn sàng:**
📥 **Từ:** {config_data.get('source_channel_name', 'N/A')}
📤 **Đến:** {config_data.get('target_channel_name', 'N/A')}

🚀 **Bước tiếp theo:**
• Nhấn "Bắt đầu Copy" để bot tự động copy tin nhắn
• Hoặc vào "Danh sách cấu hình" để xem chi tiết

⚡ **Sẵn sàng copy ngay!** Bot sẽ copy tin nhắn mới từ channel nguồn.

📱 Nhấn /start để quay lại menu chính!
                """,
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Lỗi lưu cấu hình:** {str(e)}",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
    
    async def show_config_details(self, query, config_id):
        """Hiển thị chi tiết cấu hình"""
        user_id = query.from_user.id
        configs = self.db.get_all_user_configs(user_id)  # Lấy tất cả configs để có thể xem cả inactive
        
        config = None
        for c in configs:
            if c['id'] == config_id:
                config = c
                break
        
        if not config:
            await query.edit_message_text(
                "❌ **Không tìm thấy cấu hình!**",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
            return
        
        # Emoji trạng thái
        status_emoji = "🟢" if config['is_active'] else "⚪"
        status_text = "Đang chạy" if config['is_active'] else "Đã dừng"
        
        text = f"""
📋 **CHI TIẾT CẤU HÌNH #{config['id']}**

{status_emoji} **Trạng thái:** {status_text}

📥 **Channel nguồn:** {config['source_channel_name']}
📤 **Channel đích:** {config['target_channel_name']}

🎯 **Pattern lọc:** 
`{config['extract_pattern'] or 'Không có'}`

📄 **Header:** 
{config['header_text'] or 'Không có'}

📄 **Footer:** 
{config['footer_text'] or 'Không có'}

🔘 **Button:** {config['button_text'] or 'Không có'}
🔗 **URL:** {config['button_url'] or 'Không có'}

📅 **Tạo lúc:** {config['created_at']}

👇 **Chọn hành động:**
        """
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.config_actions(config_id, config['is_active']),
            parse_mode='Markdown'
        )
    
    async def delete_configuration(self, query, config_id):
        """Xóa cấu hình với tùy chọn xóa vĩnh viễn hoặc vô hiệu hóa"""
        user_id = query.from_user.id
        
        try:
            # Lấy thông tin config để hiển thị
            config = self.db.get_config_by_id(config_id, user_id)
            if not config:
                await query.edit_message_text(
                    "❌ **Không tìm thấy cấu hình!**",
                    reply_markup=Keyboards.back_to_main(),
                    parse_mode='Markdown'
                )
                return
            
            # Dừng copying nếu đang chạy
            client = await self.bot.get_or_restore_client(user_id)
            if client:
                await client.stop_copying(config_id)
            
            text = f"""
🗑️ **XÁC NHẬN XÓA CẤU HÌNH**

📋 **Cấu hình:**
📥 **Từ:** {config['source_channel_name']}
📤 **Đến:** {config['target_channel_name']}

⚠️ **Chọn loại xóa:**

🔴 **Xóa vĩnh viễn:** Xóa hoàn toàn khỏi hệ thống
⚪ **Vô hiệu hóa:** Chỉ tắt, có thể khôi phục sau

👇 **Chọn hành động:**
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🔴 Xóa vĩnh viễn", callback_data=f"delete_permanent_{config_id}"),
                    InlineKeyboardButton("⚪ Vô hiệu hóa", callback_data=f"delete_disable_{config_id}")
                ],
                [InlineKeyboardButton("❌ Hủy", callback_data="list_configs")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Lỗi khi chuẩn bị xóa cấu hình:** {str(e)}",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
    
    async def delete_configuration_permanent(self, query, config_id):
        """Xóa cấu hình vĩnh viễn"""
        user_id = query.from_user.id
        
        try:
            # Dừng copying trước
            client = await self.bot.get_or_restore_client(user_id)
            if client:
                await client.stop_copying(config_id)
            
            # Xóa vĩnh viễn
            success = self.db.delete_config_permanently(config_id, user_id)
            
            if success:
                await query.edit_message_text(
                    "🔴 **Đã xóa cấu hình vĩnh viễn!**\n\n✅ Cấu hình đã được xóa hoàn toàn khỏi hệ thống.",
                    reply_markup=Keyboards.back_to_main(),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Không thể xóa cấu hình!**\n\nCấu hình có thể đã được xóa trước đó.",
                    reply_markup=Keyboards.back_to_main(),
                    parse_mode='Markdown'
                )
            
            # Tự động quay lại danh sách sau 2 giây
            await asyncio.sleep(2)
            await self.bot.show_user_configs(query)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Lỗi xóa cấu hình vĩnh viễn:** {str(e)}",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
    
    async def delete_configuration_disable(self, query, config_id):
        """Vô hiệu hóa cấu hình (soft delete)"""
        user_id = query.from_user.id
        
        try:
            # Dừng copying trước
            client = await self.bot.get_or_restore_client(user_id)
            if client:
                await client.stop_copying(config_id)
            
            # Chỉ set inactive
            self.db.delete_config(config_id, user_id)
            
            await query.edit_message_text(
                "⚪ **Đã vô hiệu hóa cấu hình!**\n\n✅ Cấu hình đã được tắt nhưng vẫn có thể khôi phục.",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
            
            # Tự động quay lại danh sách sau 2 giây
            await asyncio.sleep(2)
            await self.bot.show_user_configs(query)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Lỗi vô hiệu hóa cấu hình:** {str(e)}",
                reply_markup=Keyboards.back_to_main(),
                parse_mode='Markdown'
            )
    
    async def start_copying_config(self, query, config_id):
        """Bắt đầu copy cho một cấu hình cụ thể"""
        user_id = query.from_user.id
        
        try:
            configs = self.db.get_user_configs(user_id)
            config = None
            for c in configs:
                if c['id'] == config_id:
                    config = c
                    break
            
            if not config:
                await self.safe_edit_message(
                    query,
                    "❌ **Không tìm thấy cấu hình!**",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Lấy hoặc khôi phục client của user
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    "❌ **Không tìm thấy phiên đăng nhập!**\n\nVui lòng đăng nhập lại.",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            success = await client.start_copying(config)
            
            if success:
                # Cập nhật trạng thái active trong database
                self.db.update_config_status(config_id, user_id, True)
                
                await self.safe_edit_message(
                    query,
                    f"""
🚀 **BẮT ĐẦU COPY THÀNH CÔNG!**

📥 **Từ:** {config['source_channel_name']}
📤 **Đến:** {config['target_channel_name']}

✅ Bot đang chạy và sẽ tự động copy tin nhắn mới!

⚠️ **Lưu ý:** Để dừng copy, nhấn "Dừng Copy" ở menu chính.
                    """,
                    reply_markup=Keyboards.back_to_main()
                )
            else:
                await self.safe_edit_message(
                    query,
                    "❌ **Không thể bắt đầu copy!**\n\nVui lòng kiểm tra quyền truy cập channel.",
                    reply_markup=Keyboards.back_to_main()
                )
                
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            )
    
    async def stop_copying_config(self, query, config_id):
        """Dừng copy cho một cấu hình cụ thể"""
        user_id = query.from_user.id
        
        try:
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    "❌ **Không có phiên copy nào đang chạy!**",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            success = await client.stop_copying(config_id)
            
            if success:
                # Cập nhật trạng thái inactive trong database
                self.db.update_config_status(config_id, user_id, False)
                
                await self.safe_edit_message(
                    query,
                    "⏹️ **Đã dừng copy thành công!**",
                    reply_markup=Keyboards.back_to_main()
                )
            else:
                await self.safe_edit_message(
                    query,
                    "❌ **Không thể dừng copy!**",
                    reply_markup=Keyboards.back_to_main()
                )
                
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            )
    
    async def start_all_copying(self, query):
        """Bắt đầu copy tất cả cấu hình của user"""
        user_id = query.from_user.id
        
        try:
            # Lấy TẤT CẢ configs của user (kể cả inactive) để có thể start
            configs = self.db.get_all_user_configs(user_id)
            
            if not configs:
                await self.safe_edit_message(
                    query,
                    """
❌ **Không có cấu hình nào!**

🔍 **Bạn chưa tạo cấu hình copy channel nào.**

💡 **Hướng dẫn:**
1. Vào "Cấu hình Copy Channel" 
2. Chọn channel nguồn và channel đích
3. Lưu cấu hình
4. Quay lại đây để bắt đầu copy

📱 Nhấn /start để vào menu chính!
                    """,
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Lấy hoặc khôi phục client
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    """
❌ **Không tìm thấy phiên đăng nhập!**

🔐 **Vui lòng:**
1. Kiểm tra trạng thái đăng nhập
2. Thử lệnh /recover để khôi phục session
3. Hoặc đăng nhập lại tài khoản

💡 **Tip:** Dùng /status để kiểm tra trạng thái
                    """,
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Thử start từng config
            success_count = 0
            failed_configs = []
            
            for config in configs:
                try:
                    print(f"🔄 Attempting to start config {config['id']}: {config['source_channel_name']} -> {config['target_channel_name']}")
                    
                    success = await client.start_copying(config)
                    if success:
                        success_count += 1
                        # Cập nhật trạng thái active trong database
                        self.db.update_config_status(config['id'], user_id, True)
                        print(f"✅ Started config {config['id']} successfully")
                    else:
                        failed_configs.append(config)
                        # Đánh dấu config không active nếu start thất bại
                        self.db.update_config_status(config['id'], user_id, False)
                        print(f"❌ Failed to start config {config['id']}")
                        
                except Exception as config_error:
                    print(f"❌ Error starting config {config['id']}: {config_error}")
                    failed_configs.append(config)
                    self.db.update_config_status(config['id'], user_id, False)
            
            # Hiển thị kết quả chi tiết
            if success_count > 0:
                if failed_configs:
                    # Một số config thành công, một số thất bại
                    failed_list = "\n".join([f"• {c['source_channel_name']} → {c['target_channel_name']}" for c in failed_configs[:3]])
                    if len(failed_configs) > 3:
                        failed_list += f"\n• ... và {len(failed_configs) - 3} config khác"
                    
                    await self.safe_edit_message(
                        query,
                        f"""
🔶 **BẮT ĐẦU COPY THÀNH CÔNG MỘT PHẦN**

✅ **Đã bắt đầu:** {success_count}/{len(configs)} cấu hình
🤖 **Bot đang chạy và copy tin nhắn mới!**

❌ **Không thể start:** {len(failed_configs)} cấu hình
{failed_list}

💡 **Gợi ý:** 
• Kiểm tra quyền truy cập channel
• Thử /recover để khôi phục session
• Xem chi tiết trong "Danh sách cấu hình"

⚠️ **Để dừng:** Nhấn "Dừng Copy" ở menu chính
                        """,
                        reply_markup=Keyboards.back_to_main()
                    )
                else:
                    # Tất cả config đều thành công
                    await self.safe_edit_message(
                        query,
                        f"""
🚀 **BẮT ĐẦU COPY TẤT CẢ THÀNH CÔNG!**

✅ **Đã bắt đầu:** {success_count}/{len(configs)} cấu hình  
🤖 **Bot đang chạy và copy tin nhắn mới!**

📊 **Configs đang hoạt động:**
{chr(10).join([f"• {c['source_channel_name']} → {c['target_channel_name']}" for c in configs[:5]])}
{f'• ... và {len(configs) - 5} config khác' if len(configs) > 5 else ''}

⚠️ **Để dừng:** Nhấn "Dừng Copy" ở menu chính
                        """,
                        reply_markup=Keyboards.back_to_main()
                    )
            else:
                # Tất cả config đều thất bại
                failed_reasons = []
                for config in failed_configs[:3]:
                    failed_reasons.append(f"• {config['source_channel_name']} → {config['target_channel_name']}")
                
                await self.safe_edit_message(
                    query,
                    f"""
❌ **KHÔNG THỂ BẮT ĐẦU CONFIG NÀO!**

🔍 **Đã thử:** {len(configs)} cấu hình
❌ **Thất bại:** {len(failed_configs)} cấu hình

📋 **Configs thất bại:**
{chr(10).join(failed_reasons)}
{f'• ... và {len(failed_configs) - 3} config khác' if len(failed_configs) > 3 else ''}

🛠️ **Các bước khắc phục:**
1. **Kiểm tra session:** /status hoặc /recover
2. **Kiểm tra quyền channel:** Đảm bảo bot có quyền truy cập
3. **Thử từng config riêng:** Vào "Danh sách cấu hình"  
4. **Đăng nhập lại:** Nếu session có vấn đề

💡 **Debug:** Kiểm tra console để xem chi tiết lỗi
                    """,
                    reply_markup=Keyboards.back_to_main()
                )
            
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"""
❌ **LỖI NGHIÊM TRỌNG!**

🔍 **Chi tiết lỗi:** {str(e)}

🛠️ **Khắc phục:**
1. Thử lại sau 30 giây
2. Dùng /recover để khôi phục session  
3. Kiểm tra /status
4. Đăng nhập lại nếu cần

💡 **Debug:** Lỗi này đã được ghi log, báo admin nếu tiếp tục
                """,
                reply_markup=Keyboards.back_to_main()
            )
    
    async def stop_all_copying(self, query):
        """Dừng tất cả việc copy"""
        user_id = query.from_user.id
        
        try:
            client = await self.bot.get_or_restore_client(user_id)
            
            if not client:
                await self.safe_edit_message(
                    query,
                    "❌ **Không có phiên copy nào đang chạy!**",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Lấy tất cả configs hiện tại đang active
            configs = self.db.get_user_configs(user_id)
            
            success = await client.stop_all_copying()
            
            if success:
                # Cập nhật tất cả configs thành inactive trong database
                for config in configs:
                    self.db.update_config_status(config['id'], user_id, False)
                
                await self.safe_edit_message(
                    query,
                    f"⏹️ **Đã dừng tất cả copy thành công!**\n\n📊 **Đã dừng:** {len(configs)} cấu hình",
                    reply_markup=Keyboards.back_to_main()
                )
            else:
                await self.safe_edit_message(
                    query,
                    "❌ **Có lỗi khi dừng copy!**",
                    reply_markup=Keyboards.back_to_main()
                )
                
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            ) 