from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
    @staticmethod
    def main_menu():
        """Menu chính của bot"""
        keyboard = [
            [InlineKeyboardButton("🔐 Đăng nhập tài khoản", callback_data="login")],
            [InlineKeyboardButton("⚙️ Cấu hình Copy Channel", callback_data="setup_config")],
            [InlineKeyboardButton("📋 Danh sách cấu hình", callback_data="list_configs")],
            [InlineKeyboardButton("🚀 Bắt đầu Copy", callback_data="start_copying")],
            [InlineKeyboardButton("⏹️ Dừng Copy", callback_data="stop_copying")],
            [InlineKeyboardButton("📊 Trạng thái phiên", callback_data="check_status")],
            [InlineKeyboardButton("🚪 Đăng xuất", callback_data="logout_account")],
            [InlineKeyboardButton("❓ Hướng dẫn", callback_data="help")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def config_menu():
        """Menu cấu hình"""
        keyboard = [
            [InlineKeyboardButton("📥 Chọn Channel nguồn", callback_data="select_source_channel")],
            [InlineKeyboardButton("📤 Chọn Channel đích", callback_data="select_target_channel")],
            [InlineKeyboardButton("🎯 Thiết lập Text cần lấy", callback_data="setup_extract_pattern")],
            [InlineKeyboardButton("📄 Thiết lập Header/Footer", callback_data="setup_header_footer")],
            [InlineKeyboardButton("🔘 Thiết lập Button", callback_data="setup_button")],
            [InlineKeyboardButton("✅ Lưu cấu hình", callback_data="save_config")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def header_footer_menu():
        """Menu thiết lập header/footer"""
        keyboard = [
            [InlineKeyboardButton("📝 Thiết lập Header", callback_data="setup_header")],
            [InlineKeyboardButton("📝 Thiết lập Footer", callback_data="setup_footer")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="setup_config")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def button_menu():
        """Menu thiết lập button"""
        keyboard = [
            [InlineKeyboardButton("📝 Thiết lập Text Button", callback_data="setup_button_text")],
            [InlineKeyboardButton("🔗 Thiết lập URL Button", callback_data="setup_button_url")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="setup_config")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_menu():
        """Menu xác nhận"""
        keyboard = [
            [InlineKeyboardButton("✅ Xác nhận", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Hủy", callback_data="confirm_no")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_to_main():
        """Nút quay lại menu chính"""
        keyboard = [
            [InlineKeyboardButton("🔙 Menu chính", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def config_list_buttons(configs):
        """Tạo keyboard cho danh sách cấu hình"""
        keyboard = []
        for config in configs:
            # Thêm emoji trạng thái
            status_emoji = "🟢" if config.get('is_active', False) else "⚪"
            status_text = "Đang chạy" if config.get('is_active', False) else "Đã dừng"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {config['source_channel_name']} → {config['target_channel_name']} ({status_text})", 
                    callback_data=f"view_config_{config['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🔙 Menu chính", callback_data="main_menu")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def config_actions(config_id, is_active=False):
        """Menu hành động cho mỗi cấu hình"""
        keyboard = []
        
        # Nút Start/Stop tùy theo trạng thái
        if is_active:
            keyboard.append([InlineKeyboardButton("⏹️ Dừng Copy", callback_data=f"stop_config_{config_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🚀 Bắt đầu Copy", callback_data=f"start_config_{config_id}")])
        
        # Các nút khác
        keyboard.extend([
            [InlineKeyboardButton("✏️ Chỉnh sửa", callback_data=f"edit_config_{config_id}")],
            [InlineKeyboardButton("🗑️ Xóa", callback_data=f"delete_config_{config_id}")],
            [InlineKeyboardButton("🔙 Danh sách", callback_data="list_configs")]
        ])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def channel_selection_buttons(channels, page=0, per_page=15):
        """Tạo keyboard để chọn channel với hiển thị ID và pagination"""
        keyboard = []
        
        # Tính toán pagination
        start_idx = page * per_page
        end_idx = start_idx + per_page
        total_pages = (len(channels) + per_page - 1) // per_page
        
        # Hiển thị channels cho trang hiện tại
        current_channels = channels[start_idx:end_idx]
        
        for i, channel in enumerate(current_channels, start=start_idx+1):
            # Tạo text hiển thị với format: "Tên Channel (ID: 123456789)"
            channel_title = channel.get('title', 'Unknown')
            if not channel_title or channel_title is None:
                channel_title = 'Unknown'
            
            channel_id = str(channel['id'])
            channel_type = channel.get('type', 'channel')
            
            # Cắt ngắn tên nếu quá dài
            if len(channel_title) > 28:
                channel_title = channel_title[:25] + "..."
            
            # Format text hiển thị với số thứ tự
            type_emoji = "📺"
            if channel_type == 'supergroup':
                type_emoji = "👥"
            elif channel_type == 'group':
                type_emoji = "👫"
            elif channel_type == 'private':
                type_emoji = "💬"
            
            display_text = f"{i:2d}. {type_emoji} {channel_title}"
            
            keyboard.append([
                InlineKeyboardButton(
                    display_text,
                    callback_data=f"select_channel_{channel['id']}"
                )
            ])
        
        # Thêm navigation buttons nếu có nhiều trang
        if total_pages > 1:
            nav_buttons = []
            
            # Nút "◀️ Trước"
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "◀️ Trước", 
                        callback_data=f"channel_page_{page-1}"
                    )
                )
            
            # Hiển thị trang hiện tại
            nav_buttons.append(
                InlineKeyboardButton(
                    f"📄 {page+1}/{total_pages}",
                    callback_data="current_page"
                )
            )
            
            # Nút "▶️ Tiếp"
            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "▶️ Tiếp", 
                        callback_data=f"channel_page_{page+1}"
                    )
                )
            
            keyboard.append(nav_buttons)
        
        # Nút quay lại
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="setup_config")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def login_menu():
        """Menu đăng nhập"""
        keyboard = [
            [InlineKeyboardButton("📱 Nhập số điện thoại", callback_data="enter_phone")],
            [InlineKeyboardButton("🔑 Nhập mã xác thực", callback_data="enter_code")],
            [InlineKeyboardButton("🔙 Menu chính", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard) 