import pdfplumber
import json
import re
import os
import sys

# Funkcja do znajdowania ścieżki do zasobów
def resource_path(relative_path):
    """ Zwraca bezwzględną ścieżkę do zasobu, działa zarówno w trybie development jak i po zapakowaniu """
    try:
        # PyInstaller tworzy folder tymczasowy i przechowuje w nim ścieżkę w _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

def extract_tables_from_pdf(pdf_path, verbose=False):
    """
    Ekstrahuje dane z tabel w pliku PDF.
    
    Args:
        pdf_path: Ścieżka do pliku PDF
        verbose: Czy wypisywać informacje do konsoli
    
    Returns:
        list: Lista z danymi wyekstrahowanymi z tabel
    """
    with pdfplumber.open(pdf_path) as pdf:
        all_data = []
        for page_num, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                if verbose:
                    print(f"Strona {page_num + 1}: Znaleziono tabelę z {len(table)} wierszami")
                # Pomijaj wiersze zawierające nagłówki (np. "Cena wywoławcza")
                cleaned_table = [
                    row for row in table 
                    if len(row) > 11 and row[11] is not None and "Cena wywoławcza" not in str(row[11])
                ]
                all_data.extend(cleaned_table)
        return all_data

def process_pdf_to_json(pdf_path, verbose=False):
    """
    Przetwarza plik PDF do formatu JSON.
    
    Args:
        pdf_path: Ścieżka do pliku PDF
        verbose: Czy wypisywać informacje do konsoli
    
    Returns:
        dict: Słownik ze statystykami przetwarzania
    """
    stats = {}
    
    if verbose:
        print("Rozpoczynam ekstrakcję danych z PDF...")
    tables_data = extract_tables_from_pdf(pdf_path, verbose)
    
    if verbose:
        print(f"Wyodrębniono {len(tables_data)} wierszy danych z PDF")
    
    stats["extracted_rows"] = len(tables_data)
    
    # Function to safely convert string to float, handling various formats
    def safe_float(value, default=None):
        if not value or not isinstance(value, str):
            return default
        
        # Usuń wszystkie znaki niebędące cyframi, kropkami lub minusami
        cleaned = re.sub(r'[^\d.-]', '', value.replace(",", "."))
        
        try:
            return float(cleaned) if cleaned else default
        except ValueError:
            if verbose:
                print(f"Błąd konwersji na float: '{cleaned}' z oryginału '{value}'")
            return default

    # Function to safely convert string to int
    def safe_int(value, default=None):
        if not value or not isinstance(value, str):
            return default
        
        # Try to extract just numbers if there are any
        match = re.search(r'^\d+', value.strip())
        if match:
            return int(match.group())
        return default

    # Funkcja do rozdzielenia tekstu zawierającego informacje o obniżce
    def extract_attributes_and_discount(text):
        if not text or not isinstance(text, str):
            return "", ""
        
        # Szukamy wzorca obniżki w tekście
        obniżka_match = re.search(r'obni[żz]ka\s+(\d+)\s*%', text.lower())
        
        if obniżka_match:
            # Jeśli znaleziono obniżkę, wydziel ją z tekstu
            obniżka = f"obniżka {obniżka_match.group(1)}%"
            # Usuń fragment z obniżką z oryginalnego tekstu
            pozostały_tekst = re.sub(r'obni[żz]ka\s+\d+\s*%', '', text, flags=re.IGNORECASE).strip()
            return pozostały_tekst, obniżka
        else:
            # Jeśli nie ma obniżki, zwróć oryginalny tekst
            return text, ""

    # Filtruj wiersze zawierające "Razem" w dowolnej kolumnie
    filtered_data = [
        row for row in tables_data 
        if not any("Razem" in str(cell) for cell in row)
    ]
    
    if verbose:
        print(f"Po filtrowaniu pozostało {len(filtered_data)} wierszy")
    
    stats["filtered_rows"] = len(filtered_data)
    
    # Pokaż szczegóły dla kilku przykładowych wierszy
    if verbose:
        for i, row in enumerate(filtered_data[:3]):
            try:
                if len(row) < 12:  # Minimalna oczekiwana liczba kolumn
                    print(f"Pominięto wiersz: za mało kolumn ({len(row)})")
                    continue
                    
                print(f"\n--- Wiersz przykładowy {i+1} ---")
                print(f"LP: '{row[0]}'")
                print(f"Data/godzina: '{row[2]}'")
                print(f"Miejsce: '{row[3]}'")
                print(f"Położenie: '{row[4]}'")
                print(f"Forma: '{row[5]}'")
                print(f"Rodzaj przetargu: '{row[6]}'")
                print(f"Rodzaj nieruchomości: '{row[7]}'")
                print(f"Atrybuty/obniżka: '{row[8]}'")
                print(f"Powierzchnia ogólna (kolumna 9): '{row[9]}'")
                print(f"Powierzchnia ur (kolumna 10): '{row[10]}'")
                print(f"Cena wywoławcza (kolumna 11): '{row[11]}'")
                print(f"Kolejny przetarg (kolumna 12): '{row[12]}'")
                print(f"Uwagi (kolumna 13): '{row[13] if len(row) > 13 else ''}'")
                    
            except Exception as e:
                if verbose:
                    print(f"Błąd przy wyświetlaniu wiersza {i+1}: {e}")

    # Wróć do przetworzenia wszystkich wierszy
    processed_data = []
    error_count = 0
    for row in filtered_data:
        try:
            if len(row) < 12:  # Minimalna oczekiwana liczba kolumn
                continue
            
            # Rozdzielamy atrybuty i obniżkę
            atrybuty, obniżka = extract_attributes_and_discount(row[8])
            
            # Rozdzielamy rodzaj i charakter nieruchomości
            rodzaj_nieruchomości = row[7] if row[7] else ""
            parts = rodzaj_nieruchomości.strip().split('\n') if isinstance(rodzaj_nieruchomości, str) else []
            typ_nieruchomości = parts[0] if parts else ""
            charakter_nieruchomości = parts[1] if len(parts) > 1 else ""
                
            processed_row = {
                "lp": row[0],
                "data_godzina": row[2],
                "miejsce": row[3],
                "położenie": row[4],
                "forma": row[5],
                "rodzaj_przetargu": row[6],
                "typ_nieruchomości": typ_nieruchomości,
                "charakter_nieruchomości": charakter_nieruchomości,
                "obniżka": obniżka,
                "atrybuty": atrybuty,
                "powierzchnia_ogolna": safe_float(row[9]),
                "powierzchnia_ur": safe_float(row[10]),
                "cena_wywoławcza": safe_float(row[11]),  # Poprawiona kolumna z ceną (11)
                "kolejny_przetarg": safe_int(row[12]) if len(row) > 12 else None,
                "uwagi": row[13] if len(row) > 13 else None
            }
            
            # Sprawdź czy wymagane pola są wypełnione
            required_fields = ["lp", "data_godzina", "miejsce"]
            if all(processed_row[field] for field in required_fields):
                processed_data.append(processed_row)
                
        except Exception as e:
            error_count += 1
            if verbose:
                print(f"Błąd przy przetwarzaniu wiersza {row[0] if row and len(row) > 0 else 'nieznany'}: {e}")
    
    stats["processed_rows"] = len(processed_data)
    stats["errors"] = error_count
    
    # Zapisz dane do pliku JSON
    output_file = "przetargi.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"przetargi": processed_data}, f, indent=4, ensure_ascii=False)
    
    if verbose:
        print(f"Zapisano {len(processed_data)} wierszy do pliku JSON")
        
    return stats

def main():
    """
    Główna funkcja do uruchamiania z linii poleceń.
    """
    import sys
    
    # Sprawdź czy podano ścieżkę do pliku PDF jako argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        process_pdf_to_json(pdf_path, verbose=True)
    else:
        print("Podaj ścieżkę do pliku PDF jako argument.")
        sys.exit(1)

if __name__ == "__main__":
    main()