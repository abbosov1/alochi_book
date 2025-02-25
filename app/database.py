import aiosqlite

DB_PATH = "database.db"


async def init_db():
    """
    Инициализирует базу данных, создавая таблицу users, если она не существует.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT,
                name TEXT,
                school TEXT
            )
        """)
        await db.commit()


async def user_exists(user_id: int) -> bool:
    """
    Проверяет, существует ли пользователь с данным user_id.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_user(user_id: int, phone: str = None, name: str = None, school: str = None):
    """
    Добавляет пользователя в базу. Если пользователь уже есть, заменяет данные.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, phone, name, school) VALUES (?, ?, ?, ?)",
            (user_id, phone, name, school)
        )
        await db.commit()


async def update_user(user_id: int, phone: str = None, name: str = None, school: str = None):
    """
    Обновляет данные пользователя. Если передано значение None, поле не изменяется.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if phone is not None:
            await db.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        if name is not None:
            await db.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        if school is not None:
            await db.execute("UPDATE users SET school = ? WHERE user_id = ?", (school, user_id))
        await db.commit()


async def get_user(user_id: int):
    """
    Возвращает информацию о пользователе в виде кортежа (user_id, phone, name, school),
    либо None, если пользователь не найден.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, phone, name, school FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row
