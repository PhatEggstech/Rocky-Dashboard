from mcp_server.local_auth import LocalAuthStore


def test_existing_auth_db_migrates_and_accepts_bod(tmp_path):
    database = tmp_path / "oauth.sqlite3"
    store = LocalAuthStore(str(database))
    store.create_or_replace_user(
        username="existing_admin",
        password="admin-password",
        role="admin",
        name="Existing Admin",
    )

    # Simulate the role constraint used by a release before BOD was introduced.
    with store._connect() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            """
            CREATE TABLE old_users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff')),
                store_id INTEGER,
                staff_id INTEGER,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL
            );
            INSERT INTO old_users SELECT * FROM users;
            DROP TABLE users;
            ALTER TABLE old_users RENAME TO users;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")

    store.create_or_replace_user(
        username="bod_assistant",
        password="bod-password",
        role="bod",
        name="Trợ lý BOD",
    )
    assert store.verify_login("existing_admin", "admin-password") is not None
    assert store.verify_login("bod_assistant", "bod-password")[2] == "bod"
