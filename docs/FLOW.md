# Kitchen Bot – Message Flow Diagram

## Message Processing Flow

```
User sends message in Telegram group
        │
        ▼
  [handlers.py] handle_message()
        │
        ▼
  [parser.py] parse(text)
        │
        ├─── Is it a /command? ──► Ignore (handled by CommandHandler)
        │
        ├─── Detect intent prefix (intents.py)
        │         צריך/חסר/תוסיף → ADD
        │         קניתי/הגיע     → MARK_DONE
        │         לא צריך/בטל   → CANCEL
        │         החזר/שחזר     → RESTORE
        │         (bare text)   → ADD
        │
        ├─── Extract name + quantity + unit
        │
        └─── Fuzzy match against inventory (fuzzy.py)
                  │
                  ├─ Exact match (confidence=1.0) ──────────────────────┐
                  │                                                       │
                  ├─ Good fuzzy match (confidence≥0.85) ─────────────────┤
                  │                                                       │
                  └─ Poor match (confidence<0.85) ──► Show confirmation  │
                         keyboard → user confirms → continue             │
                                                                         ▼
                                                              [handlers.py] _process_parsed()
                                                                         │
                                                   ┌─────────────────────┼─────────────────────┐
                                                   ▼                     ▼                     ▼
                                              ADD intent          MARK_DONE intent       CANCEL intent
                                                   │                     │                     │
                                                   ▼                     ▼                     ▼
                                         Is product in         completions_manager      completions_manager
                                         inventory?            .set_status("נקנה")     .set_status("בוטל")
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                     ▼
                               Known product        Unknown product
                                    │                     │
                                    ▼                     ▼
                         completions_manager      Show keyboard:
                         .add_or_update()         [Add to inventory]
                              │                   [Today only]
                         ┌────┴────┐              [Cancel]
                         ▼         ▼
                       Added    Updated
                    (new row)   (accumulate qty)
                         │
                         ▼
                   history_manager
                   .log_action()
                         │
                         ▼
                   Reply to user
```

## Data Model

### מלאי קבוע (Permanent Inventory)
```
מזהה מוצר | שם מוצר | קטגוריה | כמות יעד | יחידת מידה | פעיל | הערות
A1B2C3D4  | חלב      | גבינות   | 6         | ליטר        | TRUE |
```

### השלמות להיום (Today's Completions)
```
תאריך    | שעה   | שם מוצר | כמות | יחידה | קטגוריה | מי דיווח | מקור    | סטטוס | הערות
15/06/24 | 09:30 | חלב      | 2    | ליטר  | גבינות  | דני      | telegram| פתוח  |
```

### היסטוריה (History / Audit Log)
```
תאריך    | שעה   | פעולה       | שם מוצר | כמות | יחידה | מי ביצע | הודעה מקורית | פרטים
15/06/24 | 09:30 | הוספת חוסר | חלב      | 2    | ליטר  | דני     | חלב 2        |
15/06/24 | 11:00 | סימון נקנה | חלב      |      |       | רחל     | קניתי חלב    |
```
