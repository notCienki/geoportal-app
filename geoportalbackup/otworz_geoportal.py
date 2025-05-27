import json
import webbrowser
import re
import sys
import time
import argparse
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# Funkcja do znajdowania ścieżki do zasobów
def resource_path(relative_path):
    """ Zwraca bezwzględną ścieżkę do zasobu, działa zarówno w trybie development jak i po zapakowaniu """
    try:
        # PyInstaller tworzy folder tymczasowy i przechowuje w nim ścieżkę w _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

def get_chrome_path():
    """
    Zwraca ścieżkę do przeglądarki Chrome na różnych systemach operacyjnych
    """
    import platform
    import os
    
    system = platform.system()
    
    if system == "Windows":
        # Próbujemy znaleźć Chrome w rejestrze Windows
        try:
            import winreg
            # Sprawdź najpierw dla użytkownika
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            chrome_path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            return chrome_path
        except ImportError:
            # Moduł winreg nie istnieje (jesteśmy na macOS/Linux)
            pass
        except Exception:
            # Jeśli nie znaleziono w HKCU, sprawdź w HKLM
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                chrome_path, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                return chrome_path
            except:
                # Spróbuj standardowych lokalizacji, jeśli rejestr zawiódł
                common_locations = [
                    os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
                ]
                for location in common_locations:
                    if os.path.exists(location):
                        return location
                
                # Jeśli nie znaleziono w żadnej lokalizacji
                return None
    elif system == "Darwin":  # macOS
        # Standardowe lokalizacje Chrome na macOS
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path
        return None
    else:  # Linux i inne
        # Używamy 'which' do znalezienia ścieżki na Linux
        for chrome_cmd in ["google-chrome", "chrome", "chromium", "chromium-browser"]:
            try:
                import subprocess
                chrome_path = subprocess.check_output(["which", chrome_cmd]).decode("utf-8").strip()
                if chrome_path:
                    return chrome_path
            except:
                pass
        return None

def create_chrome_driver(chrome_path=None, log_callback=None):
    """
    Tworzy i konfiguruje ChromeDriver do automatyzacji
    
    Args:
        chrome_path: Ścieżka do przeglądarki Chrome
        log_callback: Funkcja do wywoływania z komunikatami logowania
    
    Returns:
        Obiekt WebDriver lub None w przypadku błędu
    """
    try:
        _log("Konfigurowanie ChromeDriver...", log_callback)
        
        # Dodatkowe opcje Chrome dla lepszej kompatybilności
        chrome_options = Options()
        
        # Wyłączamy protokół "data:" który może powodować problemy
        chrome_options.add_argument("--disable-features=DataUrlSupport")
        
        # Ustawienia bezpieczeństwa, które mogą pomóc z dostępem do lokalnych plików
        chrome_options.add_argument("--allow-file-access-from-files")
        chrome_options.add_argument("--allow-file-access")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-site-isolation-trials")
        
        # Dodatkowe ustawienia zapobiegające błędom
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Ustawienie własnego profilu dla Chrome
        import tempfile
        import os
        user_data_dir = os.path.join(tempfile.gettempdir(), "geoportal_chrome_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Ustaw ścieżkę do Chrome jeśli została podana
        if chrome_path:
            _log(f"Używanie Chrome z lokalizacji: {chrome_path}", log_callback)
            chrome_options.binary_location = chrome_path

        # Inicjalizacja ChromeDriver
        driver = None
        
        # Importujemy selenium.webdriver globalnie, żeby uniknąć błędów z dostępem do zmiennej
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        # Sprawdź system operacyjny
        import platform
        system = platform.system()
        
        # Metoda dla macOS używając lokalnego ChromeDrivera (preferowana dla macOS)
        if system == "Darwin":  # macOS
            try:
                _log("Próba metody dla macOS: Używanie lokalnego ChromeDrivera", log_callback)
                
                # Sprawdź czy istnieje lokalny ChromeDriver w katalogu aplikacji
                driver_name = "chromedriver"
                chrome_driver_path = resource_path(driver_name)
                
                # Jeśli nie istnieje, spróbuj pobrać i rozpakować ChromeDriver
                if not os.path.exists(chrome_driver_path):
                    _log("ChromeDriver nie znaleziony, próbuję pobrać...", log_callback)
                    try:
                        # Używamy subprocess do uruchomienia polecenia brew, które może być dostępne na macOS
                        import subprocess
                        _log("Próbuję użyć ChromeDrivera systemowego", log_callback)
                        
                        # Znajdź systemowy ChromeDriver używając which
                        try:
                            driver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
                            if driver_path:
                                chrome_driver_path = driver_path
                                _log(f"Znaleziono systemowy ChromeDriver: {chrome_driver_path}", log_callback)
                        except:
                            _log("Nie znaleziono systemowego ChromeDrivera", log_callback)
                    except:
                        _log("Nie udało się pobrać ChromeDrivera automatycznie", log_callback)
                else:
                    _log(f"Znaleziono lokalny ChromeDriver w: {chrome_driver_path}", log_callback)
                
                # Ustawienie uprawnień wykonywania dla ChromeDrivera
                if os.path.exists(chrome_driver_path):
                    try:
                        import stat
                        os.chmod(chrome_driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                        _log("Ustawiono uprawnienia wykonywania dla ChromeDrivera", log_callback)
                    except Exception as e:
                        _log(f"Ostrzeżenie: Nie udało się ustawić uprawnień: {e}", log_callback)
                
                # Inicjalizacja ChromeDrivera
                service = Service(executable_path=chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log(f"Sukces! ChromeDriver został zainicjalizowany na macOS", log_callback)
                return driver
            except Exception as e:
                _log(f"Metoda dla macOS nie powiodła się: {e}", log_callback)
                # Na macOS często błędy dotyczą uprawnień lub niekompatybilności wersji
                _log("Wskazówka: Spróbuj zainstalować ChromeDriver przez brew: `brew install --cask chromedriver`", log_callback)
        
        # Metoda 1: Użyj WebDriverManager (jeśli jest zainstalowany)
        try:
            _log("Próba metody 1: WebDriverManager", log_callback)
            try:
                # Najpierw sprawdź czy webdriver_manager jest w ogóle dostępny
                import importlib
                webdriver_manager_spec = importlib.util.find_spec("webdriver_manager")
                if webdriver_manager_spec is None:
                    raise ImportError("Moduł webdriver_manager nie jest zainstalowany")
                
                from webdriver_manager.chrome import ChromeDriverManager
                
                _log("Moduł webdriver_manager jest dostępny, próbuję pobrać ChromeDriver", log_callback)
                
                # Szczegółowa obsługa błędów
                try:
                    chrome_driver_path = ChromeDriverManager().install()
                    _log(f"ChromeDriver został pobrany do: {chrome_driver_path}", log_callback)
                except Exception as install_error:
                    _log(f"Błąd podczas pobierania ChromeDrivera: {install_error}", log_callback)
                    raise
                
                service = Service(chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log(f"Sukces! ChromeDriver został zainicjalizowany z WebDriverManager", log_callback)
                return driver
            except ImportError as import_error:
                _log(f"WebDriverManager nie jest dostępny: {import_error}", log_callback)
                _log("Wskazówka: Zainstaluj webdriver_manager za pomocą pip: `pip install webdriver-manager`", log_callback)
                raise
            except Exception as e:
                _log(f"Inny błąd podczas inicjalizacji WebDriverManager: {e}", log_callback)
                raise
        except Exception as e:
            _log(f"Metoda 1 nie powiodła się: {e}", log_callback)
        
        # Metoda 2: Użyj bezpośrednio ChromeDriver
        if not driver:
            try:
                _log("Próba metody 2: Bezpośrednie użycie ChromeDriver", log_callback)
                driver = webdriver.Chrome(options=chrome_options)
                _log(f"Sukces! ChromeDriver został zainicjalizowany bezpośrednio", log_callback)
                return driver
            except Exception as e:
                _log(f"Metoda 2 nie powiodła się: {e}", log_callback)
        
        # Metoda 3: Pobranie ChromeDrivera z lokalnego katalogu zasobów
        if not driver:
            try:
                _log("Próba metody 3: Używanie ChromeDrivera z katalogu zasobów", log_callback)
                
                # Sprawdź system operacyjny
                import platform
                system = platform.system()
                
                # Ścieżka do ChromeDriver w zależności od systemu
                if system == "Windows":
                    driver_name = "chromedriver.exe"
                else:
                    driver_name = "chromedriver"
                
                # Ścieżka do ChromeDrivera w katalogu zasobów
                chrome_driver_path = resource_path(driver_name)
                _log(f"Szukam ChromeDrivera w: {chrome_driver_path}", log_callback)
                
                if not os.path.exists(chrome_driver_path):
                    _log(f"BŁĄD: ChromeDriver nie istnieje w: {chrome_driver_path}", log_callback)
                    
                    # Sprawdź katalog bieżący
                    current_dir = os.path.abspath(".")
                    current_driver = os.path.join(current_dir, driver_name)
                    _log(f"Sprawdzam katalog bieżący: {current_driver}", log_callback)
                    if os.path.exists(current_driver):
                        chrome_driver_path = current_driver
                        _log(f"Znaleziono ChromeDriver w katalogu bieżącym", log_callback)
                    else:
                        _log("ChromeDriver nie znaleziony również w katalogu bieżącym", log_callback)
                        raise FileNotFoundError(f"ChromeDriver nie znaleziony: {chrome_driver_path}")
                
                service = Service(chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log(f"Sukces! ChromeDriver został zainicjalizowany z lokalnego katalogu", log_callback)
                return driver
            except Exception as e:
                _log(f"Metoda 3 nie powiodła się: {e}", log_callback)
        
        # Jeśli wszystkie metody zawiodły
        _log("UWAGA: Nie udało się zainicjalizować ChromeDriver", log_callback)
        
        # Zasugeruj rozwiązania specyficzne dla systemu operacyjnego
        if system == "Darwin":  # macOS
            _log("Sugestie dla macOS:", log_callback)
            _log("1. Zainstaluj ChromeDriver przez brew: brew install --cask chromedriver", log_callback)
            _log("2. Sprawdź czy wersja ChromeDrivera jest zgodna z wersją Chrome", log_callback)
            _log("3. Upewnij się, że ChromeDriver ma uprawnienia do wykonywania (chmod +x chromedriver)", log_callback)
        elif system == "Windows":
            _log("Sugestie dla Windows:", log_callback)
            _log("1. Pobierz ChromeDriver z https://chromedriver.chromium.org/downloads", log_callback)
            _log("2. Umieść plik chromedriver.exe w katalogu aplikacji", log_callback)
            _log("3. Upewnij się, że wersja ChromeDrivera jest zgodna z wersją Chrome", log_callback)
        else:  # Linux
            _log("Sugestie dla Linux:", log_callback)
            _log("1. Zainstaluj ChromeDriver przez menedżer pakietów", log_callback)
            _log("2. Upewnij się, że ChromeDriver ma uprawnienia do wykonywania (chmod +x chromedriver)", log_callback)
            _log("3. Dodaj ścieżkę do ChromeDrivera do zmiennej PATH", log_callback)
            
        return None
        
    except Exception as e:
        _log(f"Wystąpił błąd podczas konfigurowania ChromeDriver: {e}", log_callback)
        
        # Pokaż szczegółowy traceback w konsoli
        import traceback
        if log_callback is None:  # Tryb konsolowy
            traceback.print_exc()
        else:
            # W trybie GUI pokaż skrócony traceback
            tb_lines = traceback.format_exc().split('\n')
            for line in tb_lines[-10:]:  # Pokaż tylko 10 ostatnich linii
                _log(line, log_callback)
                
        return None

def debug_chrome_environment(log_callback=None):
    """
    Funkcja diagnostyczna do sprawdzania środowiska Chrome i ChromeDriver
    
    Args:
        log_callback: Funkcja do wywoływania z komunikatami logowania
    """
    import os
    import platform
    import sys
    
    _log("\n===== DIAGNOSTYKA CHROME I CHROMEDRIVER =====", log_callback)
    
    # Informacje o systemie
    _log(f"System operacyjny: {platform.platform()}", log_callback)
    _log(f"Architektura: {platform.architecture()}", log_callback)
    _log(f"Python: {sys.version}", log_callback)
    
    # Sprawdź czy Chrome jest zainstalowany
    _log("\nSzukam zainstalowanego Chrome...", log_callback)
    chrome_path = get_chrome_path()
    if chrome_path:
        _log(f"✓ Chrome znaleziony w: {chrome_path}", log_callback)
        _log(f"  Sprawdzanie czy plik istnieje: {os.path.exists(chrome_path)}", log_callback)
    else:
        _log("❌ Nie znaleziono Chrome w standardowych lokalizacjach", log_callback)
    
    # Szukaj ChromeDriver w katalogu aplikacji
    _log("\nSzukam ChromeDriver w katalogu aplikacji...", log_callback)
    try:
        driver_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        chrome_driver_path = resource_path(driver_name)
        _log(f"Szukam {driver_name} w: {chrome_driver_path}", log_callback)
        if os.path.exists(chrome_driver_path):
            _log(f"✓ ChromeDriver znaleziony w: {chrome_driver_path}", log_callback)
        else:
            _log(f"❌ ChromeDriver nie znaleziony w: {chrome_driver_path}", log_callback)
            
        # Sprawdź katalog bieżący
        current_dir = os.path.abspath(".")
        current_driver = os.path.join(current_dir, driver_name)
        _log(f"Szukam {driver_name} w katalogu bieżącym: {current_dir}", log_callback)
        if os.path.exists(current_driver):
            _log(f"✓ ChromeDriver znaleziony w katalogu bieżącym: {current_driver}", log_callback)
        else:
            _log(f"❌ ChromeDriver nie znaleziony w katalogu bieżącym", log_callback)
    except Exception as e:
        _log(f"Błąd podczas szukania ChromeDriver: {e}", log_callback)
    
    # Sprawdź PATH
    _log("\nZmienne środowiskowe:", log_callback)
    try:
        path = os.environ.get('PATH', '')
        _log(f"PATH zawiera {len(path.split(os.pathsep))} elementów", log_callback)
        if platform.system() == "Windows":
            program_files = os.environ.get('PROGRAMFILES', 'Nie znaleziono')
            program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'Nie znaleziono')
            local_app_data = os.environ.get('LOCALAPPDATA', 'Nie znaleziono')
            _log(f"PROGRAMFILES: {program_files}", log_callback)
            _log(f"PROGRAMFILES(X86): {program_files_x86}", log_callback)
            _log(f"LOCALAPPDATA: {local_app_data}", log_callback)
    except Exception as e:
        _log(f"Błąd podczas sprawdzania zmiennych środowiskowych: {e}", log_callback)
    
    # Sprawdź, czy webdriver-manager jest zainstalowany
    _log("\nSprawdzam moduł webdriver-manager...", log_callback)
    try:
        import webdriver_manager
        _log(f"✓ webdriver-manager jest zainstalowany (wersja: {webdriver_manager.__version__})", log_callback)
    except ImportError:
        _log("❌ webdriver-manager nie jest zainstalowany", log_callback)
    except Exception as e:
        _log(f"Błąd podczas sprawdzania webdriver-manager: {e}", log_callback)
    
    _log("\n=== KONIEC DIAGNOSTYKI ===\n", log_callback)

def get_powiat_from_polozenie(polozenie_str):
    """Wyodrębnia nazwę powiatu z pola 'położenie'"""
    if not polozenie_str:
        return None
    
    # Próba dopasowania powiatu - druga część po "/"
    match = re.search(r'podkarpackie/\s*(\w+(?:[-\s]+\w+)*)', polozenie_str)
    if match:
        return match.group(1).strip()
    return None

def get_geoportal_url(powiat):
    """Zwraca URL do geoportalu dla danego powiatu"""
    # Słownik mapujący nazwy powiatów na odpowiednie URL-e z pełnymi adresami
    powiat_urls = {
        "łańcucki": "https://lancut.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice+OSM+",
        "ropczycko sędziszowski": "https://spropczyce.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice1,granice2+OSM+",
        "rzeszowski": "https://powiatrzeszowski.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice+OSM+"
        # Dodaj więcej powiatów według potrzeb
    }
    
    # Normalizujemy nazwę powiatu (małe litery, usunięcie białych znaków)
    powiat_norm = powiat.lower().strip() if powiat else ""
    
    # Zwróć URL dla danego powiatu lub domyślny URL jeśli nie znaleziono
    return powiat_urls.get(powiat_norm, "https://mapy.geoportal.gov.pl")

def parse_dzialka_info(polozenie):
    """Wyodrębnia informacje o działce: województwo, powiat, gmina, obręb, numer działki"""
    if not polozenie:
        return {}
    
    info = {}
    
    # Województwo
    woj_match = re.search(r'^(\w+)/', polozenie)
    if woj_match:
        info['wojewodztwo'] = woj_match.group(1).strip()
    
    # Powiat
    powiat_match = re.search(r'podkarpackie/\s*(\w+(?:[-\s]+\w+)*)', polozenie)
    if powiat_match:
        info['powiat'] = powiat_match.group(1).strip()
    
    # Gmina
    gmina_match = re.search(r'(?:podkarpackie/\s*\w+(?:[-\s]+\w+)*/\s*)([^/]+)', polozenie)
    if gmina_match:
        info['gmina'] = gmina_match.group(1).strip()
    
    # Obręb (miejscowość) - często jest za gminą
    obreb_match = re.search(r'(?:podkarpackie/\s*\w+(?:[-\s]+\w+)*/\s*[^/]+/\s*)([^/\(]+)', polozenie)
    if obreb_match:
        info['obreb'] = obreb_match.group(1).strip()
    
    # Numer działki (ostatnia część po '/')
    dzialka_match = re.search(r'(\d+(?:/\d+)*(?:\s*i\s*\d+(?:/\d+)*)*)\s*(?:\(kompleks\))?$', polozenie)
    if dzialka_match:
        info['nr_dzialki'] = dzialka_match.group(1).strip()
    
    return info

def search_dzialka_selenium(powiat, dzialka_info, log_callback=None):
    """
    Wyszukuje działkę na geoportalu za pomocą Selenium
    
    Args:
        powiat: Nazwa powiatu
        dzialka_info: Słownik z informacjami o działce
        log_callback: Funkcja do wywoływania z komunikatami logowania
    """
    url = get_geoportal_url(powiat)
    log_message = f"Automatyczne wyszukiwanie działki nr {dzialka_info.get('nr_dzialki')} w obrębie {dzialka_info.get('obreb')}"
    _log(log_message, log_callback)
    _log(f"Otwieranie geoportalu dla powiatu {powiat}: {url}", log_callback)
    
    try:
        # Znajdź Chrome i inicjalizuj ChromeDriver
        chrome_path = get_chrome_path()
        if chrome_path:
            _log(f"Znaleziono Chrome w lokalizacji: {chrome_path}", log_callback)
        else:
            _log("UWAGA: Nie znaleziono zainstalowanego Google Chrome! Próbuję użyć domyślnej lokalizacji...", log_callback)
        
        # Użyj nowej funkcji do utworzenia WebDrivera
        driver = create_chrome_driver(chrome_path, log_callback)
        
        if not driver:
            _log("BŁĄD: Nie udało się zainicjalizować ChromeDriver!", log_callback)
            _log("Spróbuj zainstalować Chrome i uruchomić aplikację ponownie.", log_callback)
            if not log_callback:  # W trybie konsoli
                import webbrowser
                webbrowser.open(url)  # Otwórz URL w domyślnej przeglądarce
                return
        
        # Otwórz URL w przeglądarce
        _log(f"Otwieram adres URL: {url}", log_callback)
        driver.get(url)
        
        # Poczekaj na załadowanie strony
        _log("Czekam na załadowanie strony...", log_callback)
        time.sleep(5)
        
        # Różne implementacje dla różnych powiatów
        if "łańcucki" in powiat.lower():
            # Implementacja dla powiatu łańcuckiego
            search_lancut(driver, dzialka_info, log_callback)
        elif "ropczycko sędziszowski" in powiat.lower():
            # Implementacja dla powiatu ropczycko-sędziszowskiego
            search_ropczyce(driver, dzialka_info, log_callback)
        elif "rzeszowski" in powiat.lower():
            # Implementacja dla powiatu rzeszowskiego
            search_rzeszowski(driver, dzialka_info, log_callback)
        else:
            # Dla innych powiatów tylko otwórz stronę
            _log(f"Automatyczne wyszukiwanie dla powiatu {powiat} nie jest jeszcze zaimplementowane.", log_callback)
            _log(f"Otworzono stronę geoportalu, możesz ręcznie wyszukać działkę.", log_callback)
        
        # Pozostaw przeglądarkę otwartą
        _log("\nPrzeglądarka pozostanie otwarta. Zamknij ją ręcznie po zakończeniu przeglądania.", log_callback)
        
        # W trybie bez GUI nie czekamy na klawisz, ale zostawiamy przeglądarkę otwartą
        if log_callback is None:  # Jeśli nie ma funkcji zwrotnej, jesteśmy w trybie konsolowym
            input("\nNaciśnij Enter, aby zamknąć przeglądarkę i zakończyć program...")
            driver.quit()
        
    except Exception as e:
        error_message = f"Wystąpił błąd podczas automatycznego wyszukiwania: {e}"
        _log(error_message, log_callback)
        
        # W trybie konsoli pokazujemy pełny błąd
        if log_callback is None:
            import traceback
            traceback.print_exc()
            
        _log("Spróbuj wyszukać działkę ręcznie w już otwartej przeglądarce.", log_callback)

def _log(message, callback=None):
    """
    Funkcja pomocnicza do logowania komunikatów
    
    Args:
        message: Komunikat do wyświetlenia
        callback: Funkcja do wywołania z komunikatem (dla GUI) lub None (dla konsoli)
    """
    if callback:
        callback(message)
    else:
        print(message)

def search_lancut(driver, dzialka_info, log_callback=None):
    """
    Wyszukuje działkę na geoportalu powiatu łańcuckiego
    
    Args:
        driver: Obiekt WebDriver Selenium
        dzialka_info: Słownik z informacjami o działce
        log_callback: Funkcja do wywoływania z komunikatami logowania
    """
    try:
        _log("Czekam na załadowanie strony geoportalu...", log_callback)
        time.sleep(5)  # Dajemy więcej czasu na załadowanie
        
        # Kliknij w nagłówek "Szukaj" jeśli jest zwinięty
        _log("Szukam nagłówka 'Szukaj'...", log_callback)
        try:
            # Najpierw próbujemy znaleźć nagłówek po ID
            search_header = driver.find_element(By.ID, "szukaj_id")
            _log("Znaleziono nagłówek 'Szukaj' po ID", log_callback)
            search_header.click()
            _log("Kliknięto nagłówek 'Szukaj'", log_callback)
            time.sleep(1)
        except:
            try:
                # Alternatywnie szukamy po tekście
                search_header = driver.find_element(By.XPATH, "//a[text()='Szukaj']")
                _log("Znaleziono nagłówek 'Szukaj' po tekście", log_callback)
                search_header.click()
                _log("Kliknięto nagłówek 'Szukaj'", log_callback)
                time.sleep(1)
            except:
                _log("Nie znaleziono nagłówka 'Szukaj'. Być może menu jest już rozwinięte.", log_callback)
        
        # Kliknij w przycisk "Działka"
        _log("Szukam przycisku 'Działka'...", log_callback)
        try:
            # Próbujemy znaleźć przycisk po ID
            dzialka_button = driver.find_element(By.ID, "szukaj_dzialki")
            _log("Znaleziono przycisk 'Działka' po ID", log_callback)
            dzialka_button.click()
            _log("Kliknięto przycisk 'Działka'", log_callback)
        except:
            try:
                # Alternatywnie szukamy po tytule
                dzialka_button = driver.find_element(By.XPATH, "//button[@title='Wyszukiwanie numeru działki']")
                _log("Znaleziono przycisk 'Działka' po tytule", log_callback)
                dzialka_button.click()
                _log("Kliknięto przycisk 'Działka'", log_callback)
            except:
                _log("Nie znaleziono przycisku 'Działka'. Spróbuj wyszukać działkę ręcznie.", log_callback)
                return
        
        # Czekamy na załadowanie iframe
        _log("Czekam na załadowanie okna dialogowego...", log_callback)
        time.sleep(3)
        
        # Szukamy iframe, który zawiera formularz wyszukiwania działek
        _log("Szukam iframe z formularzem wyszukiwania...", log_callback)
        try:
            # Szukamy iframe po ID lub nazwie
            iframe = None
            try:
                iframe = driver.find_element(By.ID, "frame_szukaj_dzialki")
                _log("Znaleziono iframe po ID: frame_szukaj_dzialki", log_callback)
            except:
                try:
                    iframe = driver.find_element(By.NAME, "frame_szukaj_dzialki")
                    _log("Znaleziono iframe po nazwie: frame_szukaj_dzialki", log_callback)
                except:
                    # Próbujemy znaleźć dowolny iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        iframe = iframes[0]
                        _log(f"Znaleziono iframe (jeden z {len(iframes)})", log_callback)
                        
            if iframe is None:
                _log("Nie znaleziono iframe. Spróbuj wyszukać działkę ręcznie.", log_callback)
                return
            
            # Przełączamy się do iframe
            driver.switch_to.frame(iframe)
            _log("Przełączono kontekst do iframe", log_callback)
            
            # Teraz możemy wyszukiwać elementy wewnątrz iframe
            time.sleep(2)
            
            # Znajdź pole wyboru obrębu (dropdown) - teraz wiemy, że ma ID "prefix"
            _log("Szukam pola wyboru obrębu (ID: prefix)...", log_callback)
            try:
                select_element = driver.find_element(By.ID, "prefix")
                _log("Znaleziono pole wyboru obrębu po ID 'prefix'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    select_element = driver.find_element(By.XPATH, "//select[contains(@style, 'max-width:330px')]")
                    _log("Znaleziono pole wyboru obrębu po atrybucie style='max-width:330px'", log_callback)
                except:
                    _log("Nie znaleziono pola wyboru obrębu. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
                
            # Wybierz obręb
            select = Select(select_element)
            obreb = dzialka_info.get('obreb', '')
            found = False
            
            _log(f"Próbuję znaleźć obręb '{obreb}' na liście...", log_callback)
            
            # Wydrukuj wszystkie dostępne opcje dla debugowania tylko w trybie konsoli
            if log_callback is None:
                _log("Dostępne opcje obrębu:", log_callback)
                for i, option in enumerate(select.options):
                    _log(f"  {i}: {option.text}", log_callback)
                
            # Szukamy dopasowania nazwy obrębu w opcjach w formacie "ALBIGOWA (Gmina Łańcut)"
            for option in select.options:
                option_text = option.text.upper()
                if obreb.upper() in option_text:
                    select.select_by_visible_text(option.text)
                    found = True
                    _log(f"Wybrano obręb: {option.text}", log_callback)
                    break
            
            if not found:
                _log(f"Nie znaleziono obrębu '{obreb}'. Wybierz obręb ręcznie.", log_callback)
            
            time.sleep(1)
            
            # Znajdź pole do wprowadzenia numeru działki - ID "tekst" w iframe
            _log("Szukam pola do wprowadzenia numeru działki (ID: tekst)...", log_callback)
            try:
                input_element = driver.find_element(By.ID, "tekst")
                _log("Znaleziono pole numeru działki po ID 'tekst'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    input_element = driver.find_element(By.XPATH, "//input[@size='35']")
                    _log("Znaleziono pole numeru działki po atrybucie size='35'", log_callback)
                except:
                    _log("Nie znaleziono pola numeru działki. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
            
            # Wpisz numer działki
            input_element.clear()
            input_element.send_keys(dzialka_info.get('nr_dzialki', ''))
            _log(f"Wpisano numer działki: {dzialka_info.get('nr_dzialki', '')}", log_callback)
            
            time.sleep(1)
            
            # Znajdź przycisk "Szukaj" - ma ID "szukaj_btn"
            _log("Szukam przycisku 'Szukaj' (ID: szukaj_btn)...", log_callback)
            try:
                search_button = driver.find_element(By.ID, "szukaj_btn")
                _log("Znaleziono przycisk 'Szukaj' po ID 'szukaj_btn'", log_callback)
            except:
                try:
                    # Szukamy przycisku po tekście wewnątrz span z klasą ui-button-text
                    search_button = driver.find_element(By.XPATH, "//span[@class='ui-button-text' and text()='Szukaj']/parent::*")
                    _log("Znaleziono przycisk 'Szukaj' po tekście", log_callback)
                except:
                    try:
                        # Jeszcze jeden alternatywny selektor
                        search_button = driver.find_element(By.XPATH, "//button[contains(@class, 'ui-button')]")
                        _log("Znaleziono przycisk 'Szukaj' po klasie ui-button", log_callback)
                    except:
                        _log("Nie znaleziono przycisku 'Szukaj'. Spróbuj nacisnąć Enter w polu numeru działki...", log_callback)
                        try:
                            # Spróbuj nacisnąć Enter w polu numeru działki
                            input_element.send_keys(Keys.RETURN)
                            _log("Naciśnięto Enter w polu numeru działki", log_callback)
                            time.sleep(1)
                            return
                        except:
                            _log("Nie udało się nacisnąć Enter. Spróbuj zatwierdzić wyszukiwanie ręcznie.", log_callback)
                            return
            
            # Kliknij przycisk "Szukaj"
            search_button.click()
            _log("Kliknięto przycisk 'Szukaj'", log_callback)
            
            # Poczekaj na wyniki wyszukiwania
            time.sleep(3)
            
            _log("Wyszukiwanie działki zakończone. Poczekaj na wyniki wyszukiwania.", log_callback)
            
            # Przełączamy się z powrotem do głównego dokumentu
            driver.switch_to.default_content()
            _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            
        except Exception as e:
            error_message = f"Wystąpił błąd podczas pracy z iframe: {e}"
            _log(error_message, log_callback)
            
            # W trybie konsoli pokazujemy pełny błąd
            if log_callback is None:
                import traceback
                traceback.print_exc()
            
            # Próbujemy przełączyć się z powrotem do głównego dokumentu
            try:
                driver.switch_to.default_content()
                _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            except:
                pass
                
    except Exception as e:
        error_message = f"Wystąpił nieoczekiwany błąd: {e}"
        _log(error_message, log_callback)
        
        # W trybie konsoli pokazujemy pełny błąd
        if log_callback is None:
            import traceback
            traceback.print_exc()
            
        _log("Możesz kontynuować wyszukiwanie ręcznie.", log_callback)

def search_ropczyce(driver, dzialka_info, log_callback=None):
    """
    Wyszukuje działkę na geoportalu powiatu ropczycko-sędziszowskiego
    
    Args:
        driver: Obiekt WebDriver Selenium
        dzialka_info: Słownik z informacjami o działce
        log_callback: Funkcja do wywoływania z komunikatami logowania
    """
    try:
        _log("Czekam na załadowanie strony geoportalu...", log_callback)
        time.sleep(5)  # Dajemy więcej czasu na załadowanie
        
        # Kliknij w nagłówek "Szukaj" jeśli jest zwinięty
        _log("Szukam nagłówka 'Szukaj'...", log_callback)
        try:
            # Najpierw próbujemy znaleźć nagłówek po tekście
            search_header = driver.find_element(By.XPATH, "//a[text()='Szukaj']")
            _log("Znaleziono nagłówek 'Szukaj' po tekście", log_callback)
            search_header.click()
            _log("Kliknięto nagłówek 'Szukaj'", log_callback)
            time.sleep(1)
        except:
            _log("Nie znaleziono nagłówka 'Szukaj'. Być może menu jest już rozwinięte.", log_callback)
        
        # Kliknij w przycisk "Działka"
        _log("Szukam przycisku 'Działka'...", log_callback)
        try:
            # Próbujemy znaleźć przycisk po ID
            dzialka_button = driver.find_element(By.ID, "szukaj_dzialki")
            _log("Znaleziono przycisk 'Działka' po ID", log_callback)
            dzialka_button.click()
            _log("Kliknięto przycisk 'Działka'", log_callback)
        except:
            try:
                # Alternatywnie szukamy po tytule
                dzialka_button = driver.find_element(By.XPATH, "//button[@title='Wyszukiwanie numeru działki']")
                _log("Znaleziono przycisk 'Działka' po tytule", log_callback)
                dzialka_button.click()
                _log("Kliknięto przycisk 'Działka'", log_callback)
            except:
                _log("Nie znaleziono przycisku 'Działka'. Spróbuj wyszukać działkę ręcznie.", log_callback)
                return
        
        # Czekamy na załadowanie iframe
        _log("Czekam na załadowanie okna dialogowego...", log_callback)
        time.sleep(3)
        
        # Szukamy iframe, który zawiera formularz wyszukiwania działek
        _log("Szukam iframe z formularzem wyszukiwania...", log_callback)
        try:
            # Szukamy iframe po ID lub nazwie
            iframe = None
            try:
                iframe = driver.find_element(By.ID, "frame_szukaj_dzialki")
                _log("Znaleziono iframe po ID: frame_szukaj_dzialki", log_callback)
            except:
                try:
                    iframe = driver.find_element(By.NAME, "frame_szukaj_dzialki")
                    _log("Znaleziono iframe po nazwie: frame_szukaj_dzialki", log_callback)
                except:
                    # Próbujemy znaleźć dowolny iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        iframe = iframes[0]
                        _log(f"Znaleziono iframe (jeden z {len(iframes)})", log_callback)
                        
            if iframe is None:
                _log("Nie znaleziono iframe. Spróbuj wyszukać działkę ręcznie.", log_callback)
                return
            
            # Przełączamy się do iframe
            driver.switch_to.frame(iframe)
            _log("Przełączono kontekst do iframe", log_callback)
            
            # Teraz możemy wyszukiwać elementy wewnątrz iframe
            time.sleep(2)
            
            # Znajdź pole wyboru obrębu (dropdown) - teraz wiemy, że ma ID "prefix"
            _log("Szukam pola wyboru obrębu (ID: prefix)...", log_callback)
            try:
                select_element = driver.find_element(By.ID, "prefix")
                _log("Znaleziono pole wyboru obrębu po ID 'prefix'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    select_element = driver.find_element(By.XPATH, "//select[contains(@style, 'max-width:330px')]")
                    _log("Znaleziono pole wyboru obrębu po atrybucie style='max-width:330px'", log_callback)
                except:
                    _log("Nie znaleziono pola wyboru obrębu. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
                
            # Wybierz obręb
            select = Select(select_element)
            obreb = dzialka_info.get('obreb', '')
            found = False
            
            _log(f"Próbuję znaleźć obręb '{obreb}' na liście...", log_callback)
            
            # Wydrukuj wszystkie dostępne opcje dla debugowania tylko w trybie konsoli
            if log_callback is None:
                _log("Dostępne opcje obrębu:", log_callback)
                for i, option in enumerate(select.options):
                    _log(f"  {i}: {option.text}", log_callback)
                
            # Szukamy dopasowania nazwy obrębu w opcjach w formacie "NAWSIE (Wielopole Skrzyńskie)"
            for option in select.options:
                option_text = option.text.upper()
                if obreb.upper() in option_text:
                    select.select_by_visible_text(option.text)
                    found = True
                    _log(f"Wybrano obręb: {option.text}", log_callback)
                    break
            
            if not found:
                _log(f"Nie znaleziono obrębu '{obreb}'. Wybierz obręb ręcznie.", log_callback)
            
            time.sleep(1)
            
            # Znajdź pole do wprowadzenia numeru działki - ID "tekst" w iframe
            _log("Szukam pola do wprowadzenia numeru działki (ID: tekst)...", log_callback)
            try:
                input_element = driver.find_element(By.ID, "tekst")
                _log("Znaleziono pole numeru działki po ID 'tekst'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    input_element = driver.find_element(By.XPATH, "//input[@size='35']")
                    _log("Znaleziono pole numeru działki po atrybucie size='35'", log_callback)
                except:
                    _log("Nie znaleziono pola numeru działki. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
            
            # Wpisz numer działki
            input_element.clear()
            input_element.send_keys(dzialka_info.get('nr_dzialki', ''))
            _log(f"Wpisano numer działki: {dzialka_info.get('nr_dzialki', '')}", log_callback)
            
            time.sleep(1)
            
            # Znajdź przycisk "Szukaj" - ma ID "szukaj_btn"
            _log("Szukam przycisku 'Szukaj' (ID: szukaj_btn)...", log_callback)
            try:
                search_button = driver.find_element(By.ID, "szukaj_btn")
                _log("Znaleziono przycisk 'Szukaj' po ID 'szukaj_btn'", log_callback)
            except:
                try:
                    # Szukamy przycisku po tekście wewnątrz span z klasą ui-button-text
                    search_button = driver.find_element(By.XPATH, "//span[@class='ui-button-text' and text()='Szukaj']/parent::*")
                    _log("Znaleziono przycisk 'Szukaj' po tekście", log_callback)
                except:
                    try:
                        # Jeszcze jeden alternatywny selektor
                        search_button = driver.find_element(By.XPATH, "//button[contains(@class, 'ui-button')]")
                        _log("Znaleziono przycisk 'Szukaj' po klasie ui-button", log_callback)
                    except:
                        _log("Nie znaleziono przycisku 'Szukaj'. Spróbuj nacisnąć Enter w polu numeru działki...", log_callback)
                        try:
                            # Spróbuj nacisnąć Enter w polu numeru działki
                            input_element.send_keys(Keys.RETURN)
                            _log("Naciśnięto Enter w polu numeru działki", log_callback)
                            time.sleep(1)
                            return
                        except:
                            _log("Nie udało się nacisnąć Enter. Spróbuj zatwierdzić wyszukiwanie ręcznie.", log_callback)
                            return
            
            # Kliknij przycisk "Szukaj"
            search_button.click()
            _log("Kliknięto przycisk 'Szukaj'", log_callback)
            
            # Poczekaj na wyniki wyszukiwania
            time.sleep(3)
            
            _log("Wyszukiwanie działki zakończone. Poczekaj na wyniki wyszukiwania.", log_callback)
            
            # Przełączamy się z powrotem do głównego dokumentu
            driver.switch_to.default_content()
            _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            
        except Exception as e:
            error_message = f"Wystąpił błąd podczas pracy z iframe: {e}"
            _log(error_message, log_callback)
            
            # W trybie konsoli pokazujemy pełny błąd
            if log_callback is None:
                import traceback
                traceback.print_exc()
            
            # Próbujemy przełączyć się z powrotem do głównego dokumentu
            try:
                driver.switch_to.default_content()
                _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            except:
                pass
                
    except Exception as e:
        error_message = f"Wystąpił nieoczekiwany błąd: {e}"
        _log(error_message, log_callback)
        
        # W trybie konsoli pokazujemy pełny błąd
        if log_callback is None:
            import traceback
            traceback.print_exc()
            
        _log("Możesz kontynuować wyszukiwanie ręcznie.", log_callback)

def search_rzeszowski(driver, dzialka_info, log_callback=None):
    """
    Wyszukuje działkę na geoportalu powiatu rzeszowskiego
    
    Args:
        driver: Obiekt WebDriver Selenium
        dzialka_info: Słownik z informacjami o działce
        log_callback: Funkcja do wywoływania z komunikatami logowania
    """
    try:
        _log("Czekam na załadowanie strony geoportalu powiatu rzeszowskiego...", log_callback)
        time.sleep(5)  # Dajemy więcej czasu na załadowanie
        
        # Kliknij w nagłówek "Szukaj" jeśli jest zwinięty
        _log("Szukam nagłówka 'Szukaj'...", log_callback)
        try:
            # Najpierw próbujemy znaleźć nagłówek po tekście
            search_header = driver.find_element(By.XPATH, "//a[text()='Szukaj']")
            _log("Znaleziono nagłówek 'Szukaj' po tekście", log_callback)
            search_header.click()
            _log("Kliknięto nagłówek 'Szukaj'", log_callback)
            time.sleep(1)
        except:
            try:
                # Alternatywnie szukamy po ID
                search_header = driver.find_element(By.ID, "szukaj_id")
                _log("Znaleziono nagłówek 'Szukaj' po ID", log_callback)
                search_header.click()
                _log("Kliknięto nagłówek 'Szukaj'", log_callback)
                time.sleep(1)
            except:
                _log("Nie znaleziono nagłówka 'Szukaj'. Być może menu jest już rozwinięte.", log_callback)
        
        # Kliknij w przycisk "Działka"
        _log("Szukam przycisku 'Działka'...", log_callback)
        try:
            # Próbujemy znaleźć przycisk po ID
            dzialka_button = driver.find_element(By.ID, "szukaj_dzialki")
            _log("Znaleziono przycisk 'Działka' po ID", log_callback)
            dzialka_button.click()
            _log("Kliknięto przycisk 'Działka'", log_callback)
        except:
            try:
                # Alternatywnie szukamy po tytule
                dzialka_button = driver.find_element(By.XPATH, "//button[@title='Wyszukiwanie numeru działki']")
                _log("Znaleziono przycisk 'Działka' po tytule", log_callback)
                dzialka_button.click()
                _log("Kliknięto przycisk 'Działka'", log_callback)
            except:
                try:
                    # Jeszcze jedna alternatywa - po tekście
                    dzialka_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Działka')]")
                    _log("Znaleziono przycisk 'Działka' po tekście", log_callback)
                    dzialka_button.click()
                    _log("Kliknięto przycisk 'Działka'", log_callback)
                except:
                    _log("Nie znaleziono przycisku 'Działka'. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
        
        # Czekamy na załadowanie iframe
        _log("Czekam na załadowanie okna dialogowego...", log_callback)
        time.sleep(3)
        
        # Szukamy iframe, który zawiera formularz wyszukiwania działek
        _log("Szukam iframe z formularzem wyszukiwania...", log_callback)
        try:
            # Szukamy iframe po ID lub nazwie
            iframe = None
            try:
                iframe = driver.find_element(By.ID, "frame_szukaj_dzialki")
                _log("Znaleziono iframe po ID: frame_szukaj_dzialki", log_callback)
            except:
                try:
                    iframe = driver.find_element(By.NAME, "frame_szukaj_dzialki")
                    _log("Znaleziono iframe po nazwie: frame_szukaj_dzialki", log_callback)
                except:
                    # Próbujemy znaleźć dowolny iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        iframe = iframes[0]
                        _log(f"Znaleziono iframe (jeden z {len(iframes)})", log_callback)
                        
            if iframe is None:
                _log("Nie znaleziono iframe. Spróbuj wyszukać działkę ręcznie.", log_callback)
                return
            
            # Przełączamy się do iframe
            driver.switch_to.frame(iframe)
            _log("Przełączono kontekst do iframe", log_callback)
            
            # Teraz możemy wyszukiwać elementy wewnątrz iframe
            time.sleep(2)
            
            # Znajdź pole wyboru obrębu (dropdown) - teraz wiemy, że ma ID "prefix"
            _log("Szukam pola wyboru obrębu (ID: prefix)...", log_callback)
            try:
                select_element = driver.find_element(By.ID, "prefix")
                _log("Znaleziono pole wyboru obrębu po ID 'prefix'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    select_element = driver.find_element(By.XPATH, "//select[contains(@style, 'max-width:330px')]")
                    _log("Znaleziono pole wyboru obrębu po atrybucie style='max-width:330px'", log_callback)
                except:
                    _log("Nie znaleziono pola wyboru obrębu. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
                
            # Wybierz obręb
            select = Select(select_element)
            obreb = dzialka_info.get('obreb', '')
            found = False
            
            _log(f"Próbuję znaleźć obręb '{obreb}' na liście...", log_callback)
            
            # Wydrukuj wszystkie dostępne opcje dla debugowania tylko w trybie konsoli
            if log_callback is None:
                _log("Dostępne opcje obrębu:", log_callback)
                for i, option in enumerate(select.options):
                    _log(f"  {i}: {option.text}", log_callback)
                
            # Przygotuj nazwę obrębu - usuń znaki nowej linii i normalizuj białe znaki
            normalized_obreb = ' '.join(obreb.upper().split())
            _log(f"Znormalizowana nazwa obrębu do wyszukania: '{normalized_obreb}'", log_callback)
            
            # Szukamy dopasowania nazwy obrębu w opcjach
            for option in select.options:
                option_text = option.text.upper()
                if normalized_obreb in option_text:
                    select.select_by_visible_text(option.text)
                    found = True
                    _log(f"Wybrano obręb: {option.text}", log_callback)
                    break
            
            if not found:
                _log(f"Nie znaleziono obrębu '{obreb}'. Wybierz obręb ręcznie.", log_callback)
            
            time.sleep(1)
            
            # Znajdź pole do wprowadzenia numeru działki - ID "tekst" w iframe
            _log("Szukam pola do wprowadzenia numeru działki (ID: tekst)...", log_callback)
            try:
                input_element = driver.find_element(By.ID, "tekst")
                _log("Znaleziono pole numeru działki po ID 'tekst'", log_callback)
            except:
                try:
                    # Alternatywny selektor
                    input_element = driver.find_element(By.XPATH, "//input[@size='35']")
                    _log("Znaleziono pole numeru działki po atrybucie size='35'", log_callback)
                except:
                    _log("Nie znaleziono pola numeru działki. Spróbuj wyszukać działkę ręcznie.", log_callback)
                    return
            
            # Wpisz numer działki
            input_element.clear()
            input_element.send_keys(dzialka_info.get('nr_dzialki', ''))
            _log(f"Wpisano numer działki: {dzialka_info.get('nr_dzialki', '')}", log_callback)
            
            time.sleep(1)
            
            # Znajdź przycisk "Szukaj" - ma ID "szukaj_btn"
            _log("Szukam przycisku 'Szukaj' (ID: szukaj_btn)...", log_callback)
            try:
                search_button = driver.find_element(By.ID, "szukaj_btn")
                _log("Znaleziono przycisk 'Szukaj' po ID 'szukaj_btn'", log_callback)
            except:
                try:
                    # Szukamy przycisku po tekście wewnątrz span z klasą ui-button-text
                    search_button = driver.find_element(By.XPATH, "//span[@class='ui-button-text' and text()='Szukaj']/parent::*")
                    _log("Znaleziono przycisk 'Szukaj' po tekście", log_callback)
                except:
                    try:
                        # Jeszcze jeden alternatywny selektor
                        search_button = driver.find_element(By.XPATH, "//button[contains(@class, 'ui-button')]")
                        _log("Znaleziono przycisk 'Szukaj' po klasie ui-button", log_callback)
                    except:
                        _log("Nie znaleziono przycisku 'Szukaj'. Spróbuj nacisnąć Enter w polu numeru działki...", log_callback)
                        try:
                            # Spróbuj nacisnąć Enter w polu numeru działki
                            input_element.send_keys(Keys.RETURN)
                            _log("Naciśnięto Enter w polu numeru działki", log_callback)
                            time.sleep(1)
                            return
                        except:
                            _log("Nie udało się nacisnąć Enter. Spróbuj zatwierdzić wyszukiwanie ręcznie.", log_callback)
                            return
            
            # Kliknij przycisk "Szukaj"
            search_button.click()
            _log("Kliknięto przycisk 'Szukaj'", log_callback)
            
            # Poczekaj na wyniki wyszukiwania
            time.sleep(3)
            
            _log("Wyszukiwanie działki zakończone. Poczekaj na wyniki wyszukiwania.", log_callback)
            
            # Przełączamy się z powrotem do głównego dokumentu
            driver.switch_to.default_content()
            _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            
        except Exception as e:
            error_message = f"Wystąpił błąd podczas pracy z iframe: {e}"
            _log(error_message, log_callback)
            
            # W trybie konsoli pokazujemy pełny błąd
            if log_callback is None:
                import traceback
                traceback.print_exc()
            
            # Próbujemy przełączyć się z powrotem do głównego dokumentu
            try:
                driver.switch_to.default_content()
                _log("Przełączono kontekst z powrotem do głównego dokumentu", log_callback)
            except:
                pass
                
    except Exception as e:
        error_message = f"Wystąpił nieoczekiwany błąd: {e}"
        _log(error_message, log_callback)
        
        # W trybie konsoli pokazujemy pełny błąd
        if log_callback is None:
            import traceback
            traceback.print_exc()
            
        _log("Możesz kontynuować wyszukiwanie ręcznie.", log_callback)

def main():
    """
    Główna funkcja programu - dla wywołań z terminala.
    Użyj search_dzialka_selenium z parametrem log_callback dla integracji z GUI.
    """
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="Otwieranie geoportalu dla działek")
    parser.add_argument("--search-file", help="Ścieżka do pliku JSON z danymi wyszukiwania")
    parser.add_argument("--silent", action="store_true", help="Tryb cichy (bez komunikatów)")
    parser.add_argument("--debug", action="store_true", help="Uruchom diagnostykę Chrome i ChromeDriver")
    args = parser.parse_args()
    
    # Funkcja logowania w zależności od trybu
    log_func = None if not args.silent else lambda msg: None
    
    # Uruchom diagnostykę jeśli wybrano opcję debug
    if args.debug:
        debug_chrome_environment(log_func)
        return
    
    # Sprawdź czy mamy plik z danymi wyszukiwania
    if args.search_file:
        try:
            with open(args.search_file, 'r', encoding='utf-8') as f:
                search_data = json.load(f)
                
            powiat = search_data.get('powiat')
            dzialka_info = search_data.get('dzialka_info')
            
            if powiat and dzialka_info:
                _log(f"Uruchamiam automatyczne wyszukiwanie dla powiatu {powiat}", log_func)
                _log(f"Dane działki: {dzialka_info}", log_func)
                search_dzialka_selenium(powiat, dzialka_info, log_func)
                return
            else:
                _log("Niepełne dane w pliku wyszukiwania", log_func)
        except Exception as e:
            _log(f"Błąd podczas przetwarzania pliku wyszukiwania: {e}", log_func)
            if log_func is None:  # Tylko w trybie konsoli pokazujemy pełny błąd
                import traceback
                traceback.print_exc()
    
    # Standardowe uruchomienie jeśli nie podano pliku wyszukiwania
    _log("========== OTWIERANIE GEOPORTALU DLA POWIATÓW ==========", log_func)
    
    # 1. Wczytaj dane z pliku JSON
    input_file = 'przetargi_najlepsze_oferty.json'
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            przetargi = data['przetargi']
            _log(f"Wczytano {len(przetargi)} przetargów z pliku {input_file}", log_func)
    except Exception as e:
        _log(f"BŁĄD: Nie udało się wczytać pliku {input_file}: {e}", log_func)
        return
    
    # 2. Pobierz unikalne powiaty
    powiaty = {}
    for przetarg in przetargi:
        if 'położenie' in przetarg:
            powiat = get_powiat_from_polozenie(przetarg['położenie'])
            if powiat:
                powiaty[powiat] = powiaty.get(powiat, 0) + 1
    
    if not powiaty:
        _log("Nie znaleziono żadnych powiatów w danych", log_func)
        return
    
    # 3. Wyświetl listę dostępnych powiatów
    _log("\nDostępne powiaty:", log_func)
    for i, (powiat, count) in enumerate(powiaty.items(), 1):
        _log(f"{i}. {powiat} ({count} przetargów)", log_func)
    
    # Tylko w wersji konsolowej pokazujemy interaktywny wybór
    if log_func is None:
        # 4. Wybór sposobu wyszukiwania
        _log("\nWybierz sposób działania:", log_func)
        _log("1. Otwórz geoportal dla wybranego powiatu", log_func)
        _log("2. Wyszukaj konkretną działkę (automatyczne wyszukiwanie)", log_func)
        
        try:
            mode_choice = int(input("Twój wybór (1 lub 2): "))
            if mode_choice == 1:
                # Tryb otwierania geoportalu dla powiatu
                while True:
                    try:
                        choice = input("\nWybierz numer powiatu (lub wpisz 'wszystkie' aby otworzyć wszystkie): ")
                        
                        if choice.lower() == 'wszystkie':
                            # Otwórz geoportale dla wszystkich powiatów
                            for powiat in powiaty.keys():
                                url = get_geoportal_url(powiat)
                                _log(f"Otwieranie geoportalu dla powiatu {powiat}: {url}", log_func)
                                webbrowser.open(url)
                            break
                        else:
                            # Otwórz geoportal dla wybranego powiatu
                            choice_num = int(choice)
                            if 1 <= choice_num <= len(powiaty):
                                selected_powiat = list(powiaty.keys())[choice_num - 1]
                                url = get_geoportal_url(selected_powiat)
                                _log(f"Otwieranie geoportalu dla powiatu {selected_powiat}: {url}", log_func)
                                webbrowser.open(url)
                                break
                            else:
                                _log(f"Wybierz numer od 1 do {len(powiaty)}", log_func)
                    except ValueError:
                        _log("Wprowadź poprawny numer lub 'wszystkie'", log_func)
                        
            elif mode_choice == 2:
                # Tryb automatycznego wyszukiwania działki
                _log("\nDostępne przetargi:", log_func)
                for i, przetarg in enumerate(przetargi, 1):
                    polozenie = przetarg.get('położenie', 'Brak danych')
                    _log(f"{i}. {polozenie}", log_func)
                
                while True:
                    try:
                        choice = int(input("\nWybierz numer przetargu: "))
                        if 1 <= choice <= len(przetargi):
                            selected_przetarg = przetargi[choice - 1]
                            polozenie = selected_przetarg.get('położenie', '')
                            
                            # Wyodrębnij informacje o działce
                            dzialka_info = parse_dzialka_info(polozenie)
                            powiat = dzialka_info.get('powiat', '')
                            
                            _log(f"\nWybrana działka:", log_func)
                            _log(f"Powiat: {dzialka_info.get('powiat', 'Nie określono')}", log_func)
                            _log(f"Gmina: {dzialka_info.get('gmina', 'Nie określono')}", log_func)
                            _log(f"Obręb: {dzialka_info.get('obreb', 'Nie określono')}", log_func)
                            _log(f"Nr działki: {dzialka_info.get('nr_dzialki', 'Nie określono')}", log_func)
                            
                            # Sprawdź czy automatyczne wyszukiwanie jest wspierane dla tego powiatu
                            supported_powiaty = ["łańcucki", "ropczycko sędziszowski", "rzeszowski"]
                            
                            if powiat and any(p.lower() in powiat.lower() for p in supported_powiaty):
                                _log(f"\nPowiat {powiat} jest wspierany przez automatyczne wyszukiwanie!", log_func)
                                
                                # Zapytaj o tryb wyszukiwania
                                auto_search = input("Czy chcesz użyć automatycznego wyszukiwania działki? (tak/nie): ")
                                if auto_search.lower() == 'tak':
                                    # Uruchom wyszukiwanie Selenium
                                    search_dzialka_selenium(powiat, dzialka_info, log_func)
                                else:
                                    # Otwórz tylko stronę geoportalu
                                    url = get_geoportal_url(powiat)
                                    _log(f"\nOtwieranie geoportalu dla powiatu {powiat}: {url}", log_func)
                                    _log(f"Teraz możesz ręcznie wyszukać działkę nr {dzialka_info.get('nr_dzialki', '')} w obrębie {dzialka_info.get('obreb', '')}", log_func)
                                    webbrowser.open(url)
                            else:
                                _log(f"\nAutomatyczne wyszukiwanie dla powiatu {powiat} nie jest jeszcze zaimplementowane.", log_func)
                                url = get_geoportal_url(powiat)
                                _log(f"Otwieranie geoportalu dla powiatu {powiat}: {url}", log_func)
                                _log(f"Teraz możesz ręcznie wyszukać działkę nr {dzialka_info.get('nr_dzialki', '')} w obrębie {dzialka_info.get('obreb', '')}", log_func)
                                webbrowser.open(url)
                            
                            break
                        else:
                            _log(f"Wybierz numer od 1 do {len(przetargi)}", log_func)
                    except ValueError:
                        _log("Wprowadź poprawny numer", log_func)
            else:
                _log("Wybierz 1 lub 2!", log_func)
                
        except ValueError:
            _log("Wprowadź poprawny numer (1 lub 2)", log_func)

if __name__ == "__main__":
    main()