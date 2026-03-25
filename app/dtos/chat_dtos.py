from pydantic import BaseModel, Field


class ChatTestRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatTestResponse(BaseModel):
    response: str
