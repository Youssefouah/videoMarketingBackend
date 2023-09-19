from fastapi import APIRouter, Depends, Body, HTTPException, status
from bson import ObjectId
from datetime import datetime, timedelta
import calendar

import oauth2
from database import User, Video, Meta
from serializers.userSerializers import userResponseEntity

router = APIRouter()


@router.get("/marketeer", description="gets marketeer stats")
def get_stats(user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({"_id": ObjectId(user_id)})

    stats = {
        "downloads": 0,
        "month_downloads": 0,
        "total_views": 0,
        "total_likes": 0,
        "first_posts": 0,
    }
    stats["downloads"] = Video.count_documents({"marketeer": ObjectId(user_id)})

    start_date = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end_date = datetime.utcnow()

    # define the aggregation pipeline for monthly downloads
    pipeline = [
        # filter the documents by the user ID and the date range
        {
            "$match": {
                "marketeer": ObjectId(user_id),
                "created_at": {"$gte": start_date, "$lte": end_date},
            }
        },
        # project only the fields that we need (in this case just the post ID)
        # group the documents by user ID and count the number of posts for each user
        {"$group": {"_id": None, "count": {"$sum": 1}}},
    ]

    # execute the monthly downloads aggregation pipeline and retrieve the result
    result = Video.aggregate(pipeline)
    for row in result:
        stats["month_downloads"] = row["count"]

    stats["total_views"] = user["views"]
    stats["total_likes"] = user["likes"]

    # specify the start date and calculate the end date (40 days later)
    start_date = user["created_at"]
    end_date = start_date + timedelta(days=40)

    # construct the aggregation pipeline
    pipeline = [
        # match documents with created_at field within the specified period
        {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
        # group by null to count the number of matching documents
        {"$group": {"_id": None, "count": {"$sum": 1}}},
    ]

    # execute the pipeline and retrieve the result
    result = Video.aggregate(pipeline)

    for row in result:
        stats["first_posts"] = row["count"]

    stats["days_left"] = (end_date - datetime.utcnow()).days

    return {"status": "success", "stats": stats}


@router.get("/creator", description="gets creator stats")
def get_creator_stats(user_id: str = Depends(oauth2.require_user)):
    user = userResponseEntity(User.find_one({"_id": ObjectId(user_id)}))

    stats = {
        "cash_prize_1": 2000,
        "month_uploads": 0,
        "total_uploads": 0,
        "cash_prize_2": 0,
        "ranking": 1,
        "creators": 0,
        "champions": [],
        "uploads": 0,
        "total_views": 0,
        "total_likes": 0,
    }
    stats["total_uploads"] = Video.count_documents({})
    stats["creators"] = User.count_documents({"role": "creator"})
    stats["jackpot"] = Meta.find_one({})["rewards"]

    start_date = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end_date = datetime.utcnow()

    # define the aggregation pipeline for monthly uploads
    pipeline = [
        # filter the documents by the user ID and the date range
        {
            "$match": {
                "creator": ObjectId(user_id),
                "created_at": {"$gte": start_date, "$lte": end_date},
            }
        },
        # project only the fields that we need (in this case just the post ID)
        # group the documents by user ID and count the number of posts for each user
        {"$group": {"_id": None, "count": {"$sum": 1}}},
    ]

    # execute the monthly uploads aggregation pipeline and retrieve the result
    result = Video.aggregate(pipeline)
    for row in result:
        stats["month_uploads"] = row["count"]

    result = Video.aggregate(
        [
            {"$group": {"_id": "$creator", "count": {"$sum": 1}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "user_info",
                }
            },
            {"$unwind": "$user_info"},
            {"$sort": {"count": -1}},
            {"$project": {"user_info.name": 1, "count": 1}},
            {"$limit": 5},
        ]
    )

    champions = []
    for doc in result:
        champions.append({"creator": doc["user_info"]["name"], "uploads": doc["count"]})
    stats["champions"] = champions

    # define the aggregation pipeline for views and likes sumup
    pipeline = [
        # match documents belonging to the given user
        {"$match": {"creator": ObjectId(user_id)}},
        # group by null and sum up the likes count
        {"$group": {"_id": None, "uploads": {"$sum": 1}}},
    ]

    stats["total_views"] = user["views"]
    stats["total_likes"] = user["likes"]
    stats["uploads"] = Video.count_documents({"creator": ObjectId(user_id)})

    return {"status": "success", "stats": stats}


@router.post("/jackpot")
async def update_jackpot(jackpot: int = Body(..., embed=True)):
    Meta.update_one({}, {"$set": {"rewards": jackpot}})
    return {"state": "success"}


@router.get("/admin", description="gets dashboard info")
async def get_dashboard_info(user_id: str = Depends(oauth2.require_user)):
    user = User.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You have no permission to get dashboard data!",
        )
    info = {"revenue": 12000000, "brands": 1000, "this_month_revenue": 2000000}
    info["creators"] = User.count_documents({"role": "creator"})
    info["marketeers"] = User.count_documents({"role": "marketeer"})
    info["videos"] = Video.count_documents({})

    pipeline = [
        {
            "$project": {
                "likes": 1,
                "views": 1,
                "tiktoks": {"$size": "$tiktok"},
                "youtubes": {"$size": "$youtube"},
                "twitters": {"$size": "$twitter"},
                "facebooks": {"$size": "$facebook"},
                "instagrams": {"$size": "$instagram"},
            }
        },
        {
            "$group": {
                "_id": None,
                "total_likes": {"$sum": "$likes"},
                "total_views": {"$sum": "$views"},
                "total_tiktoks": {"$sum": "$tiktoks"},
                "total_youtubes": {"$sum": "$youtubes"},
                "total_twitters": {"$sum": "$twitters"},
                "total_facebooks": {"$sum": "$facebooks"},
                "total_instagrams": {"$sum": "$instagrams"},
            }
        },
        {
            "$project": {
                "total_likes": 1,
                "total_views": 1,
                "channels": {
                    "$add": [
                        "$total_tiktoks",
                        "$total_youtubes",
                        "$total_twitters",
                        "$total_facebooks",
                        "$total_instagrams",
                    ]
                },
            }
        },
    ]

    result = list(User.aggregate(pipeline))
    info["likes"] = result[0]["total_likes"]
    info["views"] = result[0]["total_views"]
    info["channels"] = result[0]["channels"]

    start_date = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end_date = datetime.utcnow()
    info["this_month_uploads"] = Video.count_documents(
        {"created_at": {"$gte": start_date, "$lte": end_date}}
    )
    info["this_month_downloads"] = Video.count_documents(
        {
            "created_at": {"$gte": start_date, "$lte": end_date},
            "marketeer": {"$ne": None},
        }
    )

    performance = []

    for i in range(datetime.utcnow().month, 13):
        start_date = datetime.utcnow().replace(
            year=datetime.utcnow().year - 1,
            month=i,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        end_date = datetime.utcnow().replace(
            year=datetime.utcnow().year - 1,
            month=i,
            day=calendar.monthrange(start_date.year, start_date.month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=99,
        )
        unit_uploads = Video.count_documents(
            {"created_at": {"$gte": start_date, "$lte": end_date}}
        )
        unit_downloads = Video.count_documents(
            {
                "created_at": {"$gte": start_date, "$lte": end_date},
                "marketeer": {"$ne": None},
            }
        )
        new_marketeers = User.count_documents(
            {"role": "marketeer", "created_at": {"$gte": start_date, "$lte": end_date}}
        )
        performance.append(
            {
                "uploads": unit_uploads,
                "downloads": unit_downloads,
                "marketeers": new_marketeers,
                "month_abbr": calendar.month_abbr[1:][i - 1]
            }
        )

    for i in range(1, datetime.utcnow().month):
        start_date = datetime.utcnow().replace(
            month=i, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end_date = datetime.utcnow().replace(
            month=i,
            day=calendar.monthrange(start_date.year, start_date.month)[1],
            hour=23,
            minute=59,
            second=59,
            microsecond=99,
        )
        unit_uploads = Video.count_documents(
            {"created_at": {"$gte": start_date, "$lte": end_date}}
        )
        unit_downloads = Video.count_documents(
            {
                "created_at": {"$gte": start_date, "$lte": end_date},
                "marketeer": {"$ne": None},
            }
        )
        new_marketeers = User.count_documents(
            {"role": "marketeer", "created_at": {"$gte": start_date, "$lte": end_date}}
        )
        performance.append(
            {
                "uploads": unit_uploads,
                "downloads": unit_downloads,
                "marketeers": new_marketeers,
                "month_abbr": calendar.month_abbr[1:][i - 1]
            }
        )

    info["performance"] = performance

    return {"status": "success", "info": info}
