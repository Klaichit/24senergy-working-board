# 24sEnergy Working Board

บอร์ดงานคอนเทนต์โซเชียล — สะท้อนข้อมูลจาก Notion + ภาพจริงของแต่ละโพสต์ ออกมาเป็นหน้าเดียวที่เปิดแล้ว
กดคัดลอกไปโพสต์ได้เลย ซิงก์อัตโนมัติทุกวัน 08:00

> **repo นี้เป็น public — โค้ดอยู่ในนี้ ค่าประจำอินสแตนซ์ไม่อยู่**
> `config.json` และ `drive_folders.json` ถูก gitignore ไว้ เพราะมีลิงก์บอร์ด (ใครมีลิงก์เปิดได้)
> กับ id ของ Notion และ Drive — ขอไฟล์จริงจากโฟลเดอร์ทีม แล้ววางไว้ข้าง ๆ สคริปต์
> โครงสร้างที่ต้องกรอกดูได้จาก `config.example.json` / `drive_folders.example.json`

## ระบบทำงานยังไง

```
Notion (แหล่งความจริง)  ──┐
                          ├──►  inject.py  ──►  board.html  ──►  Artifact (ลิงก์ที่ทีมเปิด)
โฟลเดอร์ภาพใน Drive  ────┘
```

หน้าบอร์ดเป็น HTML ที่มีตัวเรนเดอร์อยู่ในตัว และเก็บข้อมูลไว้ **สามบล็อกแยกกัน**

| บล็อก | เนื้อหา | เปลี่ยนเมื่อ |
|---|---|---|
| `board-config` | แบรนด์ / label / ขั้นตอน / กฎแฮชแท็ก | แก้ `config.json` |
| `board-data` | แถวจาก Notion | ทุกวัน 08:00 |
| `board-images` | ภาพย่อฝังเป็น data URI | สั่ง “อัปเดตภาพเข้าบอร์ด” |

จับคู่ภาพกับโพสต์ด้วย **วันที่กำหนดเผยแพร่** ที่ตรงกับชื่อโฟลเดอร์ Drive (`YYYY-MM-DD หัวข้อ`)

> **กฎเหล็ก:** งาน sync ที่รันบนคลาวด์แตะได้เฉพาะ `board-data`
> มันเข้าเครื่องไม่ได้ ถ้าเขียนทับ `board-images` ภาพจะหายทั้งบอร์ดและกู้เองไม่ได้

## ใช้งาน

```bash
python3 inject.py                       # ประกอบ board.html จาก template + config + data + images
python3 inject.py board.html            # อัปเดตเฉพาะข้อมูล Notion ในหน้าที่มีอยู่ (งาน sync รายวัน)
python3 inject.py board.html --images   # อัปเดตบล็อกภาพด้วย
python3 inject.py --sql                 # พิมพ์ SQL สำหรับ scheduled task ของแบรนด์นี้
python3 refresh_images.py               # ย่อ/เข้ารหัสภาพที่ stage มา แล้วผสมเข้า images.json
```

ขั้นตอนละเอียด (รวมวิธีอัปเดตภาพแบบ incremental) อยู่ใน [`SYNC.md`](SYNC.md)

## เพิ่มบริษัทใหม่

โค้ดไม่มีชื่อแบรนด์ฝังอยู่เลย เพิ่มบริษัท = เพิ่มไฟล์ config

1. ก๊อป `config.example.json` → `config.<brand>.json` แก้ 8 หมวด (แบรนด์ · locale · Notion · ขั้นตอน · ป้ายสถานะ · แฮชแท็ก · label · ภาพ)
2. `python3 inject.py --config config.<brand>.json --sql` → เอา SQL ไปใส่ scheduled task
3. `python3 inject.py --config config.<brand>.json` → ได้ `board.html`
4. publish เป็น artifact ใหม่ แล้วเอา URL กลับมาใส่ `artifactUrl` ใน config

`config.example.json` เป็นแบรนด์สมมติภาษาอังกฤษ ใช้ทดสอบว่าเทมเพลตยังสะอาดอยู่ —
ถ้าโคลนแล้วรันได้โดยไม่แตะโค้ด แปลว่าพร้อมรับบริษัทถัดไป

## ไฟล์ในนี้

| ไฟล์ | หน้าที่ |
|---|---|
| `board_template.html` | เทมเพลตกลาง ไม่มีชื่อแบรนด์ |
| `config.example.json` | โครงค่าประจำแบรนด์ (ก๊อปเป็น `config.json` แล้วกรอกของจริง) |
| `inject.py` | ประกอบหน้า / พิมพ์ SQL |
| `refresh_images.py` | ย่อและฝังภาพแบบ incremental |
| `drive_folders.example.json` | โครง วันที่ → id โฟลเดอร์ Drive |
| `SYNC.md` | คู่มือปฏิบัติการฉบับเต็ม |

ไฟล์ที่ไม่ commit (`.gitignore`): `config.json` `drive_folders.json` `data.json` `images.json`
`board.html` `manifest.json` — สองตัวแรกมี id/ลิงก์ภายใน ที่เหลือสร้างใหม่ได้เสมอจาก Notion
กับโฟลเดอร์ภาพ และ `data.json` มีร่างแคปชันที่ยังไม่เผยแพร่

## ค้างไว้

ขั้นตอนอัปเดตภาพยังต้องใช้เครื่องที่ต่อโฟลเดอร์ Drive ไว้ ทำให้เจ้าของเครื่องเป็นคอขวด
แก้ได้ด้วยการย้ายภาพไปที่เก็บที่คลาวด์อ่านได้เอง แล้วให้บอร์ดอ้าง URL แทน data URI
(หน้าจะเบาจาก ~1.8 MB เหลือหลักร้อย KB ด้วย)
