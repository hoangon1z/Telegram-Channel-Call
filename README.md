# 🤖 Telegram Channel Copy Bot

Bot Telegram tự động copy tin nhắn từ channel này sang channel khác với nhiều tính năng nâng cao.

## ✨ Tính Năng Chính

- 🔐 **Đăng nhập an toàn**: Sử dụng Telegram API chính thức
- 📥 **Copy Channel**: Tự động copy tin nhắn từ channel nguồn sang channel đích
- 🎯 **Lọc nội dung**: Sử dụng RegEx để lọc text cần thiết
- 📝 **Header/Footer**: Thêm văn bản đầu và cuối tin nhắn
- 🔘 **Button tùy chỉnh**: Thêm button với link tùy chỉnh
- 👥 **Multi-user**: Hỗ trợ nhiều người dùng cùng lúc
- 💾 **Database**: Lưu trữ cấu hình trong SQLite
- 🎨 **Giao diện đẹp**: Inline keyboard dễ sử dụng
- 🏗️ **Kiến trúc Modular**: Code được tổ chức theo modules chuyên nghiệp

## 🛠️ Cài Đặt

### 1. Clone Repository

```bash
git clone <repository-url>
cd TelegrambotCopy
```

### 2. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu Hình Environment

Sao chép file `.env` và cập nhật thông tin:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env`:

```env
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id
API_HASH=your_api_hash
DATABASE_URL=data/telegram_bot.db
```

### 4. Lấy API_ID và API_HASH

1. Truy cập [my.telegram.org](https://my.telegram.org)
2. Đăng nhập với tài khoản Telegram
3. Vào "API development tools"
4. Tạo application mới
5. Copy `api_id` và `api_hash` vào file `.env`

### 5. Chạy Bot

```bash
python main.py
```

## 📋 Hướng Dẫn Sử Dụng

### Bước 1: Đăng Nhập
1. Khởi động bot bằng `/start`
2. Nhấn "🔐 Đăng nhập tài khoản"
3. Nhập số điện thoại
4. Nhập mã xác thực từ Telegram

### Bước 2: Cấu Hình Copy Channel
1. Nhấn "⚙️ Cấu hình Copy Channel"
2. Chọn channel nguồn (để copy từ đó)
3. Chọn channel đích (để gửi tin nhắn đến)
4. Tùy chọn thiết lập:
   - Pattern lọc text (RegEx)
   - Header/Footer văn bản
   - Button với link tùy chỉnh
5. Lưu cấu hình

### Bước 3: Bắt Đầu Copy
1. Vào "📋 Danh sách cấu hình"
2. Chọn cấu hình muốn chạy
3. Nhấn "🚀 Bắt đầu Copy"

## 🔧 Tính Năng Nâng Cao

### Pattern Lọc (RegEx)
Sử dụng Regular Expression để lọc nội dung:

- `\d+` - Lấy tất cả số
- `https?://[^\s]+` - Lấy tất cả link
- `#\w+` - Lấy tất cả hashtag
- `@\w+` - Lấy tất cả mention
- `\$[A-Z]+` - Lấy symbol coin

### Header/Footer
Thêm văn bản tùy chỉnh:

**Header (đầu tin nhắn):**
```
🔥 Tin nóng từ kênh ABC
�� Thông báo quan trọng:
```

**Footer (cuối tin nhắn):**
```
📱 Theo dõi: @mychannel
🔗 Website: https://example.com
```

### Button Tùy Chỉnh
Thêm button với:
- Text button: "📱 Tham gia ngay"
- URL: "https://t.me/yourchannel"

## 📁 Cấu Trúc Project

```
TelegrambotCopy/
├── main.py                    # 🚀 Entry point chính
├── setup.py                   # 📦 Package setup
├── requirements.txt           # 📋 Dependencies Python
├── .env                      # 🔧 Environment variables
├── .env.example              # 📝 Environment template
├── .gitignore                # 🚫 Git ignore rules
├── LICENSE                   # ⚖️ MIT License
├── MANIFEST.in               # 📦 Package manifest
├── README.md                 # 📚 Documentation
│
├── bot/                      # 🤖 Core bot modules
│   ├── __init__.py           # Package init
│   ├── core.py               # 🧠 Main TelegramBot class
│   ├── main_handlers.py      # 🎛️ Button handler routing
│   │
│   ├── auth/                 # 🔐 Authentication module
│   │   ├── __init__.py
│   │   └── handlers.py       # Login, phone verification, 2FA
│   │
│   ├── config/               # ⚙️ Configuration module
│   │   ├── __init__.py
│   │   └── handlers.py       # Pattern setup, config management
│   │
│   ├── channels/             # 📡 Channel management module
│   │   ├── __init__.py
│   │   └── manager.py        # Channel selection, dialog caching
│   │
│   ├── messages/             # 💬 Message processing module
│   │   ├── __init__.py
│   │   └── processor.py      # Message queue, media forwarding
│   │
│   └── utils/                # 🛠️ Utility modules
│       ├── __init__.py
│       ├── states.py         # Conversation states
│       ├── keyboards.py      # Inline keyboards
│       ├── database.py       # SQLite operations
│       ├── client.py         # Pyrogram wrapper
│       └── handlers.py       # Misc handlers
│
├── data/                     # 💾 Data directory
│   └── telegram_bot.db       # SQLite database
│
└── docs/                     # 📖 Documentation
    ├── CHANGELOG.md          # Session management improvements
    └── REFACTOR.md           # Modular architecture guide
```

## 🏗️ Kiến Trúc Modular

Bot được thiết kế theo kiến trúc modular chuyên nghiệp:

### 🧠 Core (`bot/core.py`)
- Main TelegramBot class
- Session management và restoration
- Bot lifecycle management

### 🔐 Authentication (`bot/auth/`)
- Phone number validation
- SMS code verification
- Two-factor authentication
- Session recovery

### ⚙️ Configuration (`bot/config/`)
- Pattern setup và validation
- Configuration management
- Help và documentation

### 📡 Channel Management (`bot/channels/`)
- Channel selection với pagination
- Dialog caching và performance
- Channel information display

### 💬 Message Processing (`bot/messages/`)
- Message queue system
- Pattern extraction
- Header/footer addition
- Multi-media forwarding

### 🛠️ Utilities (`bot/utils/`)
- Database operations
- Telegram client wrapper
- Keyboard definitions
- Shared states và helpers

## 🗃️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT,
    is_authenticated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Channel Configs Table
```sql
CREATE TABLE channel_configs (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Sessions Table
```sql
CREATE TABLE user_sessions (
    user_id INTEGER PRIMARY KEY,
    session_string TEXT,
    api_id INTEGER,
    api_hash TEXT
);
```

## ⚠️ Lưu Ý Quan Trọng

### Quyền Truy Cập
- Cần là **member** hoặc **admin** của channel nguồn
- Cần quyền **gửi tin nhắn** ở channel đích
- Bot chỉ copy **tin nhắn mới**, không copy tin nhắn cũ

### Bảo Mật
- Thông tin đăng nhập được **mã hóa** an toàn
- Session được lưu trong database **local**
- Không chia sẻ API_ID, API_HASH với người khác

### Giới Hạn
- Tuân thủ [Telegram API Limits](https://core.telegram.org/api/obtaining_api_id#api-rate-limits)
- Không spam tin nhắn
- Respect channel owners' content

## 🚨 Xử Lý Lỗi

### Lỗi Thường Gặp

**"API_ID và API_HASH không hợp lệ"**
- Kiểm tra lại thông tin từ my.telegram.org
- Đảm bảo format đúng trong file .env

**"Không thể truy cập channel"**
- Kiểm tra quyền member/admin của channel nguồn

**"Session hết hạn"**
- Đăng nhập lại tài khoản
- Kiểm tra kết nối mạng

## 📞 Hỗ Trợ

- **Issues**: Tạo issue trên GitHub
- **Telegram**: @yourusername
- **Email**: your.email@example.com

## 📄 License

MIT License - xem file `LICENSE` để biết chi tiết.

## 🎯 Roadmap

- [ ] Thêm schedule copy theo thời gian
- [ ] Hỗ trợ copy từ nhiều channel cùng lúc
- [ ] Web dashboard quản lý
- [ ] Webhook integration
- [ ] Analytics và báo cáo

## Troubleshooting

### Vấn đề: Bot không copy tin nhắn về channel đích

**Nguyên nhân có thể:**

1. **Message handlers không được đăng ký đúng cách:**
   - Kiểm tra console log xem có thông báo "🎯 Debug - Message handler registered for channel {ID}, config {ID}" không
   - Nếu không thấy, có thể do lỗi trong quá trình start_copying

2. **Session không hợp lệ:**
   - Thử đăng xuất và đăng nhập lại tài khoản
   - Kiểm tra session trong database có hợp lệ không

3. **Không có quyền truy cập channel:**
   - Đảm bảo tài khoản đã join channel nguồn
   - Đảm bảo bot có quyền gửi tin nhắn vào channel đích

4. **Config không được đánh dấu active:**
   - Kiểm tra database table `channel_configs` xem config có `is_active = TRUE` không
   - Thử stop và start lại config

5. **Pattern filter loại bỏ tất cả tin nhắn:**
   - Kiểm tra pattern regex có đúng không
   - Thử tắt pattern filter để test

**Debug steps:**

1. Kiểm tra logs trong console khi start bot
2. Gửi tin nhắn test vào channel nguồn
3. Xem có log "📥 Debug - New message received" không
4. Kiểm tra message có đi vào queue không: "📤 Message queued for processing"
5. Xem có lỗi khi xử lý message không

**Commands for debugging:**
```bash
# Kiểm tra database
sqlite3 telegram_bot.db "SELECT * FROM channel_configs WHERE is_active = 1;"

# Restart bot with debug
python main.py
```

---

**Made with ❤️ for Telegram Community** 