import os
import psycopg2
from psycopg2 import sql
import random

# --- DB 설정 ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "stockeye-db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocks_db")

def create_admin_user():
    """테스트용 관리자 사용자를 생성합니다."""
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()

        telegram_admin_id = os.getenv("TELEGRAM_ADMIN_ID")
        if telegram_admin_id:
            telegram_id = int(telegram_admin_id)
            print(f"Using TELEGRAM_ADMIN_ID from environment: {telegram_id}")
        else:
            telegram_id = random.randint(1000000000, 9999999999)
            print(f"TELEGRAM_ADMIN_ID not set, generating random ID: {telegram_id}")

        username = f"admin_{telegram_id}"
        email = f"{username}@test.com"
        
        # Check if user with this telegram_id already exists
        cur.execute(sql.SQL("SELECT telegram_id FROM app_users WHERE telegram_id = %s"), (telegram_id,))
        if cur.fetchone():
            print(f"User with telegram_id {telegram_id} already exists. Skipping creation.")
            cur.close()
            return

        query = sql.SQL("INSERT INTO app_users (username, email, role, telegram_id, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, NOW(), NOW()) RETURNING telegram_id")
        
        cur.execute(query, (username, email, "admin", telegram_id, True))
        
        new_telegram_id = cur.fetchone()[0]
        
        print(f"Admin user created with telegram_id: {new_telegram_id}")

        cur.close()

    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    create_admin_user()