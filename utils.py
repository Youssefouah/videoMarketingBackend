from passlib.context import CryptContext
import os
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)


def generate_filename(filename):
    # Get the file extension
    ext = os.path.splitext(filename)[1]

    # Generate a unique filename
    unique_filename = str(uuid.uuid4())

    # Concatenate the filename and extension with the unique filename
    return f"{unique_filename}{ext}"