from fastapi import APIRouter, HTTPException, status, Request, Response, Depends, Body
from datetime import datetime, timedelta
from random import randbytes
import hashlib
from pydantic import EmailStr
from bson import ObjectId

from schemas import userSchemas
from serializers.userSerializers import userEntity
from emails.verifyEmail import VerifyEmail
from emails.forgotEmail import ForgotEmail
from database import User
import utils
from oauth2 import AuthJWT, require_user
from config import settings

router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(payload: userSchemas.CreateUserSchema, request: Request):
    # Check if user already exist
    user = User.find_one({"email": payload.email.lower()})
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exist"
        )
    # Compare password and passwordConfirm
    if payload.password != payload.passwordConfirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )
    #  Hash the password
    payload.password = utils.hash_password(payload.password)
    del payload.passwordConfirm
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
        "message": "Verification token successfully sent to your email",
    }


@router.post("/login")
async def login(
    payload: userSchemas.LoginUserSchema,
    response: Response,
    Authorize: AuthJWT = Depends(),
):
    # Check if the user exist
    db_user = User.find_one({"email": payload.email.lower()})
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect Email or Password",
        )
    user = userEntity(db_user)

    # Check if the password is valid
    if not utils.verify_password(payload.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect Email or Password",
        )

    # Create access token
    access_token = Authorize.create_access_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN)
    )

    # Create refresh token
    refresh_token = Authorize.create_refresh_token(
        subject=str(user["id"]),
        expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN),
    )

    # Store refresh and access tokens in cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRES_IN * 60,
        expires=REFRESH_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="logged_in",
        value="True",
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )

    # Send both access
    return {"status": "success", "access_token": access_token, "role": user["role"], "verified": user["verified"]}


@router.get("/refresh")
async def refresh_token(response: Response, Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_refresh_token_required()

        user_id = Authorize.get_jwt_subject()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh access token",
            )
        user = userEntity(User.find_one({"_id": ObjectId(str(user_id))}))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The user belonging to this token no logger exist",
            )
        access_token = Authorize.create_access_token(
            subject=str(user["id"]),
            expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN),
        )
    except Exception as e:
        error = e.__class__.__name__
        if error == "MissingTokenError":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide refresh token",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="logged_in",
        value="True",
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    return {"access_token": access_token}


@router.get("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    Authorize: AuthJWT = Depends(),
    user_id: str = Depends(require_user),
):
    Authorize.unset_jwt_cookies()
    response.set_cookie(
        key="logged_in",
        value="",
        max_age=-1,
        secure=True,
        samesite="none",
        httponly=True,
    )

    return {"status": "success"}


@router.patch("/verifyemail/{token}")
async def verify_me(token: str, response: Response, Authorize: AuthJWT = Depends()):
    hashedCode = hashlib.sha256()
    hashedCode.update(bytes.fromhex(token))
    verification_code = hashedCode.hexdigest()
    db_user = User.find_one({"verification_code": verification_code})
    result = User.find_one_and_update(
        {"verification_code": verification_code},
        {
            "$set": {
                "verification_code": None,
                "verified": True,
                "updated_at": datetime.utcnow(),
            }
        },
        new=True,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verification code or account already verified",
        )
    user = userEntity(db_user)

    # Create access token
    access_token = Authorize.create_access_token(
        subject=str(user["id"]), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN)
    )

    # Create refresh token
    refresh_token = Authorize.create_refresh_token(
        subject=str(user["id"]),
        expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN),
    )

    # Store refresh and access tokens in cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRES_IN * 60,
        expires=REFRESH_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )
    response.set_cookie(
        key="logged_in",
        value="True",
        max_age=ACCESS_TOKEN_EXPIRES_IN * 60,
        expires=ACCESS_TOKEN_EXPIRES_IN * 60,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="none",
    )

    # Send both access
    return {"status": "success", "access_token": access_token, "role": user["role"]}


@router.patch("/resetpassword")
async def reset_password(email: str = Body(..., embed=True)):
    user = User.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account with this email.")

    generated_password = randbytes(10).hex()
    User.find_one_and_update({"email": email}, {"$set": {"password": utils.hash_password(generated_password), "updated_at": datetime.utcnow()}})

    try:
        await ForgotEmail(userEntity(user), generated_password, [EmailStr(email)]).sendResetPassword()
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error sending email",
        )
    return { "status": "success" }