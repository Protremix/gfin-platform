import psycopg2
conn = psycopg2.connect("dbname=gfin user=gfin password=GfinSecure2026! host=localhost")
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
for r in cur.fetchall():
    print(r[0])
cur.close()
conn.close()
