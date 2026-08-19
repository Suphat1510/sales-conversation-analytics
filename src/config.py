from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "conversation_analytics.db"
EXPORT_DIR = DATA_DIR / "exports"

CSV_ALIASES = {
    "conversation_id": ["conversation_id", "conversationid", "chat_id", "chatid", "room_id", "roomid", "room", "conversation", "thread_id"],
    "sender": ["sender", "role", "speaker", "from", "user_type", "sender_type", "actor"],
    "message": ["message", "text", "content", "body", "msg", "chat", "ข้อความ"],
    "timestamp": ["timestamp", "datetime", "date_time", "created_at", "sent_at", "time", "date", "วันที่", "เวลา"],
}

CUSTOMER_ALIASES = {"customer", "client", "user", "ลูกค้า", "buyer", "guest", "visitor"}
STAFF_ALIASES = {"staff", "agent", "admin", "seller", "sales", "employee", "พนักงาน", "แอดมิน", "ร้าน", "shop"}
