import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils.keyboards import Keyboards
from bot.utils.client import TelegramClient
from bot.utils.states import WAITING_PHONE, WAITING_CODE, WAITING_2FA_PASSWORD

# Add Pyrogram exceptions for better error handling
try:
    from pyrogram.errors import SessionPasswordNeeded, PeerIdInvalid
except ImportError:
    # Fallback if pyrogram is not available
    SessionPasswordNeeded = None
    PeerIdInvalid = None

class AuthHandlers:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.temp_data = bot_instance.temp_data
        self.user_clients = bot_instance.user_clients
        self.api_id = bot_instance.api_id
        self.api_hash = bot_instance.api_hash
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode='Markdown'):
        """Safely edit message with error handling"""
        return await self.bot.safe_edit_message(query, text, reply_markup, parse_mode)
    
    async def show_login_menu(self, query):
        """Hiển thị menu đăng nhập với kiểm tra session đã có"""
        user_id = query.from_user.id
        user = self.db.get_user(user_id)
        
        # Kiểm tra xem có session đã lưu không
        existing_client = await self.bot.get_or_restore_client(user_id)
        
        if existing_client and user and user['is_authenticated']:
            # User đã có session hợp lệ
            try:
                me = await existing_client.client.get_me()
                text = f"""
✅ **BẠN ĐÃ ĐĂNG NHẬP THÀNH CÔNG!**

👤 **Tài khoản:** {me.first_name} {getattr(me, 'last_name', '') or ''}
📱 **Số điện thoại:** {user['phone_number'] or 'N/A'}
🆔 **User ID:** {me.id}
📅 **Đăng nhập lần cuối:** {user.get('last_active', 'N/A')}

🎉 **Session đã được khôi phục tự động!**
✅ Bạn có thể sử dụng bot ngay bây giờ

🚀 **Bước tiếp theo:**
• Tạo cấu hình copy channel  
• Bắt đầu copy tin nhắn
• Quản lý cấu hình hiện có

💡 **Không cần đăng nhập lại!**
                """
                await self.safe_edit_message(
                    query,
                    text,
                    reply_markup=Keyboards.back_to_main()
                )
                return
                
            except Exception as e:
                print(f"⚠️ Error validating existing session for user {user_id}: {e}")
                # Continue to show login menu if session validation fails
        
        # Kiểm tra session trong database nhưng client chưa khởi tạo
        if user and user['is_authenticated'] and self.db.is_session_valid(user_id):
            text = f"""
🔄 **ĐANG KHÔI PHỤC SESSION...**

📱 **Số điện thoại:** {user['phone_number']}
👤 **Tên:** {user['first_name']} {user['last_name'] or ''}

⏳ **Đang khôi phục session đã lưu...**
🔐 **Không cần đăng nhập lại!**

💡 **Session sẽ được khôi phục tự động trong vài giây**

🔙 Nhấn "Quay lại" để kiểm tra lại sau
            """
            await self.safe_edit_message(
                query,
                text,
                reply_markup=Keyboards.back_to_main()
            )
            
            # Trigger session restoration in background
            asyncio.create_task(self._restore_user_session_background(user_id))
            return
        
        # Không có session hợp lệ - cần đăng nhập mới
        text = f"""
🔐 **ĐĂNG NHẬP TÀI KHOẢN TELEGRAM**

⚠️ **Lưu ý quan trọng:**
• Bạn cần đăng nhập tài khoản Telegram để bot có thể copy tin nhắn
• Bot cần API_ID và API_HASH từ my.telegram.org
• Thông tin đăng nhập được mã hóa an toàn
• **CHỈ CẦN ĐĂNG NHẬP 1 LẦN** - session sẽ được lưu tự động

📱 **Bước 1:** Nhấn "Nhập số điện thoại"
🔑 **Bước 2:** Nhập mã xác thực từ Telegram

⚡ **Sau khi đăng nhập:**
✅ Session được lưu vĩnh viễn
🔄 Tự động khôi phục khi khởi động lại bot
❌ Không cần đăng nhập lại

**Cần API_ID và API_HASH?**
1. Truy cập: https://my.telegram.org
2. Đăng nhập và tạo ứng dụng mới  
3. Cập nhật file .env với thông tin này
        """
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.login_menu()
        )
    
    async def _restore_user_session_background(self, user_id: int):
        """Background task để khôi phục session"""
        try:
            await asyncio.sleep(2)  # Small delay
            client = await self.bot.get_or_restore_client(user_id)
            if client:
                print(f"✅ Background session restoration successful for user {user_id}")
                # Restore active configs
                await self.bot.restore_active_configs(user_id)
            else:
                print(f"❌ Background session restoration failed for user {user_id}")
        except Exception as e:
            print(f"❌ Error in background session restoration for user {user_id}: {e}")
    
    async def request_phone_number(self, query):
        """Yêu cầu nhập số điện thoại"""
        if not self.api_id or not self.api_hash:
            await self.safe_edit_message(
                query,
                "❌ **Lỗi cấu hình!**\n\nVui lòng cập nhật API_ID và API_HASH trong file .env",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
        
        text = """
📱 **NHẬP SỐ ĐIỆN THOẠI**

Vui lòng nhập số điện thoại Telegram của bạn:
(Định dạng: +84xxxxxxxxx)

📝 **Ví dụ:** +84901234567
        """
        await self.safe_edit_message(query, text)
        return WAITING_PHONE
    
    async def request_verification_code(self, query):
        """Yêu cầu nhập mã xác thực"""
        text = """
🔑 **NHẬP MÃ XÁC THỰC**

Vui lòng nhập mã xác thực 5 chữ số từ Telegram:

📝 **Ví dụ:** 12345
        """
        await self.safe_edit_message(query, text)
        return WAITING_CODE
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý số điện thoại được nhập với kiểm tra session đã có"""
        phone_number = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone_number):
            await update.message.reply_text(
                "❌ **Số điện thoại không hợp lệ!**\n\nVui lòng nhập đúng định dạng: +84xxxxxxxxx"
            )
            return WAITING_PHONE
        
        # ⚠️ QUAN TRỌNG: Kiểm tra session đã có cho số điện thoại này
        user = self.db.get_user(user_id)
        if user and user.get('phone_number') == phone_number and user.get('is_authenticated'):
            # Thử khôi phục session đã có
            existing_client = await self.bot.get_or_restore_client(user_id)
            if existing_client:
                await update.message.reply_text(
                    f"""
🎉 **ĐÃ TÌM THẤY SESSION ĐÃ LƯU!**

📱 **Số điện thoại:** {phone_number}
✅ **Đã đăng nhập trước đó**
🔄 **Session được khôi phục tự động**

**KHÔNG CẦN ĐĂNG NHẬP LẠI!**

🚀 Nhấn /start để sử dụng bot ngay!
                    """,
                    reply_markup=Keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
        
        try:
            # ⚠️ CHỈ TẠO CLIENT MỚI KHI THỰC SỰ CẦN THIẾT
            print(f"📱 Creating new login session for {phone_number} (user {user_id})")
            
            client = TelegramClient(user_id, self.api_id, self.api_hash)
            phone_code_hash = await client.login_with_phone(phone_number)
            
            if phone_code_hash:
                # Lưu thông tin tạm thời
                self.temp_data[user_id] = {
                    'phone_number': phone_number,
                    'phone_code_hash': phone_code_hash,
                    'client': client
                }
                
                await update.message.reply_text(
                    f"""
✅ **Mã xác thực đã được gửi đến {phone_number}**

🔑 **Vui lòng nhập mã xác thực 5 chữ số:**

📝 **Ví dụ:** 12345

💡 **Lưu ý:** Session sẽ được lưu vĩnh viễn sau khi xác thực thành công
                    """,
                    parse_mode='Markdown'
                )
                return WAITING_CODE
            else:
                await update.message.reply_text(
                    "❌ **Không thể gửi mã xác thực!**\n\nVui lòng kiểm tra lại số điện thoại.",
                    reply_markup=Keyboards.back_to_main()
                )
                return ConversationHandler.END
                
        except Exception as e:
            error_str = str(e).lower()
            if "flood" in error_str or "too many attempts" in error_str:
                await update.message.reply_text(
                    f"""
⚠️ **TELEGRAM ĐÃ CHẶN DO QUÁ NHIỀU LẦN ĐĂNG NHẬP**

🛑 **Lỗi:** {str(e)}

🔧 **Khắc phục:**
1. **Đợi 24 giờ** trước khi thử lại
2. Kiểm tra xem đã có session được lưu chưa: `/status`
3. Thử khôi phục session cũ: `/recover`

⚠️ **Quan trọng:** 
• Telegram giới hạn số lần đăng nhập từ cùng IP/device
• Bot này đã được thiết kế để CHỈ ĐĂNG NHẬP 1 LẦN
• Session sẽ được lưu vĩnh viễn sau đăng nhập thành công

💡 **Gợi ý:** Nếu bạn đã đăng nhập trước đó, thử lệnh `/recover` để khôi phục session
                    """,
                    reply_markup=Keyboards.back_to_main(),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ **Lỗi:** {str(e)}",
                    reply_markup=Keyboards.back_to_main()
                )
            return ConversationHandler.END
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý mã xác thực được nhập"""
        code = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            await update.message.reply_text(
                "❌ **Phiên đăng nhập đã hết hạn!**\n\nVui lòng bắt đầu lại.",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
        
        try:
            temp_data = self.temp_data[user_id]
            client = temp_data['client']
            
            success = await client.verify_code(
                temp_data['phone_number'],
                temp_data['phone_code_hash'],
                code
            )
            
            if success == "2fa_required":
                # Lưu phone number vào database trước khi chuyển sang 2FA
                self.db.update_user_auth(user_id, False, temp_data['phone_number'])
                
                # Cần mật khẩu 2FA
                await update.message.reply_text(
                    """
🔒 **CẦN MẬT KHẨU 2FA**

🔐 Tài khoản của bạn đã bật xác thực 2 bước.
📝 Vui lòng nhập mật khẩu 2FA:

⚠️ **Lưu ý:** Đây là mật khẩu bạn đã thiết lập trong Telegram Settings > Privacy and Security > Two-Step Verification
                    """,
                    parse_mode='Markdown'
                )
                return WAITING_2FA_PASSWORD
                
            elif success:
                # Đăng nhập thành công
                # Set bot instance cho client
                client.set_bot_instance(self.bot)
                
                # Lưu client vào bộ nhớ
                self.user_clients[user_id] = client
                
                await update.message.reply_text(
                    """
🎉 **Đăng nhập thành công!**

✅ Tài khoản của bạn đã được xác thực
🚀 Bây giờ bạn có thể cấu hình copy channel

Nhấn /start để bắt đầu sử dụng!
                    """,
                    reply_markup=Keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                
                # Xóa dữ liệu tạm thời
                del self.temp_data[user_id]
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ **Mã xác thực không đúng!**\n\nVui lòng thử lại:"
                )
                return WAITING_CODE
                
        except Exception as e:
            error_msg = str(e)
            print(f"Exception in handle_code_input: {error_msg}")
            
            # Handle both Pyrogram exceptions and string-based detection
            is_2fa_needed = False
            
            # Check for Pyrogram SessionPasswordNeeded exception
            if SessionPasswordNeeded and isinstance(e, SessionPasswordNeeded):
                is_2fa_needed = True
            # Fallback string-based detection
            elif ("SESSION_PASSWORD_NEEDED" in error_msg or 
                  "Two-step verification" in error_msg or
                  "SessionPasswordNeeded" in str(type(e))):
                is_2fa_needed = True
            
            if is_2fa_needed:
                # Lưu phone number vào database trước khi chuyển sang 2FA
                temp_data = self.temp_data[user_id]
                self.db.update_user_auth(user_id, False, temp_data['phone_number'])
                
                await update.message.reply_text(
                    """
🔒 **CẦN MẬT KHẨU 2FA**

🔐 Tài khoản của bạn đã bật xác thực 2 bước.
📝 Vui lòng nhập mật khẩu 2FA:

⚠️ **Lưu ý:** Đây là mật khẩu bạn đã thiết lập trong Telegram Settings > Privacy and Security > Two-Step Verification
                    """,
                    parse_mode='Markdown'
                )
                return WAITING_2FA_PASSWORD
            else:
                await update.message.reply_text(
                    f"❌ **Lỗi xác thực:** {error_msg}\n\nVui lòng thử lại hoặc bắt đầu lại quá trình đăng nhập.",
                    reply_markup=Keyboards.back_to_main()
                )
                return ConversationHandler.END
    
    async def handle_2fa_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý mật khẩu 2FA được nhập"""
        password = update.message.text.strip()
        user_id = update.effective_user.id
        
        if user_id not in self.temp_data:
            await update.message.reply_text(
                "❌ **Phiên đăng nhập đã hết hạn!**\n\nVui lòng bắt đầu lại.",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
        
        try:
            temp_data = self.temp_data[user_id]
            client = temp_data['client']
            
            # Xác thực với mật khẩu 2FA
            success = await client.verify_2fa_password(password)
            
            if success:
                # Set bot instance cho client
                client.set_bot_instance(self.bot)
                
                # Lưu client vào bộ nhớ
                self.user_clients[user_id] = client
                
                await update.message.reply_text(
                    """
🎉 **Đăng nhập thành công với 2FA!**

✅ Tài khoản của bạn đã được xác thực
🚀 Bây giờ bạn có thể cấu hình copy channel

Nhấn /start để bắt đầu sử dụng!
                    """,
                    reply_markup=Keyboards.main_menu(),
                    parse_mode='Markdown'
                )
                
                # Xóa dữ liệu tạm thời
                del self.temp_data[user_id]
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ **Mật khẩu 2FA không đúng!**\n\nVui lòng thử lại:"
                )
                return WAITING_2FA_PASSWORD
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi xác thực 2FA:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            )
            return ConversationHandler.END
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Kiểm tra trạng thái phiên đăng nhập"""
        user_id = update.effective_user.id
        
        try:
            user = self.db.get_user(user_id)
            
            if not user or not user['is_authenticated']:
                status_text = """
🔴 **CHƯA ĐĂNG NHẬP**

❌ Bạn chưa đăng nhập tài khoản Telegram
🔐 Nhấn /start để bắt đầu đăng nhập
                """
            else:
                # Kiểm tra client có hoạt động không
                client = await self.bot.get_or_restore_client(user_id)
                
                if client:
                    configs = self.db.get_user_configs(user_id)
                    active_configs = len([c for c in configs if c.get('is_active', True)])
                    
                    status_text = f"""
🟢 **ĐÃ ĐĂNG NHẬP**

👤 **Tài khoản:** {user['first_name']} {user['last_name'] or ''}
📱 **Số ĐT:** {user['phone_number']}
📋 **Cấu hình:** {active_configs} cấu hình
✅ **Phiên:** Đang hoạt động

🚀 Nhấn /start để mở menu chính
                    """
                else:
                    status_text = """
🟡 **PHIÊN HẾT HẠN**

⚠️ Phiên đăng nhập đã hết hạn
🔐 Vui lòng đăng nhập lại
📱 Nhấn /start để bắt đầu
                    """
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi kiểm tra trạng thái:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def show_status_callback(self, query):
        """Hiển thị trạng thái qua callback"""
        user_id = query.from_user.id
        
        try:
            user = self.db.get_user(user_id)
            
            if not user or not user['is_authenticated']:
                status_text = """
🔴 **CHƯA ĐĂNG NHẬP**

❌ Bạn chưa đăng nhập tài khoản Telegram
🔐 Sử dụng menu "Đăng nhập tài khoản" để bắt đầu
                """
            else:
                # Kiểm tra client có hoạt động không
                client = await self.bot.get_or_restore_client(user_id)
                
                if client:
                    configs = self.db.get_user_configs(user_id)
                    active_configs = len([c for c in configs if c.get('is_active', True)])
                    
                    status_text = f"""
🟢 **ĐÃ ĐĂNG NHẬP**

👤 **Tài khoản:** {user['first_name']} {user['last_name'] or ''}
📱 **Số ĐT:** {user['phone_number']}
📋 **Cấu hình:** {active_configs} cấu hình
✅ **Phiên:** Đang hoạt động

🤖 Bot sẵn sàng copy channels!
                    """
                else:
                    status_text = """
🟡 **PHIÊN HẾT HẠN**

⚠️ Phiên đăng nhập đã hết hạn hoặc không hợp lệ
🔐 Vui lòng đăng nhập lại bằng menu "Đăng nhập tài khoản"
                    """
            
            await self.safe_edit_message(
                query,
                status_text,
                reply_markup=Keyboards.back_to_main()
            )
            
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi kiểm tra trạng thái:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            )
    
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho lệnh /logout"""
        user_id = update.effective_user.id
        
        try:
            # Dừng tất cả copying nếu có
            if user_id in self.user_clients:
                client = self.user_clients[user_id]
                await client.stop_all_copying()
                del self.user_clients[user_id]
            
            # Xóa session từ database
            self.db.clear_user_session(user_id, "User logout")
            
            # Xóa temp data
            if user_id in self.temp_data:
                del self.temp_data[user_id]
            
            await update.message.reply_text(
                """
🚪 **ĐÃ ĐĂNG XUẤT THÀNH CÔNG!**

✅ **Đã thực hiện:**
• Dừng tất cả copy channels
• Xóa thông tin phiên đăng nhập
• Xóa dữ liệu tạm thời

🔐 **Để sử dụng lại bot:**
• Nhấn /start để bắt đầu
• Đăng nhập lại tài khoản Telegram

👋 Cảm ơn bạn đã sử dụng bot!
                """,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi khi đăng xuất:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def logout_callback(self, query):
        """Xử lý đăng xuất qua callback"""
        user_id = query.from_user.id
        
        try:
            # Kiểm tra xem có đăng nhập không
            user = self.db.get_user(user_id)
            if not user or not user['is_authenticated']:
                await self.safe_edit_message(
                    query,
                    "❌ **Bạn chưa đăng nhập!**\n\nKhông có gì để đăng xuất.",
                    reply_markup=Keyboards.back_to_main()
                )
                return
            
            # Dừng tất cả copying nếu có
            if user_id in self.user_clients:
                client = self.user_clients[user_id]
                await client.stop_all_copying()
                del self.user_clients[user_id]
            
            # Xóa session từ database
            self.db.clear_user_session(user_id, "User logout via callback")
            
            # Xóa temp data
            if user_id in self.temp_data:
                del self.temp_data[user_id]
            
            await self.safe_edit_message(
                query,
                """
🚪 **ĐÃ ĐĂNG XUẤT THÀNH CÔNG!**

✅ **Đã thực hiện:**
• Dừng tất cả copy channels
• Xóa thông tin phiên đăng nhập
• Xóa dữ liệu tạm thời

🔐 **Để sử dụng lại bot:**
Sử dụng menu "Đăng nhập tài khoản"

👋 Cảm ơn bạn đã sử dụng bot!
                """,
                reply_markup=Keyboards.back_to_main()
            )
            
        except Exception as e:
            await self.safe_edit_message(
                query,
                f"❌ **Lỗi khi đăng xuất:** {str(e)}",
                reply_markup=Keyboards.back_to_main()
            )
    
    async def recover_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Thử khôi phục session với multiple recovery strategies"""
        user_id = update.effective_user.id
        
        try:
            progress_msg = await update.message.reply_text(
                "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n📝 Bước 1/4: Kiểm tra session database...",
                parse_mode='Markdown'
            )
            
            # Step 1: Kiểm tra session trong database
            if not self.db.is_session_valid(user_id):
                # Try to restore from backup
                await progress_msg.edit_text(
                    "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n📋 Bước 1.5/4: Kiểm tra backup sessions...",
                    parse_mode='Markdown'
                )
                
                backups = self.db.get_session_backups(user_id)
                if backups:
                    # Try to restore from latest backup
                    if self.db.restore_session_from_backup(user_id):
                        await progress_msg.edit_text(
                            "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n✅ Bước 1.5/4: Khôi phục từ backup thành công!",
                            parse_mode='Markdown'
                        )
                    else:
                        await progress_msg.edit_text(
                            """
❌ **KHÔNG CÓ SESSION HỢP LỆ**

🔍 **Đã kiểm tra:**
• Session trong database: ❌
• Backup sessions: ❌

🔐 **Bạn cần đăng nhập lại:**
• Nhấn /start → "Đăng nhập tài khoản" 
• Làm theo hướng dẫn đăng nhập

⚠️ **Lý do session bị mất:**
• Đăng xuất từ thiết bị khác
• Thay đổi mật khẩu Telegram
• Session hết hạn tự nhiên
• Lỗi kết nối kéo dài
                            """,
                            parse_mode='Markdown'
                        )
                        return
                else:
                    await progress_msg.edit_text(
                        """
❌ **KHÔNG CÓ SESSION VÀ BACKUP**

🔐 **Bạn cần đăng nhập lại:**
• Nhấn /start → "Đăng nhập tài khoản" 
• Làm theo hướng dẫn đăng nhập

⚠️ **Nguyên nhân:** Không tìm thấy session hoặc backup nào.
                        """,
                        parse_mode='Markdown'
                    )
                    return
            
            # Step 2: Thử các recovery strategies
            await progress_msg.edit_text(
                "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n🔧 Bước 2/4: Thử khôi phục client...",
                parse_mode='Markdown'
            )
            
            client = await self.bot.get_or_restore_client(user_id)
            
            if client:
                # Step 3: Test connection
                await progress_msg.edit_text(
                    "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n🧪 Bước 3/4: Kiểm tra kết nối...",
                    parse_mode='Markdown'
                )
                
                try:
                    me = await client.client.get_me()
                    user_data = self.db.get_user(user_id)
                    
                    # Step 4: Restore active configs
                    await progress_msg.edit_text(
                        "🔄 **ĐANG THỬ KHÔI PHỤC SESSION...**\n\n⚙️ Bước 4/4: Khôi phục cấu hình...",
                        parse_mode='Markdown'
                    )
                    
                    await self.bot.restore_active_configs(user_id)
                    
                    await progress_msg.edit_text(
                        f"""
✅ **KHÔI PHỤC SESSION THÀNH CÔNG!**

👤 **Tài khoản:** {me.first_name} {getattr(me, 'last_name', '') or ''}
📱 **Số ĐT:** {user_data.get('phone_number', 'N/A') if user_data else 'N/A'}
🆔 **User ID:** {me.id}
🕐 **Thời gian:** {user_data.get('last_active', 'N/A') if user_data else 'N/A'}

🔧 **Đã khôi phục:**
✅ Session connection
✅ User authentication  
✅ Active configurations
✅ Message handlers

🚀 **Sẵn sàng sử dụng!** Bạn có thể:
• Xem cấu hình hiện có
• Tạo cấu hình copy channel mới
• Bắt đầu copy tin nhắn

💡 Nhấn /start để mở menu chính
                        """,
                        parse_mode='Markdown'
                    )
                    
                    # Backup session sau khi recover thành công
                    self.db.backup_session(user_id, "Post successful recovery")
                    
                except Exception as test_error:
                    await progress_msg.edit_text(
                        f"""
⚠️ **SESSION ĐƯỢC KHÔI PHỤC NHƯNG CÓ VẤN ĐỀ**

🔍 **Chi tiết lỗi:** {str(test_error)}

🛠️ **Đã thử:** 
✅ Khôi phục session từ database
✅ Tạo client connection
❌ Test connection thất bại

💡 **Khuyến nghị:**
1. **Thử lại:** Chờ 30 giây và gõ /recover lại
2. **Đăng nhập mới:** /start → "Đăng nhập tài khoản"
3. **Kiểm tra mạng:** Đảm bảo kết nối internet ổn định

⚠️ **Có thể do:** Rate limit hoặc tạm thời lỗi API Telegram
                        """,
                        parse_mode='Markdown'
                    )
            else:
                # Try recovery từ backup nếu có
                backups = self.db.get_session_backups(user_id)
                if backups:
                    await progress_msg.edit_text(
                        f"🔄 **THỬ PHƯƠNG PHÁP BACKUP...**\n\n📋 Tìm thấy {len(backups)} backup sessions, đang thử...",
                        parse_mode='Markdown'
                    )
                    
                    # Try each backup
                    for i, backup in enumerate(backups[:3]):  # Try top 3 backups
                        await progress_msg.edit_text(
                            f"🔄 **THỬ BACKUP {i+1}/3...**\n\n📋 Reason: {backup['reason']}\n⏰ Created: {backup['created_at']}",
                            parse_mode='Markdown'
                        )
                        
                        if self.db.restore_session_from_backup(user_id, backup['id']):
                            retry_client = await self.bot.get_or_restore_client(user_id)
                            if retry_client:
                                try:
                                    me = await retry_client.client.get_me()
                                    await progress_msg.edit_text(
                                        f"""
✅ **KHÔI PHỤC TỪNG BACKUP THÀNH CÔNG!**

👤 **Tài khoản:** {me.first_name} {getattr(me, 'last_name', '') or ''}
📋 **Backup:** {backup['reason']}
⏰ **Ngày tạo backup:** {backup['created_at']}

🚀 **Session đã sẵn sàng!**
💡 Nhấn /start để mở menu chính
                                        """,
                                        parse_mode='Markdown'
                                    )
                                    return
                                except Exception as backup_test_error:
                                    continue
                
                # All recovery methods failed
                await progress_msg.edit_text(
                    """
❌ **KHÔNG THỂ KHÔI PHỤC SESSION**

🔄 **Đã thử tất cả phương pháp:**
❌ Session database restore
❌ Multiple recovery strategies  
❌ Backup session restore
❌ Connection repair attempts

💡 **Giải pháp duy nhất - Đăng nhập lại:**
1. **Bước 1:** Nhấn /start
2. **Bước 2:** Chọn "Đăng nhập tài khoản"
3. **Bước 3:** Làm theo hướng dẫn đăng nhập

⚠️ **Lý do có thể:**
• Session đã bị revoke bởi Telegram
• Tài khoản bị hạn chế tạm thời  
• Thay đổi mật khẩu/2FA
• Vấn đề nghiêm trọng với API connection

🔒 **An toàn:** Tất cả dữ liệu cấu hình của bạn vẫn được lưu và sẽ tự động khôi phục sau khi đăng nhập lại.
                    """,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"""
❌ **LỖI NGHIÊM TRỌNG KHI KHÔI PHỤC SESSION**

🔍 **Chi tiết lỗi:** {str(e)}

🚨 **Lỗi hệ thống - Vui lòng:**
1. **Screenshot lỗi này** để báo admin
2. **Thử đăng nhập lại:** /start  
3. **Kiểm tra /status** để xem trạng thái hệ thống
4. **Liên hệ admin** nếu vấn đề tiếp tục

⚠️ **Lưu ý:** Đây có thể là lỗi tạm thời, thử lại sau 5-10 phút.
                """,
                parse_mode='Markdown'
            ) 