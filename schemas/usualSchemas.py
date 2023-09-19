from pydantic import BaseModel

class AddChannelRequestSchema(BaseModel):
    channel_type: str
    channel_list: list

class UpdateProfileRequestSchema(BaseModel):
    field_name: str
    field_data: str