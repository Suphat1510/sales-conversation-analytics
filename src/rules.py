from __future__ import annotations
import re

COMMON = {
    "need": {
        "ราคา/แพ็กเกจ": [r"ราคา", r"แพ็กเกจ", r"package", r"pricing", r"ค่าบริการ", r"รายเดือน"],
        "รายงาน/ยอดขาย": [r"รายงาน", r"report", r"ยอดขาย", r"dashboard", r"สรุปยอด"],
        "หลายสาขา": [r"หลายสาขา", r"multi.?branch", r"หลายร้าน", r"สำนักงานใหญ่"],
        "สต๊อก/สินค้า": [r"สต[๊็]?อก", r"stock", r"inventory", r"วัตถุดิบ"],
        "สมาชิก/CRM": [r"สมาชิก", r"member", r"membership", r"crm", r"สะสมแต้ม", r"loyalty"],
    },
    "pain_point": {
        "ระบบเดิมใช้งานยาก": [r"ใช้งานยาก", r"ยุ่งยาก", r"ซับซ้อน", r"ระบบเดิม", r"ช้า", r"ค้าง"],
        "จัดการหลายสาขาลำบาก": [r"หลายสาขา.*ลำบาก", r"แยกสาขา", r"รวมยอด.*สาขา", r"ดูยอด.*หลายสาขา"],
        "จัดการสต๊อกยาก": [r"สต[๊็]?อก.*ยาก", r"ของหาย", r"สต[๊็]?อกไม่ตรง", r"นับสต[๊็]?อก"],
        "ข้อมูล/รายงานไม่ชัด": [r"ดูยอดไม่ได้", r"รายงานไม่", r"ข้อมูลไม่", r"เช[็]?กยอด.*ไม่ได้"],
    },
    "purchase_signal": {
        "ถามราคา": [r"ราคา", r"เท่าไหร่", r"ค่าบริการ", r"กี่บาท"],
        "ขอ Demo": [r"demo", r"เดโม", r"ทดลองใช้", r"ทดลองระบบ"],
        "ถามเริ่มใช้งาน": [r"เริ่มใช้", r"ติดตั้ง", r"เปิดใช้", r"พร้อมใช้", r"ใช้ได้เมื่อไหร่"],
        "ขอใบเสนอราคา": [r"ใบเสนอราคา", r"quotation", r"quote"],
        "ถามชำระเงิน": [r"ชำระ", r"จ่าย", r"โอน", r"payment"],
    },
}

PRODUCT_RULES = {
    "SPA": {
        "interest": {
            "Booking/Appointment": [r"จองคิว", r"booking", r"appointment", r"นัดหมาย"],
            "Membership": [r"สมาชิก", r"membership", r"member"],
            "Course/Package": [r"คอร์ส", r"course", r"package", r"แพ็กเกจ"],
            "Therapist/Staff": [r"หมอนวด", r"therapist", r"พนักงาน", r"ช่าง", r"ตารางงาน"],
            "Commission": [r"commission", r"คอมมิช", r"ค่ามือ"],
            "Room/Resource": [r"ห้อง", r"เตียง", r"room", r"resource"],
        },
        "need": {
            "จัดการคิว": [r"จองคิว", r"คิว", r"นัดหมาย", r"booking"],
            "จัดการคอร์ส": [r"คอร์ส", r"course", r"package", r"ครั้งคงเหลือ"],
            "จัดการพนักงานบริการ": [r"หมอนวด", r"therapist", r"ตารางพนักงาน", r"ช่าง"],
        },
    },
    "FNB": {
        "interest": {
            "Table Management": [r"โต๊ะ", r"table", r"ย้ายโต๊ะ", r"รวมโต๊ะ"],
            "Kitchen/KDS": [r"ครัว", r"kitchen", r"kds", r"ใบครัว"],
            "QR Ordering": [r"qr", r"คิวอาร์", r"สั่งอาหาร.*มือถือ", r"สแกน.*สั่ง"],
            "Stock/Recipe": [r"สต[๊็]?อก", r"stock", r"สูตรอาหาร", r"วัตถุดิบ", r"recipe"],
            "Delivery": [r"delivery", r"เดลิเวอ", r"grab", r"lineman", r"shopeefood"],
            "Multi Branch": [r"หลายสาขา", r"multi.?branch", r"สำนักงานใหญ่"],
        },
        "need": {
            "จัดการโต๊ะ": [r"โต๊ะ", r"table", r"ย้ายโต๊ะ", r"รวมโต๊ะ"],
            "จัดการครัว": [r"ครัว", r"kitchen", r"kds", r"ใบครัว"],
            "จัดการออเดอร์": [r"ออเดอร์", r"order", r"สั่งอาหาร", r"รายการอาหาร"],
            "จัดการวัตถุดิบ": [r"วัตถุดิบ", r"สูตรอาหาร", r"recipe", r"food cost"],
        },
    },
}


def classify_text(text: str, product_type: str) -> dict[str, dict[str, int]]:
    text = (text or "").lower()
    groups: dict[str, dict[str, list[str]]] = {}
    for tag_type, rules in COMMON.items():
        groups.setdefault(tag_type, {}).update(rules)
    for tag_type, rules in PRODUCT_RULES.get(product_type, {}).items():
        groups.setdefault(tag_type, {}).update(rules)

    result: dict[str, dict[str, int]] = {}
    for tag_type, rules in groups.items():
        for name, patterns in rules.items():
            hits = sum(len(re.findall(p, text, flags=re.IGNORECASE)) for p in patterns)
            if hits:
                result.setdefault(tag_type, {})[name] = hits
    return result
