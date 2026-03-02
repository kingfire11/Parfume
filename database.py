import aiosqlite
from datetime import datetime

DB_PATH = “perfume.db”

async def init_db():
async with aiosqlite.connect(DB_PATH) as db:
await db.executescript(”””
– Точки продаж
CREATE TABLE IF NOT EXISTS points (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
address TEXT,
sell_price REAL NOT NULL DEFAULT 0,
commission REAL NOT NULL DEFAULT 0,
commission_type TEXT NOT NULL DEFAULT ‘fixed’,  – ‘fixed’ или ‘percent’
last_visit TEXT,
active INTEGER DEFAULT 1
);

```
        -- Ароматы (справочник)
        CREATE TABLE IF NOT EXISTS aromas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        -- Склад (общий)
        CREATE TABLE IF NOT EXISTS warehouse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aroma_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            cost_price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (aroma_id) REFERENCES aromas(id)
        );

        -- Остатки на точках
        CREATE TABLE IF NOT EXISTS point_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id INTEGER NOT NULL,
            aroma_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (point_id) REFERENCES points(id),
            FOREIGN KEY (aroma_id) REFERENCES aromas(id),
            UNIQUE(point_id, aroma_id)
        );

        -- Закупки (приход на склад)
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aroma_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (aroma_id) REFERENCES aromas(id)
        );

        -- Поставки на точки
        CREATE TABLE IF NOT EXISTS supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id INTEGER NOT NULL,
            aroma_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (point_id) REFERENCES points(id),
            FOREIGN KEY (aroma_id) REFERENCES aromas(id)
        );

        -- Инкассации (забрал деньги)
        CREATE TABLE IF NOT EXISTS encashments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            bottles_sold INTEGER NOT NULL DEFAULT 0,
            my_profit REAL NOT NULL DEFAULT 0,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (point_id) REFERENCES points(id)
        );

        -- Расходы
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT
        );
    """)
    await db.commit()
```

# ─── ТОЧКИ ───────────────────────────────────────────────────────────────────

async def get_all_points(active_only=True):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
query = “SELECT * FROM points”
if active_only:
query += “ WHERE active = 1”
query += “ ORDER BY name”
async with db.execute(query) as cursor:
return await cursor.fetchall()

async def get_point(point_id):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(“SELECT * FROM points WHERE id = ?”, (point_id,)) as cursor:
return await cursor.fetchone()

async def add_point(name, address, sell_price, commission, commission_type):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(
“INSERT INTO points (name, address, sell_price, commission, commission_type) VALUES (?, ?, ?, ?, ?)”,
(name, address, sell_price, commission, commission_type)
)
await db.commit()

async def update_point_visit(point_id):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(
“UPDATE points SET last_visit = ? WHERE id = ?”,
(datetime.now().strftime(”%Y-%m-%d %H:%M”), point_id)
)
await db.commit()

# ─── АРОМАТЫ ─────────────────────────────────────────────────────────────────

async def get_all_aromas():
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(“SELECT * FROM aromas ORDER BY name”) as cursor:
return await cursor.fetchall()

async def get_aroma_by_name(name):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(“SELECT * FROM aromas WHERE name = ?”, (name,)) as cursor:
return await cursor.fetchone()

async def add_aroma(name):
async with aiosqlite.connect(DB_PATH) as db:
try:
await db.execute(“INSERT INTO aromas (name) VALUES (?)”, (name,))
await db.commit()
async with db.execute(“SELECT id FROM aromas WHERE name = ?”, (name,)) as cursor:
row = await cursor.fetchone()
return row[0]
except Exception:
async with db.execute(“SELECT id FROM aromas WHERE name = ?”, (name,)) as cursor:
row = await cursor.fetchone()
return row[0] if row else None

# ─── СКЛАД ───────────────────────────────────────────────────────────────────

async def get_warehouse():
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(”””
SELECT w.*, a.name as aroma_name
FROM warehouse w JOIN aromas a ON w.aroma_id = a.id
WHERE w.quantity > 0
ORDER BY a.name
“””) as cursor:
return await cursor.fetchall()

async def get_warehouse_item(aroma_id):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(“SELECT * FROM warehouse WHERE aroma_id = ?”, (aroma_id,)) as cursor:
return await cursor.fetchone()

async def add_to_warehouse(aroma_id, quantity, cost_price):
async with aiosqlite.connect(DB_PATH) as db:
existing = None
async with db.execute(“SELECT * FROM warehouse WHERE aroma_id = ?”, (aroma_id,)) as cursor:
existing = await cursor.fetchone()
if existing:
new_qty = existing[2] + quantity
# Средневзвешенная себестоимость
new_cost = (existing[2] * existing[3] + quantity * cost_price) / new_qty
await db.execute(
“UPDATE warehouse SET quantity = ?, cost_price = ? WHERE aroma_id = ?”,
(new_qty, new_cost, aroma_id)
)
else:
await db.execute(
“INSERT INTO warehouse (aroma_id, quantity, cost_price) VALUES (?, ?, ?)”,
(aroma_id, quantity, cost_price)
)
await db.commit()

async def deduct_from_warehouse(aroma_id, quantity):
async with aiosqlite.connect(DB_PATH) as db:
async with db.execute(“SELECT quantity FROM warehouse WHERE aroma_id = ?”, (aroma_id,)) as cursor:
row = await cursor.fetchone()
if not row or row[0] < quantity:
return False
await db.execute(
“UPDATE warehouse SET quantity = quantity - ? WHERE aroma_id = ?”,
(quantity, aroma_id)
)
await db.commit()
return True

# ─── ОСТАТКИ НА ТОЧКЕ ────────────────────────────────────────────────────────

async def get_point_stock(point_id):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
async with db.execute(”””
SELECT ps.*, a.name as aroma_name
FROM point_stock ps JOIN aromas a ON ps.aroma_id = a.id
WHERE ps.point_id = ? AND ps.quantity > 0
ORDER BY a.name
“””, (point_id,)) as cursor:
return await cursor.fetchall()

async def get_point_total_stock(point_id):
async with aiosqlite.connect(DB_PATH) as db:
async with db.execute(
“SELECT SUM(quantity) FROM point_stock WHERE point_id = ?”, (point_id,)
) as cursor:
row = await cursor.fetchone()
return row[0] or 0

async def add_to_point_stock(point_id, aroma_id, quantity):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(”””
INSERT INTO point_stock (point_id, aroma_id, quantity)
VALUES (?, ?, ?)
ON CONFLICT(point_id, aroma_id)
DO UPDATE SET quantity = quantity + excluded.quantity
“””, (point_id, aroma_id, quantity))
await db.commit()

# ─── ПОСТАВКИ ────────────────────────────────────────────────────────────────

async def add_supply(point_id, aroma_id, quantity):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(
“INSERT INTO supplies (point_id, aroma_id, quantity, date) VALUES (?, ?, ?, ?)”,
(point_id, aroma_id, quantity, datetime.now().strftime(”%Y-%m-%d %H:%M”))
)
await db.commit()

async def get_supplies_history(point_id=None, limit=20):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
if point_id:
query = “””
SELECT s.*, p.name as point_name, a.name as aroma_name
FROM supplies s
JOIN points p ON s.point_id = p.id
JOIN aromas a ON s.aroma_id = a.id
WHERE s.point_id = ?
ORDER BY s.date DESC LIMIT ?
“””
async with db.execute(query, (point_id, limit)) as cursor:
return await cursor.fetchall()
else:
query = “””
SELECT s.*, p.name as point_name, a.name as aroma_name
FROM supplies s
JOIN points p ON s.point_id = p.id
JOIN aromas a ON s.aroma_id = a.id
ORDER BY s.date DESC LIMIT ?
“””
async with db.execute(query, (limit,)) as cursor:
return await cursor.fetchall()

# ─── ИНКАССАЦИИ ──────────────────────────────────────────────────────────────

async def add_encashment(point_id, amount, bottles_sold, my_profit, note=None):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(
“INSERT INTO encashments (point_id, amount, bottles_sold, my_profit, date, note) VALUES (?, ?, ?, ?, ?, ?)”,
(point_id, amount, bottles_sold, my_profit, datetime.now().strftime(”%Y-%m-%d %H:%M”), note)
)
# Уменьшаем остаток на точке (равномерно по всем ароматам — упрощение)
await db.commit()

async def get_encashments(point_id=None, date_from=None, date_to=None):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
conditions = []
params = []
if point_id:
conditions.append(“e.point_id = ?”)
params.append(point_id)
if date_from:
conditions.append(“e.date >= ?”)
params.append(date_from)
if date_to:
conditions.append(“e.date <= ?”)
params.append(date_to)
where = (“WHERE “ + “ AND “.join(conditions)) if conditions else “”
query = f”””
SELECT e.*, p.name as point_name
FROM encashments e JOIN points p ON e.point_id = p.id
{where}
ORDER BY e.date DESC
“””
async with db.execute(query, params) as cursor:
return await cursor.fetchall()

# ─── РАСХОДЫ ─────────────────────────────────────────────────────────────────

async def add_expense(category, amount, note=None):
async with aiosqlite.connect(DB_PATH) as db:
await db.execute(
“INSERT INTO expenses (category, amount, date, note) VALUES (?, ?, ?, ?)”,
(category, amount, datetime.now().strftime(”%Y-%m-%d %H:%M”), note)
)
await db.commit()

async def get_expenses(date_from=None, date_to=None):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
conditions = []
params = []
if date_from:
conditions.append(“date >= ?”)
params.append(date_from)
if date_to:
conditions.append(“date <= ?”)
params.append(date_to)
where = (“WHERE “ + “ AND “.join(conditions)) if conditions else “”
async with db.execute(f”SELECT * FROM expenses {where} ORDER BY date DESC”, params) as cursor:
return await cursor.fetchall()

# ─── СТАТИСТИКА ──────────────────────────────────────────────────────────────

async def get_stats(date_from=None, date_to=None):
async with aiosqlite.connect(DB_PATH) as db:
db.row_factory = aiosqlite.Row
conditions = []
params = []
if date_from:
conditions.append(“e.date >= ?”)
params.append(date_from)
if date_to:
conditions.append(“e.date <= ?”)
params.append(date_to)
where = (“WHERE “ + “ AND “.join(conditions)) if conditions else “”

```
    async with db.execute(f"""
        SELECT
            p.id, p.name,
            SUM(e.amount) as total_revenue,
            SUM(e.bottles_sold) as total_bottles,
            SUM(e.my_profit) as total_profit
        FROM encashments e JOIN points p ON e.point_id = p.id
        {where}
        GROUP BY p.id
        ORDER BY total_profit DESC
    """, params) as cursor:
        return await cursor.fetchall()
```
