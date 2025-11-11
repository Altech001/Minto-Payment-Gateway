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
                    "amount": 1000,
                    "country": "UG",
                    "reference": uuid.uuid4(),
                    "description": "Payment for services",
                    "callback_url": "https://your-app.com/webhook",
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


from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import httpx
import uuid
from datetime import datetime
from config import settings

app = FastAPI(title="Pay Collections API", version="1.0.0")

# Configuration
MARZ_API_BASE_URL = settings.MARZ_API_BASE_URL
API_CREDENTIALS = settings.MARZ_API_KEY


class CollectionRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (+256xxxxxxxxx)")
    amount: int = Field(..., ge=500, le=10_000_000, description="Amount in UGX (500-10,000,000)")
    country: str = Field(default="UG", description="Country code")
    reference: str = Field(..., description="Unique UUID v4 reference")
    description: Optional[str] = Field(None, max_length=255, description="Payment description")
    callback_url: Optional[str] = Field(None, max_length=255, description="Webhook callback URL")

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        cleaned = ''.join(char for char in v if char.isdigit() or char == '+')
        
        if cleaned.startswith('+256'):
            phone = cleaned
        elif cleaned.startswith('256'):
            phone = '+' + cleaned
        elif cleaned.startswith('0'):
            phone = '+256' + cleaned[1:]
        elif len(cleaned) == 9:
            phone = '+256' + cleaned
        else:
            raise ValueError(
                'Invalid phone number format. '
                'Accepted formats: +256xxxxxxxxx, 256xxxxxxxxx, 0xxxxxxxxx, or xxxxxxxxx'
            )
        
        if not phone.startswith('+256'):
            raise ValueError('Phone number must be a valid Ugandan number')
        
        if len(phone) != 13:  # +256 + 9 digits
            raise ValueError(
                f'Invalid phone number length. Expected 9 digits after country code, got {len(phone) - 4}'
            )
        
        if not phone[4:].isdigit():
            raise ValueError('Phone number must contain only digits after country code')
        
        return phone

    @field_validator('reference')
    @classmethod
    def validate_reference(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Reference must be a valid UUID v4 format')
        if len(v) > 50:
            raise ValueError('Reference must not exceed 50 characters')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "phone_number": "0700000000",
                "amount": 1000,
                "country": "UG",
                "reference": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Payment for services",
                "callback_url": "https://your-app.com/webhook"
            }]
        }
    }


class CollectionResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: dict


class SendMoneyRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (+256xxxxxxxxx)")
    amount: int = Field(..., ge=500, le=10_000_000, description="Amount in UGX (500-10,000,000)")
    country: str = Field(default="UG", description="Country code")
    reference: str = Field(..., description="Unique UUID v4 reference")
    description: Optional[str] = Field(None, max_length=255, description="Payment description")
    callback_url: Optional[str] = Field(None, max_length=255, description="Webhook callback URL")

    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        cleaned = ''.join(char for char in v if char.isdigit() or char == '+')
        
        if cleaned.startswith('+256'):
            phone = cleaned
        elif cleaned.startswith('256'):
            phone = '+' + cleaned
        elif cleaned.startswith('0'):
            phone = '+256' + cleaned[1:]
        elif len(cleaned) == 9:
            phone = '+256' + cleaned
        else:
            raise ValueError(
                'Invalid phone number format. '
                'Accepted formats: +256xxxxxxxxx, 256xxxxxxxxx, 0xxxxxxxxx, or xxxxxxxxx'
            )
        
        if not phone.startswith('+256'):
            raise ValueError('Phone number must be a valid Ugandan number')
        
        if len(phone) != 13:
            raise ValueError(
                f'Invalid phone number length. Expected 9 digits after country code, got {len(phone) - 4}'
            )
        
        if not phone[4:].isdigit():
            raise ValueError('Phone number must contain only digits after country code')
        
        return phone

    @field_validator('reference')
    @classmethod
    def validate_reference(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Reference must be a valid UUID v4 format')
        if len(v) > 50:
            raise ValueError('Reference must not exceed 50 characters')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "phone_number": "0700000000",
                "amount": 500,
                "country": "UG",
                "reference": "123e4567-e89b-12d3-a456-426614174001",
                "description": "Payment Collection For SMS",
                "callback_url": "https://mintospay.vercel.app/webhook/callback"
            }]
        }
    }


@app.post(
    "/collect-money",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    collection: CollectionRequest,
    authorization: Optional[str] = Header(None)
):
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
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
                data=form_data
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get(
    "/collect-money/{collection_uuid}",
)
async def get_collection(
    collection_uuid: str,
    authorization: Optional[str] = Header(None)
):
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MARZ_API_BASE_URL}/collect-money/{collection_uuid}",
                headers={"Authorization": auth_header}
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get(
    "/collect-money/services",
    summary="Get available mobile money services",
    description="Retrieve the list of available mobile money providers"
)
async def get_services(
    authorization: Optional[str] = Header(None)
):
    """
    Get the list of available mobile money services (MTN, Airtel).
    """
    
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MARZ_API_BASE_URL}/collect-money/services",
                headers={"Authorization": auth_header}
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Check if the API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Marz Pay Collections API"
    }


# Webhook receiver endpoint (optional - for receiving callbacks from Marz)
@app.post("/webhook/marz-callback", summary="Receive Marz Pay webhooks")
async def marz_webhook(payload: dict):
    """
    Endpoint to receive webhook notifications from Marz Pay.
    Configure this URL in your Marz Pay dashboard or pass it as callback_url.
    
    Process the webhook payload and update your database accordingly.
    """
    # Log the webhook payload
    print(f"Received webhook: {payload}")
    
    
    return {"status": "received", "message": "Webhook processed successfully"}


# ==================== SEND MONEY (DISBURSEMENT) ENDPOINTS ====================

@app.post(
    "/send-money",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send money to a recipient",
    description="Initiate a mobile money disbursement to a customer",
    tags=["Send Money"]
)
async def send_money(
    send_request: SendMoneyRequest,
    authorization: Optional[str] = Header(None)
):
    
    # Use provided authorization or default credentials
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
    # Prepare form data for Marz API
    form_data = {
        "phone_number": send_request.phone_number,
        "amount": str(send_request.amount),
        "country": send_request.country,
        "reference": send_request.reference,
    }
    
    if send_request.description:
        form_data["description"] = send_request.description
    if send_request.callback_url:
        form_data["callback_url"] = send_request.callback_url
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MARZ_API_BASE_URL}/send-money",
                headers={"Authorization": auth_header},
                data=form_data
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get(
    "/send-money/{transaction_uuid}",
    summary="Get send money details",
    description="Retrieve the status and details of a specific send money transaction",
    tags=["Send Money"]
)
async def get_send_money(
    transaction_uuid: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get the details and current status of a send money transaction.
    
    - **transaction_uuid**: The UUID of the send money transaction
    
    Returns transaction status: pending, processing, successful, failed, or sandbox
    """
    
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MARZ_API_BASE_URL}/send-money/{transaction_uuid}",
                headers={"Authorization": auth_header}
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get(
    "/send-money/services",
    summary="Get available send money services",
    description="Retrieve the list of available mobile money providers for disbursements",
    tags=["Send Money"]
)
async def get_send_money_services(
    authorization: Optional[str] = Header(None)
):
    """
    Get the list of available mobile money services for sending money (MTN, Airtel).
    """
    
    auth_header = authorization or f"Basic {API_CREDENTIALS}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MARZ_API_BASE_URL}/send-money/services",
                headers={"Authorization": auth_header}
            )
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.content else {"error": str(e)}
        raise HTTPException(
            status_code=e.response.status_code,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Failed to connect to Marz Pay API", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An unexpected error occurred", "message": str(e)}
        )


@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Check if the API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Marz Pay Collections API"
    }


# Webhook receiver endpoint (optional - for receiving callbacks from Marz)
@app.post("/webhook/callback",)
async def marz_webhook(payload: dict):

    # print(f"Received webhook: {payload}")
    
    return {"status": "received", {payload}: "Webhook processed successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)