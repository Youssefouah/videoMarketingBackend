from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from serializers.userSerializers import userResponseEntity, userEntity
from datetime import datetime, timedelta
from random import randbytes
import hashlib
from pydantic import EmailStr
from config import settings

from database import User, Video
from schemas import userSchemas, usualSchemas
import oauth2
import utils
from emails.verifyEmail import VerifyEmail
from emails.contactEmail import ContactEmail

router = APIRouter()


@router.get(
    "/me",
    response_model=userSchemas.UserResponse,
    description="gets profile from cookie",
)
def get_me(user_id: str = Depends(oauth2.require_user)):
    user = userResponseEntity(User.find_one({"_id": ObjectId(user_id)}))
    return {"status": "success", "user": user}


@router.get("/", description="gets users list")
def get_users(user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You have no permission to get users list.",
        )
    # Set the date range (first 40 days)
    start_date = datetime.now() - timedelta(days=40)

    # Define the pipeline stages for aggregation
    pipeline = [
        {
            "$lookup": {
                "from": "videos",
                "localField": "_id",
                "foreignField": "creator",
                "as": "uploads",
            }
        },
        {
            "$lookup": {
                "from": "videos",
                "localField": "_id",
                "foreignField": "marketeer",
                "as": "downloads",
            }
        },
        {
            "$project": {
                "name": 1,
                "role": 1,
                "tiktok": 1,
                "youtube": 1,
                "twitter": 1,
                "facebook": 1,
                "instagram": 1,
                "views": 1,
                "likes": 1,
                "upload_count": {"$size": "$uploads"},
                "download_count": {"$size": "$downloads"},
                "created_at": 1,
                "first_40d_download_count": {
                    "$reduce": {
                        "input": "$downloads",
                        "initialValue": 0,
                        "in": {
                            "$cond": [
                                {"$gte": ["$this.created_at", start_date]},
                                {"$add": ["$$value", 1]},
                                "$$value",
                            ]
                        },
                    }
                },
            }
        },
    ]
    users = User.aggregate(pipeline)
    users_list = []
    for user in users:
        user.pop("_id")
        users_list.append(user)
    return {"status": "success", "users": users_list}


@router.post("/", description="create new user")
async def create_user(
    payload: userSchemas.CreateUserSchema, user_id: str = Depends(oauth2.require_user)
):
    user = User.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You have no permission to create new user!",
        )

    # Check if user already exist
    user = User.find_one({"email": payload.email.lower()})

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exist"
        )

    #  Hash the password
    payload.password = utils.hash_password(payload.password)
    del payload.passwordConfirm
    if payload.role == "creator":
        count = User.count_documents({"role": "creator"})
        payload.hashtag = f"#eurasia{str(count).zfill(10)}"
    payload.email = payload.email.lower()
    payload.created_at = datetime.utcnow()
    payload.updated_at = payload.created_at

    result = User.insert_one(payload.dict())
    new_user = User.find_one({"_id": result.inserted_id})

    try:
        token = randbytes(10)
        hashedCode = hashlib.sha256()
        hashedCode.update(token)
        verification_code = hashedCode.hexdigest()
        User.find_one_and_update(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "verification_code": verification_code,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        # print(token.hex())
        await VerifyEmail(userEntity(new_user), token.hex(), [EmailStr(payload.email)]).sendVerificationCode()
    except Exception as error:
        print(error)
        User.find_one_and_update(
            {"_id": result.inserted_id},
            {"$set": {"verification_code": None, "updated_at": datetime.utcnow()}},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error sending email",
        )
    return {
        "status": "success",
        "message": "Verification token successfully sent to user email",
    }


@router.put("/channel", description="add new channels")
async def add_channel(
    payload: usualSchemas.AddChannelRequestSchema,
    user_id: str = Depends(oauth2.require_user),
):
    User.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {payload.channel_type.lower(): payload.channel_list}},
    )
    return {"status": "success"}


@router.patch("/", description="updates user profile")
async def update_profile(
    payload: usualSchemas.UpdateProfileRequestSchema,
    user_id: str = Depends(oauth2.require_user),
):
    if payload.field_name == "email":
        exsiting = User.find_one({"email": payload.field_data})
        if exsiting:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email is already in use!"
            )
    if payload.field_name == "password":
        if len(payload.field_data) < 8:
            raise HTTPException(
                status_code=status.HTTP_411_LENGTH_REQUIRED,
                detail="Password must be longer than 8 letters.",
            )
        payload.field_data = utils.hash_password(payload.field_data)
    User.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {payload.field_name: payload.field_data}}
    )
    return {"status": "success"}


@router.post("/contact", description="Contact")
async def contact(content: userSchemas.ContactSchema, user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({"_id": ObjectId(user_id)})
    try:
        await ContactEmail(userResponseEntity(user), content.name, content.email, content.message, content.role, [EmailStr(settings.EMAIL_FROM)]).sendContent()
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email Couldn't be sent.")
    return {"status": "success"}