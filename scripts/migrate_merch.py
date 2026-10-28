import sqlite3

c = sqlite3.connect('insight_circle.db')
cols = [col[1] for col in c.execute('PRAGMA table_info(merchandise_orders)').fetchall()]
for col_name, col_type in [
    ('currency', 'VARCHAR(10) DEFAULT "KES"'),
    ('payment_status', 'VARCHAR(20) DEFAULT "unpaid"'),
    ('payment_method', 'VARCHAR(30) DEFAULT "mpesa"'),
    ('payment_reference', 'VARCHAR(100)'),
    ('variant_id', 'VARCHAR')
]:
    if col_name not in cols:
        c.execute(f'ALTER TABLE merchandise_orders ADD COLUMN {col_name} {col_type}')
        print(f'Added column {col_name}')
c.commit()
print('Columns now:', [col[1] for col in c.execute('PRAGMA table_info(merchandise_orders)').fetchall()])
