from fastapi import APIRouter, HTTPException

from app.dtos.chat_dtos import ChatTestRequest, ChatTestResponse
from app.services.openai_chat_service import OpenAIChatService

router = APIRouter(tags=["chat-test"])


@router.post("/chat-test", response_model=ChatTestResponse)
async def chat_test(body: ChatTestRequest):
    try:
        response = await OpenAIChatService().generate_response(body.message)
    except RuntimeError as exc:
        detail = str(exc)
        if detail == "OPENAI_API_KEY is not configured":
            raise HTTPException(status_code=500, detail=detail) from exc
        raise HTTPException(status_code=502, detail="OpenAI request failed") from exc

    return ChatTestResponse(response=response)
