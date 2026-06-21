import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://typeahead_user:typeahead_password@localhost:5432/typeahead_db")
    rows = await conn.fetch("SELECT query FROM queries WHERE query LIKE 'iphone%' LIMIT 10;")
    print("Results for iphone%:")
    for r in rows:
        print(r['query'])
    
    rows2 = await conn.fetch("SELECT COUNT(*) FROM queries;")
    print("Total count:", rows2[0]['count'])
    await conn.close()

asyncio.run(main())
