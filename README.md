Freelance App — Setup & Database

Prerequisites
- Python 3.8+
- MySQL / MariaDB (XAMPP is fine)
- `mysql` client (for import) or phpMyAdmin

1) Create & import the database
- The project includes `db_schema.sql` which creates the `talenthub_db` schema and tables.
- To import with the `mysql` CLI (run from project root):

```bash
mysql -u root -p < db_schema.sql
```

- If using XAMPP / phpMyAdmin: create a database named `talenthub_db` (utf8mb4) then import `db_schema.sql` through the Import UI.

2) Python environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

If `requirements.txt` is missing, install minimal deps:
```bash
pip install flask mysql-connector-python werkzeug
```

3) Configure the app
- By default app connects to `localhost`, user `root`, empty password, database `talenthub_db` (see `app.py` -> `get_db()`).
- For production, change `app.secret_key` and set a proper DB user/password.

4) Run the app
```bash
python app.py
```

5) Optional: create a DB user (recommended)
```sql
CREATE USER 'talent_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON talenthub_db.* TO 'talent_user'@'localhost';
FLUSH PRIVILEGES;
```

Notes
- `db_schema.sql` contains foreign keys with `ON DELETE CASCADE` for simple cleanup. Adjust as needed.
- Passwords are hashed using Werkzeug — no plaintext stored.

If you want, I can run the import for you now (requires local MySQL client and permissions)."# TalentHub" 
