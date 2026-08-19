from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
import pandas as pd

from .db import transaction, query_df
from .rules import classify_text

ProgressCallback = Callable[[str, int, int, str], None]


def _minutes(delta) -> float | None:
    if pd.isna(delta):
        return None
    return max(float(delta.total_seconds() / 60), 0.0)


def _average_session_duration(valid: pd.DataFrame, gap_hours: float = 24.0) -> float | None:
    """Return average active chat-session duration in minutes.

    A new session starts when the gap between consecutive messages is greater
    than ``gap_hours``. This avoids treating a customer returning days or months
    later as one continuously active conversation.
    """
    if valid.empty:
        return None
    dts = valid["dt"].dropna().sort_values().tolist()
    if not dts:
        return None
    sessions: list[list[pd.Timestamp]] = [[dts[0]]]
    threshold = pd.Timedelta(hours=gap_hours)
    for dt in dts[1:]:
        if dt - sessions[-1][-1] > threshold:
            sessions.append([dt])
        else:
            sessions[-1].append(dt)
    durations = []
    for session in sessions:
        if len(session) == 1:
            durations.append(0.0)
        else:
            durations.append(_minutes(session[-1] - session[0]) or 0.0)
    return sum(durations) / len(durations) if durations else None


def rebuild_analytics(
    product_type: str | None = None,
    batch_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> int:
    """Recalculate conversation analytics efficiently.

    When batch_id is supplied, only conversations touched by that import batch
    are rebuilt. Messages for all target conversations are fetched in one SQL
    query, avoiding one SELECT per conversation.
    """
    filters = []
    params: list[object] = []
    if product_type:
        filters.append("c.product_type=?")
        params.append(product_type)
    if batch_id:
        filters.append("EXISTS (SELECT 1 FROM messages bm WHERE bm.conversation_key=c.conversation_key AND bm.batch_id=?)")
        params.append(batch_id)
    where = "WHERE " + " AND ".join(filters) if filters else ""

    convs = query_df(
        f"SELECT c.conversation_key, c.product_type FROM conversations c {where} ORDER BY c.conversation_key",
        tuple(params),
    )
    total = len(convs)
    if total == 0:
        if progress_callback:
            progress_callback("analytics", 0, 0, "ไม่มีห้องใหม่ที่ต้องวิเคราะห์")
        return 0

    # Fetch messages for all targeted conversations in one pass.
    msg_filters = []
    msg_params: list[object] = []
    if product_type:
        msg_filters.append("c.product_type=?")
        msg_params.append(product_type)
    if batch_id:
        msg_filters.append("EXISTS (SELECT 1 FROM messages bm WHERE bm.conversation_key=c.conversation_key AND bm.batch_id=?)")
        msg_params.append(batch_id)
    msg_where = "WHERE " + " AND ".join(msg_filters) if msg_filters else ""
    msgs_all = query_df(
        f"""
        SELECT m.conversation_key, c.product_type, m.sender_type, m.message_text, m.sent_at, m.rowid AS msg_rowid
        FROM messages m
        JOIN conversations c ON c.conversation_key=m.conversation_key
        {msg_where}
        ORDER BY m.conversation_key,
                 CASE WHEN m.sent_at IS NULL THEN 1 ELSE 0 END,
                 m.sent_at,
                 m.rowid
        """,
        tuple(msg_params),
    )
    if msgs_all.empty:
        return 0

    msgs_all["dt"] = pd.to_datetime(msgs_all["sent_at"], errors="coerce", format="mixed")
    grouped = {key: grp for key, grp in msgs_all.groupby("conversation_key", sort=False)}

    now = datetime.now(timezone.utc).isoformat()
    updated = 0
    with transaction() as conn:
        for idx, conv in enumerate(convs.itertuples(index=False), start=1):
            ckey = conv.conversation_key
            ptype = conv.product_type
            msgs = grouped.get(ckey)
            if msgs is None or msgs.empty:
                continue

            valid = msgs.dropna(subset=["dt"])
            started = valid["dt"].min() if not valid.empty else pd.NaT
            ended = valid["dt"].max() if not valid.empty else pd.NaT
            duration = _average_session_duration(valid, gap_hours=24.0)

            customer_mask = msgs["sender_type"].eq("customer")
            staff_mask = msgs["sender_type"].eq("staff")
            customer_count = int(customer_mask.sum())
            staff_count = int(staff_mask.sum())

            first_response = None
            response_times: list[float] = []
            pending_customer_dt = None
            for m in valid.itertuples(index=False):
                if m.sender_type == "customer":
                    pending_customer_dt = m.dt
                elif m.sender_type == "staff" and pending_customer_dt is not None:
                    mins = _minutes(m.dt - pending_customer_dt)
                    if mins is not None:
                        response_times.append(mins)
                        if first_response is None:
                            first_response = mins
                    pending_customer_dt = None
            avg_response = sum(response_times) / len(response_times) if response_times else None
            last_sender = msgs.iloc[-1]["sender_type"]
            is_dropoff = int(last_sender == "staff" and customer_count > 0)

            customer_text = "\n".join(msgs.loc[customer_mask, "message_text"].fillna("").astype(str))
            tags = classify_text(customer_text, ptype)
            purchase_count = sum(tags.get("purchase_signal", {}).values())

            conn.execute(
                "UPDATE conversations SET started_at=?, ended_at=?, message_count=?, customer_message_count=?, staff_message_count=? WHERE conversation_key=?",
                (
                    None if pd.isna(started) else started.isoformat(sep=" "),
                    None if pd.isna(ended) else ended.isoformat(sep=" "),
                    len(msgs), customer_count, staff_count, ckey,
                ),
            )
            conn.execute("DELETE FROM conversation_tags WHERE conversation_key=?", (ckey,))
            tag_rows = []
            for tag_type, items in tags.items():
                for tag_name, hits in items.items():
                    tag_rows.append((ckey, tag_type, tag_name, hits))
            if tag_rows:
                conn.executemany(
                    "INSERT INTO conversation_tags(conversation_key,tag_type,tag_name,hit_count) VALUES (?,?,?,?)",
                    tag_rows,
                )
            conn.execute(
                """
                INSERT INTO conversation_metrics(
                    conversation_key,first_response_minutes,conversation_duration_minutes,
                    avg_staff_response_minutes,is_dropoff,has_purchase_signal,
                    purchase_signal_count,updated_at
                ) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(conversation_key) DO UPDATE SET
                    first_response_minutes=excluded.first_response_minutes,
                    conversation_duration_minutes=excluded.conversation_duration_minutes,
                    avg_staff_response_minutes=excluded.avg_staff_response_minutes,
                    is_dropoff=excluded.is_dropoff,
                    has_purchase_signal=excluded.has_purchase_signal,
                    purchase_signal_count=excluded.purchase_signal_count,
                    updated_at=excluded.updated_at
                """,
                (ckey, first_response, duration, avg_response, is_dropoff, int(purchase_count > 0), purchase_count, now),
            )
            updated += 1
            if progress_callback and (idx == 1 or idx == total or idx % 25 == 0):
                progress_callback("analytics", idx, total, f"กำลังวิเคราะห์ห้อง {idx:,}/{total:,}")

    if batch_id:
        save_analysis_snapshot(batch_id)
    return updated


def overview(product: str = "ALL", start_date=None, end_date=None) -> dict:
    filters = []
    params = []
    if product != "ALL":
        filters.append("c.product_type=?")
        params.append(product)
    if start_date:
        filters.append("date(c.started_at)>=date(?)")
        params.append(str(start_date))
    if end_date:
        filters.append("date(c.started_at)<=date(?)")
        params.append(str(end_date))
    where = "WHERE " + " AND ".join(filters) if filters else ""
    df = query_df(f"""
        SELECT COUNT(*) conversations,
               COALESCE(SUM(c.message_count),0) messages,
               AVG(m.first_response_minutes) avg_first_response,
               AVG(m.conversation_duration_minutes) avg_duration,
               AVG(m.is_dropoff)*100 dropoff_rate,
               AVG(m.has_purchase_signal)*100 purchase_signal_rate
        FROM conversations c
        LEFT JOIN conversation_metrics m USING(conversation_key)
        {where}
    """, tuple(params))
    return df.iloc[0].to_dict() if not df.empty else {}


def tags_df(tag_type: str, product: str = "ALL", limit: int = 20) -> pd.DataFrame:
    where = ["t.tag_type=?"]
    params = [tag_type]
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    params.append(limit)
    return query_df(f"""
        SELECT t.tag_name,
               COUNT(DISTINCT t.conversation_key) AS conversations,
               SUM(t.hit_count) AS mentions
        FROM conversation_tags t
        JOIN conversations c USING(conversation_key)
        WHERE {' AND '.join(where)}
        GROUP BY t.tag_name
        ORDER BY conversations DESC, mentions DESC
        LIMIT ?
    """, tuple(params))


def tag_deep_df(tag_type: str, product: str = "ALL", limit: int = 30) -> pd.DataFrame:
    where = ["t.tag_type=?"]
    params: list[object] = [tag_type]
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    params.append(limit)
    return query_df(f"""
        SELECT t.tag_name,
               COUNT(DISTINCT t.conversation_key) AS conversations,
               SUM(t.hit_count) AS mentions,
               ROUND(AVG(COALESCE(m.has_purchase_signal,0))*100,1) AS purchase_rate,
               ROUND(AVG(COALESCE(m.purchase_signal_count,0)),2) AS avg_purchase_signals,
               ROUND(AVG(COALESCE(m.is_dropoff,0))*100,1) AS dropoff_rate,
               ROUND(AVG(m.first_response_minutes),1) AS avg_first_response_minutes,
               ROUND(AVG(m.conversation_duration_minutes),1) AS avg_duration_minutes
        FROM conversation_tags t
        JOIN conversations c USING(conversation_key)
        LEFT JOIN conversation_metrics m USING(conversation_key)
        WHERE {' AND '.join(where)}
        GROUP BY t.tag_name
        ORDER BY conversations DESC, mentions DESC
        LIMIT ?
    """, tuple(params))


def cooccurrence_df(type_a: str, type_b: str, product: str = "ALL", limit: int = 30) -> pd.DataFrame:
    where = ["a.tag_type=?", "b.tag_type=?", "a.tag_name<>b.tag_name"]
    params: list[object] = [type_a, type_b]
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    params.append(limit)
    return query_df(f"""
        SELECT a.tag_name AS item_a,
               b.tag_name AS item_b,
               COUNT(DISTINCT a.conversation_key) AS conversations,
               ROUND(AVG(COALESCE(m.has_purchase_signal,0))*100,1) AS purchase_rate,
               ROUND(AVG(COALESCE(m.is_dropoff,0))*100,1) AS dropoff_rate
        FROM conversation_tags a
        JOIN conversation_tags b ON a.conversation_key=b.conversation_key
        JOIN conversations c ON c.conversation_key=a.conversation_key
        LEFT JOIN conversation_metrics m ON m.conversation_key=a.conversation_key
        WHERE {' AND '.join(where)}
        GROUP BY a.tag_name,b.tag_name
        ORDER BY conversations DESC, purchase_rate DESC
        LIMIT ?
    """, tuple(params))


def response_impact_df(product: str = "ALL") -> pd.DataFrame:
    where = ["m.first_response_minutes IS NOT NULL"]
    params: list[object] = []
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    return query_df(f"""
        SELECT CASE
                 WHEN m.first_response_minutes <= 5 THEN '≤ 5 นาที'
                 WHEN m.first_response_minutes <= 15 THEN '6–15 นาที'
                 WHEN m.first_response_minutes <= 30 THEN '16–30 นาที'
                 ELSE '> 30 นาที'
               END AS response_bucket,
               COUNT(*) AS conversations,
               ROUND(AVG(m.has_purchase_signal)*100,1) AS purchase_rate,
               ROUND(AVG(m.is_dropoff)*100,1) AS dropoff_rate,
               ROUND(AVG(m.first_response_minutes),1) AS avg_response
        FROM conversation_metrics m
        JOIN conversations c USING(conversation_key)
        WHERE {' AND '.join(where)}
        GROUP BY response_bucket
        ORDER BY CASE response_bucket
                   WHEN '≤ 5 นาที' THEN 1
                   WHEN '6–15 นาที' THEN 2
                   WHEN '16–30 นาที' THEN 3
                   ELSE 4 END
    """, tuple(params))


def product_comparison_df() -> pd.DataFrame:
    return query_df("""
        SELECT c.product_type,
               COUNT(*) AS conversations,
               COALESCE(SUM(c.message_count),0) AS messages,
               ROUND(AVG(m.first_response_minutes),1) AS avg_first_response,
               ROUND(AVG(m.conversation_duration_minutes),1) AS avg_duration,
               ROUND(AVG(m.is_dropoff)*100,1) AS dropoff_rate,
               ROUND(AVG(m.has_purchase_signal)*100,1) AS purchase_rate
        FROM conversations c
        LEFT JOIN conversation_metrics m USING(conversation_key)
        GROUP BY c.product_type
        ORDER BY c.product_type
    """)


def trend_df(product: str = "ALL") -> pd.DataFrame:
    where = "WHERE product_type=?" if product != "ALL" else ""
    params = (product,) if product != "ALL" else ()
    return query_df(f"""
        SELECT substr(started_at,1,7) AS month, COUNT(*) AS conversations
        FROM conversations
        {where}
        AND started_at IS NOT NULL
        GROUP BY substr(started_at,1,7)
        ORDER BY month
    """ if where else """
        SELECT substr(started_at,1,7) AS month, COUNT(*) AS conversations
        FROM conversations
        WHERE started_at IS NOT NULL
        GROUP BY substr(started_at,1,7)
        ORDER BY month
    """, params)


def lead_table(product: str = "ALL", min_signal_count: int = 1) -> pd.DataFrame:
    where = ["m.purchase_signal_count>=?"]
    params = [min_signal_count]
    if product != "ALL":
        where.append("c.product_type=?")
        params.append(product)
    return query_df(f"""
        SELECT c.external_conversation_id AS conversation_id,
               c.product_type,
               c.started_at,
               c.message_count,
               ROUND(m.first_response_minutes,2) first_response_minutes,
               m.purchase_signal_count,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='interest' THEN t.tag_name END) interests,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='need' THEN t.tag_name END) needs,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='pain_point' THEN t.tag_name END) pain_points,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='purchase_signal' THEN t.tag_name END) signals
        FROM conversations c
        JOIN conversation_metrics m USING(conversation_key)
        LEFT JOIN conversation_tags t USING(conversation_key)
        WHERE {' AND '.join(where)}
        GROUP BY c.conversation_key
        ORDER BY m.purchase_signal_count DESC, c.started_at DESC
        LIMIT 500
    """, tuple(params))


def save_analysis_snapshot(batch_id: str) -> int:
    """Persist the analyzed state for conversations touched by one import batch.

    This makes Analysis History immutable: later uploads may update the same
    conversation globally, but the historical batch view still shows the
    metrics/tags that were produced when that batch was analyzed.
    """
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        touched = conn.execute(
            "SELECT DISTINCT conversation_key FROM messages WHERE batch_id=?",
            (batch_id,),
        ).fetchall()
        keys = [r[0] for r in touched]
        conn.execute("DELETE FROM batch_conversation_metrics WHERE batch_id=?", (batch_id,))
        conn.execute("DELETE FROM batch_conversation_tags WHERE batch_id=?", (batch_id,))
        if not keys:
            conn.execute(
                "INSERT INTO analysis_runs(batch_id, analyzed_at, status, conversations_analyzed) VALUES (?,?,?,0) "
                "ON CONFLICT(batch_id) DO UPDATE SET analyzed_at=excluded.analyzed_at,status=excluded.status,conversations_analyzed=0",
                (batch_id, now, "completed"),
            )
            return 0

        placeholders = ",".join(["?"] * len(keys))
        metric_rows = conn.execute(
            f"""
            SELECT c.conversation_key,c.product_type,c.external_conversation_id,
                   c.started_at,c.ended_at,c.message_count,c.customer_message_count,c.staff_message_count,
                   m.first_response_minutes,m.conversation_duration_minutes,m.avg_staff_response_minutes,
                   COALESCE(m.is_dropoff,0),COALESCE(m.has_purchase_signal,0),COALESCE(m.purchase_signal_count,0)
            FROM conversations c
            LEFT JOIN conversation_metrics m USING(conversation_key)
            WHERE c.conversation_key IN ({placeholders})
            """,
            tuple(keys),
        ).fetchall()
        conn.executemany(
            """
            INSERT INTO batch_conversation_metrics(
                batch_id,conversation_key,product_type,external_conversation_id,started_at,ended_at,
                message_count,customer_message_count,staff_message_count,first_response_minutes,
                conversation_duration_minutes,avg_staff_response_minutes,is_dropoff,has_purchase_signal,purchase_signal_count
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [(batch_id, *tuple(r)) for r in metric_rows],
        )
        tag_rows = conn.execute(
            f"""
            SELECT conversation_key,tag_type,tag_name,hit_count
            FROM conversation_tags
            WHERE conversation_key IN ({placeholders})
            """,
            tuple(keys),
        ).fetchall()
        if tag_rows:
            conn.executemany(
                "INSERT INTO batch_conversation_tags(batch_id,conversation_key,tag_type,tag_name,hit_count) VALUES (?,?,?,?,?)",
                [(batch_id, *tuple(r)) for r in tag_rows],
            )
        conn.execute(
            "INSERT INTO analysis_runs(batch_id, analyzed_at, status, conversations_analyzed) VALUES (?,?,?,?) "
            "ON CONFLICT(batch_id) DO UPDATE SET analyzed_at=excluded.analyzed_at,status=excluded.status,conversations_analyzed=excluded.conversations_analyzed",
            (batch_id, now, "completed", len(metric_rows)),
        )
    return len(metric_rows)


def analysis_history_df(product: str = "ALL") -> pd.DataFrame:
    where = "WHERE b.product_type=?" if product != "ALL" else ""
    params = (product,) if product != "ALL" else ()
    return query_df(f"""
        SELECT b.batch_id,b.product_type,b.period_label,b.source_filename,b.imported_at,
               a.analyzed_at,a.conversations_analyzed,b.rows_seen,b.rows_inserted,b.rows_skipped,
               CASE WHEN a.batch_id IS NOT NULL THEN 'วิเคราะห์แล้ว' ELSE 'ยังไม่วิเคราะห์' END AS analysis_status
        FROM import_batches b
        LEFT JOIN analysis_runs a ON a.batch_id=b.batch_id
        {where}
        ORDER BY COALESCE(a.analyzed_at,b.imported_at) DESC
    """, params)


def batch_overview(batch_id: str) -> dict:
    df = query_df("""
        SELECT COUNT(*) conversations,
               COALESCE(SUM(message_count),0) messages,
               AVG(first_response_minutes) avg_first_response,
               AVG(conversation_duration_minutes) avg_duration,
               AVG(is_dropoff)*100 dropoff_rate,
               AVG(has_purchase_signal)*100 purchase_signal_rate
        FROM batch_conversation_metrics
        WHERE batch_id=?
    """, (batch_id,))
    return df.iloc[0].to_dict() if not df.empty else {}


def batch_tags_df(batch_id: str, tag_type: str, limit: int = 20) -> pd.DataFrame:
    return query_df("""
        SELECT tag_name,COUNT(DISTINCT conversation_key) AS conversations,SUM(hit_count) AS mentions
        FROM batch_conversation_tags
        WHERE batch_id=? AND tag_type=?
        GROUP BY tag_name
        ORDER BY conversations DESC,mentions DESC
        LIMIT ?
    """, (batch_id, tag_type, limit))


def batch_tag_deep_df(batch_id: str, tag_type: str, limit: int = 30) -> pd.DataFrame:
    return query_df("""
        SELECT t.tag_name,
               COUNT(DISTINCT t.conversation_key) AS conversations,
               SUM(t.hit_count) AS mentions,
               ROUND(AVG(COALESCE(m.has_purchase_signal,0))*100,1) AS purchase_rate,
               ROUND(AVG(COALESCE(m.purchase_signal_count,0)),2) AS avg_purchase_signals,
               ROUND(AVG(COALESCE(m.is_dropoff,0))*100,1) AS dropoff_rate,
               ROUND(AVG(m.first_response_minutes),1) AS avg_first_response_minutes,
               ROUND(AVG(m.conversation_duration_minutes),1) AS avg_duration_minutes
        FROM batch_conversation_tags t
        JOIN batch_conversation_metrics m
          ON m.batch_id=t.batch_id AND m.conversation_key=t.conversation_key
        WHERE t.batch_id=? AND t.tag_type=?
        GROUP BY t.tag_name
        ORDER BY conversations DESC,mentions DESC
        LIMIT ?
    """, (batch_id, tag_type, limit))


def batch_lead_table(batch_id: str, min_signal_count: int = 1) -> pd.DataFrame:
    return query_df("""
        SELECT m.external_conversation_id AS conversation_id,
               m.product_type,m.started_at,m.message_count,
               ROUND(m.first_response_minutes,2) AS first_response_minutes,
               m.purchase_signal_count,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='interest' THEN t.tag_name END) interests,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='need' THEN t.tag_name END) needs,
               GROUP_CONCAT(DISTINCT CASE WHEN t.tag_type='purchase_signal' THEN t.tag_name END) signals
        FROM batch_conversation_metrics m
        LEFT JOIN batch_conversation_tags t
          ON t.batch_id=m.batch_id AND t.conversation_key=m.conversation_key
        WHERE m.batch_id=? AND m.purchase_signal_count>=?
        GROUP BY m.conversation_key
        ORDER BY m.purchase_signal_count DESC,m.started_at DESC
        LIMIT 500
    """, (batch_id, min_signal_count))
