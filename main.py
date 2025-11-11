from fastapi import FastAPI
from routes import marz 
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Mintos Pay",
    description="Payment Gateway For LUCOSMS",
    openapi_url="/openapi.json",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"Mintos 1.0.0": "success"}

app.include_router(marz.router)

