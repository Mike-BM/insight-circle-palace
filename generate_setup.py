from app.auth import get_password_hash
import datetime
import uuid

hash = get_password_hash('admin123')
admin_id = str(uuid.uuid4())
now = datetime.datetime.utcnow().isoformat()

# Read alembic sql
with open('init_db.sql', 'r', encoding='utf-16le') as f:
    alembic_sql = f.read()

# Remove COMMIT; from end to append our insert inside the transaction
if alembic_sql.strip().endswith('COMMIT;'):
    alembic_sql = alembic_sql[:alembic_sql.rfind('COMMIT;')]

seed_sql = f"\nINSERT INTO users (id, email, password_hash, full_name, role, status, email_verified, created_at) VALUES ('{admin_id}', 'admin@insightcircle.com', '{hash}', 'Admin User', 'admin', 'active', true, '{now}');\n\nCOMMIT;\n"

with open('setup.sql', 'w', encoding='utf-8') as f:
    f.write(alembic_sql + seed_sql)
