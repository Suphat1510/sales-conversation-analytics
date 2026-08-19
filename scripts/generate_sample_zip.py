from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / "sample_conversations.zip"
spa = '''conversation_id,sender,message,timestamp
S001,customer,ขอสอบถามแพ็กเกจและระบบจองคิวค่ะ,2026-08-01 10:00:00
S001,staff,มีระบบ Booking และ Membership ค่ะ,2026-08-01 10:03:00
S001,customer,ขอราคาและเดโมได้ไหมคะ,2026-08-01 10:05:00
S001,staff,ได้ค่ะ,2026-08-01 10:06:00
'''
fnb = '''conversation_id,sender,message,timestamp
F001,customer,ร้านมี 3 สาขา อยากจัดการสต๊อกและดูรายงานยอดขาย,2026-08-02 11:00:00
F001,staff,ระบบรองรับ Multi Branch และ Stock ค่ะ,2026-08-02 11:04:00
F001,customer,ขอใบเสนอราคาได้ไหม,2026-08-02 11:08:00
'''
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("spa_sample.csv", spa)
    z.writestr("fnb_sample.csv", fnb)
print(out)
