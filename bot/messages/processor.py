import asyncio
import re
from typing import Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class MessageProcessor:
    def __init__(self, bot_instance):
        self.bot_instance = bot_instance
        self.db = bot_instance.db
        self.message_queue = asyncio.Queue()
        self.processing_task = None
        
    async def init_async(self):
        """Khởi tạo message processor"""
        self.processing_task = asyncio.create_task(self.process_message_queue())
        print("🔄 Message processor started...")
        
    async def process_message_queue(self):
        """Background task để xử lý message queue"""
        while True:
            try:
                # Lấy message từ queue
                message_data = await self.message_queue.get()
                
                if message_data is None:  # Shutdown signal
                    break
                    
                await self.handle_incoming_message(message_data)
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                import traceback
                traceback.print_exc()
    
    async def add_message_to_queue(self, message_data: Dict[str, Any]):
        """Thêm tin nhắn vào queue để xử lý"""
        await self.message_queue.put(message_data)
    
    async def handle_incoming_message(self, message_data: Dict[str, Any]):
        """Xử lý tin nhắn đến từ pyrogram client"""
        try:
            user_id = message_data['user_id']
            config_id = message_data['config_id']
            original_message = message_data['message']
            source_channel_id = message_data['source_channel_id']
            target_channel_id = message_data['target_channel_id']
            
            print(f"📨 Processing message from user {user_id}, config {config_id}")
            print(f"🔍 Debug - Source: {source_channel_id}, Target: {target_channel_id}")
            
            # Safe string handling for debug logs
            message_content = original_message.get('text', '') or original_message.get('caption', '') or ''
            print(f"📄 Debug - Message content: {message_content[:100]}...")
            
            # Lấy cấu hình chi tiết từ database
            configs = self.db.get_user_configs(user_id)
            config = next((c for c in configs if c['id'] == config_id), None)
            
            if not config:
                print(f"❌ Config {config_id} not found for user {user_id}")
                return
            
            print(f"✅ Debug - Config found: {config.get('extract_pattern', 'No pattern')}")
            
            # Áp dụng pattern extraction nếu có
            if config.get('extract_pattern') and config['extract_pattern'].strip():
                pattern = config['extract_pattern']
                print(f"🎯 Debug - Applying pattern: '{pattern}'")
                try:
                    matches = re.findall(pattern, message_content, re.IGNORECASE | re.DOTALL)
                    if matches:
                        message_content = ' '.join(matches)
                        print(f"✅ Debug - Pattern matched: '{message_content[:100]}...'")
                    else:
                        print(f"🔍 No pattern match found, skipping message")
                        original_text = original_message.get('text', '') or original_message.get('caption', '') or ''
                        print(f"🔍 Debug - Original text was: '{original_text[:200]}...'")
                        return  # Không có match thì không copy
                except Exception as e:
                    print(f"❌ Pattern error: {e}")
                    # Nếu pattern lỗi, vẫn gửi tin nhắn gốc
            else:
                print("🔄 Debug - No pattern filter, processing original message")
            
            # Xây dựng tin nhắn cuối cùng
            final_text = ""
            
            # Thêm header nếu có
            if config.get('header_text') and config['header_text'].strip():
                final_text += config['header_text'] + "\n\n"
                print(f"📄 Debug - Added header")
            
            # Thêm nội dung chính
            final_text += message_content
            
            # Thêm footer nếu có
            if config.get('footer_text') and config['footer_text'].strip():
                final_text += "\n\n" + config['footer_text']
                print(f"📄 Debug - Added footer")
            
            print(f"📤 Debug - Final message length: {len(final_text)}")
            print(f"📤 Debug - Final message preview: '{final_text[:200]}...'")
            
            # Tạo inline button nếu có cấu hình
            reply_markup = None
            if (config.get('button_text') and config['button_text'].strip() and 
                config.get('button_url') and config['button_url'].strip()):
                button = InlineKeyboardButton(
                    config['button_text'],
                    url=config['button_url']
                )
                reply_markup = InlineKeyboardMarkup([[button]])
                print(f"🔘 Debug - Added button: {config['button_text']}")
            
            print(f"🚀 Debug - About to send message to {target_channel_id}")
            
            # Gửi tin nhắn qua bot telegram
            await self.send_processed_message(
                target_channel_id=target_channel_id,
                message_data=original_message,
                final_text=final_text,
                reply_markup=reply_markup
            )
            
            print(f"✅ Message processed and sent to {target_channel_id}")
            
        except Exception as e:
            print(f"❌ Error handling incoming message: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_processed_message(self, target_channel_id: int, message_data: Dict, 
                                   final_text: str, reply_markup=None):
        """Gửi tin nhắn đã xử lý đến channel đích qua bot telegram"""
        try:
            if not self.bot_instance.bot_instance:
                print("❌ Bot instance not available")
                return
            
            print(f"🎯 Debug - Sending to channel {target_channel_id}")
            print(f"📊 Debug - Message data keys: {list(message_data.keys())}")
            
            # Xử lý các loại tin nhắn khác nhau
            if message_data.get('photo'):
                print(f"📸 Debug - Sending photo with caption")
                await self.bot_instance.bot_instance.send_photo(
                    chat_id=target_channel_id,
                    photo=message_data['photo']['file_id'],
                    caption=final_text if final_text.strip() else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif message_data.get('video'):
                print(f"🎬 Debug - Sending video with caption")
                await self.bot_instance.bot_instance.send_video(
                    chat_id=target_channel_id,
                    video=message_data['video']['file_id'],
                    caption=final_text if final_text.strip() else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif message_data.get('document'):
                print(f"📎 Debug - Sending document with caption")
                await self.bot_instance.bot_instance.send_document(
                    chat_id=target_channel_id,
                    document=message_data['document']['file_id'],
                    caption=final_text if final_text.strip() else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif message_data.get('audio'):
                print(f"🎵 Debug - Sending audio with caption")
                await self.bot_instance.bot_instance.send_audio(
                    chat_id=target_channel_id,
                    audio=message_data['audio']['file_id'],
                    caption=final_text if final_text.strip() else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif message_data.get('voice'):
                print(f"🎤 Debug - Sending voice note")
                await self.bot_instance.bot_instance.send_voice(
                    chat_id=target_channel_id,
                    voice=message_data['voice']['file_id'],
                    caption=final_text if final_text.strip() else None,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            elif message_data.get('sticker'):
                print(f"🔖 Debug - Sending sticker")
                await self.bot_instance.bot_instance.send_sticker(
                    chat_id=target_channel_id,
                    sticker=message_data['sticker']['file_id'],
                    reply_markup=reply_markup
                )
                # Gửi text riêng nếu có
                if final_text.strip():
                    print(f"💬 Debug - Sending text separately after sticker")
                    await self.bot_instance.bot_instance.send_message(
                        chat_id=target_channel_id,
                        text=final_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
            else:
                print(f"💬 Debug - Sending text message only")
                if final_text.strip():
                    await self.bot_instance.bot_instance.send_message(
                        chat_id=target_channel_id,
                        text=final_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    print(f"⚠️ Debug - No text content to send")
        
        except Exception as e:
            print(f"❌ Error sending processed message: {e}")
            print(f"❌ Debug - Error details: {type(e).__name__}: {str(e)}")
            # Fallback: try to send as plain text without markdown
            try:
                print(f"🔄 Debug - Trying fallback without markdown")
                if final_text.strip():
                    await self.bot_instance.bot_instance.send_message(
                        chat_id=target_channel_id,
                        text=final_text,
                        reply_markup=reply_markup
                    )
                    print(f"✅ Debug - Fallback successful")
            except Exception as fallback_error:
                print(f"❌ Fallback send also failed: {fallback_error}")
                print(f"❌ Debug - Fallback error details: {type(fallback_error).__name__}: {str(fallback_error)}")
    
    async def shutdown(self):
        """Shutdown message processor"""
        print("🔄 Shutting down message processor...")
        if self.processing_task and not self.processing_task.done():
            await self.message_queue.put(None)  # Shutdown signal
            try:
                await asyncio.wait_for(self.processing_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.processing_task.cancel()
        print("✅ Message processor shutdown complete") 