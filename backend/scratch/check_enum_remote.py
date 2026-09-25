import psycopg2
conn = psycopg2.connect('postgresql://postgres:Arshviro709@db.phovkeqnydbuiwbqxagu.supabase.co:5432/postgres')
cur = conn.cursor()
cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'notificationtype'")
print([r[0] for r in cur.fetchall()])
conn.close()
