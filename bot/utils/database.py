import sqlite3
import json
import shutil
import os
from datetime import datetime
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "data/telegram_bot.db"):
        self.db_path = db_path
        self.init_database()
        self.migrate_database()
    
    def init_database(self):
        """Khởi tạo database và tạo các bảng cần thiết"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bảng người dùng
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                is_authenticated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng cấu hình copy channel
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_channel_id TEXT,
                source_channel_name TEXT,
                target_channel_id TEXT,
                target_channel_name TEXT,
                header_text TEXT,
                footer_text TEXT,
                extract_pattern TEXT,
                button_text TEXT,
                button_url TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Bảng session Pyrogram
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER PRIMARY KEY,
                session_string TEXT,
                api_id INTEGER,
                api_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Bảng backup sessions để khôi phục khi cần
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_string TEXT,
                api_id INTEGER,
                api_hash TEXT,
                backup_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def migrate_database(self):
        """Migrate database schema to latest version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Kiểm tra xem cột last_active đã tồn tại chưa
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'last_active' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN last_active TIMESTAMP')
                # Set default values for existing records
                cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE last_active IS NULL')
                print("✅ Added last_active column to users table")
            else:
                print("ℹ️ Column last_active already exists")
                
        except sqlite3.OperationalError as e:
            print(f"Migration error for last_active: {e}")
        
        try:
            # Kiểm tra xem các cột đã tồn tại chưa trong user_sessions
            cursor.execute("PRAGMA table_info(user_sessions)")
            session_columns = [column[1] for column in cursor.fetchall()]
            
            if 'created_at' not in session_columns:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN created_at TIMESTAMP')
                # Set default values for existing records  
                cursor.execute('UPDATE user_sessions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL')
                print("✅ Added created_at column to user_sessions table")
            
            if 'updated_at' not in session_columns:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN updated_at TIMESTAMP')
                # Set default values for existing records
                cursor.execute('UPDATE user_sessions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')
                print("✅ Added updated_at column to user_sessions table")
                
        except sqlite3.OperationalError as e:
            print(f"Migration error for user_sessions: {e}")
        
        # Create session_backups table if not exists
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_backups'")
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE session_backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_string TEXT,
                        api_id INTEGER,
                        api_hash TEXT,
                        backup_reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                print("✅ Created session_backups table")
        except sqlite3.OperationalError as e:
            print(f"Migration error for session_backups: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Database migration completed")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Thêm user mới hoặc cập nhật thông tin user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Lấy thông tin user với error handling tốt hơn"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Lấy thông tin structure của table trước
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                user_dict = {
                    'user_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'phone_number': row[4],
                    'is_authenticated': row[5],
                    'created_at': row[6]
                }
                
                # Thêm last_active nếu có
                if 'last_active' in columns and len(row) > 7:
                    user_dict['last_active'] = row[7]
                else:
                    user_dict['last_active'] = None
                    
                return user_dict
            return None
            
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            return None
        finally:
            conn.close()
    
    def update_user_auth(self, user_id: int, is_authenticated: bool, phone_number: str = None):
        """Cập nhật trạng thái xác thực của user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET is_authenticated = ?, phone_number = ?
            WHERE user_id = ?
        ''', (is_authenticated, phone_number, user_id))
        
        conn.commit()
        conn.close()
    
    def save_channel_config(self, user_id: int, config: Dict[str, Any]):
        """Lưu cấu hình copy channel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO channel_configs 
            (user_id, source_channel_id, source_channel_name, target_channel_id, target_channel_name,
             header_text, footer_text, extract_pattern, button_text, button_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            config.get('source_channel_id'),
            config.get('source_channel_name'),
            config.get('target_channel_id'),
            config.get('target_channel_name'),
            config.get('header_text', ''),
            config.get('footer_text', ''),
            config.get('extract_pattern', ''),
            config.get('button_text', ''),
            config.get('button_url', ''),
            config.get('is_active', True)
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_configs(self, user_id: int):
        """Lấy các cấu hình active của user"""
        return self.get_active_user_configs(user_id)
    
    def get_active_user_configs(self, user_id: int):
        """Lấy các cấu hình active của user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM channel_configs 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        configs = []
        for row in rows:
            configs.append({
                'id': row[0],
                'user_id': row[1],
                'source_channel_id': row[2],
                'source_channel_name': row[3],
                'target_channel_id': row[4],
                'target_channel_name': row[5],
                'header_text': row[6],
                'footer_text': row[7],
                'extract_pattern': row[8],
                'button_text': row[9],
                'button_url': row[10],
                'is_active': row[11],
                'created_at': row[12]
            })
        
        return configs
    
    def get_all_user_configs(self, user_id: int):
        """Lấy tất cả cấu hình của user (bao gồm cả inactive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM channel_configs 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        configs = []
        for row in rows:
            configs.append({
                'id': row[0],
                'user_id': row[1],
                'source_channel_id': row[2],
                'source_channel_name': row[3],
                'target_channel_id': row[4],
                'target_channel_name': row[5],
                'header_text': row[6],
                'footer_text': row[7],
                'extract_pattern': row[8],
                'button_text': row[9],
                'button_url': row[10],
                'is_active': row[11],
                'created_at': row[12]
            })
        
        return configs
    
    def update_config_status(self, config_id: int, user_id: int, is_active: bool):
        """Cập nhật trạng thái active của config"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE channel_configs SET is_active = ? 
            WHERE id = ? AND user_id = ?
        ''', (is_active, config_id, user_id))
        
        conn.commit()
        conn.close()
    
    def save_user_session(self, user_id: int, session_string: str, api_id: int, api_hash: str):
        """Lưu session string của user với automatic backup và better error handling"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Kiểm tra structure của bảng user_sessions
            cursor.execute("PRAGMA table_info(user_sessions)")
            columns = [column[1] for column in cursor.fetchall()]
            has_updated_at = 'updated_at' in columns
            has_created_at = 'created_at' in columns
            
            # Backup existing session trước khi overwrite
            cursor.execute('SELECT session_string FROM user_sessions WHERE user_id = ?', (user_id,))
            existing_session = cursor.fetchone()
            
            if existing_session and existing_session[0]:
                # Backup session cũ
                cursor.execute('''
                    INSERT INTO session_backups (user_id, session_string, api_id, api_hash, backup_reason)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, existing_session[0], api_id, api_hash, "Auto backup before update"))
                print(f"📋 Backed up existing session for user {user_id}")
            
            # Insert or update session với appropriate columns
            if has_updated_at and has_created_at:
                # Full version với timestamps
                cursor.execute('''
                    INSERT OR REPLACE INTO user_sessions (user_id, session_string, api_id, api_hash, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, session_string, api_id, api_hash))
            elif has_created_at:
                # Version với created_at only
                cursor.execute('''
                    INSERT OR REPLACE INTO user_sessions (user_id, session_string, api_id, api_hash, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, session_string, api_id, api_hash))
            else:
                # Basic version without timestamps
                cursor.execute('''
                    INSERT OR REPLACE INTO user_sessions (user_id, session_string, api_id, api_hash)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, session_string, api_id, api_hash))
            
            # Cleanup old backups (keep only last 5 per user)
            cursor.execute('''
                DELETE FROM session_backups 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM session_backups 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 5
                )
            ''', (user_id, user_id))
            
            conn.commit()
            print(f"💾 Session saved for user {user_id}")
            
        except Exception as e:
            print(f"❌ Error saving session for user {user_id}: {e}")
            conn.rollback()
            raise  # Re-raise để caller có thể handle
        finally:
            conn.close()
    
    def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Lấy session của user với fallback to backup"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Try to get current session first
            cursor.execute('SELECT * FROM user_sessions WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row and row[1]:  # session_string exists
                return {
                    'user_id': row[0],
                    'session_string': row[1],
                    'api_id': row[2],
                    'api_hash': row[3],
                    'created_at': row[4] if len(row) > 4 else None,
                    'updated_at': row[5] if len(row) > 5 else None
                }
            
            # If no valid session, try to get from backup
            print(f"⚠️ No valid session found for user {user_id}, checking backups...")
            cursor.execute('''
                SELECT user_id, session_string, api_id, api_hash, created_at, backup_reason
                FROM session_backups 
                WHERE user_id = ? AND session_string IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (user_id,))
            
            backup_row = cursor.fetchone()
            if backup_row and backup_row[1]:
                print(f"📋 Found backup session for user {user_id}: {backup_row[5]}")
                
                # Restore from backup
                restored_session = {
                    'user_id': backup_row[0],
                    'session_string': backup_row[1],
                    'api_id': backup_row[2],
                    'api_hash': backup_row[3]
                }
                
                # Save restored session as current
                self.save_user_session(user_id, backup_row[1], backup_row[2], backup_row[3])
                print(f"✅ Restored session from backup for user {user_id}")
                
                return restored_session
                
        except Exception as e:
            print(f"❌ Error getting session for user {user_id}: {e}")
        finally:
            conn.close()
            
        return None
    
    def delete_config(self, config_id: int, user_id: int):
        """Xóa cấu hình (chỉ set inactive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE channel_configs SET is_active = FALSE 
            WHERE id = ? AND user_id = ?
        ''', (config_id, user_id))

        conn.commit()
        conn.close()
    
    def delete_config_permanently(self, config_id: int, user_id: int):
        """Xóa cấu hình vĩnh viễn khỏi database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM channel_configs 
            WHERE id = ? AND user_id = ?
        ''', (config_id, user_id))

        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows > 0
    
    def get_config_by_id(self, config_id: int, user_id: int):
        """Lấy cấu hình theo ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM channel_configs 
            WHERE id = ? AND user_id = ?
        ''', (config_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'source_channel_id': row[2],
                'source_channel_name': row[3],
                'target_channel_id': row[4],
                'target_channel_name': row[5],
                'header_text': row[6],
                'footer_text': row[7],
                'extract_pattern': row[8],
                'button_text': row[9],
                'button_url': row[10],
                'is_active': row[11],
                'created_at': row[12]
            }
        return None
    
    def get_all_authenticated_users(self):
        """Lấy tất cả users đã xác thực và có session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.phone_number, 
                   s.session_string, s.api_id, s.api_hash
            FROM users u
            JOIN user_sessions s ON u.user_id = s.user_id
            WHERE u.is_authenticated = TRUE AND s.session_string IS NOT NULL
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'phone_number': row[3],
                'session_string': row[4],
                'api_id': row[5],
                'api_hash': row[6]
            })
        
        return users
    
    def update_user_last_active(self, user_id: int):
        """Cập nhật thời gian hoạt động cuối của user với error handling"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Kiểm tra xem cột last_active có tồn tại không
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'last_active' in columns:
                cursor.execute('''
                    UPDATE users SET last_active = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
            else:
                print(f"Warning: last_active column not found, skipping update for user {user_id}")
                
        except Exception as e:
            print(f"Error updating last_active for user {user_id}: {e}")
        finally:
            conn.close()
    
    def clear_user_session(self, user_id: int, reason: str = "Unknown"):
        """Xóa session của user khi logout hoặc lỗi với lý do ghi log"""
        print(f"⚠️ Clearing session for user {user_id}. Reason: {reason}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
        cursor.execute('UPDATE users SET is_authenticated = FALSE WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()
        
        print(f"✅ Session cleared for user {user_id}")
    
    def is_session_valid(self, user_id: int) -> bool:
        """Kiểm tra xem session có tồn tại và hợp lệ không"""
        session_data = self.get_user_session(user_id)
        user_data = self.get_user(user_id)
        
        return (session_data is not None and 
                session_data.get('session_string') is not None and
                user_data is not None and
                user_data.get('is_authenticated', False))
    
    def backup_session(self, user_id: int, reason: str = "Manual backup"):
        """Backup session trước khi thực hiện operations có rủi ro với improved functionality"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current session
            cursor.execute('SELECT session_string, api_id, api_hash FROM user_sessions WHERE user_id = ?', (user_id,))
            session_data = cursor.fetchone()
            
            if session_data and session_data[0]:
                # Create backup entry
                cursor.execute('''
                    INSERT INTO session_backups (user_id, session_string, api_id, api_hash, backup_reason)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, session_data[0], session_data[1], session_data[2], reason))
                
                # Also backup database file
                try:
                    backup_path = f"data/telegram_bot.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.db_path, backup_path)
                    print(f"📋 Database backed up to: {backup_path}")
                    
                    # Keep only last 3 database backups
                    import glob
                    backups = sorted(glob.glob("data/telegram_bot.db.backup_*"))
                    while len(backups) > 3:
                        os.remove(backups[0])
                        print(f"🗑️ Removed old backup: {backups[0]}")
                        backups.pop(0)
                        
                except Exception as backup_error:
                    print(f"⚠️ Failed to backup database file: {backup_error}")
                
                conn.commit()
                print(f"📋 Session backup created for user {user_id}: {reason}")
                return True
            else:
                print(f"⚠️ No session to backup for user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error backing up session for user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def restore_session_from_backup(self, user_id: int, backup_id: int = None):
        """Khôi phục session từ backup cụ thể"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if backup_id:
                cursor.execute('''
                    SELECT session_string, api_id, api_hash, backup_reason
                    FROM session_backups 
                    WHERE id = ? AND user_id = ?
                ''', (backup_id, user_id))
            else:
                # Get latest backup
                cursor.execute('''
                    SELECT session_string, api_id, api_hash, backup_reason
                    FROM session_backups 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (user_id,))
            
            backup_data = cursor.fetchone()
            if backup_data:
                # Restore session
                self.save_user_session(user_id, backup_data[0], backup_data[1], backup_data[2])
                print(f"✅ Session restored from backup for user {user_id}: {backup_data[3]}")
                return True
            else:
                print(f"❌ No backup found for user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error restoring session for user {user_id}: {e}")
            return False
        finally:
            conn.close()
    
    def get_session_backups(self, user_id: int):
        """Lấy danh sách backups của user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, backup_reason, created_at
                FROM session_backups 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            
            backups = []
            for row in cursor.fetchall():
                backups.append({
                    'id': row[0],
                    'reason': row[1],
                    'created_at': row[2]
                })
            
            return backups
            
        except Exception as e:
            print(f"❌ Error getting backups for user {user_id}: {e}")
            return []
        finally:
            conn.close() 