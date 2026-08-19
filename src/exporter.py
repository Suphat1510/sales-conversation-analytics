from __future__ import annotations
from datetime import datetime
from .config import EXPORT_DIR
from .db import query_df


def export_conversation_dataset() -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = query_df("""
        SELECT c.external_conversation_id AS conversation_id,
               c.product_type, c.started_at, c.ended_at, c.message_count,
               c.customer_message_count, c.staff_message_count,
               m.first_response_minutes, m.conversation_duration_minutes,
               m.avg_staff_response_minutes, m.is_dropoff,
               m.has_purchase_signal, m.purchase_signal_count
        FROM conversations c
        LEFT JOIN conversation_metrics m USING(conversation_key)
    """)
    path = EXPORT_DIR / f"conversation_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)
