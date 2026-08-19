from app.auth import get_password_hash
import datetime
import uuid

hash = get_password_hash('admin123')
admin_id = str(uuid.uuid4())
now = datetime.datetime.utcnow().isoformat()

sql = f"\nINSERT INTO users (id, email, password_hash, full_name, role, status, email_verified, created_at) VALUES ('{admin_id}', 'admin@insightcircle.com', '{hash}', 'Admin User', 'admin', 'active', true, '{now}');\n"

with open("init_db.sql", "a", encoding="utf-8") as f:
    f.write(sql)
