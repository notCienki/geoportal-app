from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from typing import Optional, List, Dict, Any
import json
import os
import sys
import subprocess
import threading
from pathlib import Path
from pdf_parser import extract_data_from_pdf
from filter_logic import filter_records, get_best_offers, calculate_stats
from selenium_runner import open_in_geoportal, parse_dzialka_info, get_geoportal_url

app = FastAPI(title="Geoportal App", description="PDF processing and geoportal integration API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve index.html from templates folder"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    best_offers_only: Optional[bool] = Query(False, description="Apply best offers filter"),
    location: Optional[str] = Query(None, description="Filter by specific location"),
    min_area: Optional[float] = Query(None, description="Minimum area in hectares"),
    max_area: Optional[float] = Query(None, description="Maximum area in hectares"),
    min_price: Optional[float] = Query(None, description="Minimum price in PLN"),
    max_price: Optional[float] = Query(None, description="Maximum price in PLN"),
    counties: Optional[str] = Query(None, description="Comma-separated list of counties"),
    property_types: Optional[str] = Query(None, description="Comma-separated list of property types"),
    min_days_from_now: Optional[int] = Query(7, description="Minimum days from today"),
    max_days_from_now: Optional[int] = Query(None, description="Maximum days from today"),
    min_discount: Optional[int] = Query(None, description="Minimum discount percentage")
):
    """
    Accept PDF file, extract data with pdfplumber, filter it using the modular filter_logic, and return JSON
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read uploaded file content
        contents = await file.read()
        
        # Extract data from PDF using the new parser
        processed_data = extract_data_from_pdf(contents)
        
        # Build filter parameters
        filters = {}
        
        if best_offers_only:
            filters['best_offers_only'] = True
        else:
            # Apply individual filters
            if location:
                filters['location'] = location
            if min_area is not None:
                filters['min_area'] = min_area
            if max_area is not None:
                filters['max_area'] = max_area
            if min_price is not None:
                filters['min_price'] = min_price
            if max_price is not None:
                filters['max_price'] = max_price
            if counties:
                filters['counties'] = [c.strip() for c in counties.split(',')]
            if property_types:
                filters['property_types'] = [pt.strip() for pt in property_types.split(',')]
            if min_days_from_now is not None:
                filters['min_days_from_now'] = min_days_from_now
            if max_days_from_now is not None:
                filters['max_days_from_now'] = max_days_from_now
            if min_discount is not None:
                filters['min_discount'] = min_discount
        
        # Apply filtering using the new modular filter_logic
        filtered_data = filter_records(processed_data, filters) if filters else processed_data
        
        # Calculate statistics
        stats = calculate_stats(filtered_data)
        
        response = {
            "filename": file.filename,
            "total_records": len(processed_data),
            "filtered_records": len(filtered_data),
            "statistics": stats,
            "applied_filters": filters,
            "data": filtered_data
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/best-offers")
async def get_best_offers_endpoint(file: UploadFile = File(...)):
    """
    Accept PDF file and return only the best offers using predefined criteria
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read uploaded file content
        contents = await file.read()
        
        # Extract data from PDF using the new parser
        processed_data = extract_data_from_pdf(contents)
        
        # Get best offers using predefined criteria
        best_offers = get_best_offers(processed_data)
        
        # Calculate statistics
        stats = calculate_stats(best_offers)
        
        response = {
            "filename": file.filename,
            "total_records": len(processed_data),
            "best_offers_count": len(best_offers),
            "statistics": stats,
            "best_offers": best_offers
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.get("/geoportal/{record_id}")
async def open_geoportal(record_id: int):
    """
    Legacy endpoint - Open record in geoportal using selenium runner
    """
    try:
        # Path to the selenium runner script
        script_path = Path(__file__).parent / "selenium_runner.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Selenium runner script not found")
        
        # Run the selenium script with the record ID
        result = subprocess.run([
            sys.executable, str(script_path), "--record-id", str(record_id)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "message": f"Successfully opened record {record_id} in geoportal", "output": result.stdout}
        else:
            return {"success": False, "message": f"Failed to open record {record_id}", "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Request timeout - selenium script took too long")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening geoportal: {str(e)}")


@app.post("/open-geoportal")
async def open_geoportal_with_record(record: Dict[str, Any]):
    """
    Open geoportal with record data using comprehensive powiat-specific automation
    
    Expected record format:
    {
        "położenie": "podkarpackie/łańcucki/Łańcut/Albigowa/123",
        "lp": 1,
        "other_fields": "..."
    }
    """
    try:
        if 'położenie' not in record:
            raise HTTPException(status_code=400, detail="Record must contain 'położenie' field")
        
        # Parse location data to get detailed information
        dzialka_info = parse_dzialka_info(record['położenie'])
        powiat = dzialka_info.get('powiat', '')
        geoportal_url = get_geoportal_url(powiat)
        
        # Check if automatic search is supported
        supported_powiaty = ["łańcucki", "ropczycko sędziszowski", "rzeszowski"]
        is_automatic_supported = powiat and any(p.lower() in powiat.lower() for p in supported_powiaty)
        
        # Create a message collector for web interface
        messages = []
        
        def web_log_callback(message: str):
            messages.append(message)
            print(f"[Geoportal] {message}")  # Also log to console
        
        # Run selenium automation in a separate thread to avoid blocking
        def run_selenium():
            try:
                open_in_geoportal(record, web_log_callback)
            except Exception as e:
                web_log_callback(f"Selenium automation error: {e}")
        
        # Start selenium automation in background
        selenium_thread = threading.Thread(target=run_selenium)
        selenium_thread.daemon = True
        selenium_thread.start()
        
        return {
            "success": True,
            "message": "Geoportal automation started successfully",
            "details": {
                "powiat": powiat,
                "gmina": dzialka_info.get('gmina', 'Not specified'),
                "obreb": dzialka_info.get('obreb', 'Not specified'),
                "nr_dzialki": dzialka_info.get('nr_dzialki', 'Not specified'),
                "geoportal_url": geoportal_url,
                "automatic_search_supported": is_automatic_supported,
                "automation_type": "Selenium with Chrome automation" if is_automatic_supported else "Manual search required"
            },
            "note": "Browser will open automatically. Check your taskbar/dock for Chrome window."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting geoportal automation: {str(e)}")


@app.post("/parse-location")
async def parse_location_endpoint(data: Dict[str, str]):
    """
    Parse location string and return extracted plot information
    
    Expected format:
    {
        "polozenie": "podkarpackie/łańcucki/Łańcut/Albigowa/123"
    }
    """
    try:
        if 'polozenie' not in data:
            raise HTTPException(status_code=400, detail="Request must contain 'polozenie' field")
        
        polozenie = data['polozenie']
        dzialka_info = parse_dzialka_info(polozenie)
        geoportal_url = get_geoportal_url(dzialka_info.get('powiat', ''))
        
        return {
            "success": True,
            "original_location": polozenie,
            "extracted_data": dzialka_info,
            "geoportal_url": geoportal_url,
            "automation_supported": dzialka_info.get('powiat', '').lower() in ['łańcucki', 'ropczycko sędziszowski', 'rzeszowski']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing location: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
