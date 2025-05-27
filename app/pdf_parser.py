"""
PDF Parser Module
Refactored from pdfToText.py to provide a clean function for extracting data from PDF files.
"""

import pdfplumber
import re
import io
from typing import List, Dict, Optional, Union


def safe_float(value: Union[str, None], default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert string to float, handling various formats.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default if conversion fails
    """
    if not value or not isinstance(value, str):
        return default
    
    # Remove all characters that are not digits, dots or minus signs
    cleaned = re.sub(r'[^\d.-]', '', value.replace(",", "."))
    
    try:
        return float(cleaned) if cleaned else default
    except ValueError:
        return default


def safe_int(value: Union[str, None], default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert string to int.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default if conversion fails
    """
    if not value or not isinstance(value, str):
        return default
    
    # Try to extract just numbers if there are any
    match = re.search(r'^\d+', value.strip())
    if match:
        return int(match.group())
    return default


def extract_attributes_and_discount(text: Union[str, None]) -> tuple:
    """
    Extract attributes and discount information from text.
    
    Args:
        text: Text containing attributes and possibly discount info
        
    Returns:
        Tuple of (attributes, discount)
    """
    if not text or not isinstance(text, str):
        return "", ""
    
    # Look for discount pattern in text (obniżka X%)
    discount_match = re.search(r'obni[żz]ka\s+(\d+)\s*%', text.lower())
    
    if discount_match:
        # If discount found, separate it from the text
        discount = f"obniżka {discount_match.group(1)}%"
        # Remove discount fragment from original text
        attributes = re.sub(r'obni[żz]ka\s+\d+\s*%', '', text, flags=re.IGNORECASE).strip()
        return attributes, discount
    else:
        # If no discount, return original text
        return text.strip(), ""


def extract_property_type_and_character(property_text: Union[str, None]) -> tuple:
    """
    Extract property type and character from property description.
    
    Args:
        property_text: Text containing property type and character info
        
    Returns:
        Tuple of (property_type, property_character)
    """
    if not property_text or not isinstance(property_text, str):
        return "", ""
    
    parts = property_text.strip().split('\n')
    property_type = parts[0] if parts else ""
    property_character = parts[1] if len(parts) > 1 else ""
    
    return property_type, property_character


def extract_tables_from_pdf_bytes(pdf_bytes: bytes, verbose: bool = False) -> List[List[str]]:
    """
    Extract table data from PDF bytes.
    
    Args:
        pdf_bytes: PDF file as bytes
        verbose: Whether to print debug information
        
    Returns:
        List of table rows, where each row is a list of cell values
    """
    pdf_file = io.BytesIO(pdf_bytes)
    all_data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page_num, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                if verbose:
                    print(f"Page {page_num + 1}: Found table with {len(table)} rows")
                
                # Skip rows containing headers (e.g., "Cena wywoławcza")
                cleaned_table = [
                    row for row in table 
                    if len(row) > 11 and row[11] is not None and "Cena wywoławcza" not in str(row[11])
                ]
                all_data.extend(cleaned_table)
    
    return all_data


def filter_table_data(table_data: List[List[str]], verbose: bool = False) -> List[List[str]]:
    """
    Filter table data to remove unwanted rows.
    
    Args:
        table_data: Raw table data
        verbose: Whether to print debug information
        
    Returns:
        Filtered table data
    """
    # Filter out rows containing "Razem" in any column
    filtered_data = [
        row for row in table_data 
        if not any("Razem" in str(cell) for cell in row if cell)
    ]
    
    if verbose:
        print(f"After filtering: {len(filtered_data)} rows remaining from {len(table_data)} original rows")
    
    return filtered_data


def process_table_row(row: List[str]) -> Optional[Dict]:
    """
    Process a single table row into structured data.
    
    Args:
        row: List of cell values from a table row
        
    Returns:
        Dictionary with processed row data or None if row is invalid
    """
    if len(row) < 12:  # Minimum expected number of columns
        return None
    
    try:
        # Extract attributes and discount from column 8
        attributes, discount = extract_attributes_and_discount(row[8] if len(row) > 8 else "")
        
        # Extract property type and character from column 7
        property_type, property_character = extract_property_type_and_character(row[7] if len(row) > 7 else "")
        
        processed_row = {
            "lp": safe_int(row[0]) if row[0] else None,
            "data_godzina": row[2] if len(row) > 2 else "",
            "miejsce": row[3] if len(row) > 3 else "",
            "położenie": row[4] if len(row) > 4 else "",
            "forma": row[5] if len(row) > 5 else "",
            "rodzaj_przetargu": row[6] if len(row) > 6 else "",
            "typ_nieruchomości": property_type,
            "charakter_nieruchomości": property_character,
            "atrybuty": attributes,
            "obniżka": discount,
            "powierzchnia_ogolna": safe_float(row[9]) if len(row) > 9 else None,
            "powierzchnia_ur": safe_float(row[10]) if len(row) > 10 else None,
            "cena_wywoławcza": safe_float(row[11]) if len(row) > 11 else None,
            "kolejny_przetarg": safe_int(row[12]) if len(row) > 12 else None,
            "uwagi": row[13] if len(row) > 13 else None
        }
        
        # Check if required fields are present
        required_fields = ["lp", "data_godzina", "miejsce"]
        if all(processed_row[field] for field in required_fields):
            return processed_row
            
    except Exception as e:
        # Log error but continue processing
        print(f"Error processing row: {e}")
        return None
    
    return None


def extract_data_from_pdf(file: bytes) -> List[Dict]:
    """
    Extract and process auction data from PDF file bytes.
    
    This is the main function that extracts table data from a PDF file,
    processes it into structured records, and returns a list of dictionaries
    containing the auction information.
    
    Args:
        file: PDF file content as bytes
        
    Returns:
        List of dictionaries, each containing processed auction record data
        
    Example:
        >>> with open('auctions.pdf', 'rb') as f:
        ...     pdf_bytes = f.read()
        >>> records = extract_data_from_pdf(pdf_bytes)
        >>> len(records)
        203
        >>> records[0]['lp']
        1
        >>> records[0]['cena_wywoławcza']
        50000.0
    """
    try:
        # Extract table data from PDF
        table_data = extract_tables_from_pdf_bytes(file, verbose=False)
        
        # Filter unwanted rows
        filtered_data = filter_table_data(table_data, verbose=False)
        
        # Process each row into structured data
        processed_data = []
        for row in filtered_data:
            processed_row = process_table_row(row)
            if processed_row:
                processed_data.append(processed_row)
        
        return processed_data
        
    except Exception as e:
        raise ValueError(f"Error processing PDF file: {str(e)}")


# Backward compatibility functions for existing code
def extract_tables_from_pdf(pdf_path: str, verbose: bool = False) -> List[List[str]]:
    """
    Extract tables from PDF file path (for backward compatibility).
    
    Args:
        pdf_path: Path to PDF file
        verbose: Whether to print debug information
        
    Returns:
        List of table rows
    """
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    return extract_tables_from_pdf_bytes(pdf_bytes, verbose)


def process_pdf_to_json(pdf_path: str, verbose: bool = False) -> Dict:
    """
    Process PDF file to JSON format (for backward compatibility).
    
    Args:
        pdf_path: Path to PDF file
        verbose: Whether to print debug information
        
    Returns:
        Dictionary with processing statistics
    """
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    processed_data = extract_data_from_pdf(pdf_bytes)
    
    stats = {
        "extracted_rows": len(processed_data),
        "filtered_rows": len(processed_data),
        "processed_rows": len(processed_data),
        "errors": 0
    }
    
    if verbose:
        print(f"Processed {len(processed_data)} records from PDF")
    
    return stats
