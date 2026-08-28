import sqlite3
import psycopg

NEON_URL = "postgresql://neondb_owner:npg_hqrO7D5glaKj@ep-round-smoke-ael2llxu-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require"
SQLITE_PATH = "db.sqlite3"

BOOLEAN_COLS = {
    'is_superuser', 'is_staff', 'is_active',
    'is_edited', 'is_deleted', 'is_muted', 'is_read', 'is_pinned'
}

def sync_data():
    print(f"Connecting to SQLite ({SQLITE_PATH})...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print("Connecting to Neon PostgreSQL...")
    pg_conn = psycopg.connect(NEON_URL)
    pg_cur = pg_conn.cursor()

    tables = [
        ('auth_user', 'id'),
        ('core_userprofile', 'id'),
        ('core_post', 'id'),
        ('core_comment', 'id'),
        ('core_like', 'id'),
        ('core_follow', 'id'),
        ('core_story', 'id'),
        ('core_conversation', 'id'),
        ('core_conversationparticipant', 'id'),
        ('core_message', 'id'),
        ('core_messagereaction', 'id'),
    ]

    print("Cleaning any existing partial data in Neon...")
    for table, _ in reversed(tables):
        try:
            pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
        except Exception as e:
            print(f"Truncate notice on {table}: {e}")
    pg_conn.commit()

    for table, pk_col in tables:
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
        if not rows:
            print(f"Table {table}: 0 rows (skipped)")
            continue

        cols = [col[0] for col in sqlite_cur.description]
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))

        insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT ("{pk_col}") DO NOTHING;'

        processed_data = []
        for row in rows:
            row_vals = []
            for c in cols:
                val = row[c]
                if (c in BOOLEAN_COLS or c.startswith('is_') or c.startswith('has_')) and val is not None:
                    row_vals.append(bool(val))
                else:
                    row_vals.append(val)
            processed_data.append(tuple(row_vals))

        pg_cur.executemany(insert_sql, processed_data)
        pg_conn.commit()

        # Update PostgreSQL sequence to match highest id
        try:
            pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), COALESCE((SELECT MAX({pk_col}) FROM {table}), 1));")
            pg_conn.commit()
        except Exception as seq_err:
            pass

        print(f"✓ Synced {len(rows)} rows into {table}")

    print("\n🎉 ALL SQLite data successfully synchronized into Neon PostgreSQL!")
    
    # Verify in PostgreSQL
    print("\n--- Neon Verification ---")
    pg_cur.execute("SELECT id, username, email, is_active FROM auth_user;")
    for u in pg_cur.fetchall():
        print(f"User: #{u[0]} {u[1]} ({u[2]}) - Active: {u[3]}")

    pg_cur.execute("SELECT id, sender_id, content FROM core_message;")
    for m in pg_cur.fetchall():
        print(f"Message: #{m[0]} from user #{m[1]}: {m[2][:45]}...")

    sqlite_conn.close()
    pg_conn.close()

if __name__ == '__main__':
    sync_data()
