"""
Authentication module for Telegram Bot

Handles user authentication, phone verification, 2FA, and session management.
"""

from .handlers import AuthHandlers

__all__ = ['AuthHandlers'] 