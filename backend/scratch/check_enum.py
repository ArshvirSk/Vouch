import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/vouch')
    rows = await conn.fetch("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'notificationtype'")
    print([r['enumlabel'] for r in rows])
    await conn.close()

asyncio.run(run())
