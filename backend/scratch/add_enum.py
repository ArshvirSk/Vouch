import psycopg2
conn = psycopg2.connect('postgresql://postgres:Arshviro709@db.phovkeqnydbuiwbqxagu.supabase.co:5432/postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'VOTE_REMINDER'")
print("Added VOTE_REMINDER to notificationtype")
conn.close()
