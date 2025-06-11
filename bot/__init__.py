"""
Telegram Channel Copy Bot

A modular Telegram bot for copying messages between channels with advanced features:
- Multi-user support with session management
- Pattern-based message filtering
- Custom headers/footers and buttons
- Channel management with pagination
- Comprehensive error handling and retry mechanisms

Architecture:
- bot.core: Main TelegramBot class
- bot.auth: Authentication handlers
- bot.config: Configuration management
- bot.channels: Channel selection and management
- bot.messages: Message processing and forwarding
- bot.utils: Utility functions and shared components
"""

__version__ = "2.0.0"
__author__ = "TelegramBot Team" 