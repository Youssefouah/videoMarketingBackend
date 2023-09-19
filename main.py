from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from routers import auth, user, video, stats

origins = [settings.CLIENT_ORIGIN, "http://localhost:3000", "https://main.dhizbzme1ajly.amplifyapp.com"]
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(video.router, prefix="/api/videos", tags=["Videos"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])

@app.get("/")
async def health_checker():
    return {"status": "success"}

if __name__ == '__main__':
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=9000)
