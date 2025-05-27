"""
Filter Logic Module
Refactored from filtruj_wszystko.py to provide filtering functionality for auction records.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


def get_powiat(polozenie_str: str) -> Optional[str]:
    """
    Extract county (powiat) name from location string.
    
    Args:
        polozenie_str: Location string in format "region/county/municipality/..."
        
    Returns:
        County name or None if not found
    """
    if not polozenie_str:
        return None
    
    # Try to match county - second part after "/"
    match = re.search(r'podkarpackie/\s*(\w+(?:[-\s]+\w+)*)', polozenie_str)
    if match:
        return match.group(1).strip()
    return None


def parse_auction_date(date_string: str) -> Optional[datetime]:
    """
    Parse auction date from string format ("15.04.2025\n9:00") to datetime object.
    
    Args:
        date_string: Date string in format "dd.mm.yyyy\nhh:mm"
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    try:
        # Split date and time
        parts = date_string.strip().split('\n')
        date_part = parts[0]  # e.g., "15.04.2025"
        
        # Split date into day, month, year
        day, month, year = map(int, date_part.split('.'))
        
        # Create datetime object (ignoring time, we only care about date)
        return datetime(year, month, day)
    except Exception:
        return None


def filter_by_location(records: List[Dict], target_location: str) -> List[Dict]:
    """
    Filter records by specific location (city/municipality).
    
    Args:
        records: List of auction records
        target_location: Target location to filter by
        
    Returns:
        Filtered list of records
    """
    return [
        record for record in records 
        if (record.get('miejsce') and target_location in record['miejsce']) or
           (record.get('położenie') and target_location in record['położenie'])
    ]


def filter_by_counties(records: List[Dict], target_counties: List[str]) -> List[Dict]:
    """
    Filter records by specific counties.
    
    Args:
        records: List of auction records
        target_counties: List of target county names
        
    Returns:
        Filtered list of records
    """
    return [
        record for record in records
        if 'położenie' in record and get_powiat(record['położenie']) and 
        any(county.lower() in get_powiat(record['położenie']).lower() 
            for county in target_counties)
    ]


def filter_by_form(records: List[Dict], target_form: str = "sprzedaż") -> List[Dict]:
    """
    Filter records by auction form (e.g., sale vs lease).
    
    Args:
        records: List of auction records
        target_form: Target form (default: "sprzedaż" for sale)
        
    Returns:
        Filtered list of records
    """
    return [
        record for record in records
        if record.get('forma') and record['forma'].lower() == target_form.lower()
    ]


def filter_by_area(records: List[Dict], min_area: float, max_area: Optional[float] = None) -> List[Dict]:
    """
    Filter records by area constraints.
    
    Args:
        records: List of auction records
        min_area: Minimum area in hectares
        max_area: Maximum area in hectares (optional)
        
    Returns:
        Filtered list of records
    """
    filtered = [
        record for record in records
        if record.get('powierzchnia_ogolna') is not None and 
           record['powierzchnia_ogolna'] >= min_area
    ]
    
    if max_area is not None:
        filtered = [
            record for record in filtered
            if record['powierzchnia_ogolna'] <= max_area
        ]
    
    return filtered


def filter_by_price(records: List[Dict], min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[Dict]:
    """
    Filter records by price constraints.
    
    Args:
        records: List of auction records
        min_price: Minimum price in PLN (optional)
        max_price: Maximum price in PLN (optional)
        
    Returns:
        Filtered list of records
    """
    filtered = records[:]
    
    if min_price is not None:
        filtered = [
            record for record in filtered
            if record.get('cena_wywoławcza') is not None and 
               record['cena_wywoławcza'] >= min_price
        ]
    
    if max_price is not None:
        filtered = [
            record for record in filtered
            if record.get('cena_wywoławcza') is not None and 
               record['cena_wywoławcza'] <= max_price
        ]
    
    return filtered


def filter_by_date_range(records: List[Dict], min_days_from_now: int = 7, max_days_from_now: Optional[int] = None) -> List[Dict]:
    """
    Filter records by auction date range.
    
    Args:
        records: List of auction records
        min_days_from_now: Minimum days from today (default: 7)
        max_days_from_now: Maximum days from today (optional)
        
    Returns:
        Filtered list of records
    """
    current_date = datetime.now()
    min_date = current_date + timedelta(days=min_days_from_now)
    max_date = current_date + timedelta(days=max_days_from_now) if max_days_from_now else None
    
    filtered = []
    for record in records:
        if 'data_godzina' in record:
            auction_date = parse_auction_date(record['data_godzina'])
            if auction_date and auction_date >= min_date:
                if max_date is None or auction_date <= max_date:
                    filtered.append(record)
    
    return filtered


def filter_by_property_type(records: List[Dict], property_types: List[str]) -> List[Dict]:
    """
    Filter records by property type.
    
    Args:
        records: List of auction records
        property_types: List of allowed property types (e.g., ["rolna", "budowlana"])
        
    Returns:
        Filtered list of records
    """
    return [
        record for record in records
        if record.get('typ_nieruchomości') and 
           any(prop_type.lower() in record['typ_nieruchomości'].lower() 
               for prop_type in property_types)
    ]


def filter_by_discount(records: List[Dict], min_discount: Optional[int] = None) -> List[Dict]:
    """
    Filter records by discount percentage.
    
    Args:
        records: List of auction records
        min_discount: Minimum discount percentage (optional)
        
    Returns:
        Filtered list of records
    """
    if min_discount is None:
        return records
    
    filtered = []
    for record in records:
        discount_text = record.get('obniżka', '')
        if discount_text:
            # Extract discount percentage from text like "obniżka 50%"
            match = re.search(r'(\d+)', discount_text)
            if match:
                discount_percent = int(match.group(1))
                if discount_percent >= min_discount:
                    filtered.append(record)
        elif min_discount == 0:  # Include records with no discount if min_discount is 0
            filtered.append(record)
    
    return filtered


def calculate_stats(records: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistics for a list of records.
    
    Args:
        records: List of auction records
        
    Returns:
        Dictionary with calculated statistics
    """
    if not records:
        return {
            "count": 0,
            "avg_area": 0,
            "avg_price": 0,
            "min_price": 0,
            "max_price": 0,
            "avg_price_per_hectare": 0
        }
    
    areas = [r['powierzchnia_ogolna'] for r in records if r.get('powierzchnia_ogolna') is not None]
    prices = [r['cena_wywoławcza'] for r in records if r.get('cena_wywoławcza') is not None]
    
    # Calculate price per hectare for records with both area and price
    price_per_hectare = []
    for record in records:
        area = record.get('powierzchnia_ogolna')
        price = record.get('cena_wywoławcza')
        if area and price and area > 0:
            price_per_hectare.append(price / area)
    
    stats = {
        "count": len(records),
        "avg_area": sum(areas) / len(areas) if areas else 0,
        "avg_price": sum(prices) / len(prices) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "avg_price_per_hectare": sum(price_per_hectare) / len(price_per_hectare) if price_per_hectare else 0
    }
    
    return stats


def filter_records(records: List[Dict], filters: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """
    Main filtering function that applies multiple filters to auction records.
    This function returns best offers or relevant results based on specified criteria.
    
    Args:
        records: List of auction records to filter
        filters: Dictionary with filter criteria. Supported keys:
            - location: str - Filter by specific location (e.g., "Trzebownisko")
            - counties: List[str] - Filter by counties (e.g., ["łańcucki", "rzeszowski"])
            - form: str - Filter by auction form (default: "sprzedaż")
            - min_area: float - Minimum area in hectares
            - max_area: float - Maximum area in hectares
            - min_price: float - Minimum price in PLN
            - max_price: float - Maximum price in PLN
            - min_days_from_now: int - Minimum days from today (default: 7)
            - max_days_from_now: int - Maximum days from today
            - property_types: List[str] - Allowed property types
            - min_discount: int - Minimum discount percentage
            - best_offers_only: bool - Apply default "best offers" criteria
    
    Returns:
        List of filtered auction records representing best offers or relevant results
        
    Example:
        >>> records = load_auction_records()
        >>> best_offers = filter_records(records, {
        ...     "best_offers_only": True
        ... })
        >>> len(best_offers)
        15
        >>> custom_filter = filter_records(records, {
        ...     "location": "Trzebownisko",
        ...     "min_area": 0.08,
        ...     "max_price": 20000,
        ...     "min_days_from_now": 7
        ... })
    """
    if not records:
        return []
    
    # Use default filters if none provided
    if filters is None:
        filters = {}
    
    # Apply "best offers" preset if requested
    if filters.get('best_offers_only', False):
        filters.update({
            'location': 'Trzebownisko',
            'counties': ['łańcucki', 'ropczycko sędziszowski', 'rzeszowski'],
            'form': 'sprzedaż',
            'min_area': 0.08,
            'max_price': 20000,
            'min_days_from_now': 7
        })
    
    # Start with all records
    filtered_records = records[:]
    
    # Apply location filter
    if filters.get('location'):
        filtered_records = filter_by_location(filtered_records, filters['location'])
    
    # Apply county filter
    if filters.get('counties'):
        filtered_records = filter_by_counties(filtered_records, filters['counties'])
    
    # Apply form filter (default to "sprzedaż" if not specified)
    form = filters.get('form', 'sprzedaż')
    filtered_records = filter_by_form(filtered_records, form)
    
    # Apply area filters
    min_area = filters.get('min_area')
    max_area = filters.get('max_area')
    if min_area is not None:
        filtered_records = filter_by_area(filtered_records, min_area, max_area)
    
    # Apply price filters
    min_price = filters.get('min_price')
    max_price = filters.get('max_price')
    if min_price is not None or max_price is not None:
        filtered_records = filter_by_price(filtered_records, min_price, max_price)
    
    # Apply date range filter
    min_days = filters.get('min_days_from_now', 7)  # Default to 7 days
    max_days = filters.get('max_days_from_now')
    filtered_records = filter_by_date_range(filtered_records, min_days, max_days)
    
    # Apply property type filter
    if filters.get('property_types'):
        filtered_records = filter_by_property_type(filtered_records, filters['property_types'])
    
    # Apply discount filter
    if filters.get('min_discount') is not None:
        filtered_records = filter_by_discount(filtered_records, filters['min_discount'])
    
    return filtered_records


def get_best_offers(records: List[Dict]) -> List[Dict]:
    """
    Convenience function to get best offers using predefined criteria.
    This replicates the exact logic from filtruj_wszystko.py.
    
    Args:
        records: List of auction records
        
    Returns:
        List of best offer records
    """
    return filter_records(records, {'best_offers_only': True})


# Backward compatibility function for existing code
def main(records: List[Dict], verbose: bool = False) -> Dict[str, Any]:
    """
    Main filtering function for backward compatibility with filtruj_wszystko.py
    
    Args:
        records: List of auction records
        verbose: Whether to print debug information
        
    Returns:
        Dictionary with filtering statistics
    """
    if verbose:
        print("========== FILTERING AUCTIONS - COMPREHENSIVE SCRIPT ==========")
    
    initial_count = len(records)
    
    # Apply best offers filter
    best_offers = get_best_offers(records)
    final_count = len(best_offers)
    
    # Calculate statistics
    stats = calculate_stats(best_offers)
    stats.update({
        "initial_count": initial_count,
        "final_count": final_count,
        "filtered_percent": final_count / initial_count * 100 if initial_count > 0 else 0
    })
    
    if verbose:
        print(f"\nInitial number of auctions: {initial_count}")
        print(f"After applying all filters: {final_count} ({stats['filtered_percent']:.2f}% of initial)")
        print(f"Average area: {stats['avg_area']:.2f} ha")
        print(f"Average price: {stats['avg_price']:.2f} PLN")
        print(f"Price range: {stats['min_price']:.2f} - {stats['max_price']:.2f} PLN")
        print(f"Average price per hectare: {stats['avg_price_per_hectare']:.2f} PLN/ha")
    
    return stats
