from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import SessionPasswordNeeded, PeerIdInvalid, ChatAdminRequired
from pyrogram.enums import ChatType
import asyncio
import re
import os
import shutil
from typing import Dict, List, Optional
from bot.utils.database import Database
from datetime import datetime

class TelegramClient:
    def __init__(self, user_id: int, api_id: int, api_hash: str, session_string: str = None, bot_instance=None):
        self.user_id = user_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.client = None
        self.db = Database()
        self.active_configs = {}
        self.running_tasks = {}
        self.peer_cache = {}  # Cache for peer information
        self.bot_instance = bot_instance  # Reference to main bot for message queue
        self.session_name = f"sessions/user_{self.user_id}"
        
        # Tạo thư mục sessions nếu chưa có
        os.makedirs("sessions", exist_ok=True)
    
    def set_bot_instance(self, bot_instance):
        """Set reference to main bot instance"""
        self.bot_instance = bot_instance
    
    def backup_session_file(self):
        """Backup session file trước khi thực hiện operations có rủi ro"""
        try:
            session_file = f"{self.session_name}.session"
            if os.path.exists(session_file):
                backup_file = f"{session_file}.backup"
                shutil.copy2(session_file, backup_file)
                print(f"📋 Session file backed up: {backup_file}")
                return True
        except Exception as e:
            print(f"⚠️ Failed to backup session file: {e}")
        return False
    
    def restore_session_file(self):
        """Khôi phục session file từ backup"""
        try:
            session_file = f"{self.session_name}.session"
            backup_file = f"{session_file}.backup"
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, session_file)
                print(f"📋 Session file restored from backup")
                return True
        except Exception as e:
            print(f"⚠️ Failed to restore session file: {e}")
        return False

    def convert_message_to_dict(self, message: Message) -> Dict:
        """Convert pyrogram message to dictionary format"""
        message_dict = {
            'message_id': message.id,
            'text': getattr(message, 'text', None),
            'caption': getattr(message, 'caption', None),
            'date': message.date.isoformat() if hasattr(message, 'date') and message.date else None
        }
        
        # Handle different media types
        if hasattr(message, 'photo') and message.photo:
            message_dict['photo'] = {
                'file_id': message.photo.file_id,
                'file_unique_id': message.photo.file_unique_id,
                'width': message.photo.width,
                'height': message.photo.height,
                'file_size': getattr(message.photo, 'file_size', None)
            }
        
        if hasattr(message, 'video') and message.video:
            message_dict['video'] = {
                'file_id': message.video.file_id,
                'file_unique_id': message.video.file_unique_id,
                'width': message.video.width,
                'height': message.video.height,
                'duration': message.video.duration,
                'file_size': getattr(message.video, 'file_size', None)
            }
        
        if hasattr(message, 'document') and message.document:
            message_dict['document'] = {
                'file_id': message.document.file_id,
                'file_unique_id': message.document.file_unique_id,
                'file_name': getattr(message.document, 'file_name', None),
                'mime_type': getattr(message.document, 'mime_type', None),
                'file_size': getattr(message.document, 'file_size', None)
            }
        
        if hasattr(message, 'audio') and message.audio:
            message_dict['audio'] = {
                'file_id': message.audio.file_id,
                'file_unique_id': message.audio.file_unique_id,
                'duration': message.audio.duration,
                'performer': getattr(message.audio, 'performer', None),
                'title': getattr(message.audio, 'title', None),
                'file_size': getattr(message.audio, 'file_size', None)
            }
        
        if hasattr(message, 'voice') and message.voice:
            message_dict['voice'] = {
                'file_id': message.voice.file_id,
                'file_unique_id': message.voice.file_unique_id,
                'duration': message.voice.duration,
                'file_size': getattr(message.voice, 'file_size', None)
            }
        
        if hasattr(message, 'sticker') and message.sticker:
            message_dict['sticker'] = {
                'file_id': message.sticker.file_id,
                'file_unique_id': message.sticker.file_unique_id,
                'width': message.sticker.width,
                'height': message.sticker.height,
                'is_animated': getattr(message.sticker, 'is_animated', False),
                'file_size': getattr(message.sticker, 'file_size', None)
            }
        
        return message_dict
    
    async def initialize_client(self):
        """Khởi tạo Pyrogram client với persistent session - KHÔNG TẠO SESSION MỚI"""
        try:
            print(f"🔄 Initializing client for user {self.user_id}...")
            
            # Kiểm tra session file đã có sẵn
            session_file = f"{self.session_name}.session"
            has_session_file = os.path.exists(session_file)
            has_session_string = self.session_string is not None
            
            print(f"📁 Session file exists: {has_session_file}")
            print(f"🔗 Session string available: {has_session_string}")
            
            # QUAN TRỌNG: Luôn ưu tiên session file đã có
            if has_session_file:
                print(f"✅ Using existing session file for user {self.user_id}")
                # Backup session database và file trước khi sử dụng
                self.db.backup_session(self.user_id, "Before using existing session file")
                self.backup_session_file()
                
                # Tạo client với session file có sẵn (KHÔNG dùng session_string)
                self.client = Client(
                    self.session_name,
                    api_id=self.api_id,
                    api_hash=self.api_hash,
                    workdir="."  # Dùng session file trong thư mục hiện tại
                )
                
            elif has_session_string:
                print(f"🔗 Using session string for user {self.user_id}")
                # Backup session database trước khi tạo từ session string
                self.db.backup_session(self.user_id, "Before creating from session string")
                
                # Tạo client từ session string (chỉ khi KHÔNG có session file)
                self.client = Client(
                    self.session_name,
                    api_id=self.api_id,
                    api_hash=self.api_hash,
                    session_string=self.session_string,
                    workdir="."
                )
                
            else:
                print(f"❌ No session data available for user {self.user_id}")
                return False

            # Khởi động client với retry mechanism và session validation
            max_retries = 2  # Giảm retry để tránh spam
            for attempt in range(max_retries):
                try:
                    print(f"🔌 Connecting attempt {attempt + 1}/{max_retries}...")
                    await self.client.start()
                    break
                except Exception as start_error:
                    error_str = str(start_error).lower()
                    print(f"⚠️ Connection attempt {attempt + 1} failed: {start_error}")
                    
                    # Kiểm tra lỗi nghiêm trọng
                    if any(critical in error_str for critical in [
                        'auth_key_invalid', 'user_deactivated', 'account_banned',
                        'session_revoked', 'unauthorized', 'session_expired'
                    ]):
                        print(f"🔴 Critical auth error detected: {start_error}")
                        # Xóa session bị lỗi
                        self.cleanup_invalid_session()
                        return False
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3)  # Tăng delay
                    else:
                        print(f"❌ All connection attempts failed for user {self.user_id}")
                        return False

            # Validate connection
            try:
                me = await self.client.get_me()
                print(f"✅ Client connected successfully for {me.first_name} (ID: {me.id})")
                
                # QUAN TRỌNG: Chỉ cập nhật session string nếu cần thiết
                if not has_session_file or not self.session_string:
                    try:
                        current_session_string = await self.client.export_session_string()
                        if current_session_string:
                            self.session_string = current_session_string
                            self.db.save_user_session(self.user_id, current_session_string, self.api_id, self.api_hash)
                            print(f"💾 Session string saved for user {self.user_id}")
                        else:
                            print(f"⚠️ Could not export session string for user {self.user_id}")
                    except Exception as save_error:
                        print(f"⚠️ Warning - cannot save session string: {save_error}")
                        # Không fail vì client đã connect thành công
                else:
                    print(f"ℹ️ Session already exists, no need to update for user {self.user_id}")
                    
            except Exception as validate_error:
                print(f"❌ Client validation failed: {validate_error}")
                return False

            # Pre-cache dialogs để tránh peer resolution errors
            await self._cache_dialogs()

            return True
            
        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ Error initializing client for user {self.user_id}: {e}")
            
            # Phân loại lỗi để quyết định có nên báo fail không
            critical_errors = [
                'auth_key_invalid', 'user_deactivated', 'account_banned',
                'session_revoked', 'unauthorized', 'session_password_needed',
                'phone_number_invalid', 'session_expired'
            ]
            
            if any(error in error_str for error in critical_errors):
                print(f"🔴 Critical authentication error: {e}")
                self.cleanup_invalid_session()
                return False
            else:
                print(f"⚠️ Non-critical error, session might still be recoverable")
                return False
    
    def cleanup_invalid_session(self):
        """Dọn dẹp session không hợp lệ"""
        try:
            # Xóa session file
            session_file = f"{self.session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
                print(f"🗑️ Removed invalid session file: {session_file}")
            
            # Clear session from database
            self.db.clear_user_session(self.user_id, "Invalid session cleanup")
            
        except Exception as e:
            print(f"⚠️ Error cleaning up session: {e}")
    
    async def _cache_dialogs(self):
        """Cache dialog information to avoid peer resolution errors với improved functionality"""
        try:
            print(f"📱 Refreshing dialog cache for user {self.user_id}...")
            dialog_count = 0
            channel_count = 0
            
            # Clear existing cache
            self.peer_cache.clear()
            
            async for dialog in self.client.get_dialogs():
                try:
                    if hasattr(dialog.chat, 'id'):
                        chat_id = dialog.chat.id
                        chat_title = getattr(dialog.chat, 'title', getattr(dialog.chat, 'first_name', 'Unknown'))
                        chat_username = getattr(dialog.chat, 'username', '')
                        chat_type = str(getattr(dialog.chat, 'type', 'unknown')).split('.')[-1].lower()
                        
                        # Cache all dialogs but prioritize channels and groups
                        cache_entry = {
                            'title': chat_title,
                            'username': chat_username,
                            'type': chat_type,
                            'cached_at': datetime.now().isoformat()
                        }
                        
                        self.peer_cache[chat_id] = cache_entry
                        dialog_count += 1
                        
                        # Count channels/groups specifically
                        if chat_type in ['channel', 'supergroup', 'group']:
                            channel_count += 1
                            
                        # Limit cache size to prevent memory issues
                        if dialog_count >= 200:  # Increased limit
                            print(f"📱 Cache limit reached, stopping at {dialog_count} dialogs")
                            break
                            
                except Exception as dialog_error:
                    print(f"⚠️ Error caching dialog: {dialog_error}")
                    continue
            
            print(f"📱 Successfully cached {dialog_count} dialogs ({channel_count} channels/groups) for user {self.user_id}")
            
            # Save cache to database for persistence across restarts
            try:
                cache_data = {
                    'user_id': self.user_id,
                    'cache_count': dialog_count,
                    'channel_count': channel_count,
                    'cached_at': datetime.now().isoformat()
                }
                # You could implement cache persistence here if needed
                print(f"💾 Cache statistics saved: {cache_data}")
            except Exception as save_error:
                print(f"⚠️ Could not save cache statistics: {save_error}")
                
        except Exception as e:
            print(f"❌ Error caching dialogs for user {self.user_id}: {e}")
            # Don't raise the error, just log it
    
    async def login_with_phone(self, phone_number: str):
        """Đăng nhập bằng số điện thoại với improved session handling"""
        try:
            # Backup session trước khi login
            self.backup_session_file()
            
            self.client = Client(
                self.session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                workdir="."  # Sử dụng session file
            )
            
            await self.client.connect()
            code = await self.client.send_code(phone_number)
            return code.phone_code_hash
        except Exception as e:
            print(f"❌ Error sending code: {e}")
            # Thử restore session nếu có lỗi
            self.restore_session_file()
            return None
    
    async def verify_code(self, phone_number: str, phone_code_hash: str, code: str):
        """Xác thực mã OTP với improved session saving"""
        try:
            await self.client.sign_in(phone_number, phone_code_hash, code)
            
            # Lưu session string và file
            session_string = await self.client.export_session_string()
            self.session_string = session_string
            self.db.save_user_session(self.user_id, session_string, self.api_id, self.api_hash)
            self.db.update_user_auth(self.user_id, True, phone_number)
            
            # Backup session file sau khi login thành công
            self.backup_session_file()
            
            print(f"✅ Login successful for user {self.user_id}")
            return True
            
        except SessionPasswordNeeded:
            # Pyrogram specific exception for 2FA
            print("2FA required for authentication")
            return "2fa_required"
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error verifying code: {error_msg}")
            
            # Fallback check for string-based detection
            if "SESSION_PASSWORD_NEEDED" in error_msg or "Two-step verification" in error_msg:
                return "2fa_required"
            
            return False
    
    async def verify_2fa_password(self, password: str):
        """Xác thực mật khẩu 2FA với improved session backup"""
        try:
            await self.client.check_password(password)
            
            # Lưu session string sau khi xác thực 2FA thành công
            session_string = await self.client.export_session_string()
            self.session_string = session_string
            self.db.save_user_session(self.user_id, session_string, self.api_id, self.api_hash)
            
            # Lấy thông tin user để có phone number
            user_data = self.db.get_user(self.user_id)
            phone_number = user_data.get('phone_number', '') if user_data else ''
            self.db.update_user_auth(self.user_id, True, phone_number)
            
            # Backup session file sau khi 2FA thành công
            self.backup_session_file()
            
            print(f"✅ 2FA verification successful for user {self.user_id}")
            return True
        except Exception as e:
            print(f"❌ Error verifying 2FA password: {e}")
            return False
    
    async def get_dialogs(self):
        """Lấy danh sách chat/channel"""
        try:
            if not self.client:
                await self.initialize_client()
            
            # Đảm bảo client đã sẵn sàng
            if not self.client.is_connected:
                await self.client.start()
            
            dialogs = []
            all_dialogs = []  # For debugging
            
            async for dialog in self.client.get_dialogs():
                try:
                    # Get title safely
                    title = getattr(dialog.chat, 'title', None)
                    if not title:
                        title = getattr(dialog.chat, 'first_name', 'Unknown')
                    
                    # Collect all dialogs for debugging
                    all_dialogs.append({
                        'id': dialog.chat.id,
                        'title': title,
                        'type': str(dialog.chat.type).split('.')[-1].lower()  # Convert enum to string
                    })
                    
                    # Include channels, supergroups, and groups using ChatType enum
                    if dialog.chat.type in [ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP]:
                        dialog_info = {
                            'id': dialog.chat.id,
                            'title': title,
                            'username': getattr(dialog.chat, 'username', None),
                            'type': str(dialog.chat.type).split('.')[-1].lower()  # Convert enum to string
                        }
                        dialogs.append(dialog_info)
                        
                        # Cache the dialog for future reference
                        self.peer_cache[dialog.chat.id] = dialog_info
                        
                except Exception as dialog_error:
                    print(f"Error processing dialog {getattr(dialog.chat, 'id', 'unknown')}: {dialog_error}")
                    continue
            
            # Debug information
            print(f"Debug: Found {len(all_dialogs)} total dialogs:")
            for d in all_dialogs[:10]:  # Show first 10 for debugging
                print(f"  - {d['title']} ({d['type']}) - ID: {d['id']}")
            
            if len(all_dialogs) > 10:
                print(f"  ... and {len(all_dialogs) - 10} more")
            
            print(f"Debug: Filtered to {len(dialogs)} channels/groups/supergroups")
            
            # If no channels found, try including private chats for testing
            if not dialogs:
                print("No channels/groups found, including all chat types for debugging...")
                async for dialog in self.client.get_dialogs():
                    try:
                        # Get title safely
                        title = getattr(dialog.chat, 'title', None)
                        if not title:
                            title = getattr(dialog.chat, 'first_name', 'Unknown Chat')
                        
                        dialog_info = {
                            'id': dialog.chat.id,
                            'title': title,
                            'username': getattr(dialog.chat, 'username', None),
                            'type': str(dialog.chat.type).split('.')[-1].lower()
                        }
                        dialogs.append(dialog_info)
                        self.peer_cache[dialog.chat.id] = dialog_info
                    except Exception as dialog_error:
                        print(f"Error processing dialog: {dialog_error}")
                        continue
                
                print(f"Debug: Now showing all {len(dialogs)} chats (including private)")
            
            return dialogs
        except Exception as e:
            print(f"Error getting dialogs: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def start_copying(self, config: Dict):
        """Bắt đầu copy tin nhắn từ channel nguồn sang channel đích với improved error handling"""
        try:
            if not self.client:
                await self.initialize_client()
            
            source_channel_id = int(config['source_channel_id'])
            target_channel_id = int(config['target_channel_id'])
            config_id = config['id']
            
            print(f"🚀 Debug - Starting copy from {source_channel_id} to {target_channel_id}")
            
            # Kiểm tra xem config đã được active chưa
            if config_id in self.active_configs:
                print(f"⚠️ Config {config_id} is already active, skipping...")
                return True
            
            # Step 1: Validate source channel access with retry and cache refresh
            try:
                print(f"🔍 Validating source channel access: {source_channel_id}")
                source_chat = await self._validate_channel_access(source_channel_id, "source")
                if not source_chat:
                    return False
                    
                print(f"✅ Source channel validated: {getattr(source_chat, 'title', 'Unknown')}")
            except Exception as source_error:
                print(f"❌ Cannot access source channel {source_channel_id}: {source_error}")
                return False
            
            # Step 2: Validate target channel access
            try:
                print(f"🔍 Validating target channel access: {target_channel_id}")
                target_chat = await self._validate_channel_access(target_channel_id, "target")
                if not target_chat:
                    return False
                    
                print(f"✅ Target channel validated: {getattr(target_chat, 'title', 'Unknown')}")
            except Exception as target_error:
                print(f"❌ Cannot access target channel {target_channel_id}: {target_error}")
                return False
            
            # Step 3: Lưu cấu hình đang chạy
            self.active_configs[config_id] = config
            print(f"📋 Debug - Active configs: {list(self.active_configs.keys())}")
            
            # Step 4: Tạo một handler function cho config này
            async def message_handler(client, message: Message):
                try:
                    # Kiểm tra xem config vẫn còn active không
                    if config_id not in self.active_configs:
                        print(f"⚠️ Config {config_id} is no longer active, ignoring message")
                        return
                    
                    print(f"📥 Debug - New message received from {source_channel_id} for config {config_id}")
                    print(f"📝 Debug - Message ID: {message.id}")
                    
                    # Safe string handling for debug logs
                    message_text = getattr(message, 'text', None) or ''
                    message_caption = getattr(message, 'caption', None) or ''
                    
                    print(f"📝 Debug - Message text: '{message_text[:100]}...'")
                    print(f"📝 Debug - Message caption: '{message_caption[:100]}...'")
                    print(f"📝 Debug - Message type: {type(message).__name__}")
                    
                    await self._process_and_copy_message(message, self.active_configs[config_id])
                except PeerIdInvalid as e:
                    print(f"Peer ID invalid when copying message: {e}")
                    # Try to refresh the peer cache
                    await self._cache_dialogs()
                except Exception as e:
                    print(f"Error copying message for config {config_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Step 5: Đăng ký message handler
            handler = self.client.add_handler(
                self.client.on_message(filters.chat(source_channel_id) & ~filters.service)(message_handler)
            )
            
            # Lưu handler reference để có thể remove sau này
            if not hasattr(self, 'message_handlers'):
                self.message_handlers = {}
            self.message_handlers[config_id] = handler
            
            print(f"✅ Started copying from {source_channel_id} to {target_channel_id}")
            print(f"🎯 Debug - Message handler registered for channel {source_channel_id}, config {config_id}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error starting copy: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Classify error types for better handling
            if "peer id invalid" in error_msg.lower():
                print(f"🔍 Peer ID validation error - trying to refresh cache and validate channels")
                # Try to refresh cache and validate again
                try:
                    await self._cache_dialogs()
                    await asyncio.sleep(2)  # Give some time for cache to update
                    
                    # Try to validate channels again
                    source_valid = await self._validate_channel_access(int(config['source_channel_id']), "source", retry=False)
                    target_valid = await self._validate_channel_access(int(config['target_channel_id']), "target", retry=False)
                    
                    if not source_valid:
                        print(f"❌ Source channel {config['source_channel_id']} is not accessible")
                    if not target_valid:
                        print(f"❌ Target channel {config['target_channel_id']} is not accessible")
                        
                except Exception as retry_error:
                    print(f"❌ Retry validation also failed: {retry_error}")
            
            return False
    
    async def _validate_channel_access(self, channel_id: int, channel_type: str = "channel", retry: bool = True):
        """Validate channel access with retry mechanism and improved error handling"""
        max_retries = 3 if retry else 1
        
        for attempt in range(max_retries):
            try:
                print(f"🔍 Attempt {attempt + 1}/{max_retries} to validate {channel_type} channel {channel_id}")
                
                # Try to get chat info
                chat = await self.client.get_chat(channel_id)
                
                # Validate chat type and permissions
                if hasattr(chat, 'type'):
                    chat_type = str(chat.type).lower()
                    if 'channel' not in chat_type and 'group' not in chat_type and 'supergroup' not in chat_type:
                        print(f"⚠️ Invalid chat type for {channel_type}: {chat_type}")
                        return None
                
                # Test if we can actually interact with the channel
                try:
                    if channel_type == "target":
                        # For target channel, check if we can send messages
                        # We don't actually send, just check permissions
                        permissions = getattr(chat, 'permissions', None)
                        if permissions and not getattr(permissions, 'can_send_messages', True):
                            print(f"⚠️ No permission to send messages to target channel {channel_id}")
                            
                    print(f"✅ Channel validation successful for {channel_type} {channel_id}: {getattr(chat, 'title', 'Unknown')}")
                    return chat
                    
                except Exception as perm_error:
                    print(f"⚠️ Permission check failed for {channel_type} {channel_id}: {perm_error}")
                    # Continue anyway, as some permission checks might not be accurate
                    return chat
                
            except PeerIdInvalid:
                print(f"❌ Peer ID invalid for {channel_type} channel {channel_id}")
                if attempt < max_retries - 1:
                    print(f"🔄 Refreshing cache and retrying...")
                    await self._cache_dialogs()
                    await asyncio.sleep(2)
                else:
                    print(f"❌ All attempts failed - channel {channel_id} is not accessible")
                    return None
                    
            except Exception as e:
                error_msg = str(e).lower()
                print(f"❌ Error validating {channel_type} channel {channel_id}: {e}")
                
                # Check for critical errors that shouldn't be retried
                critical_errors = ['banned', 'deleted', 'not found', 'access denied']
                if any(err in error_msg for err in critical_errors):
                    print(f"🔴 Critical error - stopping retries")
                    return None
                
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print(f"❌ All validation attempts failed for {channel_type} channel {channel_id}")
                    return None
        
        return None
    
    async def _process_and_copy_message(self, message: Message, config: Dict):
        """Xử lý và gửi tin nhắn vào queue để bot telegram xử lý"""
        try:
            print(f"🔄 Debug - Processing message {message.id} for config {config['id']}")
            
            if not self.bot_instance:
                print("❌ Bot instance not available for message processing")
                return
            
            print(f"✅ Debug - Bot instance available")
            
            # Convert pyrogram message to dict format
            message_dict = self.convert_message_to_dict(message)
            print(f"📊 Debug - Converted message keys: {list(message_dict.keys())}")
            
            # Tạo data package để gửi vào queue
            message_data = {
                'user_id': self.user_id,
                'config_id': config['id'],
                'message': message_dict,
                'source_channel_id': config['source_channel_id'],
                'target_channel_id': config['target_channel_id']
            }
            
            print(f"📦 Debug - Message data package created")
            print(f"👤 Debug - User ID: {self.user_id}")
            print(f"⚙️ Debug - Config ID: {config['id']}")
            print(f"📥 Debug - Source: {config['source_channel_id']}")
            print(f"📤 Debug - Target: {config['target_channel_id']}")
            
            # Gửi vào message queue để bot telegram xử lý
            await self.bot_instance.add_message_to_queue(message_data)
            
            print(f"📤 Message queued for processing: {message.id}")
                
        except Exception as e:
            print(f"❌ Error queueing message: {e}")
            import traceback
            traceback.print_exc()
    
    async def stop_copying(self, config_id: int):
        """Dừng copy cho một cấu hình"""
        try:
            if config_id not in self.active_configs:
                print(f"⚠️ Config {config_id} is not active")
                return True
            
            # Remove message handler
            if hasattr(self, 'message_handlers') and config_id in self.message_handlers:
                handler = self.message_handlers[config_id]
                self.client.remove_handler(handler)
                del self.message_handlers[config_id]
                print(f"🗑️ Removed message handler for config {config_id}")
            
            # Remove from active configs
            del self.active_configs[config_id]
            print(f"⏹️ Stopped copying for config {config_id}")
            
            return True
        except Exception as e:
            print(f"Error stopping copy for config {config_id}: {e}")
            return False
    
    async def stop_all_copying(self):
        """Dừng tất cả việc copy"""
        try:
            # Stop tất cả configs
            config_ids = list(self.active_configs.keys())
            
            for config_id in config_ids:
                await self.stop_copying(config_id)
            
            print(f"⏹️ Stopped all copying ({len(config_ids)} configs)")
            return True
        except Exception as e:
            print(f"Error stopping all copying: {e}")
            return False
    
    async def test_channel_access(self, channel_id: int):
        """Kiểm tra quyền truy cập channel"""
        try:
            if not self.client:
                await self.initialize_client()
            
            chat = await self.client.get_chat(channel_id)
            return True
        except PeerIdInvalid:
            print(f"Channel {channel_id} not found in peer cache, refreshing...")
            await self._cache_dialogs()
            try:
                chat = await self.client.get_chat(channel_id)
                return True
            except Exception as retry_error:
                print(f"Error accessing channel {channel_id} after cache refresh: {retry_error}")
                return False
        except Exception as e:
            print(f"Error accessing channel {channel_id}: {e}")
            return False 