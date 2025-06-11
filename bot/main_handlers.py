from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils.states import *

def create_button_handler(bot_instance):
    """Tạo button handler với tất cả logic routing"""
    
    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler chính cho tất cả callback buttons"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Khởi tạo temp_data cho user nếu chưa có
        if user_id not in bot_instance.temp_data:
            bot_instance.temp_data[user_id] = {}
        
        # Xử lý các callback khác nhau
        if data == "main_menu":
            await bot_instance.show_main_menu(query)
        
        elif data == "login":
            await bot_instance.auth_handlers.show_login_menu(query)
        
        elif data == "enter_phone":
            return await bot_instance.auth_handlers.request_phone_number(query)
        
        elif data == "enter_code":
            return await bot_instance.auth_handlers.request_verification_code(query)
        
        elif data == "setup_config":
            await bot_instance.config_handlers.show_config_menu(query)
        
        elif data == "select_source_channel":
            await bot_instance.channel_manager.show_channel_selection(query, "source")
            
        elif data == "select_target_channel":
            await bot_instance.channel_manager.show_channel_selection(query, "target")
        
        elif data.startswith("select_channel_"):
            await bot_instance.channel_manager.handle_channel_selection(query, data)
        
        elif data.startswith("channel_page_"):
            # Xử lý pagination cho channel selection
            page = int(data.split("_")[2])
            await bot_instance.channel_manager.show_channel_selection_page(query, page)
        
        elif data == "current_page":
            # Không làm gì khi nhấn vào số trang hiện tại
            pass
        
        elif data == "setup_extract_pattern":
            await bot_instance.handlers.request_extract_pattern(query)
            return WAITING_EXTRACT_PATTERN
        
        elif data == "setup_header_footer":
            await bot_instance.handlers.show_header_footer_menu(query)
        
        elif data == "setup_header":
            await bot_instance.handlers.request_header_text(query)
            return WAITING_HEADER
        
        elif data == "setup_footer":
            await bot_instance.handlers.request_footer_text(query)
            return WAITING_FOOTER
        
        elif data == "setup_button":
            await bot_instance.handlers.show_button_menu(query)
        
        elif data == "setup_button_text":
            await bot_instance.handlers.request_button_text(query)
            return WAITING_BUTTON_TEXT
        
        elif data == "setup_button_url":
            await bot_instance.handlers.request_button_url(query)
            return WAITING_BUTTON_URL
        
        elif data == "save_config":
            await bot_instance.handlers.save_configuration(query)
        
        elif data == "list_configs":
            await bot_instance.config_handlers.show_user_configs(query)
        
        elif data.startswith("view_config_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.show_config_details(query, config_id)
        
        elif data.startswith("delete_config_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.delete_configuration(query, config_id)
        
        elif data.startswith("delete_permanent_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.delete_configuration_permanent(query, config_id)
        
        elif data.startswith("delete_disable_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.delete_configuration_disable(query, config_id)
        
        elif data.startswith("start_config_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.start_copying_config(query, config_id)
        
        elif data.startswith("stop_config_"):
            config_id = int(data.split("_")[2])
            await bot_instance.handlers.stop_copying_config(query, config_id)
        
        elif data == "start_copying":
            await bot_instance.handlers.start_all_copying(query)
        
        elif data == "stop_copying":
            await bot_instance.handlers.stop_all_copying(query)
        
        elif data == "help":
            await bot_instance.config_handlers.show_help(query)
        
        elif data == "check_status":
            await bot_instance.auth_handlers.show_status_callback(query)
        
        elif data == "logout_account":
            await bot_instance.auth_handlers.logout_callback(query)
        
        elif data == "recover":
            await bot_instance.auth_handlers.recover_session(update, context)
        
        return ConversationHandler.END
    
    return button_handler 