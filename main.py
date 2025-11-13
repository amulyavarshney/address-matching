from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
import os
from dotenv import load_dotenv

from app.models import AddressMatchRequest, AddressMatchResponse
from app.matcher import AddressMatcher

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Address Matching Service",
    description="A RESTful microservice for address matching with fuzzy matching, ML, and geospatial validation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the address matcher
matcher = AddressMatcher()

@app.get("/")
async def root():
    return {"message": "Address Matching Service is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/match-addresses", response_model=AddressMatchResponse)
async def match_addresses(request: AddressMatchRequest):
    """
    Match two addresses and return similarity scores and decision.
    """
    try:
        logger.info(f"Matching addresses: '{request.address1}' vs '{request.address2}'")
        result = await matcher.match_addresses(request.address1, request.address2)
        logger.info(f"Match result: {result.match} (confidence: {result.confidence_score})")
        return result
    except Exception as e:
        logger.error(f"Error matching addresses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 