import os
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)

from bot.utils.database import Database
from bot.utils.keyboards import Keyboards
from bot.utils.client import TelegramClient
from bot.utils.handlers import BotHandlers
from bot.auth.handlers import AuthHandlers
from bot.config.handlers import ConfigHandlers
from bot.channels.manager import ChannelManager
from bot.messages.processor import MessageProcessor
from bot.utils.states import *

# Load environment variables
load_dotenv()

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.api_id = int(os.getenv('API_ID', '0'))
        self.api_hash = os.getenv('API_HASH', '')
        self.db = Database()
        self.user_clients = {}  # Lưu trữ client của từng user
        self.temp_data = {}  # Lưu trữ dữ liệu tạm thời
        self.session_recovery_attempts = {}  # Track recovery attempts per user
        
        # Initialize handlers
        self.handlers = BotHandlers(self)  
        self.auth_handlers = AuthHandlers(self)
        self.config_handlers = ConfigHandlers(self)
        self.channel_manager = ChannelManager(self)
        self.message_processor = MessageProcessor(self)
        
        self.bot_instance = None  # Will be set during initialization
        
        # Tạo thư mục sessions nếu chưa có
        os.makedirs("sessions", exist_ok=True)
        
    async def init_async(self):
        """Khởi tạo các thành phần async sau khi event loop được tạo"""
        await self.restore_user_sessions()
        # Start message processing task
        await self.message_processor.init_async()
        
        # Start background session monitoring
        asyncio.create_task(self.monitor_sessions())
        
    async def monitor_sessions(self):
        """Background task để monitor và maintain sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.check_and_maintain_sessions()
            except Exception as e:
                print(f"⚠️ Error in session monitoring: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute if error
        
    async def check_and_maintain_sessions(self):
        """Kiểm tra và maintain sessions của users"""
        print("🔍 Checking session health...")
        
        for user_id, client in list(self.user_clients.items()):
            try:
                # Kiểm tra connection status
                if not client.client or not client.client.is_connected:
                    print(f"⚠️ User {user_id} disconnected, attempting reconnect...")
                    success = await self.attempt_session_recovery(user_id)
                    if not success:
                        print(f"❌ Failed to recover session for user {user_id}")
                else:
                    # Update last active
                    self.db.update_user_last_active(user_id)
                    
            except Exception as e:
                print(f"⚠️ Error checking user {user_id}: {e}")
                await self.attempt_session_recovery(user_id)
        
    async def attempt_session_recovery(self, user_id: int):
        """Thử khôi phục session cho một user cụ thể"""
        try:
            # Track recovery attempts
            if user_id not in self.session_recovery_attempts:
                self.session_recovery_attempts[user_id] = 0
                
            self.session_recovery_attempts[user_id] += 1
            
            # Giới hạn số lần thử
            if self.session_recovery_attempts[user_id] > 5:
                print(f"🔴 Max recovery attempts reached for user {user_id}")
                # Reset counter after 1 hour
                await asyncio.sleep(3600)
                self.session_recovery_attempts[user_id] = 0
                return False
            
            # Remove old client
            if user_id in self.user_clients:
                try:
                    old_client = self.user_clients[user_id]
                    if old_client.client:
                        await old_client.client.stop()
                except:
                    pass
                del self.user_clients[user_id]
            
            # Try to restore from database
            client = await self.get_or_restore_client(user_id)
            if client:
                # Restore active configs
                await self.restore_active_configs(user_id)
                self.session_recovery_attempts[user_id] = 0  # Reset on success
                return True
                
        except Exception as e:
            print(f"❌ Session recovery failed for user {user_id}: {e}")
            
        return False
        
    async def restore_user_sessions(self):
        """Khôi phục sessions của tất cả users đã đăng nhập với improved error handling"""
        try:
            print("🔄 Đang khôi phục sessions...")
            authenticated_users = self.db.get_all_authenticated_users()
            
            restored_count = 0
            failed_users = []
            
            for user_data in authenticated_users:
                try:
                    user_id = user_data['user_id']
                    session_string = user_data['session_string']
                    api_id = user_data['api_id']
                    api_hash = user_data['api_hash']
                    
                    print(f"🔄 Restoring session for user {user_data['first_name']} ({user_id})")
                    
                    # Tạo client với session đã lưu
                    client = TelegramClient(user_id, api_id, api_hash, session_string)
                    
                    # Set bot instance cho client
                    client.set_bot_instance(self)
                    
                    success = await client.initialize_client()
                    
                    if success:
                        self.user_clients[user_id] = client
                        self.db.update_user_last_active(user_id)
                        
                        # ✅ QUAN TRỌNG: Đảm bảo authentication status được cập nhật
                        try:
                            me = await client.client.get_me()
                            phone_number = me.phone_number if hasattr(me, 'phone_number') else user_data.get('phone_number')
                            self.db.update_user_auth(user_id, True, phone_number)
                            print(f"✅ Updated authentication status for user {user_data['first_name']} ({user_id})")
                        except Exception as auth_update_error:
                            print(f"⚠️ Could not update auth status for user {user_id}: {auth_update_error}")
                        
                        restored_count += 1
                        print(f"✅ Khôi phục session cho user {user_data['first_name']} ({user_id})")
                        
                        # Khôi phục các active configs (message handlers) với delay
                        await asyncio.sleep(1)  # Small delay to avoid rate limits
                        await self.restore_active_configs(user_id)
                        
                    else:
                        print(f"❌ Không thể khôi phục session cho user {user_id}")
                        failed_users.append(user_data)
                        
                except Exception as e:
                    print(f"❌ Lỗi khôi phục session cho user {user_data.get('user_id', 'unknown')}: {e}")
                    failed_users.append(user_data)
            
            print(f"🎉 Đã khôi phục {restored_count}/{len(authenticated_users)} sessions thành công!")
            
            # Retry failed users với delay
            if failed_users:
                print(f"🔄 Retrying {len(failed_users)} failed sessions...")
                await asyncio.sleep(5)  # Wait before retry
                
                for user_data in failed_users:
                    await self.retry_session_restore(user_data)
            
        except Exception as e:
            print(f"❌ Lỗi khôi phục sessions: {e}")
    
    async def retry_session_restore(self, user_data: Dict):
        """Retry khôi phục session cho một user"""
        try:
            user_id = user_data['user_id']
            print(f"🔄 Retry restoring session for user {user_id}")
            
            # Check if session data is still valid in database
            if not self.db.is_session_valid(user_id):
                print(f"❌ Session no longer valid for user {user_id}")
                return False
            
            session_data = self.db.get_user_session(user_id)
            if not session_data:
                print(f"❌ No session data found for user {user_id}")
                return False
            
            client = TelegramClient(
                user_id,
                session_data['api_id'],
                session_data['api_hash'],
                session_data['session_string']
            )
            
            client.set_bot_instance(self)
            success = await client.initialize_client()
            
            if success:
                self.user_clients[user_id] = client
                self.db.update_user_last_active(user_id)
                
                # ✅ QUAN TRỌNG: Cập nhật authentication status
                try:
                    me = await client.client.get_me()
                    phone_number = me.phone_number if hasattr(me, 'phone_number') else None
                    self.db.update_user_auth(user_id, True, phone_number)
                    print(f"✅ Updated authentication status for user {user_id} (phone: {phone_number})")
                except Exception as auth_update_error:
                    print(f"⚠️ Could not update auth status: {auth_update_error}")
                
                print(f"✅ Retry successful for user {user_id}")
                await self.restore_active_configs(user_id)
                return True
            else:
                error_str = "Failed to initialize client on retry"
                # Chỉ clear session nếu là lỗi nghiêm trọng
                if any(keyword in error_str.lower() for keyword in [
                    'auth_key_invalid', 'user_deactivated', 'account_banned',
                    'session_revoked', 'unauthorized'
                ]):
                    print(f"🔴 Critical auth error on retry for user {user_id}, clearing session")
                    self.db.clear_user_session(user_id, f"Critical auth error on retry: {error_str}")
                
                return False
                
        except Exception as e:
            print(f"❌ Error retrying session for user {user_data.get('user_id', 'unknown')}: {e}")
            return False
    
    async def restore_active_configs(self, user_id: int):
        """Khôi phục các active configs và đăng ký lại message handlers"""
        try:
            # Lấy tất cả configs của user từ database (chỉ những cái active)
            configs = self.db.get_user_configs(user_id)
            
            if not configs:
                print(f"ℹ️ No active configs found for user {user_id}")
                return
            
            client = self.user_clients.get(user_id)
            if not client:
                print(f"❌ No client found for user {user_id}")
                return
            
            # Đăng ký lại message handlers cho configs đã active
            active_count = 0
            for config in configs:
                try:
                    success = await client.start_copying(config)
                    if success:
                        active_count += 1
                        print(f"✅ Khôi phục copying: {config['source_channel_name']} -> {config['target_channel_name']}")
                    else:
                        print(f"❌ Không thể khôi phục config {config['id']} cho user {user_id}")
                        # Đánh dấu config là không active nếu không thể khôi phục
                        self.db.update_config_status(config['id'], user_id, False)
                except Exception as e:
                    print(f"❌ Lỗi khôi phục config {config['id']}: {e}")
                    # Đánh dấu config là không active nếu có lỗi
                    self.db.update_config_status(config['id'], user_id, False)
            
            if active_count > 0:
                print(f"🚀 Đã khôi phục {active_count}/{len(configs)} configs cho user {user_id}")
            else:
                print(f"⚠️ Không thể khôi phục config nào cho user {user_id}")
                
        except Exception as e:
            print(f"❌ Lỗi khôi phục active configs cho user {user_id}: {e}")
    
    async def get_or_restore_client(self, user_id: int):
        """Lấy hoặc khôi phục client cho user với improved retry mechanism và session recovery strategies"""
        # Kiểm tra client hiện tại
        if user_id in self.user_clients:
            try:
                client = self.user_clients[user_id]
                if client.client and client.client.is_connected:
                    # Đảm bảo client có bot instance
                    if not client.bot_instance:
                        client.set_bot_instance(self)
                    
                    # Test connection với một API call đơn giản
                    try:
                        await client.client.get_me()
                        print(f"✅ Using existing healthy client for user {user_id}")
                        return client
                    except Exception as test_error:
                        print(f"⚠️ Existing client unhealthy for user {user_id}: {test_error}")
                        # Continue to restoration logic
                else:
                    print(f"🔄 Client disconnected for user {user_id}, attempting reconnect...")
            except Exception as e:
                print(f"⚠️ Error checking existing client for user {user_id}: {e}")
        
        # Thử khôi phục từ database với multiple strategies
        if not self.db.is_session_valid(user_id):
            print(f"❌ No valid session found for user {user_id}")
            return None
        
        session_data = self.db.get_user_session(user_id)
        if session_data and session_data['session_string']:
            # Strategy 1: Try with existing session string
            client = await self._try_restore_with_session_string(user_id, session_data)
            if client:
                return client
            
            # Strategy 2: Try with session file if available
            client = await self._try_restore_with_session_file(user_id, session_data)
            if client:
                return client
            
            # Strategy 3: Try to repair session
            client = await self._try_repair_session(user_id, session_data)
            if client:
                return client
            
            print(f"❌ All session restoration strategies failed for user {user_id}")
        
        return None
    
    async def _try_restore_with_session_string(self, user_id: int, session_data: Dict):
        """Strategy 1: Restore using session string from database"""
        retry_count = 3
        for attempt in range(retry_count):
            try:
                print(f"🔄 Strategy 1 - Attempt {attempt + 1}/{retry_count} to restore client for user {user_id} using session string")
                
                client = TelegramClient(
                    user_id,
                    session_data['api_id'],
                    session_data['api_hash'],
                    session_data['session_string']
                )
                
                # Set bot instance cho client
                client.set_bot_instance(self)
                
                success = await client.initialize_client()
                if success:
                    # Lưu client vào bộ nhớ
                    self.user_clients[user_id] = client
                    self.db.update_user_last_active(user_id)
                    
                    # ✅ QUAN TRỌNG: Cập nhật authentication status trong database
                    try:
                        me = await client.client.get_me()
                        phone_number = me.phone_number if hasattr(me, 'phone_number') else None
                        self.db.update_user_auth(user_id, True, phone_number)
                        print(f"✅ Updated authentication status for user {user_id} (phone: {phone_number})")
                    except Exception as auth_update_error:
                        print(f"⚠️ Could not update auth status: {auth_update_error}")
                        # Still continue as client is working
                    
                    print(f"✅ Strategy 1 successful - restored client for user {user_id}")
                    return client
                else:
                    print(f"⚠️ Strategy 1 - Failed to initialize client for user {user_id} on attempt {attempt + 1}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2)  # Wait before retry
                        
            except Exception as e:
                print(f"⚠️ Strategy 1 - Error restoring client for user {user_id} on attempt {attempt + 1}: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2)  # Wait before retry
        
        return None
    
    async def _try_restore_with_session_file(self, user_id: int, session_data: Dict):
        """Strategy 2: Try restore using existing session file"""
        try:
            session_file = f"sessions/user_{user_id}.session"
            if os.path.exists(session_file):
                print(f"🔄 Strategy 2 - Trying to restore user {user_id} using existing session file")
                
                client = TelegramClient(
                    user_id,
                    session_data['api_id'],
                    session_data['api_hash'],
                    None  # No session string, will use file
                )
                
                client.set_bot_instance(self)
                success = await client.initialize_client()
                
                if success:
                    # Update session string in database if successful
                    try:
                        new_session_string = await client.client.export_session_string()
                        if new_session_string:
                            self.db.save_user_session(user_id, new_session_string, session_data['api_id'], session_data['api_hash'])
                            client.session_string = new_session_string
                    except Exception as save_error:
                        print(f"⚠️ Could not save new session string: {save_error}")
                    
                    # ✅ QUAN TRỌNG: Cập nhật authentication status
                    try:
                        me = await client.client.get_me()
                        phone_number = me.phone_number if hasattr(me, 'phone_number') else None
                        self.db.update_user_auth(user_id, True, phone_number)
                        print(f"✅ Updated authentication status for user {user_id} (phone: {phone_number})")
                    except Exception as auth_update_error:
                        print(f"⚠️ Could not update auth status: {auth_update_error}")
                    
                    self.user_clients[user_id] = client
                    self.db.update_user_last_active(user_id)
                    print(f"✅ Strategy 2 successful - restored client for user {user_id} using session file")
                    return client
                
        except Exception as e:
            print(f"⚠️ Strategy 2 failed for user {user_id}: {e}")
        
        return None
    
    async def _try_repair_session(self, user_id: int, session_data: Dict):
        """Strategy 3: Try to repair corrupted session by creating a fresh one"""
        try:
            print(f"🔄 Strategy 3 - Attempting session repair for user {user_id}")
            
            # Try to create a fresh client without session
            client = TelegramClient(
                user_id,
                session_data['api_id'],
                session_data['api_hash'],
                None
            )
            
            client.set_bot_instance(self)
            
            # This will likely fail but might give us useful error info
            try:
                success = await client.initialize_client()
                if success:
                    print(f"✅ Strategy 3 unexpected success - fresh client worked for user {user_id}")
                    # Export and save new session
                    new_session_string = await client.client.export_session_string()
                    self.db.save_user_session(user_id, new_session_string, session_data['api_id'], session_data['api_hash'])
                    
                    # ✅ QUAN TRỌNG: Cập nhật authentication status
                    try:
                        me = await client.client.get_me()
                        phone_number = me.phone_number if hasattr(me, 'phone_number') else None
                        self.db.update_user_auth(user_id, True, phone_number)
                        print(f"✅ Updated authentication status for user {user_id} (phone: {phone_number})")
                    except Exception as auth_update_error:
                        print(f"⚠️ Could not update auth status: {auth_update_error}")
                    
                    self.user_clients[user_id] = client
                    self.db.update_user_last_active(user_id)
                    return client
            except Exception as repair_error:
                error_str = str(repair_error).lower()
                if any(critical_error in error_str for critical_error in [
                    'auth_key_invalid', 'user_deactivated', 'account_banned',
                    'session_revoked', 'unauthorized', 'session_expired'
                ]):
                    print(f"🔴 Strategy 3 - Critical auth error detected for user {user_id}: {repair_error}")
                    print(f"🗑️ Clearing corrupted session for user {user_id}")
                    self.db.clear_user_session(user_id, f"Strategy 3 - Critical auth error: {str(repair_error)}")
                    return None
                else:
                    print(f"⚠️ Strategy 3 - Non-critical error for user {user_id}: {repair_error}")
            
        except Exception as e:
            print(f"⚠️ Strategy 3 failed for user {user_id}: {e}")
        
        return None
    
    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode='Markdown'):
        """Safely edit message with error handling"""
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                # Message content is same, do nothing
                return True
            elif "message to edit not found" in error_msg:
                # Message was deleted, send new message
                try:
                    await query.message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    return True
                except:
                    return False
            else:
                print(f"Error editing message: {e}")
                return False
    
    async def add_message_to_queue(self, message_data: Dict[str, Any]):
        """Thêm tin nhắn vào queue để xử lý"""
        await self.message_processor.add_message_to_queue(message_data)
    
    def set_bot_instance(self, bot_instance):
        """Set bot instance để sử dụng cho việc gửi tin nhắn"""
        self.bot_instance = bot_instance
        print("✅ Bot instance set for message processing")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho lệnh /start"""
        user = update.effective_user
        
        # Thêm user vào database
        self.db.add_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        welcome_text = f"""
🎉 **Chào mừng {user.first_name}!**

🤖 **Bot Copy Channel Telegram**

✨ **Tính năng chính:**
📥 Copy tin nhắn từ channel khác về channel của bạn
🎯 Lọc nội dung theo pattern tùy chỉnh
📝 Thêm header/footer cho tin nhắn
🔘 Thêm button tùy chỉnh
👥 Hỗ trợ nhiều người dùng

🚀 **Bắt đầu sử dụng:**
Nhấn vào các nút bên dưới để thiết lập!
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=Keyboards.main_menu(),
            parse_mode='Markdown'
        )
    
    async def show_main_menu(self, query):
        """Hiển thị menu chính"""
        user = self.db.get_user(query.from_user.id)
        status = "🟢 Đã đăng nhập" if user and user['is_authenticated'] else "🔴 Chưa đăng nhập"
        
        text = f"""
🏠 **MENU CHÍNH**

👤 **Trạng thái:** {status}
🤖 **Bot Copy Channel Telegram**

📋 **Chọn chức năng bên dưới:**
        """
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=Keyboards.main_menu()
        )
    
    async def debug_configs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug command để kiểm tra configs và channel access của user"""
        user_id = update.effective_user.id
        
        try:
            user = self.db.get_user(user_id)
            all_configs = self.db.get_all_user_configs(user_id)
            active_configs = self.db.get_user_configs(user_id)
            
            # Check client status
            client_status = "❌ Không có client"
            client_details = ""
            if user_id in self.user_clients:
                client = self.user_clients[user_id]
                if client and client.client:
                    if client.client.is_connected:
                        client_status = "✅ Client connected"
                        
                        # Get cache info
                        cache_size = len(getattr(client, 'peer_cache', {}))
                        active_handlers = len(getattr(client, 'active_configs', {}))
                        
                        client_details = f"""
• Peer cache: {cache_size} entries
• Active handlers: {active_handlers}
• Session file: {'✅' if os.path.exists(f"sessions/user_{user_id}.session") else '❌'}"""
                    else:
                        client_status = "⚠️ Client disconnected"
                else:
                    client_status = "⚠️ Client object invalid"
            
            debug_text = f"""
🐛 **DEBUG INFO FOR USER {user_id}**

👤 **User Status:**
• Authenticated: {'✅' if user and user.get('is_authenticated') else '❌'}
• Phone: {user.get('phone_number', 'N/A') if user else 'N/A'}
• Last Active: {user.get('last_active', 'N/A') if user else 'N/A'}

🔌 **Client Status:**
• {client_status}{client_details}

📊 **Configs:**
• Total configs: {len(all_configs)}
• Active configs: {len(active_configs)}
• Inactive configs: {len(all_configs) - len(active_configs)}

📋 **Config Details:**
"""
            
            if all_configs:
                for i, config in enumerate(all_configs[:3]):  # Show first 3
                    status = "🟢" if config['is_active'] else "⚪"
                    debug_text += f"""
{i+1}. {status} **Config #{config['id']}**
   📥 Source: {config['source_channel_name']} (`{config['source_channel_id']}`)
   📤 Target: {config['target_channel_name']} (`{config['target_channel_id']}`)"""
                
                if len(all_configs) > 3:
                    debug_text += f"\n... và {len(all_configs) - 3} config khác"
            else:
                debug_text += "\n❌ Không có config nào"
            
            # Add specific troubleshooting for peer ID issues
            debug_text += f"""

🛠️ **Troubleshooting Channel Issues:**
• **Peer ID Invalid:** Dùng `/test_channels` để kiểm tra
• **No configs found:** Tạo config mới trong menu
• **Client disconnected:** Thử `/recover`
• **Permission denied:** Kiểm tra quyền access channel

📱 **Useful Commands:**
• `/test_channels` - Test tất cả channel access
• `/recover` - Khôi phục session
• `/status` - Kiểm tra trạng thái chi tiết

💡 **Quick Fix:**
1. Dùng `/test_channels` để tìm channels có vấn đề
2. Xóa config có channel lỗi
3. Tạo lại config với channels hoạt động
"""
            
            await update.message.reply_text(debug_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Debug error:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def test_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test channel access cho tất cả configs của user"""
        user_id = update.effective_user.id
        
        try:
            # Get user configs
            all_configs = self.db.get_all_user_configs(user_id)
            
            if not all_configs:
                await update.message.reply_text(
                    "❌ **Không có cấu hình nào để test!**\n\nHãy tạo cấu hình trước.",
                    parse_mode='Markdown'
                )
                return
            
            # Get or restore client
            client = await self.get_or_restore_client(user_id)
            
            if not client:
                await update.message.reply_text(
                    "❌ **Không tìm thấy client!**\n\nVui lòng đăng nhập lại.",
                    parse_mode='Markdown'
                )
                return
            
            test_msg = await update.message.reply_text(
                "🧪 **ĐANG TEST CHANNEL ACCESS...**\n\n⏳ Vui lòng chờ...",
                parse_mode='Markdown'
            )
            
            results = []
            
            for i, config in enumerate(all_configs):
                try:
                    progress = f"🧪 **TESTING CHANNELS ({i+1}/{len(all_configs)})**\n\n"
                    
                    source_id = int(config['source_channel_id'])
                    target_id = int(config['target_channel_id'])
                    
                    progress += f"📋 **Config #{config['id']}:**\n"
                    progress += f"📥 Source: {config['source_channel_name']}\n"
                    progress += f"📤 Target: {config['target_channel_name']}\n\n"
                    
                    progress += f"🔍 Testing source channel..."
                    
                    await test_msg.edit_text(progress, parse_mode='Markdown')
                    
                    # Test source channel
                    source_result = "❌ Failed"
                    try:
                        source_chat = await client._validate_channel_access(source_id, "source", retry=False)
                        if source_chat:
                            source_result = f"✅ OK: {getattr(source_chat, 'title', 'Unknown')}"
                        else:
                            source_result = "❌ Not accessible"
                    except Exception as e:
                        source_result = f"❌ Error: {str(e)[:50]}..."
                    
                    progress += f"\n📥 Source: {source_result}"
                    progress += f"\n🔍 Testing target channel..."
                    
                    await test_msg.edit_text(progress, parse_mode='Markdown')
                    
                    # Test target channel
                    target_result = "❌ Failed"
                    try:
                        target_chat = await client._validate_channel_access(target_id, "target", retry=False)
                        if target_chat:
                            target_result = f"✅ OK: {getattr(target_chat, 'title', 'Unknown')}"
                        else:
                            target_result = "❌ Not accessible"
                    except Exception as e:
                        target_result = f"❌ Error: {str(e)[:50]}..."
                    
                    progress += f"\n📤 Target: {target_result}"
                    
                    await test_msg.edit_text(progress, parse_mode='Markdown')
                    await asyncio.sleep(1)  # Small delay
                    
                    # Store results
                    config_result = {
                        'config_id': config['id'],
                        'source_name': config['source_channel_name'],
                        'target_name': config['target_channel_name'],
                        'source_result': source_result,
                        'target_result': target_result,
                        'both_ok': '✅' in source_result and '✅' in target_result
                    }
                    results.append(config_result)
                    
                except Exception as config_error:
                    print(f"Error testing config {config['id']}: {config_error}")
                    results.append({
                        'config_id': config['id'],
                        'source_name': config['source_channel_name'],
                        'target_name': config['target_channel_name'],
                        'source_result': f"❌ Test error: {str(config_error)[:30]}...",
                        'target_result': "❌ Skipped",
                        'both_ok': False
                    })
            
            # Generate final report
            working_configs = len([r for r in results if r['both_ok']])
            
            final_report = f"""
🧪 **CHANNEL ACCESS TEST HOÀN TẤT**

📊 **Tổng kết:**
• Tổng cộng: {len(results)} cấu hình
• Hoạt động tốt: {working_configs} cấu hình
• Có vấn đề: {len(results) - working_configs} cấu hình

📋 **Chi tiết:**

"""
            
            for result in results[:5]:  # Show first 5
                status = "🟢" if result['both_ok'] else "🔴"
                final_report += f"""
{status} **Config #{result['config_id']}**
📥 {result['source_name']}: {result['source_result'][:40]}{'...' if len(result['source_result']) > 40 else ''}
📤 {result['target_name']}: {result['target_result'][:40]}{'...' if len(result['target_result']) > 40 else ''}
"""
            
            if len(results) > 5:
                final_report += f"\n... và {len(results) - 5} config khác"
            
            if working_configs == 0:
                final_report += f"""

❌ **KHÔNG CÓ CONFIG NÀO HOẠT ĐỘNG!**

🛠️ **Khắc phục:**
1. Kiểm tra quyền truy cập channels
2. Đảm bảo bot được add vào channels
3. Thử /recover để khôi phục session
4. Tạo lại config với channels hợp lệ
"""
            elif working_configs < len(results):
                final_report += f"""

⚠️ **MỘT SỐ CONFIG CÓ VẤN ĐỀ**

💡 **Gợi ý:**
• Kiểm tra quyền access cho channels bị lỗi
• Xóa và tạo lại config có vấn đề
• Đảm bảo channels vẫn tồn tại
"""
            else:
                final_report += f"""

🎉 **TẤT CẢ CONFIGS ĐỀU HOẠT ĐỘNG TỐT!**

✅ Sẵn sàng bắt đầu copy channels!
"""
            
            await test_msg.edit_text(final_report, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Error testing channels:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def sync_auth_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Đồng bộ authentication status nếu client đang hoạt động nhưng database chưa cập nhật"""
        user_id = update.effective_user.id
        
        try:
            # Check if user has active client
            if user_id not in self.user_clients:
                await update.message.reply_text(
                    "❌ **Không có client nào đang hoạt động!**\n\nVui lòng đăng nhập hoặc dùng `/recover` trước.",
                    parse_mode='Markdown'
                )
                return
            
            client = self.user_clients[user_id]
            
            if not client or not client.client or not client.client.is_connected:
                await update.message.reply_text(
                    "❌ **Client không kết nối!**\n\nThử `/recover` để khôi phục session.",
                    parse_mode='Markdown'
                )
                return
            
            sync_msg = await update.message.reply_text(
                "🔄 **ĐANG ĐỒNG BỘ AUTHENTICATION STATUS...**",
                parse_mode='Markdown'
            )
            
            try:
                # Test client connection và get user info
                me = await client.client.get_me()
                phone_number = me.phone_number if hasattr(me, 'phone_number') else None
                
                # Update authentication status in database
                self.db.update_user_auth(user_id, True, phone_number)
                self.db.update_user_last_active(user_id)
                
                # Verify the update worked
                user_data = self.db.get_user(user_id)
                
                await sync_msg.edit_text(
                    f"""
✅ **ĐỒNG BỘ THÀNH CÔNG!**

👤 **Thông tin tài khoản:**
• Tên: {me.first_name} {getattr(me, 'last_name', '') or ''}
• Phone: {phone_number or 'N/A'}
• User ID: {me.id}
• Username: @{me.username or 'N/A'}

📊 **Database status:**
• Authenticated: {'✅' if user_data and user_data.get('is_authenticated') else '❌'}
• Last Active: {user_data.get('last_active', 'N/A') if user_data else 'N/A'}

🎉 **Sẵn sàng sử dụng bot!** Bây giờ bạn có thể:
• Tạo cấu hình copy channel
• Xem danh sách cấu hình
• Bắt đầu copy tin nhắn

💡 Nhấn /start để mở menu chính
                    """,
                    parse_mode='Markdown'
                )
                
            except Exception as client_error:
                await sync_msg.edit_text(
                    f"""
❌ **ĐỒNG BỘ THẤT BẠI!**

🔍 **Lỗi client:** {str(client_error)}

🛠️ **Khắc phục:**
1. Thử `/recover` để khôi phục session
2. Đăng xuất và đăng nhập lại
3. Kiểm tra kết nối internet

💡 Client có thể cần được khởi động lại.
                    """,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi đồng bộ:** {str(e)}",
                parse_mode='Markdown'
            )
    
    async def force_session_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force check và sử dụng session đã có trong database"""
        user_id = update.effective_user.id
        
        try:
            check_msg = await update.message.reply_text(
                "🔍 **ĐANG KIỂM TRA SESSION ĐÃ LƯU...**",
                parse_mode='Markdown'
            )
            
            # Kiểm tra user trong database
            user = self.db.get_user(user_id)
            session_data = self.db.get_user_session(user_id)
            
            if not user:
                await check_msg.edit_text(
                    "❌ **Không tìm thấy thông tin user trong database**\n\nVui lòng đăng nhập bằng /start",
                    parse_mode='Markdown'
                )
                return
            
            if not session_data or not session_data.get('session_string'):
                await check_msg.edit_text(
                    "❌ **Không có session nào được lưu**\n\nVui lòng đăng nhập bằng /start",
                    parse_mode='Markdown'
                )
                return
            
            # Cập nhật message
            await check_msg.edit_text(
                "🔄 **ĐÃ TÌM THẤY SESSION - ĐANG KHÔI PHỤC...**",
                parse_mode='Markdown'
            )
            
            # Force restore session
            if user_id in self.user_clients:
                # Disconnect existing client first
                try:
                    old_client = self.user_clients[user_id]
                    if old_client.client:
                        await old_client.client.stop()
                except:
                    pass
                del self.user_clients[user_id]
            
            # Create new client from saved session
            client = TelegramClient(
                user_id,
                session_data['api_id'],
                session_data['api_hash'],
                session_data['session_string']
            )
            
            client.set_bot_instance(self)
            success = await client.initialize_client()
            
            if success:
                self.user_clients[user_id] = client
                
                # Update authentication status
                try:
                    me = await client.client.get_me()
                    phone_number = me.phone_number if hasattr(me, 'phone_number') else user.get('phone_number')
                    self.db.update_user_auth(user_id, True, phone_number)
                    self.db.update_user_last_active(user_id)
                    
                    # Restore active configs
                    await self.restore_active_configs(user_id)
                    
                    await check_msg.edit_text(
                        f"""
✅ **SESSION ĐÃ ĐƯỢC KHÔI PHỤC THÀNH CÔNG!**

👤 **Tài khoản:** {me.first_name} {getattr(me, 'last_name', '') or ''}
📱 **Số ĐT:** {phone_number or 'N/A'}
🆔 **User ID:** {me.id}

🎉 **Bot sẵn sàng sử dụng!**

💡 **Bây giờ bạn có thể:**
• Tạo cấu hình copy channel
• Bắt đầu copy tin nhắn  
• Quản lý cấu hình hiện có

🚀 Nhấn /start để mở menu chính!
                        """,
                        parse_mode='Markdown'
                    )
                    
                except Exception as me_error:
                    await check_msg.edit_text(
                        f"""
⚠️ **SESSION KHÔI PHỤC NHƯNG CÓ LỖI NHỎ**

✅ **Client đã kết nối thành công**
❌ **Không thể lấy thông tin user:** {str(me_error)}

🔧 **Thử lại:** `/sync_auth` để đồng bộ authentication status
                        """,
                        parse_mode='Markdown'
                    )
            else:
                await check_msg.edit_text(
                    """
❌ **KHÔNG THỂ KHÔI PHỤC SESSION**

🔍 **Nguyên nhân có thể:**
• Session đã hết hạn hoặc bị thu hồi
• Tài khoản bị khóa
• Lỗi kết nối mạng

🔧 **Khắc phục:**
1. Thử lại sau vài phút
2. Đăng nhập lại bằng /start  
3. Liên hệ support nếu vẫn lỗi
                    """,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Lỗi force check session:** {str(e)}",
                parse_mode='Markdown'
            )
    
    def run(self):
        """Chạy bot"""
        application = Application.builder().token(self.bot_token).build()
        
        # Set bot instance for message processing
        self.set_bot_instance(application.bot)
        
        # Import button handler từ bot.main_handlers
        from bot.main_handlers import create_button_handler
        button_handler = create_button_handler(self)
        
        # Conversation handler cho tất cả chức năng
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start),
                CallbackQueryHandler(button_handler)
            ],
            states={
                WAITING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handlers.handle_phone_input)],
                WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handlers.handle_code_input)],
                WAITING_2FA_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handlers.handle_2fa_password)],
                WAITING_EXTRACT_PATTERN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.config_handlers.handle_extract_pattern)],
                WAITING_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_header_input)],
                WAITING_FOOTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_footer_input)],
                WAITING_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_button_text_input)],
                WAITING_BUTTON_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_button_url_input)],
            },
            fallbacks=[
                CommandHandler('start', self.start),
                CommandHandler('logout', self.auth_handlers.logout),
                CommandHandler('status', self.auth_handlers.status),
                CommandHandler('recover', self.auth_handlers.recover_session),
                CallbackQueryHandler(button_handler)
            ],
            per_message=False
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("logout", self.auth_handlers.logout))
        application.add_handler(CommandHandler("status", self.auth_handlers.status))
        application.add_handler(CommandHandler("recover", self.auth_handlers.recover_session))
        application.add_handler(CommandHandler("debug", self.debug_configs))
        application.add_handler(CommandHandler("test_channels", self.test_channels))
        application.add_handler(CommandHandler("sync_auth", self.sync_auth_status))
        application.add_handler(CommandHandler("force_session_check", self.force_session_check))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Khởi tạo async sau khi application được tạo
        async def post_init(app):
            await self.init_async()
        
        # Cleanup function
        async def post_shutdown(app):
            await self.message_processor.shutdown()
        
        application.post_init = post_init
        application.post_shutdown = post_shutdown
        
        # Run bot
        print("🤖 Bot đang chạy...")
        print("📋 Các lệnh có sẵn:")
        print("   /start - Bắt đầu sử dụng bot")
        print("   /status - Kiểm tra trạng thái đăng nhập")
        print("   /logout - Đăng xuất tài khoản")
        print("   /recover - Khôi phục session (nếu bị lỗi)")
        print("   /debug - Xem thông tin debug và troubleshooting")
        print("   /test_channels - Kiểm tra quyền truy cập channels")
        print("   /sync_auth - Đồng bộ authentication status")
        print("   /force_session_check - Force check và sử dụng session đã có")
        print("📨 Message processor ready!")
        application.run_polling() 