# 🍳 Kitchen Bot – בוט ניהול מלאי למטבח

בוט טלגרם לניהול השלמות ומלאי מטבח בזמן אמת, מחובר ל-Google Sheets.  
עובדים שולחים הודעות בעברית טבעית – המערכת מטפלת בכל השאר.

---

## ✨ יכולות

- **הוספת חוסרים** בשפה טבעית: `חלב 2`, `צריך עגבניות 5`, `חסר מוצרלה`
- **סימון כנקנה**: `קניתי חלב`, `הגיע חלב`, `הושלם בזיליקום`
- **ביטול**: `לא צריך חלב`, `בטל גבינה`, `תמחק עגבניות`
- **שחזור**: `החזר חלב`, `תשחזר מוצרלה`
- **זיהוי שגיאות כתיב**: `מוצרלהה` → מציע `מוצרלה`
- **הצגת רשימה** מסודרת לפי קטגוריות
- **מלאי קבוע** עם השבתה/הפעלה
- **היסטוריה מלאה** של כל הפעולות
- **סיכום יומי** אוטומטי
- **ארכוב יומי** בלחיצת כפתור

---

## 🗂 מבנה הפרויקט

```
kitchen-bot/
├── main.py                  # נקודת כניסה
├── src/
│   ├── bot/
│   │   ├── handlers.py      # טיפול בהודעות חופשיות
│   │   ├── commands.py      # פקודות /command
│   │   ├── keyboards.py     # מקלדות inline
│   │   └── middlewares.py   # rate limiting, הרשאות
│   ├── sheets/
│   │   ├── client.py        # חיבור ל-Google Sheets
│   │   ├── inventory.py     # מלאי קבוע
│   │   ├── completions.py   # השלמות יומיות
│   │   └── history.py       # היסטוריה
│   ├── nlp/
│   │   ├── parser.py        # פיענוח הודעות עברית
│   │   ├── intents.py       # זיהוי כוונות
│   │   └── fuzzy.py         # תיקון שגיאות כתיב
│   └── utils/
│       ├── config.py        # ניהול הגדרות
│       ├── logger.py        # לוגים
│       ├── permissions.py   # הרשאות מנהל/משתמש
│       └── formatters.py    # עיצוב הודעות
├── scripts/
│   ├── setup_sheets.py      # הגדרה ראשונית של Sheets
│   └── backup.py            # ייצוא לקובץ Excel
├── tests/                   # בדיקות pytest
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🚀 התקנה מהירה

### שלב 1 – צור בוט טלגרם

1. פתח שיחה עם [@BotFather](https://t.me/BotFather)
2. שלח `/newbot` ועקוב אחרי ההוראות
3. שמור את ה-**token** שתקבל

### שלב 2 – הגדר Google Sheets

1. עבור ל-[Google Cloud Console](https://console.cloud.google.com)
2. צור פרויקט חדש (או בחר קיים)
3. הפעל את **Google Sheets API** ו-**Google Drive API**
4. צור **Service Account**:
   - IAM & Admin → Service Accounts → Create
   - הורד את קובץ ה-JSON
   - שמור אותו כ-`service_account.json` בתיקיית הפרויקט
5. צור **Google Sheet** חדש וריק
6. שתף אותו עם כתובת האימייל של ה-Service Account (Editor)
7. העתק את ה-**Spreadsheet ID** מה-URL

### שלב 3 – הגדר environment

```bash
cp .env.example .env
```

ערוך את `.env`:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI...
ADMIN_USER_IDS=123456789          # מספר ה-ID שלך בטלגרם
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

> **איך למצוא את ה-ID שלך בטלגרם?** שלח הודעה ל-[@userinfobot](https://t.me/userinfobot)

### שלב 4 – הרצה עם Docker

```bash
# בנייה והפעלה
docker-compose up -d

# צפייה בלוגים
docker-compose logs -f kitchen-bot

# עצירה
docker-compose down
```

### שלב 5 – הגדרת Sheets ראשונית

```bash
# מריץ setup עם מוצרים לדוגמה
docker-compose run --rm kitchen-bot python scripts/setup_sheets.py
```

### שלב 6 – הוסף לקבוצה

1. פתח את קבוצת הטלגרם של המטבח
2. הוסף את הבוט כחבר
3. הענק לו הרשאות לשלוח הודעות

---

## 💬 שימוש

### הוספת חוסרים
```
חלב
חלב 2
צריך חלב 3
חסר מוצרלה
תוסיף עגבניות 5
```

### סימון כנקנה
```
קניתי חלב
הגיע חלב
הושלם בזיליקום
```

### ביטול
```
לא צריך חלב
בטל גבינה
תמחק עגבניות
```

### שחזור
```
החזר חלב
תשחזר מוצרלה
```

### פקודות
| פקודה | תיאור |
|-------|-------|
| `/רשימה` | רשימת השלמות פעילות |
| `/מלאי` | מלאי קבוע |
| `/חפש חלב` | חיפוש מוצר |
| `/דוח` | סיכום יומי |
| `/עזרה` | עזרה |

### פקודות מנהל בלבד
| פקודה | תיאור |
|-------|-------|
| `/יום_חדש` | ארכוב + פתיחת יום חדש |
| `/הוסף_מוצר חלב 6 ליטר` | הוספה למלאי קבוע |
| `/השבת גבינה` | השבתת מוצר |
| `/הפעל גבינה` | הפעלת מוצר מושבת |

---

## 🧪 הרצת בדיקות

```bash
# בתוך Docker
docker-compose run --rm kitchen-bot pytest tests/ -v

# מקומית
pip install -r requirements.txt
pytest tests/ -v
```

---

## 💾 גיבוי ידני

```bash
# ייצוא ל-Excel
docker-compose run --rm kitchen-bot python scripts/backup.py /app/backups

# הפעל גם את שירות הגיבוי האוטומטי
docker-compose --profile backup up -d
```

---

## 🏗 הרצה ללא Docker

```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
# או: venv\Scripts\activate   # Windows

pip install -r requirements.txt
python scripts/setup_sheets.py
python main.py
```

---

## 🔧 הגדרות נוספות

### שינוי רגישות זיהוי שגיאות כתיב
```env
FUZZY_THRESHOLD=75   # 0-100, ברירת מחדל: 75
                     # נמוך יותר = יותר סלחן לשגיאות
```

### שינוי שעת סיכום יומי
```env
DAILY_SUMMARY_HOUR=22
DAILY_SUMMARY_MINUTE=0
```

---

## 🗺 תשתית לעתיד

הקוד בנוי עם הפרדת שכבות ברורה לתמיכה עתידית ב:
- **WhatsApp Business API** – הוסף handler ב-`src/bot/`
- **ממשק web** – `src/sheets/` מהווה API layer מוכן
- **סריקת ברקודים** – הוסף handler לתמונות
- **זיהוי קולי** – Whisper API + `parser.parse(transcribed_text)`
- **דוחות חודשיים** – `src/sheets/history.py` כבר שומר הכל
- **הזמנה לספקים** – ייצוא מ-`completions_manager.get_active()`

---

## 📋 דרישות מערכת

- Python 3.11+
- Docker (מומלץ)
- חשבון Google עם Google Sheets API
- בוט טלגרם (דרך @BotFather)

---

## 📄 רישיון

MIT License – שימוש חופשי לכל מטרה.
