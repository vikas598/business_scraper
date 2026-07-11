from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from db import insert_listings, get_counts_by
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Business Listings Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Listing(BaseModel):
    business_name: str
    category: str
    city: str
    address: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    source: str


class BulkInsertRequest(BaseModel):
    listings: List[Listing]


@app.get("/")
def root():
    return {"message": "API is running"}


@app.post("/listings/bulk-insert")
def bulk_insert(payload: BulkInsertRequest):
    records = [listing.model_dump() for listing in payload.listings]

    if not records:
        raise HTTPException(status_code=400, detail="No listings provided")

    inserted, failed = insert_listings(records)

    return {
        "message": "Bulk insert complete",
        "inserted": inserted,
        "failed": failed,
        "total_received": len(records)
    }

@app.get("/stats/city-wise")
def city_wise_count():
    return get_counts_by("city")


@app.get("/stats/category-wise")
def category_wise_count():
    return get_counts_by("category")


@app.get("/stats/source-wise")
def source_wise_count():
    return get_counts_by("source")