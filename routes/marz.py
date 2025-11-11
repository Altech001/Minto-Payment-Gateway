#type: ignore
from fastapi import APIRouter, HTTPException, status
from config import settings
from pydantic import BaseModel, Field
from pydantic import field_validator
import uuid
from typing import Optional
import httpx
from fastapi import Header


MARZ_API_BASE_URL = settings.MARZ_API_BASE_URL
API_CREDENTIALS = settings.MARZ_API_KEY

router = APIRouter(
    prefix="/v1/pay",
    tags=["Initialize & Verify"],
)


# Pydantic Models Here
class CollectionRequest(BaseModel):
    phone_number: str = Field(
        ..., description="Phone number with country code (+256xxxxxxxxx)"
    )
    amount: int = Field(
        ..., ge=500, le=10_000_000, description="Amount in UGX (500-10,000,000)"
    )
    country: str = Field(default="UG", description="Country code")
    reference: str = Field(uuid.uuid4(), description="Unique UUID v4 reference")
    description: Optional[str] = Field(
        None, max_length=255, description="Payment description"
    )
    callback_url: Optional[str] = Field(
        None, max_length=255, description="Webhook callback URL"
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        cleaned = "".join(char for char in v if char.isdigit() or char == "+")

        if cleaned.startswith("+256"):
            phone = cleaned
        elif cleaned.startswith("256"):
            phone = "+" + cleaned
        elif cleaned.startswith("0"):
            phone = "+256" + cleaned[1:]
        elif len(cleaned) == 9:
            phone = "+256" + cleaned
        else:
            raise ValueError(
                "Invalid phone number format. "
                "Accepted formats: +256xxxxxxxxx, 256xxxxxxxxx, 0xxxxxxxxx, or xxxxxxxxx"
            )

        if not phone.startswith("+256"):
            raise ValueError("Phone number must be a valid Ugandan number")

        if len(phone) != 13:  # +256 + 9 digits
            raise ValueError(
                f"Invalid phone number length. Expected 9 digits after country code, got {len(phone) - 4}"
            )

        if not phone[4:].isdigit():
            raise ValueError("Phone number must contain only digits after country code")

        return phone

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("Reference must be a valid UUID v4 format")
        if len(v) > 50:
            raise ValueError("Reference must not exceed 50 characters")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "phone_number": "0700000000",
                    "amount": 500,
                    "country": "UG",
                    "reference": uuid.uuid4(),
                    "description": "Payment for services",
                    "callback_url": "https://mintospay.vercel.app/webhook/callback",
                }
            ]
        }
    }


class CollectionResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: dict


@router.post(
    "/initialize",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initialize(
    collection: CollectionRequest
):
    auth_header = f"Basic {API_CREDENTIALS}"

    form_data = {
        "phone_number": collection.phone_number,
        "amount": str(collection.amount),
        "country": collection.country,
        "reference": collection.reference,
    }

    if collection.description:
        form_data["description"] = collection.description
    if collection.callback_url:
        form_data["callback_url"] = collection.callback_url

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MARZ_API_BASE_URL}/collect-money",
                headers={"Authorization": auth_header},
                data=form_data,
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)},
        )


# Verfiy The Transcation Here
@router.get("/verify/{collection_uuid}")
async def verify(collection_uuid: str):
    auth_header = f"Basic {API_CREDENTIALS}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MARZ_API_BASE_URL}/collect-money/{collection_uuid}",
                headers={"Authorization": auth_header},
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)},
        )


# Webhook receiver endpoint
@router.post("/webhook/callback")
async def marz_webhook(payload: dict):
    # print(f"Received webhook: {payload}")
    
    return {"status": "received", {payload}: "Webhook processed successfully"}
