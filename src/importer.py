from __future__ import annotations

import hashlib
import io
import json
import csv
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from .config import CSV_ALIASES, CUSTOMER_ALIASES, STAFF_ALIASES
from .db import transaction


@dataclass
class ImportResult:
    batch_id: str
    rows_seen: int = 0
    rows_inserted: int = 0
    rows_skipped: int = 0
    files_processed: int = 0
    warnings: list[str] = field(default_factory=list)
    is_duplicate: bool = False
    existing_batch_id: str | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_col(name: str) -> str:
    return re.sub(r"[^a-z0-9ก-๙]", "", str(name).strip().lower())


def infer_columns(columns) -> dict[str, str]:
    norm = {normalize_col(c): c for c in columns}
    mapping = {}
    for canonical, aliases in CSV_ALIASES.items():
        for alias in aliases:
            key = normalize_col(alias)
            if key in norm:
                mapping[canonical] = norm[key]
                break
    return mapping


def normalize_sender(value: object) -> str:
    s = str(value or "").strip().lower()
    if s in CUSTOMER_ALIASES or any(x in s for x in ["customer", "ลูกค้า", "client", "user"]):
        return "customer"
    if s in STAFF_ALIASES or any(x in s for x in ["staff", "admin", "sales", "พนักงาน", "แอดมิน", "account"]):
        return "staff"
    return "unknown"


def parse_timestamp(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    dt = pd.to_datetime(value, errors="coerce", format="mixed")
    if pd.isna(dt):
        return None
    if getattr(dt, "tzinfo", None):
        dt = dt.tz_convert(None)
    return dt.isoformat(sep=" ")


def conversation_key(product_type: str, external_id: str) -> str:
    raw = f"{product_type}|{external_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def message_hash(conv_key: str, sender: str, text: str, sent_at: str | None) -> str:
    raw = f"{conv_key}|{sender}|{text.strip()}|{sent_at or ''}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _detect_chat_header(text: str) -> int:
    """Return the physical line index containing the real CSV header.

    LINE/CRM exports may prepend metadata such as Account name, Time zone,
    and Downloaded on before the message table. We look for a row that
    contains both a sender field and a message field.
    """
    sender_names = {normalize_col(x) for x in CSV_ALIASES["sender"]} | {"sendertype"}
    message_names = {normalize_col(x) for x in CSV_ALIASES["message"]}

    for i, line in enumerate(text.splitlines()[:100]):
        try:
            cols = next(csv.reader([line]))
        except Exception:
            continue
        normalized = {normalize_col(c) for c in cols}
        if normalized & sender_names and normalized & message_names:
            return i
    return 0


def _read_csv_bytes(data: bytes) -> pd.DataFrame:
    errors = []
    for encoding in ["utf-8-sig", "utf-8", "cp874", "tis-620", "latin1"]:
        try:
            text = data.decode(encoding)
            header_line = _detect_chat_header(text)
            # Python engine handles quoted multiline messages reliably.
            return pd.read_csv(
                io.StringIO(text),
                skiprows=header_line,
                engine="python",
                quotechar='"',
            )
        except Exception as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError("อ่าน CSV ไม่สำเร็จ: " + errors[-1])


def _read_json_bytes(data: bytes) -> pd.DataFrame:
    obj = json.loads(data.decode("utf-8-sig"))
    if isinstance(obj, dict):
        for key in ["messages", "data", "conversations"]:
            if isinstance(obj.get(key), list):
                obj = obj[key]
                break
    return pd.json_normalize(obj)


def _frames_from_zip(zip_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.startswith("__MACOSX/"):
                continue
            suffix = Path(info.filename).suffix.lower()
            if suffix not in {".csv", ".json"}:
                continue
            data = zf.read(info)
            try:
                df = _read_csv_bytes(data) if suffix == ".csv" else _read_json_bytes(data)
                yield info.filename, df, None
            except Exception as exc:
                yield info.filename, None, str(exc)


def _frames_from_upload(filename: str, content: bytes):
    suffix = Path(filename).suffix.lower()
    if suffix == ".zip":
        yield from _frames_from_zip(content)
    elif suffix == ".csv":
        yield filename, _read_csv_bytes(content), None
    elif suffix == ".json":
        yield filename, _read_json_bytes(content), None
    else:
        raise ValueError("รองรับไฟล์ .zip, .csv และ .json")


ProgressCallback = Callable[[str, int, int, str], None]


def _count_upload_files(filename: str, content: bytes) -> int:
    suffix = Path(filename).suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return sum(1 for info in zf.infolist() if (not info.is_dir()) and (not info.filename.startswith("__MACOSX/")) and Path(info.filename).suffix.lower() in {".csv", ".json"})
    return 1


def import_upload(filename: str, content: bytes, product_type: str, period_label: str = "", progress_callback: ProgressCallback | None = None) -> ImportResult:
    product_type = product_type.upper()
    if product_type not in {"SPA", "FNB"}:
        raise ValueError("product_type ต้องเป็น SPA หรือ FNB")

    file_hash = sha256_bytes(content)
    batch_id = "BATCH-" + uuid.uuid4().hex[:12].upper()
    now = datetime.now(timezone.utc).isoformat()
    result = ImportResult(batch_id=batch_id)

    total_files = _count_upload_files(filename, content)
    if progress_callback:
        progress_callback("prepare", 0, max(total_files, 1), "กำลังตรวจสอบไฟล์และเตรียมนำเข้า")

    with transaction() as conn:
        duplicate_batch = conn.execute(
            "SELECT batch_id, rows_seen, rows_inserted, rows_skipped FROM import_batches WHERE file_hash=? AND product_type=? AND status='completed'",
            (file_hash, product_type),
        ).fetchone()
        if duplicate_batch:
            result.batch_id = duplicate_batch["batch_id"]
            result.existing_batch_id = duplicate_batch["batch_id"]
            result.is_duplicate = True
            result.rows_seen = int(duplicate_batch["rows_seen"] or 0)
            result.rows_inserted = 0
            result.rows_skipped = int(duplicate_batch["rows_seen"] or 0)
            if progress_callback:
                progress_callback("duplicate", 1, 1, f"ไฟล์นี้เคยวิเคราะห์แล้ว: {duplicate_batch['batch_id']}")
            return result

        conn.execute(
            "INSERT INTO import_batches(batch_id,product_type,source_filename,period_label,imported_at,file_hash,status) VALUES (?,?,?,?,?,?,?)",
            (batch_id, product_type, filename, period_label, now, file_hash, "processing"),
        )

        for file_index, (source_file, df, error) in enumerate(_frames_from_upload(filename, content), start=1):
            if progress_callback:
                progress_callback("import", file_index - 1, max(total_files, 1), f"กำลังอ่านไฟล์ {file_index:,}/{total_files:,}: {Path(source_file).name}")
            if error:
                result.warnings.append(f"{source_file}: {error}")
                continue
            if df is None or df.empty:
                result.warnings.append(f"{source_file}: ไม่มีข้อมูล")
                continue

            mapping = infer_columns(df.columns)
            required = {"sender", "message"}
            if not required.issubset(mapping):
                result.warnings.append(
                    f"{source_file}: หา column sender/message ไม่พบ (columns: {', '.join(map(str, df.columns))})"
                )
                continue

            result.files_processed += 1
            if progress_callback:
                progress_callback("import", file_index, max(total_files, 1), f"อ่านไฟล์ {file_index:,}/{total_files:,} สำเร็จ")
            has_conversation = "conversation_id" in mapping
            fallback_conv = Path(source_file).stem

            for idx, row in df.iterrows():
                result.rows_seen += 1
                text = str(row.get(mapping["message"], "") or "").strip()
                if not text or text.lower() == "nan":
                    result.rows_skipped += 1
                    continue
                external_id = str(row.get(mapping.get("conversation_id", ""), fallback_conv) if has_conversation else fallback_conv).strip()
                if not external_id or external_id.lower() == "nan":
                    external_id = fallback_conv
                ckey = conversation_key(product_type, external_id)
                sender_raw = row.get(mapping["sender"], "")
                sender_type = normalize_sender(sender_raw)

                # Some chat exports split Date and Time into separate columns.
                normalized_columns = {normalize_col(c): c for c in df.columns}
                date_col = normalized_columns.get("date") or normalized_columns.get("วันที่")
                time_col = normalized_columns.get("time") or normalized_columns.get("เวลา")
                if date_col and time_col:
                    date_value = row.get(date_col, "")
                    time_value = row.get(time_col, "")
                    sent_at = parse_timestamp(f"{date_value} {time_value}")
                else:
                    sent_at = parse_timestamp(row.get(mapping["timestamp"])) if "timestamp" in mapping else None

                mhash = message_hash(ckey, sender_type, text, sent_at)

                conn.execute(
                    "INSERT OR IGNORE INTO conversations(conversation_key,external_conversation_id,product_type,first_batch_id) VALUES (?,?,?,?)",
                    (ckey, external_id, product_type, batch_id),
                )
                cur = conn.execute(
                    "INSERT OR IGNORE INTO messages(message_hash,conversation_key,batch_id,sender_type,sender_raw,message_text,sent_at,source_file) VALUES (?,?,?,?,?,?,?,?)",
                    (mhash, ckey, batch_id, sender_type, str(sender_raw), text, sent_at, source_file),
                )
                if cur.rowcount:
                    result.rows_inserted += 1
                else:
                    result.rows_skipped += 1

        conn.execute(
            "UPDATE import_batches SET status='completed', rows_seen=?, rows_inserted=?, rows_skipped=?, notes=? WHERE batch_id=?",
            (result.rows_seen, result.rows_inserted, result.rows_skipped, "\n".join(result.warnings), batch_id),
        )

    if progress_callback:
        progress_callback("import_done", max(total_files, 1), max(total_files, 1), f"นำเข้าข้อมูลเสร็จแล้ว: เพิ่ม {result.rows_inserted:,} ข้อความ")
    return result
