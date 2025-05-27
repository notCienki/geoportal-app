import json
import re
from datetime import datetime, timedelta
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

def main(verbose=False):
    """
    Funkcja filtrująca przetargi
    
    Args:
        verbose: Czy wypisywać informacje do konsoli
    
    Returns:
        dict: Słownik ze statystykami filtrowania
    """
    if verbose:
        print("========== FILTROWANIE PRZETARGÓW - KOMPLEKSOWY SKRYPT ==========")
    
    stats = {}
    
    # 1. WCZYTANIE DANYCH WEJŚCIOWYCH
    input_file = resource_path('przetargi.json')
    if verbose:
        print(f"\n[1/6] Wczytywanie danych z pliku {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            all_count = len(data['przetargi'])
            if verbose:
                print(f"      Wczytano {all_count} przetargów")
            
            stats["all_count"] = all_count
    except Exception as e:
        if verbose:
            print(f"BŁĄD: Nie udało się wczytać pliku {input_file}: {e}")
        stats["error"] = f"Nie udało się wczytać pliku {input_file}: {str(e)}"
        return stats
    
    # 2. FILTR: TYLKO PRZETARGI Z TRZEBOWNISKA
    if verbose:
        print(f"\n[2/6] Filtrowanie przetargów z Trzebowniska...")
    trzebownisko_przetargi = [
        przetarg for przetarg in data['przetargi'] 
        if (przetarg.get('miejsce') and 'Trzebownisko' in przetarg['miejsce']) or
           (przetarg.get('położenie') and 'Trzebownisko' in przetarg['położenie'])
    ]
    trzebownisko_count = len(trzebownisko_przetargi)
    if verbose:
        print(f"      Znaleziono {trzebownisko_count} przetargów z Trzebowniska ({trzebownisko_count/all_count*100:.1f}% całości)")
    
    stats["trzebownisko_count"] = trzebownisko_count
    stats["trzebownisko_percent"] = trzebownisko_count/all_count*100 if all_count > 0 else 0
    
    # 3. FILTR: TYLKO WYBRANE POWIATY
    if verbose:
        print(f"\n[3/6] Filtrowanie według powiatów...")
    powiaty = ["łańcucki", "ropczycko sędziszowski", "rzeszowski"]
    
    # Funkcja do wyodrębnienia nazwy powiatu z pola "położenie"
    def get_powiat(polozenie_str):
        if not polozenie_str:
            return None
        
        # Próba dopasowania powiatu - druga część po "/"
        match = re.search(r'podkarpackie/\s*(\w+(?:[-\s]+\w+)*)', polozenie_str)
        if match:
            return match.group(1).strip()
        return None
    
    # Filtruj przetargi z wybranych powiatów
    powiat_przetargi = [
        przetarg for przetarg in trzebownisko_przetargi
        if 'położenie' in przetarg and get_powiat(przetarg['położenie']) and 
        any(p.lower() in get_powiat(przetarg['położenie']).lower() for p in powiaty)
    ]
    
    # Statystyki znalezionych przetargów według powiatów
    powiat_stats = {}
    for przetarg in powiat_przetargi:
        powiat = get_powiat(przetarg['położenie'])
        if powiat:
            powiat_stats[powiat] = powiat_stats.get(powiat, 0) + 1
    
    powiat_count = len(powiat_przetargi)
    if verbose:
        print(f"      Znaleziono {powiat_count} przetargów z wybranych powiatów ({powiat_count/trzebownisko_count*100:.1f}% z Trzebowniska)")
        print("      Liczba przetargów według powiatów:")
        for powiat, count in powiat_stats.items():
            print(f"      - {powiat}: {count}")
    
    stats["powiat_count"] = powiat_count
    stats["powiat_percent"] = powiat_count/trzebownisko_count*100 if trzebownisko_count > 0 else 0
    stats["powiat_stats"] = powiat_stats
    
    # 4. FILTR: TYLKO SPRZEDAŻ
    if verbose:
        print(f"\n[4/6] Filtrowanie przetargów ze sprzedażą...")
    sprzedaz_przetargi = [
        przetarg for przetarg in powiat_przetargi
        if przetarg.get('forma') and przetarg['forma'].lower() == 'sprzedaż'
    ]
    
    sprzedaz_count = len(sprzedaz_przetargi)
    if verbose:
        print(f"      Znaleziono {sprzedaz_count} przetargów ze sprzedażą ({sprzedaz_count/powiat_count*100:.1f}% z wybranych powiatów)")
    
    stats["sprzedaz_count"] = sprzedaz_count
    stats["sprzedaz_percent"] = sprzedaz_count/powiat_count*100 if powiat_count > 0 else 0
    
    # 5. FILTR: MINIMALNA POWIERZCHNIA 0.08 ha
    if verbose:
        print(f"\n[5/6] Filtrowanie według minimalnej powierzchni...")
    MIN_POWIERZCHNIA = 0.08
    
    duze_dzialki = [
        przetarg for przetarg in sprzedaz_przetargi
        if przetarg.get('powierzchnia_ogolna') is not None and przetarg['powierzchnia_ogolna'] >= MIN_POWIERZCHNIA
    ]
    
    duze_count = len(duze_dzialki)
    avg_area = 0
    if duze_count > 0:
        avg_area = sum(p['powierzchnia_ogolna'] for p in duze_dzialki if p.get('powierzchnia_ogolna') is not None) / duze_count
    
    if verbose:
        print(f"      Znaleziono {duze_count} działek o powierzchni ≥ {MIN_POWIERZCHNIA} ha ({duze_count/sprzedaz_count*100:.1f}% ze sprzedaży)")
        if duze_count > 0:
            print(f"      Średnia powierzchnia dużych działek: {avg_area:.2f} ha")
    
    stats["duze_count"] = duze_count
    stats["duze_percent"] = duze_count/sprzedaz_count*100 if sprzedaz_count > 0 else 0
    stats["avg_area"] = avg_area
    
    # 6. FILTR: MAKSYMALNA CENA 20 000 zł
    if verbose:
        print(f"\n[6/6] Filtrowanie według maksymalnej ceny...")
    MAX_CENA = 20000
    
    tanie_dzialki = [
        przetarg for przetarg in duze_dzialki
        if przetarg.get('cena_wywoławcza') is not None and przetarg['cena_wywoławcza'] <= MAX_CENA
    ]
    
    tanie_count = len(tanie_dzialki)
    
    # Statystyki cenowe
    avg_price = 0
    min_price = 0
    max_price = 0
    if tanie_count > 0:
        avg_price = sum(p['cena_wywoławcza'] for p in tanie_dzialki if p.get('cena_wywoławcza') is not None) / tanie_count
        min_price = min(p['cena_wywoławcza'] for p in tanie_dzialki if p.get('cena_wywoławcza') is not None)
        max_price = max(p['cena_wywoławcza'] for p in tanie_dzialki if p.get('cena_wywoławcza') is not None)
    
    if verbose:
        print(f"      Znaleziono {tanie_count} działek z ceną ≤ {MAX_CENA} zł ({tanie_count/duze_count*100:.1f}% z dużych działek)")
        if tanie_count > 0:
            print(f"      Statystyki cenowe:")
            print(f"      - Średnia cena: {avg_price:.2f} zł")
            print(f"      - Minimalna cena: {min_price:.2f} zł")
            print(f"      - Maksymalna cena: {max_price:.2f} zł")
    
    stats["tanie_count"] = tanie_count
    stats["tanie_percent"] = tanie_count/duze_count*100 if duze_count > 0 else 0
    stats["avg_price"] = avg_price
    stats["min_price"] = min_price
    stats["max_price"] = max_price
    
    # 7. FILTR: PRZETARGI ODBYWAJĄCE SIĘ CO NAJMNIEJ 7 DNI PO DZISIEJSZEJ DACIE
    if verbose:
        print(f"\n[7/7] Filtrowanie według daty przetargu...")
    
    # Pobierz aktualną datę
    OBECNA_DATA = datetime.now()
    MIN_DNI_DO_PRZETARGU = 7
    DATA_GRANICZNA = OBECNA_DATA + timedelta(days=MIN_DNI_DO_PRZETARGU)
    
    # Funkcja do konwersji formatu daty z pliku ("15.04.2025\n9:00") na obiekt datetime
    def parse_date(date_string):
        try:
            # Rozdziel datę i godzinę
            parts = date_string.strip().split('\n')
            date_part = parts[0]  # np. "15.04.2025"
            
            # Podziel datę na dzień, miesiąc, rok
            day, month, year = map(int, date_part.split('.'))
            
            # Utwórz obiekt datetime (pomijamy czas, bo interesuje nas tylko data)
            return datetime(year, month, day)
        except Exception as e:
            if verbose:
                print(f"Błąd przetwarzania daty '{date_string}': {e}")
            return None
    
    # Filtruj tylko przetargi, które odbędą się co najmniej 7 dni po obecnej dacie
    aktualne_przetargi = []
    for przetarg in tanie_dzialki:
        if 'data_godzina' in przetarg:
            data_przetargu = parse_date(przetarg['data_godzina'])
            if data_przetargu and data_przetargu >= DATA_GRANICZNA:
                aktualne_przetargi.append(przetarg)
    
    aktualne_count = len(aktualne_przetargi)
    
    if verbose:
        print(f"      Dzisiejsza data: {OBECNA_DATA.strftime('%d.%m.%Y')}")
        print(f"      Minimalna data przetargu: {DATA_GRANICZNA.strftime('%d.%m.%Y')} (co najmniej {MIN_DNI_DO_PRZETARGU} dni od dzisiaj)")
        print(f"      Znaleziono {aktualne_count} przetargów odbywających się po {DATA_GRANICZNA.strftime('%d.%m.%Y')}")
        print(f"      ({aktualne_count/tanie_count*100:.1f}% z tanich działek)")
    
    stats["aktualne_count"] = aktualne_count
    stats["aktualne_percent"] = aktualne_count/tanie_count*100 if tanie_count > 0 else 0
    
    # Zapisz ostateczne wyniki do pliku JSON
    final_data = {'przetargi': aktualne_przetargi}
    output_filename = 'przetargi_najlepsze_oferty.json'
    
    with open(output_filename, 'w', encoding='utf-8') as file:
        json.dump(final_data, file, indent=4, ensure_ascii=False)
    
    # PODSUMOWANIE
    if verbose:
        print("\n========== PODSUMOWANIE FILTROWANIA ==========")
        print(f"Początkowa liczba przetargów: {all_count}")
        print(f"Po zastosowaniu wszystkich filtrów: {aktualne_count} ({aktualne_count/all_count*100:.2f}% początkowej liczby)")
        print(f"Zapisano wyniki do pliku: {output_filename}")
    
    stats["filtered_percent"] = aktualne_count/all_count*100 if all_count > 0 else 0
    
    # Wyświetl znalezione przetargi
    if aktualne_count > 0 and verbose:
        print("\nOTO NAJLEPSZE OFERTY SPEŁNIAJĄCE WSZYSTKIE KRYTERIA:")
        for i, przetarg in enumerate(aktualne_przetargi, 1):
            data_przetargu = parse_date(przetarg['data_godzina'])
            dni_do_przetargu = (data_przetargu - OBECNA_DATA).days
            print(f"\n{i}. Przetarg (LP: {przetarg['lp']}):")
            print(f"   Data: {przetarg['data_godzina'].split()[0]} (za {dni_do_przetargu} dni)")
            print(f"   Położenie: {przetarg['położenie']}")
            print(f"   Typ: {przetarg['typ_nieruchomości']}")
            print(f"   Powierzchnia: {przetarg['powierzchnia_ogolna']} ha")
            print(f"   Cena: {przetarg['cena_wywoławcza']} zł ({przetarg['cena_wywoławcza']/przetarg['powierzchnia_ogolna']:.2f} zł/ha)")
            if przetarg.get('atrybuty'):
                print(f"   Atrybuty: {przetarg['atrybuty']}")
            if przetarg.get('obniżka'):
                print(f"   Obniżka: {przetarg['obniżka']}")
                
    return stats

if __name__ == '__main__':
    main(verbose=True)