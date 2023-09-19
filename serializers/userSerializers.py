def userEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "mobile": user["mobile"],
        "role": user["role"],
        "views": user["views"],
        "likes": user["likes"],
        "tiktok": user["tiktok"],
        "youtube": user["youtube"],
        "twitter": user["twitter"],
        "facebook": user["facebook"],
        "instagram": user["instagram"],
        "verified": user["verified"],
        "password": user["password"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }


def userResponseEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "mobile": user["mobile"],
        "role": user["role"],
        "verified": user["verified"],
        "views": user["views"],
        "likes": user["likes"],
        "hashtag": user["hashtag"],
        "tiktok": user["tiktok"],
        "youtube": user["youtube"],
        "twitter": user["twitter"],
        "facebook": user["facebook"],
        "instagram": user["instagram"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }


def embeddedUserResponse(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "photo": user["photo"]
    }


def userListEntity(users) -> list:
    return [userEntity(user) for user in users]
