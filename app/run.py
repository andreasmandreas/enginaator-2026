import sys
import asyncio

# psycopg3 async requires SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    # 2. Launch the app
    uvicorn.run("main:app", host="0.0.0.0", port=1488, reload=True)
