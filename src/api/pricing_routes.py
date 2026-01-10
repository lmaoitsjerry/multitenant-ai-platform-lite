"""
Pricing Guide API Routes

Manages hotel rates and pricing for the quote system.
All data stored in BigQuery per-tenant.

Endpoints:
- /api/v1/pricing/rates - CRUD for rates
- /api/v1/pricing/hotels - Hotel management
- /api/v1/pricing/seasons - Season definitions
- /api/v1/pricing/import - Bulk import
"""

import logging
import uuid
import csv
import io
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from google.cloud import bigquery

from config.loader import ClientConfig

logger = logging.getLogger(__name__)

# ==================== Routers ====================

pricing_router = APIRouter(prefix="/api/v1/pricing", tags=["Pricing Guide"])


# ==================== Pydantic Models ====================

class HotelBase(BaseModel):
    """Hotel base model"""
    hotel_name: str = Field(..., min_length=2, max_length=200)
    destination: str
    star_rating: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    adults_only: bool = False
    is_active: bool = True


class HotelCreate(HotelBase):
    pass


class HotelUpdate(BaseModel):
    hotel_name: Optional[str] = None
    destination: Optional[str] = None
    star_rating: Optional[int] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    adults_only: Optional[bool] = None
    is_active: Optional[bool] = None


class RateBase(BaseModel):
    """Rate base model"""
    hotel_name: str
    destination: str
    room_type: str
    meal_plan: str = Field(..., description="BB, HB, FB, AI")
    check_in_date: str  # YYYY-MM-DD
    check_out_date: str  # YYYY-MM-DD
    nights: int = Field(..., ge=1, le=30)
    total_7nights_pps: float = Field(..., description="Per person sharing price")
    total_7nights_single: Optional[float] = None
    total_7nights_child: Optional[float] = None
    flights_adult: Optional[float] = 0
    flights_child: Optional[float] = 0
    transfers_adult: Optional[float] = 0
    transfers_child: Optional[float] = 0
    is_active: bool = True


class RateCreate(RateBase):
    pass


class RateUpdate(BaseModel):
    room_type: Optional[str] = None
    meal_plan: Optional[str] = None
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    nights: Optional[int] = None
    total_7nights_pps: Optional[float] = None
    total_7nights_single: Optional[float] = None
    total_7nights_child: Optional[float] = None
    flights_adult: Optional[float] = None
    flights_child: Optional[float] = None
    transfers_adult: Optional[float] = None
    transfers_child: Optional[float] = None
    is_active: Optional[bool] = None


class SeasonDefinition(BaseModel):
    """Season definition"""
    destination: str
    season_name: str  # High, Low, Shoulder
    start_date: str  # MM-DD
    end_date: str  # MM-DD
    price_multiplier: float = 1.0


class ImportResult(BaseModel):
    """Bulk import result"""
    success: bool
    total_rows: int
    imported: int
    errors: List[Dict[str, Any]]


# ==================== Dependency ====================

_client_configs = {}

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    import os
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")
    
    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")
    
    return _client_configs[client_id]


def get_bigquery_client(config: ClientConfig):
    """Get BigQuery client"""
    try:
        return bigquery.Client(project=config.gcp_project_id)
    except Exception as e:
        logger.error(f"Failed to create BigQuery client: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# ==================== Rate Endpoints ====================

@pricing_router.get("/rates")
async def list_rates(
    destination: Optional[str] = None,
    hotel_name: Optional[str] = None,
    meal_plan: Optional[str] = None,
    is_active: Optional[bool] = True,
    check_in_after: Optional[str] = None,
    check_in_before: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    config: ClientConfig = Depends(get_client_config)
):
    """List rates with optional filters"""
    try:
        client = get_bigquery_client(config)
        
        # Build query - only select columns that exist in the table
        query = f"""
        SELECT 
            rate_id,
            hotel_name,
            hotel_rating,
            destination,
            room_type,
            meal_plan,
            check_in_date,
            check_out_date,
            nights,
            total_7nights_pps,
            total_7nights_single,
            total_7nights_child,
            is_active
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE 1=1
        """
        
        params = []
        
        if destination:
            query += " AND UPPER(destination) = UPPER(@destination)"
            params.append(bigquery.ScalarQueryParameter("destination", "STRING", destination))
        
        if hotel_name:
            query += " AND LOWER(hotel_name) LIKE LOWER(@hotel_name)"
            params.append(bigquery.ScalarQueryParameter("hotel_name", "STRING", f"%{hotel_name}%"))
        
        if meal_plan:
            query += " AND meal_plan = @meal_plan"
            params.append(bigquery.ScalarQueryParameter("meal_plan", "STRING", meal_plan))
        
        if is_active is not None:
            query += " AND is_active = @is_active"
            params.append(bigquery.ScalarQueryParameter("is_active", "BOOL", is_active))
        
        if check_in_after:
            query += " AND check_in_date >= @check_in_after"
            params.append(bigquery.ScalarQueryParameter("check_in_after", "DATE", check_in_after))
        
        if check_in_before:
            query += " AND check_in_date <= @check_in_before"
            params.append(bigquery.ScalarQueryParameter("check_in_before", "DATE", check_in_before))
        
        query += f" ORDER BY hotel_name, check_in_date LIMIT {limit} OFFSET {offset}"
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = client.query(query, job_config=job_config).result()
        
        rates = []
        for row in results:
            rate = dict(row)
            # Convert dates to strings
            if rate.get('check_in_date'):
                rate['check_in_date'] = str(rate['check_in_date'])
            if rate.get('check_out_date'):
                rate['check_out_date'] = str(rate['check_out_date'])
            if rate.get('created_at'):
                rate['created_at'] = rate['created_at'].isoformat()
            if rate.get('updated_at'):
                rate['updated_at'] = rate['updated_at'].isoformat()
            rates.append(rate)
        
        return {
            "success": True,
            "data": rates,
            "count": len(rates)
        }
        
    except Exception as e:
        logger.error(f"Failed to list rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.post("/rates")
async def create_rate(
    rate: RateCreate,
    config: ClientConfig = Depends(get_client_config)
):
    """Create a new rate"""
    try:
        client = get_bigquery_client(config)
        table_id = f"{config.gcp_project_id}.{config.dataset_name}.hotel_rates"
        
        rate_id = f"RATE-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        
        row = {
            "rate_id": rate_id,
            "hotel_name": rate.hotel_name,
            "destination": rate.destination,
            "room_type": rate.room_type,
            "meal_plan": rate.meal_plan,
            "check_in_date": rate.check_in_date,
            "check_out_date": rate.check_out_date,
            "nights": rate.nights,
            "total_7nights_pps": rate.total_7nights_pps,
            "total_7nights_single": rate.total_7nights_single,
            "total_7nights_child": rate.total_7nights_child,
            "flights_adult": rate.flights_adult or 0,
            "flights_child": rate.flights_child or 0,
            "transfers_adult": rate.transfers_adult or 0,
            "transfers_child": rate.transfers_child or 0,
            "is_active": rate.is_active,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        errors = client.insert_rows_json(table_id, [row])
        
        if errors:
            logger.error(f"BigQuery insert errors: {errors}")
            raise HTTPException(status_code=500, detail=f"Failed to create rate: {errors}")
        
        return {
            "success": True,
            "data": {"rate_id": rate_id, **row}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.get("/rates/{rate_id}")
async def get_rate(
    rate_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Get rate by ID"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT * FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE rate_id = @rate_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("rate_id", "STRING", rate_id)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        rate = next((dict(row) for row in results), None)
        
        if not rate:
            raise HTTPException(status_code=404, detail="Rate not found")
        
        # Convert dates
        if rate.get('check_in_date'):
            rate['check_in_date'] = str(rate['check_in_date'])
        if rate.get('check_out_date'):
            rate['check_out_date'] = str(rate['check_out_date'])
        
        return {
            "success": True,
            "data": rate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.put("/rates/{rate_id}")
async def update_rate(
    rate_id: str,
    update: RateUpdate,
    config: ClientConfig = Depends(get_client_config)
):
    """Update a rate"""
    try:
        client = get_bigquery_client(config)
        
        # Build UPDATE query dynamically
        updates = []
        params = [bigquery.ScalarQueryParameter("rate_id", "STRING", rate_id)]
        
        update_data = update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if value is not None:
                updates.append(f"{field} = @{field}")
                
                if field in ['check_in_date', 'check_out_date']:
                    params.append(bigquery.ScalarQueryParameter(field, "DATE", value))
                elif field in ['nights']:
                    params.append(bigquery.ScalarQueryParameter(field, "INT64", value))
                elif field in ['is_active']:
                    params.append(bigquery.ScalarQueryParameter(field, "BOOL", value))
                elif field in ['total_7nights_pps', 'total_7nights_single', 'total_7nights_child',
                              'flights_adult', 'flights_child', 'transfers_adult', 'transfers_child']:
                    params.append(bigquery.ScalarQueryParameter(field, "FLOAT64", value))
                else:
                    params.append(bigquery.ScalarQueryParameter(field, "STRING", value))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = CURRENT_TIMESTAMP()")
        
        query = f"""
        UPDATE `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        SET {', '.join(updates)}
        WHERE rate_id = @rate_id
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        client.query(query, job_config=job_config).result()
        
        # Fetch updated rate
        return await get_rate(rate_id, config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.delete("/rates/{rate_id}")
async def delete_rate(
    rate_id: str,
    hard_delete: bool = False,
    config: ClientConfig = Depends(get_client_config)
):
    """Delete a rate (soft delete by default)"""
    try:
        client = get_bigquery_client(config)
        
        if hard_delete:
            query = f"""
            DELETE FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
            WHERE rate_id = @rate_id
            """
        else:
            query = f"""
            UPDATE `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP()
            WHERE rate_id = @rate_id
            """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("rate_id", "STRING", rate_id)
            ]
        )
        
        client.query(query, job_config=job_config).result()
        
        return {
            "success": True,
            "message": f"Rate {rate_id} {'deleted' if hard_delete else 'deactivated'}"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Bulk Import ====================

@pricing_router.post("/rates/import")
async def import_rates(
    file: UploadFile = File(...),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Bulk import rates from CSV
    
    Expected columns:
    hotel_name, destination, room_type, meal_plan, check_in_date, check_out_date,
    nights, total_7nights_pps, total_7nights_single, total_7nights_child,
    flights_adult, flights_child, transfers_adult, transfers_child
    """
    try:
        # Read CSV
        content = await file.read()
        text = content.decode('utf-8-sig')  # Handle BOM
        reader = csv.DictReader(io.StringIO(text))
        
        client = get_bigquery_client(config)
        table_id = f"{config.gcp_project_id}.{config.dataset_name}.hotel_rates"
        
        rows = []
        errors = []
        now = datetime.utcnow()
        
        for i, row in enumerate(reader, 1):
            try:
                rate_id = f"RATE-{uuid.uuid4().hex[:8].upper()}"
                
                # Validate required fields
                required = ['hotel_name', 'destination', 'room_type', 'meal_plan', 
                           'check_in_date', 'check_out_date', 'nights', 'total_7nights_pps']
                
                missing = [f for f in required if not row.get(f)]
                if missing:
                    errors.append({"row": i, "error": f"Missing fields: {missing}"})
                    continue
                
                rows.append({
                    "rate_id": rate_id,
                    "hotel_name": row['hotel_name'].strip(),
                    "destination": row['destination'].strip(),
                    "room_type": row['room_type'].strip(),
                    "meal_plan": row['meal_plan'].strip().upper(),
                    "check_in_date": row['check_in_date'].strip(),
                    "check_out_date": row['check_out_date'].strip(),
                    "nights": int(row['nights']),
                    "total_7nights_pps": float(row['total_7nights_pps']),
                    "total_7nights_single": float(row.get('total_7nights_single') or 0) or None,
                    "total_7nights_child": float(row.get('total_7nights_child') or 0) or None,
                    "flights_adult": float(row.get('flights_adult') or 0),
                    "flights_child": float(row.get('flights_child') or 0),
                    "transfers_adult": float(row.get('transfers_adult') or 0),
                    "transfers_child": float(row.get('transfers_child') or 0),
                    "is_active": True,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                })
                
            except Exception as e:
                errors.append({"row": i, "error": str(e)})
        
        # Insert in batches
        imported = 0
        batch_size = 500
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            insert_errors = client.insert_rows_json(table_id, batch)
            
            if insert_errors:
                for err in insert_errors:
                    errors.append({"row": i + err.get('index', 0), "error": str(err.get('errors'))})
            else:
                imported += len(batch)
        
        return {
            "success": len(errors) == 0,
            "total_rows": len(rows) + len(errors),
            "imported": imported,
            "errors": errors[:50]  # Limit error output
        }
        
    except Exception as e:
        logger.error(f"Failed to import rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.get("/rates/export")
async def export_rates(
    destination: Optional[str] = None,
    config: ClientConfig = Depends(get_client_config)
):
    """Export rates to CSV format"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT 
            hotel_name, destination, room_type, meal_plan,
            check_in_date, check_out_date, nights,
            total_7nights_pps, total_7nights_single, total_7nights_child,
            flights_adult, flights_child, transfers_adult, transfers_child
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE is_active = TRUE
        """
        
        params = []
        if destination:
            query += " AND UPPER(destination) = UPPER(@destination)"
            params.append(bigquery.ScalarQueryParameter("destination", "STRING", destination))
        
        query += " ORDER BY hotel_name, check_in_date"
        
        job_config = bigquery.QueryJobConfig(query_parameters=params) if params else None
        results = client.query(query, job_config=job_config).result()
        
        # Convert to CSV
        output = io.StringIO()
        writer = None
        
        for row in results:
            row_dict = dict(row)
            if row_dict.get('check_in_date'):
                row_dict['check_in_date'] = str(row_dict['check_in_date'])
            if row_dict.get('check_out_date'):
                row_dict['check_out_date'] = str(row_dict['check_out_date'])
            
            if writer is None:
                writer = csv.DictWriter(output, fieldnames=row_dict.keys())
                writer.writeheader()
            
            writer.writerow(row_dict)
        
        from fastapi.responses import StreamingResponse
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=rates_export_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Hotel Endpoints ====================

@pricing_router.get("/hotels")
async def list_hotels(
    destination: Optional[str] = None,
    is_active: Optional[bool] = True,
    config: ClientConfig = Depends(get_client_config)
):
    """List unique hotels from rates"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT DISTINCT
            hotel_name,
            destination,
            hotel_rating as star_rating,
            MAX(is_active) as is_active
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE 1=1
        """
        
        params = []
        
        if destination:
            query += " AND UPPER(destination) = UPPER(@destination)"
            params.append(bigquery.ScalarQueryParameter("destination", "STRING", destination))
        
        query += " GROUP BY hotel_name, destination, hotel_rating ORDER BY destination, hotel_name"
        
        job_config = bigquery.QueryJobConfig(query_parameters=params) if params else None
        results = client.query(query, job_config=job_config).result()
        
        hotels = [dict(row) for row in results]
        
        return {
            "success": True,
            "data": hotels,
            "count": len(hotels)
        }
        
    except Exception as e:
        logger.error(f"Failed to list hotels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.get("/hotels/{hotel_name}/rates")
async def get_hotel_rates(
    hotel_name: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Get all rates for a specific hotel"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT *
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE LOWER(hotel_name) = LOWER(@hotel_name)
        AND is_active = TRUE
        ORDER BY check_in_date, room_type, meal_plan
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("hotel_name", "STRING", hotel_name)
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        rates = []
        for row in results:
            rate = dict(row)
            if rate.get('check_in_date'):
                rate['check_in_date'] = str(rate['check_in_date'])
            if rate.get('check_out_date'):
                rate['check_out_date'] = str(rate['check_out_date'])
            rates.append(rate)
        
        return {
            "success": True,
            "hotel_name": hotel_name,
            "data": rates,
            "count": len(rates)
        }
        
    except Exception as e:
        logger.error(f"Failed to get hotel rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Destinations & Seasons ====================

@pricing_router.get("/destinations")
async def list_destinations(
    config: ClientConfig = Depends(get_client_config)
):
    """List all destinations with hotel counts"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT 
            destination,
            COUNT(DISTINCT hotel_name) as hotel_count,
            COUNT(*) as rate_count,
            MIN(total_7nights_pps) as min_price,
            MAX(total_7nights_pps) as max_price
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        WHERE is_active = TRUE
        GROUP BY destination
        ORDER BY destination
        """
        
        results = client.query(query).result()
        
        destinations = [dict(row) for row in results]
        
        return {
            "success": True,
            "data": destinations,
            "count": len(destinations)
        }
        
    except Exception as e:
        logger.error(f"Failed to list destinations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pricing_router.get("/stats")
async def get_pricing_stats(
    config: ClientConfig = Depends(get_client_config)
):
    """Get pricing statistics"""
    try:
        client = get_bigquery_client(config)
        
        query = f"""
        SELECT 
            COUNT(*) as total_rates,
            COUNT(DISTINCT hotel_name) as total_hotels,
            COUNT(DISTINCT destination) as total_destinations,
            SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_rates,
            AVG(total_7nights_pps) as avg_price,
            MIN(total_7nights_pps) as min_price,
            MAX(total_7nights_pps) as max_price
        FROM `{config.gcp_project_id}.{config.dataset_name}.hotel_rates`
        """
        
        results = client.query(query).result()
        stats = next((dict(row) for row in results), {})
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get pricing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))