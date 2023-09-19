from fastapi import APIRouter, UploadFile, File, Depends, Body, HTTPException, status
import oauth2
import aiofiles
from bson.objectid import ObjectId
from datetime import datetime

from database import User, Video
from utils import generate_filename
from schemas.videoSchemas import VideoBaseSchema

router = APIRouter()

@router.post("/upload")
async def upload_videos(files: list[UploadFile] = File(...), hashtags: str = Body(..., embed=True), user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "creator":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You have no permission to upload videos.")

    current_time = datetime.utcnow()
    hash_array = hashtags.split(",")
    hash_array.append(user["hashtag"])

    for file in files:
        generated_name = generate_filename(file.filename)
        video_doc = VideoBaseSchema(filename=generated_name, creator=ObjectId(user_id), hashtags=hash_array, uploaded_at=current_time, created_at=current_time, updated_at=current_time)
        destination_file_path = f"./static/uploads/{generated_name}"
        async with aiofiles.open(destination_file_path, 'wb') as out_file:
            while content := await file.read(1024):
                await out_file.write(content)
        Video.insert_one(video_doc.dict())
        
    return {"status": "success"}

@router.get("/downloadable")
async def get_downloadable_videos(user_id: str = Depends(oauth2.require_user)):
    availables = Video.find({"$or": [{"marketeer": {"$exists": False}}, {"marketeer": {"$eq": None}}]})
    videos = []

    for row in availables:
        videos.append({"_id": str(row["_id"]), "src": row["filename"]})

    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = datetime.utcnow()

    # define the aggregation pipeline for monthly downloads
    pipeline = [
        # filter the documents by the user ID and the date range
        {'$match': {'marketeer': ObjectId(user_id), 'downloaded_at': {'$gte': start_date, '$lte': end_date}}},
        # project only the fields that we need (in this case just the post ID)
        # group the documents by user ID and count the number of posts for each user
        {'$group': {'_id': None, 'count': {'$sum': 1}}}
    ]

    # execute the monthly downloads aggregation pipeline and retrieve the result
    day_download = 0
    result = Video.aggregate(pipeline)
    for row in result:
        day_download = row["count"]

    downloaded_today = Video.find({"marketeer": ObjectId(user_id), "downloaded_at": {'$gte': start_date, '$lte': end_date}})
    today_list = []
    for row in downloaded_today:
        today_list.append({"_id": str(row["_id"]), "hashtags": row["hashtags"]})

    return {"status": "success", "videos": videos, "day_download": day_download, "today_list": today_list}

@router.put("/download")
async def download_videos(video_id: str = Body(..., embed=True), user_id: str = Depends(oauth2.require_user)):
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = datetime.utcnow()

    # define the aggregation pipeline for monthly downloads
    pipeline = [
        # filter the documents by the user ID and the date range
        {'$match': {'marketeer': ObjectId(user_id), 'downloaded_at': {'$gte': start_date, '$lte': end_date}}},
        # project only the fields that we need (in this case just the post ID)
        # group the documents by user ID and count the number of posts for each user
        {'$group': {'_id': None, 'count': {'$sum': 1}}}
    ]

    # execute the monthly downloads aggregation pipeline and retrieve the result
    day_download = 0
    result = Video.aggregate(pipeline)
    for row in result:
        day_download = row["count"]

    if day_download == 3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't exceed daily downloads limit.")

    video = Video.find_one({"_id": ObjectId(video_id)})
    Video.update_one({"_id": ObjectId(video_id)}, {"$set": {"marketeer": ObjectId(user_id), "downloaded_at": datetime.utcnow()}})

    return {"status": "success", "src": video["filename"]}
