# Sales Conversation Analytics — POS SPA & POS F&B

ระบบวิเคราะห์ข้อมูลบทสนทนาสำหรับทีม Sales แบบ **Incremental**: อัปโหลด ZIP/CSV/JSON เพิ่มได้เรื่อย ๆ, ป้องกันข้อมูลซ้ำ, แยก POS SPA / POS F&B, คำนวณ Customer Need / Interest / Pain Point / Purchase Signal และแสดงผลผ่าน Dashboard

## Architecture

```text
ZIP / CSV / JSON
      │
      ▼
Import & Validate
      │
      ├── Column auto-detection
      ├── Sender normalization
      └── SHA-256 deduplication
      ▼
SQLite
├── import_batches
├── conversations
├── messages
├── conversation_metrics
└── conversation_tags
      │
      ▼
Python Analytics
├── Response time
├── Drop-off
├── Needs
├── Interests
├── Pain points
└── Purchase signals
      │
      ├────────► R Statistical Analysis
      ▼
Streamlit Dashboard
```

## 1. เปิดใน VS Code

```bash
cd conversation_sales_analytics
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## 2. รัน Dashboard

```bash
streamlit run app.py
```

Browser จะเปิดที่ `http://localhost:8501`

## 3. รูปแบบข้อมูล

รองรับ `.zip`, `.csv`, `.json` โดย ZIP สามารถมี CSV/JSON หลายไฟล์และหลายโฟลเดอร์ได้

ขั้นต่ำต้องมีข้อมูล 2 ช่อง: sender + message และแนะนำให้มี conversation_id + timestamp

```csv
conversation_id,sender,message,timestamp
C001,customer,ขอสอบถามราคา POS ค่ะ,2026-08-01 10:01:00
C001,staff,สนใจแพ็กเกจไหนคะ,2026-08-01 10:03:00
```

ระบบ auto-detect alias เช่น:
- conversation_id: `room_id`, `chat_id`, `thread_id`
- sender: `role`, `speaker`, `from`
- message: `text`, `content`, `body`, `msg`
- timestamp: `created_at`, `sent_at`, `datetime`, `time`

> ถ้าไฟล์หนึ่งคือหนึ่งห้องและไม่มี conversation_id ระบบจะใช้ชื่อไฟล์เป็น ID ของห้องนั้น

## 4. Import รอบใหม่

ไปที่ `Import Data` → เลือก POS SPA หรือ POS F&B → Upload

ระบบจะ:
1. Hash ไฟล์เพื่อกันการอัปโหลดไฟล์เดิมซ้ำ
2. แตก ZIP ใน memory ไม่เก็บไฟล์แตกถาวร
3. Hash แต่ละข้อความเพื่อกัน message ซ้ำ
4. Insert เฉพาะข้อความใหม่
5. Rebuild metrics/tag ของ product ที่นำเข้า
6. Dashboard ใช้ข้อมูลใหม่ทันที

ดังนั้นฐานข้อมูลโตตาม **ข้อมูลใหม่จริง** ไม่ใช่จำนวนครั้งที่อัปโหลด

## 5. Dashboard

### Dashboard
- Conversation count
- Message count
- Average first response
- Average conversation duration
- Drop-off rate
- Purchase-signal rate
- Conversation trend
- Top Needs / Interests

### Customer Insight
- Customer Needs
- Product / Feature Interests
- Pain Points
- Purchase Signals

### Sales Opportunity
แสดง conversation ที่มี purchase signals เช่น ถามราคา / ขอ Demo / ขอใบเสนอราคา / ถามเริ่มใช้งาน เพื่อให้ Sales ใช้จัดลำดับ Follow-up

### Data Management
- Import history
- Rebuild analytics
- Export CSV สำหรับ R

## 6. SQL

Schema อยู่ที่ `sql/schema.sql` และตัวอย่าง query อยู่ที่ `sql/analysis_queries.sql`

เปิด SQLite ได้ด้วย VS Code extension เช่น SQLite Viewer หรือใช้ terminal:

```bash
sqlite3 data/conversation_analytics.db
```

## 7. R Statistical Analysis

จากหน้า Data Management กด `Export CSV สำหรับ R` หรือรัน:

```bash
python scripts/export_for_r.py
```

จากนั้น:

```bash
Rscript r/statistical_analysis.R data/exports/conversation_metrics_YYYYMMDD_HHMMSS.csv
```

สคริปต์จะสรุป response time, drop-off rate, purchase-signal rate และทำ Welch t-test เปรียบเทียบ SPA/F&B เมื่อข้อมูลเพียงพอ

## 8. ปรับ Keyword / Business Rules

แก้ที่ `src/rules.py`

แยกเป็น:
- Common rules: ราคา, รายงาน, หลายสาขา, pain point, purchase signal
- SPA: Booking, Membership, Course, Therapist, Commission ฯลฯ
- F&B: Table, Kitchen/KDS, QR Ordering, Stock/Recipe, Delivery, Multi Branch ฯลฯ

ควรปรับคำศัพท์ให้ตรงกับข้อมูลจริงของบริษัทหลังจากดู sample conversation ชุดแรก

## 9. ทดสอบ

```bash
pytest -q
```

## 10. Sample

สร้างไฟล์ตัวอย่าง:

```bash
python scripts/generate_sample_zip.py
```

หมายเหตุ: sample ZIP มีทั้ง SPA/F&B เพื่อดู format เท่านั้น เวลานำเข้าจริงหนึ่ง batch ควรเป็น product เดียวตามประเภทที่เลือกในหน้า Import

## โครงสร้างโปรเจกต์

```text
conversation_sales_analytics/
├── app.py
├── requirements.txt
├── README.md
├── src/
│   ├── analytics.py
│   ├── config.py
│   ├── db.py
│   ├── exporter.py
│   ├── importer.py
│   └── rules.py
├── sql/
│   ├── schema.sql
│   └── analysis_queries.sql
├── r/
│   └── statistical_analysis.R
├── scripts/
│   ├── init_db.py
│   ├── export_for_r.py
│   └── generate_sample_zip.py
├── tests/
└── data/
```

## ข้อควรรู้ก่อนใช้ Production

เวอร์ชันนี้ตั้งใจให้เปิดใช้และพัฒนาต่อใน VS Code ได้ง่ายด้วย SQLite. หากอนาคตมีหลายผู้ใช้พร้อมกันหรือข้อมูลโตเป็นหลายสิบล้านข้อความ สามารถย้าย storage layer ไป PostgreSQL ได้โดยคง logic analysis/dashboard เดิมเป็นส่วนใหญ่

## Performance & Deep Insight update
- Import progress แสดงขั้นตอนอ่านไฟล์และเปอร์เซ็นต์
- Analytics progress แสดงจำนวนห้องที่วิเคราะห์แล้ว/ทั้งหมด
- Incremental analytics: หลัง import จะคำนวณเฉพาะ conversation ที่มีข้อมูลใน batch ล่าสุด
- Batch message loading: ลดการ SELECT ทีละห้อง โดยโหลดข้อความเป้าหมายใน query เดียวแล้ว group ใน pandas
- Customer Insight แบบเจาะลึก: Purchase Signal rate, Drop-off rate, Response Time, conversation duration, Interest × Need co-occurrence และข้อแนะนำสำหรับ Sales


## Analysis History
- ทุก batch ที่วิเคราะห์เสร็จจะถูกบันทึกเป็น snapshot เพื่อเปิดดูย้อนหลังได้โดยไม่ต้องวิเคราะห์ซ้ำ
- หากอัปโหลดไฟล์เดิม ระบบตรวจ SHA-256 และเปิดใช้ผลเดิมแทนการรันวิเคราะห์ใหม่
- หากเป็น batch เก่าที่สร้างก่อนฟีเจอร์ History สามารถกด “บันทึกผลปัจจุบันเป็น History” ได้ โดยเป็นการ copy ผลเดิม ไม่ได้วิเคราะห์ใหม่

## ความหมายของเวลาคุยเฉลี่ยต่อรอบ
ระบบไม่นับเวลาตั้งแต่ข้อความแรกถึงข้อความสุดท้ายของห้องแบบตรง ๆ อีกแล้ว เพราะลูกค้าอาจหายไปหลายวันหรือหลายเดือนแล้วกลับมาคุยใหม่ ทำให้ตัวเลขผิดธรรมชาติ เช่นหลักแสน分鐘

ระบบจะแบ่งเป็น session: หากไม่มีข้อความต่อเนื่องเกิน 24 ชั่วโมง จะเริ่มนับเป็นรอบใหม่ แล้วคำนวณเวลาเฉลี่ยของแต่ละรอบแทน
