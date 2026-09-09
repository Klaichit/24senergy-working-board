# Content Board — ระบบบอร์ดคอนเทนต์ (multi-brand)

บอร์ดหนึ่งแบรนด์ = **เทมเพลตกลาง 1 ชุด + config 1 ไฟล์** โค้ดไม่มีชื่อแบรนด์ฝังอยู่เลย
เพิ่มบริษัทใหม่ = ก๊อป `config.json` แก้ค่า ไม่ต้องแตะโค้ด

> ค่าประจำอินสแตนซ์ (ลิงก์ artifact, id ของ Notion/Drive, path บนเครื่อง) อยู่ใน `config.json`
> ซึ่ง **ไม่ได้อยู่ใน repo** เพราะ repo นี้เป็น public — ขอไฟล์จากโฟลเดอร์ทีม
> ดูโครงสร้างที่ต้องกรอกได้จาก `config.example.json`

## โครงหน้า

หน้าเป็น HTML ที่มีตัวเรนเดอร์ในตัว เก็บข้อมูล **สามบล็อกแยกกัน**:

```html
<script id="board-config" type="application/json">…</script>   แบรนด์ / label / ขั้นตอน / กฎแฮชแท็ก
<script id="board-data"   type="application/json">…</script>   แถวจาก Notion — เปลี่ยนทุกวัน
<script id="board-images" type="application/json">…</script>   ภาพย่อฝัง — เปลี่ยนตอนสั่งอัปเดตภาพ
```

จับคู่ภาพกับโพสต์ด้วย **วันที่กำหนดเผยแพร่** ที่ตรงกับชื่อโฟลเดอร์ Drive

> **กฎเหล็ก:** งาน sync ที่รันในคลาวด์แตะได้เฉพาะ `board-data`
> มันเข้าเครื่องไม่ได้ ถ้าเขียนทับ `board-images` ภาพหายทั้งบอร์ดและกู้เองไม่ได้

## config.json — 8 จุดที่ต่างกันในแต่ละแบรนด์

| คีย์ | คืออะไร |
|---|---|
| `brand` | ชื่อหน้า คำโปรย สีแอคเซนต์ (แยก light/dark) |
| `locale` | timezone, ปี พ.ศ./ค.ศ. (`yearOffset`), ชื่อเดือน, รูปแบบวันที่ |
| `notion.dataSource` + `notion.props` | id ฐานข้อมูล และแมปชื่อ property → คีย์ที่โค้ดใช้ |
| `stages` | ชื่อ/ลำดับ/สีขั้นตอน + คำอธิบายใต้หัวข้อกลุ่ม |
| `priority` / `renderStatus` | ค่าที่ใช้ตัดสินป้าย ด่วน / สำคัญ / สถานะภาพ |
| `hashtags` | ชุดแท็กพื้นฐาน + แมปจากหมวด/กลุ่มเป้าหมาย/ประเภท/แบรนด์ |
| `labels` | ข้อความบนหน้าทั้งหมด (เปลี่ยนภาษาได้ทั้งบอร์ด) |
| `images` | โฟลเดอร์บนเครื่อง, Drive parent, ขนาด/คุณภาพภาพ, รูปแบบชื่อโฟลเดอร์ |

`config.example.json` คือตัวอย่างแบรนด์สมมติภาษาอังกฤษ ใช้เป็นแบบตั้งต้นของบริษัทถัดไป

## เพิ่มบริษัทใหม่

1. ก๊อป `config.example.json` → `config.<brand>.json` แก้ 8 หมวดข้างบน
2. `python3 inject.py --config config.<brand>.json --sql` → ได้ SQL สำหรับ scheduled task ของแบรนด์นั้น
3. `python3 inject.py --config config.<brand>.json` → ได้ `board.html` แล้ว publish เป็น artifact ใหม่
4. เอา URL ที่ได้ใส่กลับใน config (`artifactUrl`) และในprompt ของ scheduled task

## งาน sync รายวัน (คลาวด์)

query SQL จากข้อ 2 → เขียน `data.json` → อ่านหน้าเดิมจาก artifact → สลับเฉพาะบล็อก `board-data` → publish ทับ
สคริปต์เต็มอยู่ใน prompt ของ scheduled task พร้อม assert กันเขียนทับบล็อกภาพ

## อัปเดตภาพ — “อัปเดตภาพเข้าบอร์ด” (ต้องต่อเครื่อง)

ทำแบบ incremental ก๊อปเฉพาะไฟล์ที่เปลี่ยน ไบต์ของภาพไม่ผ่านบทสนทนา

1. อ่าน `cutoff` จาก `manifest.json` แล้วถามเครื่อง:
   ```bash
   cd "$HOME/mnt/<mountName>"
   echo "COUNT=$(find . -name '*.png' | wc -l)"
   find . -name '*.png' -newermt "@<cutoff>" -printf '%P\n'
   ```
   ไม่มีอะไรโผล่ + `COUNT` เท่าเดิม = จบ
2. `device_stage_files` เฉพาะไฟล์ที่โผล่
3. ```bash
   python3 refresh_images.py                      # ปกติ
   python3 refresh_images.py --inventory inv.txt  # เมื่อ COUNT ไม่ตรง (มีไฟล์ถูกลบ)
   python3 inject.py board.html --images
   ```
4. publish ทับ URL เดิม

โฟลเดอร์โพสต์ใหม่ต้องเติม `"YYYY-MM-DD": "<drive folder id>"` ใน `drive_folders.json`
ถ้าลืม ภาพยังขึ้นปกติ แค่ไม่มีปุ่มไป Drive และสคริปต์จะเตือนชื่อโฟลเดอร์ให้

## ไฟล์ในชุดนี้

- `board_template.html` — เทมเพลตกลาง ไม่มีชื่อแบรนด์ (`__TITLE__`, `__SUBTITLE__`, `__CONFIG__`, `__DATA__`, `__IMAGES__`)
- `config.json` / `config.example.json` — ค่าประจำแบรนด์
- `inject.py` — ประกอบหน้า (`--config` เลือกแบรนด์ · `--images` อัปเดตบล็อกภาพ · `--sql` พิมพ์ SQL)
- `refresh_images.py` — ย่อ/เข้ารหัส/ผสมภาพแบบ incremental + เขียน `manifest.json`
- `drive_folders.json` — วันที่ → id โฟลเดอร์ Drive
- `data.json` / `images.json` / `manifest.json` — ข้อมูลรอบล่าสุด สร้างใหม่ได้เสมอ

## ค้างไว้ (เฟส 3 — ตัดการพึ่งเครื่อง)

ตอนนี้ขั้นตอนอัปเดตภาพยังต้องใช้เครื่องที่ต่อโฟลเดอร์ไว้ ทำให้เจ้าของเครื่องเป็นคอขวด
แก้ได้ด้วยการย้ายภาพไปที่เก็บที่คลาวด์อ่านได้เอง (artifact assets / R2 / GitHub)
แล้วบอร์ดอ้าง URL แทน data URI — หน้าจะเบาลงมากด้วย (ตอนนี้ ~1.8 MB)
