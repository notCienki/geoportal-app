import customtkinter as ctk
import subprocess
import os
import datetime
import threading
from tkinter import filedialog
import json
import sys
import importlib.util

# Funkcja do znajdowania ścieżki do plików zasobów
def resource_path(relative_path):
    """ Zwraca bezwzględną ścieżkę do zasobu, działa zarówno w trybie development jak i po zapakowaniu """
    try:
        # PyInstaller tworzy folder tymczasowy i przechowuje w nim ścieżkę w _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

# Konfiguracja stylu GUI
ctk.set_appearance_mode("dark")  # zawsze używaj ciemnego motywu
ctk.set_default_color_theme("blue")  # niebieski akcent

class PrzetargiApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Geoportal Przetargi - Panel Zarządzania")
        self.geometry("1400x800")  # Zwiększony rozmiar okna z 1100x700 na 1300x800
        
        # Dodajemy ikonę aplikacji z pliku PNG
        try:
            icon_path = resource_path("3082383.png")
            # Na Windows używamy iconbitmap
            if sys.platform.startswith('win'):
                # Na Windows potrzebujemy ikony .ico, ale możemy użyć PhotoImage dla okien toplevel
                from PIL import Image, ImageTk
                self.icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.iconphoto(True, self.icon_img)
            elif sys.platform.startswith('darwin'):  # macOS
                # Na macOS można użyć iconphoto z PhotoImage
                from PIL import Image, ImageTk
                self.icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.iconphoto(True, self.icon_img)
        except Exception as e:
            print(f"Nie udało się ustawić ikony aplikacji: {e}")
        
        # Zmienne
        self.current_page = "Strona Główna"
        self.recent_files = []
        self.load_recent_files()
        self.przetargi_data = {}
        self.load_przetargi_data()

        # Sidebar - zwiększona szerokość z 220 na 250 pikseli
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        # Logo z większym marginesem wewnętrznym
        self.logo = ctk.CTkLabel(self.sidebar, text="🗂 Geoportal Przetargi", 
                              font=("Arial", 20, "bold"),
                              padx=15)  # Dodany padding poziomy
        self.logo.pack(pady=20, padx=15)  # Dodany padding do packowania
        
        # Separator - szerszy niż poprzednio
        separator = ctk.CTkFrame(self.sidebar, height=2, width=220)
        separator.pack(pady=10)

        # Menu ikony
        icons = {
            "Strona Główna": "🏠",
            "Rzeszowski": "🏙️",
            "Łańcucki": "🏛️",
            "Ropczycko-Sędziszowski": "🏢"
        }
        
        self.buttons = []
        for name, icon in icons.items():
            btn = ctk.CTkButton(
                self.sidebar, 
                text=f"{icon} {name}", 
                command=lambda n=name: self.show_page(n),
                anchor="w", 
                height=40,
                fg_color=("gray80", "gray30") if name == self.current_page else "transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray40")
            )
            # Zwiększone marginesy dla przycisków
            btn.pack(pady=8, fill="x", padx=15)
            self.buttons.append((name, btn))
        
        # Informacja o wersji na dole sidebar z dodanym paddingiem
        version_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        version_frame.pack(side="bottom", fill="x", pady=15)
        version_label = ctk.CTkLabel(version_frame, text="v1.2.0", text_color="gray50")
        version_label.pack(padx=15)  # Dodany padding poziomy

        # Kontener na strony - zwiększony padding od lewej strony
        self.pages_container = ctk.CTkFrame(self, fg_color="transparent")
        self.pages_container.pack(side="right", fill="both", expand=True)
        
        # Mapowanie nazw powiatów do wzorców wyszukiwania
        self.powiat_patterns = {
            "Rzeszowski": ["rzeszowski"],
            "Łańcucki": ["łańcucki", "łancuck"],
            "Ropczycko-Sędziszowski": ["ropczyck", "sędziszow", "sedziszow"]
        }
        
        # Tworzenie stron
        self.pages = {
            "Strona Główna": self.create_main_page(),
            "Rzeszowski": self.create_powiat_page("Powiat Rzeszowski"),
            "Łańcucki": self.create_powiat_page("Powiat Łańcucki"),
            "Ropczycko-Sędziszowski": self.create_powiat_page("Powiat Ropczycko-Sędziszowski")
        }

        self.show_page("Strona Główna")
        
    def load_przetargi_data(self):
        """Wczytuje dane z pliku przetargi_najlepsze_oferty.json"""
        try:
            with open(resource_path('przetargi_najlepsze_oferty.json'), 'r', encoding='utf-8') as f:
                self.przetargi_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.przetargi_data = {"przetargi": []}
            print("Błąd podczas ładowania przetargi_najlepsze_oferty.json")
            
    def refresh_data(self):
        # Odświeżamy dane
        self.load_przetargi_data()
        self.load_recent_files()
        
        # Aktualizujemy statystyki na stronie głównej
        stats = self.get_stats()
        
        # Aktualizujemy wartości na kartach statystyk
        if hasattr(self, 'stat_cards'):
            self.stat_cards["total"].configure(text=str(stats["total"]))
            self.stat_cards["active"].configure(text=str(stats["active"]))
            self.stat_cards["rolne"].configure(text=str(stats["rolne"]))
            
        # Aktualizujemy listę ostatnich plików
        self.update_recent_files_list()
        
        # Aktualizujemy dane w zakładkach z powiatami
        self.update_powiat_data()
        
        # Pokazujemy komunikat o odświeżeniu
        if hasattr(self, 'status_label'):
            self.status_label.configure(text="✓ Dane zostały odświeżone", text_color="#4CAF50")
            # Usuwamy komunikat po 3 sekundach
            self.after(3000, lambda: self.status_label.configure(text=""))
            
    def update_powiat_data(self):
        """Aktualizuje dane w zakładkach z powiatami"""
        for powiat_name in ["Rzeszowski", "Łańcucki", "Ropczycko-Sędziszowski"]:
            if powiat_name in self.pages:
                # Sprawdź czy zakładka ma przypisany kontener na dane
                if hasattr(self, f'{powiat_name.lower()}_data_container'):
                    container = getattr(self, f'{powiat_name.lower()}_data_container')
                    
                    # Wyczyść istniejące elementy
                    for widget in container.winfo_children():
                        widget.destroy()
                    
                    # Pobierz przetargi dla tego powiatu
                    przetargi = self.get_przetargi_for_powiat(powiat_name)
                    
                    if not przetargi:
                        no_data = ctk.CTkLabel(container, text=f"Brak przetargów dla powiatu {powiat_name}", 
                                             font=("Arial", 14), text_color="#555555")
                        no_data.pack(pady=20)
                    else:
                        # Utwórz nagłówki tabeli - zwiększone marginesy z 10 na 15
                        headers_frame = ctk.CTkFrame(container, fg_color="#1E3A8A")  # Tło nagłówków - ciemny niebieski
                        headers_frame.pack(fill="x", pady=(0, 8), padx=15)  # Zwiększone marginesy
                        
                        header_color = "#FFFFFF"  # Biały kolor dla tekstu nagłówków
                        
                        ctk.CTkLabel(headers_frame, text="LP", width=50, anchor="w", 
                                    font=("Arial", 12, "bold"), 
                                    text_color=header_color).pack(side="left", padx=(15, 10))  # Zwiększony lewy margines
                        ctk.CTkLabel(headers_frame, text="Data", width=100, anchor="w",
                                    font=("Arial", 12, "bold"),
                                    text_color=header_color).pack(side="left", padx=15)  # Zwiększone marginesy
                        ctk.CTkLabel(headers_frame, text="Położenie", width=250, anchor="w",
                                   font=("Arial", 12, "bold"),
                                   text_color=header_color).pack(side="left", padx=15)  # Zwiększone marginesy
                        ctk.CTkLabel(headers_frame, text="Rodzaj", width=100, anchor="w",
                                   font=("Arial", 12, "bold"),
                                   text_color=header_color).pack(side="left", padx=15)  # Zwiększone marginesy
                        ctk.CTkLabel(headers_frame, text="Powierzchnia", width=100, anchor="w",
                                   font=("Arial", 12, "bold"),
                                   text_color=header_color).pack(side="left", padx=15)  # Zwiększone marginesy
                        ctk.CTkLabel(headers_frame, text="Cena (PLN)", width=100, anchor="w",
                                   font=("Arial", 12, "bold"),
                                   text_color=header_color).pack(side="left", padx=15)  # Zwiększone marginesy
                        
                        # Separator z większymi marginesami
                        separator = ctk.CTkFrame(container, height=2, fg_color="#1E3A8A")
                        separator.pack(fill="x", padx=15, pady=8)  # Zwiększone marginesy
                        
                        # Kontener na scrollowanie z większymi marginesami
                        scroll_frame = ctk.CTkScrollableFrame(container, fg_color="transparent")
                        scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)  # Zwiększone marginesy
                        
                        # Kolory wierszy
                        row_colors = [("#F3F4F6", "#1F2937"), ("#E5E7EB", "#374151")]  # (tło, tekst) dla parzystych i nieparzystych
                        
                        # Dodaj przetargi
                        for i, przetarg in enumerate(przetargi[:30]):  # Ogranicz do 30 pozycji
                            bg_color, text_color = row_colors[i % 2]
                            
                            # Utwórz ramkę dla całego wiersza
                            row_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=6)
                            row_frame.pack(fill="x", pady=3, ipady=6)  # Zwiększone marginesy
                            
                            # Zapisz oryginalne kolory do późniejszego użycia w animacjach
                            row_frame.original_bg = bg_color
                            row_frame.original_text = text_color
                            
                            # LP z większym marginesem
                            lp_label = ctk.CTkLabel(row_frame, text=przetarg.get("lp", ""), 
                                      width=50, anchor="w",
                                      text_color=text_color)
                            lp_label.pack(side="left", padx=(15, 10))  # Zwiększony lewy margines
                            
                            # Data z większym marginesem
                            data = przetarg.get("data_godzina", "").split("\n")[0] if przetarg.get("data_godzina") else ""
                            data_label = ctk.CTkLabel(row_frame, text=data, 
                                       width=100, anchor="w",
                                       text_color=text_color)
                            data_label.pack(side="left", padx=15)  # Zwiększone marginesy
                            
                            # Położenie (skrócone) z większym marginesem
                            polozenie = przetarg.get("położenie", "")
                            if len(polozenie) > 30:
                                polozenie = polozenie[:27] + "..."
                            polozenie_label = ctk.CTkLabel(row_frame, text=polozenie, 
                                       width=250, anchor="w",
                                       text_color=text_color)
                            polozenie_label.pack(side="left", padx=15)  # Zwiększone marginesy
                            
                            # Rodzaj z większym marginesem
                            rodzaj = przetarg.get("typ_nieruchomości", "")
                            rodzaj_label = ctk.CTkLabel(row_frame, text=rodzaj, 
                                       width=100, anchor="w",
                                       text_color=text_color)
                            rodzaj_label.pack(side="left", padx=15)  # Zwiększone marginesy
                            
                            # Powierzchnia z większym marginesem
                            powierzchnia = str(przetarg.get("powierzchnia_ogolna", "")) + " ha"
                            powierzchnia_label = ctk.CTkLabel(row_frame, text=powierzchnia, 
                                       width=100, anchor="w",
                                       text_color=text_color)
                            powierzchnia_label.pack(side="left", padx=15)  # Zwiększone marginesy
                            
                            # Cena z większym marginesem
                            cena = f"{przetarg.get('cena_wywoławcza', 0):,.2f}".replace(",", " ")
                            cena_label = ctk.CTkLabel(row_frame, text=cena, 
                                       width=100, anchor="w",
                                       text_color=text_color)
                            cena_label.pack(side="left", padx=15)  # Zwiększone marginesy
                            
                            # Przycisk szczegółów z większym marginesem
                            details_btn = ctk.CTkButton(row_frame, text="Szczegóły", 
                                                     width=80, height=28,  # Nieznacznie większy przycisk
                                                     command=lambda p=przetarg: self.show_przetarg_details(p),
                                                     fg_color="#2563EB",
                                                     hover_color="#1D4ED8")
                            details_btn.pack(side="right", padx=15)  # Zwiększony margines

                            # Funkcje animacji przy kliknięciu
                            def on_click(event, frame=row_frame, p=przetarg):
                                # Animacja kliknięcia - zmiana koloru tła na niebieski
                                frame.configure(fg_color="#2563EB")  # Jasny niebieski
                                
                                # Pokazanie użytkownikowi, że nastąpiło kliknięcie
                                self.status_label.configure(text="Otwieranie geoportalu...", text_color="#FFB74D")
                                
                                # Ustaw wszystkie etykiety na biały tekst
                                for child in frame.winfo_children():
                                    if isinstance(child, ctk.CTkLabel):
                                        child.configure(text_color="#FFFFFF")
                                
                                # Opóźnione przywrócenie oryginalnych kolorów po 150ms
                                self.after(150, lambda: restore_color(frame))
                                
                                # Po zakończeniu animacji, wywołaj funkcję otwierającą geoportal
                                self.open_geoportal(p)
                            
                            def restore_color(frame):
                                # Przywrócenie oryginalnych kolorów
                                frame.configure(fg_color=frame.original_bg)
                                
                                # Przywróć oryginalny kolor tekstu dla wszystkich etykiet
                                for child in frame.winfo_children():
                                    if isinstance(child, ctk.CTkLabel):
                                        child.configure(text_color=frame.original_text)
                            
                            # Dodanie obsługi pojedynczego kliknięcia dla całego wiersza
                            row_frame.bind("<Button-1>", on_click)
                            
                            # Dodanie kursora "hand" gdy myszka jest nad wierszem
                            row_frame.bind("<Enter>", lambda e, frame=row_frame: frame.configure(cursor="hand2"))
                            row_frame.bind("<Leave>", lambda e, frame=row_frame: frame.configure(cursor=""))
                            
                            # Dodanie tych samych zdarzeń dla wszystkich etykiet w wierszu
                            for child in row_frame.winfo_children():
                                if isinstance(child, ctk.CTkLabel):
                                    child.bind("<Button-1>", lambda e, frame=row_frame, p=przetarg: on_click(e, frame, p))
                                    child.bind("<Enter>", lambda e, frame=row_frame: frame.configure(cursor="hand2"))
                                    child.bind("<Leave>", lambda e, frame=row_frame: frame.configure(cursor=""))

                            # Kliknięcie w przycisk szczegółów powinno tylko pokazać szczegóły, a nie otwierać geoportal
                            details_btn.bind("<Button-1>", lambda e: e.widget.invoke(), add="+")
                            # Zatrzymaj propagację zdarzenia kliknięcia
                            details_btn.bind("<Button-1>", lambda e: "break", add="+")
                            
    def get_przetargi_for_powiat(self, powiat_name):
        """Zwraca przetargi dla danego powiatu"""
        if not self.przetargi_data or "przetargi" not in self.przetargi_data:
            return []
            
        przetargi = []
        patterns = self.powiat_patterns.get(powiat_name, [])
        
        for przetarg in self.przetargi_data.get("przetargi", []):
            polozenie = przetarg.get("położenie", "").lower()
            
            # Sprawdź czy ten przetarg pasuje do wzorców dla danego powiatu
            if any(pattern in polozenie for pattern in patterns):
                przetargi.append(przetarg)
                
        # Sortuj według daty (najnowsze najpierw)
        przetargi.sort(key=lambda p: self.extract_date_for_sort(p.get("data_godzina", "")), reverse=False)
        
        return przetargi
        
    def extract_date_for_sort(self, data_str):
        """Ekstrahuje datę z formatu DD.MM.YYYY do sortowania"""
        try:
            if not data_str:
                return datetime.datetime(2100, 1, 1)  # Data w przyszłości dla pustych dat
                
            data_parts = data_str.split("\n")[0].split(".")
            if len(data_parts) >= 3:
                dzien, miesiac, rok = map(int, data_parts)
                return datetime.datetime(rok, miesiac, dzien)
            return datetime.datetime(2100, 1, 1)
        except:
            return datetime.datetime(2100, 1, 1)
            
    def show_przetarg_details(self, przetarg):
        """Wyświetla okno z szczegółami przetargu"""
        details_window = ctk.CTkToplevel(self)
        details_window.title("Szczegóły przetargu")
        details_window.geometry("600x500")
        details_window.grab_set()  # Zablokuj interakcję z głównym oknem
        
        # Zapobieganie utracie referencji do okna (błąd w niektórych systemach)
        details_window.master = self
        
        # Nagłówek
        header = ctk.CTkLabel(details_window, text=f"Przetarg #{przetarg.get('lp', '')}", 
                             font=("Arial", 18, "bold"))
        header.pack(pady=10)
        
        # Kontener na dane
        content = ctk.CTkFrame(details_window)
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Wyświetl wszystkie pola przetargu
        row = 0
        for key, value in przetarg.items():
            # Zamień nazwy kluczy na bardziej czytelne
            display_key = {
                "lp": "Numer przetargu",
                "data_godzina": "Data i godzina",
                "miejsce": "Miejsce",
                "położenie": "Położenie",
                "forma": "Forma",
                "rodzaj_przetargu": "Rodzaj przetargu",
                "typ_nieruchomości": "Typ nieruchomości",
                "charakter_nieruchomości": "Charakter nieruchomości",
                "obniżka": "Obniżka",
                "atrybuty": "Atrybuty",
                "powierzchnia_ogolna": "Powierzchnia ogólna (ha)",
                "powierzchnia_ur": "Powierzchnia UR (ha)",
                "cena_wywoławcza": "Cena wywoławcza (PLN)",
                "kolejny_przetarg": "Kolejny przetarg",
                "uwagi": "Uwagi"
            }.get(key, key)
            
            # Formatuj wartość
            if key == "cena_wywoławcza" and value is not None:
                display_value = f"{value:,.2f}".replace(",", " ")
            elif isinstance(value, (int, float)) and value is not None:
                display_value = str(value)
            elif value is None:
                display_value = "-"
            else:
                display_value = str(value).replace("\n", " ")
                
            # Etykieta klucza
            key_label = ctk.CTkLabel(content, text=display_key + ":", 
                                   anchor="e", width=150, 
                                   font=("Arial", 12, "bold"))
            key_label.grid(row=row, column=0, sticky="e", padx=(10, 5), pady=5)
            
            # Wartość
            value_label = ctk.CTkLabel(content, text=display_value, 
                                     anchor="w", width=350,
                                     font=("Arial", 12))
            value_label.grid(row=row, column=1, sticky="w", padx=(5, 10), pady=5)
            
            row += 1
            
        # Przycisk zamknięcia
        close_btn = ctk.CTkButton(details_window, text="Zamknij", 
                               command=details_window.destroy,
                               width=120, height=32)
        close_btn.pack(pady=15)

    def open_geoportal(self, przetarg):
        """Otwiera geoportal dla wybranego przetargu"""
        try:
            # Pokazujemy informację użytkownikowi
            self.status_label.configure(text="Otwieranie geoportalu...", text_color="#FFB74D")
            self.update()
            
            # Pobieramy położenie działki
            polozenie = przetarg.get("położenie", "")
            
            if not polozenie:
                self.status_label.configure(text="❌ Brak informacji o położeniu działki", text_color="#F44336")
                self.after(3000, lambda: self.status_label.configure(text=""))
                return
            
            # Importujemy moduł otworz_geoportal.py
            try:
                # Utwórz funkcję callback do logowania
                def log_callback(message):
                    print(f"Geoportal: {message}")
                    self.status_label.configure(text=message, text_color="#4CAF50")
                    self.update()
                
                # Bezpośrednio importuj funkcję z modułu (bez specyfikacji ścieżki)
                from otworz_geoportal import get_powiat_from_polozenie, parse_dzialka_info, search_dzialka_selenium
                
                # Wyodrębnij informacje o działce i powiecie
                powiat = get_powiat_from_polozenie(polozenie)
                dzialka_info = parse_dzialka_info(polozenie)
                
                if not powiat or not dzialka_info:
                    self.status_label.configure(text="❌ Nie udało się rozpoznać położenia działki", text_color="#F44336")
                    self.after(3000, lambda: self.status_label.configure(text=""))
                    return
                
                # Pokaż informację o rozpoczęciu wyszukiwania
                self.status_label.configure(
                    text=f"✓ Uruchamiam geoportal dla powiatu {powiat}. Proszę czekać...", 
                    text_color="#4CAF50"
                )
                
                # Uruchom wyszukiwanie w osobnym wątku, aby nie blokować GUI
                def run_search_thread():
                    try:
                        # Bezpośrednie wywołanie funkcji search_dzialka_selenium
                        search_dzialka_selenium(powiat, dzialka_info, log_callback)
                    except Exception as e:
                        print(f"Błąd w run_search_thread: {e}")
                        import traceback
                        traceback.print_exc()
                        self.status_label.configure(
                            text=f"❌ Błąd: {str(e)}", 
                            text_color="#F44336"
                        )
                
                # Uruchom w osobnym wątku, aby nie blokować GUI
                search_thread = threading.Thread(target=run_search_thread, daemon=True)
                search_thread.start()
                
            except Exception as e:
                print(f"Błąd podczas importowania modułu otworz_geoportal: {e}")
                import traceback
                traceback.print_exc()
                
                # Komunikat dla użytkownika
                self.status_label.configure(
                    text=f"⚠️ Problem z modułem geoportalu: {str(e)}", 
                    text_color="#FFB74D"
                )
                
            # Resetujemy status po czasie
            self.after(5000, lambda: self.status_label.configure(text=""))
            
        except Exception as e:
            # W przypadku błędu, wyświetlamy informację
            self.status_label.configure(
                text=f"❌ Błąd podczas otwierania geoportalu: {str(e)}", 
                text_color="#F44336"
            )
            print(f"Błąd podczas otwierania geoportalu: {str(e)}")
            import traceback
            traceback.print_exc()
            self.after(3000, lambda: self.status_label.configure(text=""))

    def append_to_log(self, message):
        """
        Dodaje wiadomość do statusu i aktualizuje interfejs
        
        Args:
            message: Komunikat do wyświetlenia
        """
        # Wyświetl wiadomość w etykiecie statusu
        self.status_label.configure(text=message)
        
        # Odśwież interfejs
        self.update()

    def run_chrome_diagnostics(self):
        """
        Uruchamia diagnostykę środowiska Chrome i ChromeDriver
        """
        try:
            # Importuj moduł otworz_geoportal
            from otworz_geoportal import debug_chrome_environment
            
            # Utwórz nowe okno z logami diagnostycznymi
            diagnostic_window = ctk.CTkToplevel(self)
            diagnostic_window.title("Diagnostyka Chrome i ChromeDriver")
            diagnostic_window.geometry("800x600")
            diagnostic_window.grab_set()  # Zablokuj interakcję z głównym oknem
            
            # Zapobieganie utracie referencji do okna
            diagnostic_window.master = self
            
            # Nagłówek
            header = ctk.CTkLabel(diagnostic_window, text="Diagnostyka Chrome i ChromeDriver",
                                font=("Arial", 18, "bold"))
            header.pack(pady=10)
            
            # Obszar na logi
            log_frame = ctk.CTkFrame(diagnostic_window)
            log_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Scrollowany obszar tekstowy na logi
            log_scroll = ctk.CTkScrollableFrame(log_frame)
            log_scroll.pack(fill="both", expand=True)
            
            # Obszar tekstowy na logi
            log_area = ctk.CTkTextbox(log_scroll, wrap="word", height=400)
            log_area.pack(fill="both", expand=True, padx=10, pady=10)
            log_area.configure(state="normal")
            
            # Funkcja do dodawania tekstu do logu
            def log_callback(message):
                log_area.configure(state="normal")
                log_area.insert("end", message + "\n")
                log_area.see("end")
                log_area.configure(state="disabled")
                diagnostic_window.update()
                
            # Informacja w głównym oknie
            self.status_label.configure(text="Uruchamiam diagnostykę Chrome i ChromeDriver...", text_color="#FFB74D")
            self.update()
            
            # Uruchom diagnostykę
            log_callback("Rozpoczynam diagnostykę Chrome i ChromeDriver...\n")
            debug_chrome_environment(log_callback)
            log_callback("\nDiagnostyka zakończona.")
            
            # Przycisk zamknięcia
            close_btn = ctk.CTkButton(diagnostic_window, text="Zamknij", 
                                   command=diagnostic_window.destroy,
                                   width=120, height=32)
            close_btn.pack(pady=15)
            
            # Zaktualizuj status w głównym oknie
            self.status_label.configure(text="Diagnostyka zakończona. Sprawdź wyniki w nowym oknie.", text_color="#4CAF50")
            
        except Exception as e:
            # W przypadku błędu
            self.status_label.configure(text=f"❌ Błąd diagnostyki: {str(e)}", text_color="#F44336")
            print(f"Błąd podczas uruchamiania diagnostyki: {e}")
            import traceback
            traceback.print_exc()

    def show_page(self, name):
        # Ukryj wszystkie strony
        for page in self.pages.values():
            page.pack_forget()
            
        # Wyświetl wybraną stronę - zwiększone marginesy z 20 na 25
        self.pages[name].pack(fill="both", expand=True, padx=25, pady=25)
        
        # Zaktualizuj stan przycisków
        self.current_page = name
        for btn_name, btn in self.buttons:
            if btn_name == name:
                btn.configure(fg_color=("gray80", "gray30"))
            else:
                btn.configure(fg_color="transparent")
        
        # Odśwież dane jeśli wracamy na stronę główną lub wybraliśmy zakładkę z powiatem
        if name == "Strona Główna":
            self.refresh_data()
        elif name in self.powiat_patterns:
            self.update_powiat_data()

    def create_main_page(self):
        frame = ctk.CTkFrame(self.pages_container)
        
        # Nagłówek z większym marginesem
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=15) # Zwiększony padding górny i dolny
        
        title = ctk.CTkLabel(header_frame, text="Panel Przetargów", font=("Arial", 26, "bold"))
        title.pack(side="left", padx=15) # Dodany padding poziomy
        
        date_label = ctk.CTkLabel(header_frame, text=f"Data: {datetime.date.today().strftime('%d.%m.%Y')}", 
                                font=("Arial", 16))
        date_label.pack(side="right", padx=15) # Dodany padding poziomy
        
        # Linia podziału
        separator = ctk.CTkFrame(frame, height=2)
        separator.pack(fill="x", pady=12, padx=15) # Zwiększone marginesy
        
        # Informacje ogólne
        info_frame = ctk.CTkFrame(frame)
        info_frame.pack(fill="x", pady=15, padx=15) # Dodany padding poziomy
        
        stats_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        stats_frame.pack(pady=20, padx=25) # Zwiększone marginesy
        
        # Pobieramy statystyki z pliku JSON
        stats = self.get_stats()
        
        # Statystyki w kartach
        cards_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cards_frame.pack(fill="x")
        
        # Tworzenie kart statystyk i zapisanie referencji do etykiet z wartościami
        self.stat_cards = {}
        self.stat_cards["total"] = self.create_stat_card(cards_frame, "Wszystkie przetargi", str(stats.get("total", "0")), 0)
        self.stat_cards["active"] = self.create_stat_card(cards_frame, "Aktywne", str(stats.get("active", "0")), 1)
        self.stat_cards["rolne"] = self.create_stat_card(cards_frame, "Nieruchomości rolne", str(stats.get("rolne", "0")), 2)
        
        # Przyciski akcji
        actions_frame = ctk.CTkFrame(frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=18, padx=15) # Zwiększone marginesy
        
        upload_button = ctk.CTkButton(actions_frame, text="📄 Dodaj nowy PDF", 
                                     command=self.process_pdf,
                                     width=200,
                                     height=40,
                                     font=("Arial", 14))
        upload_button.pack(side="left", padx=25) # Zwiększony margines między przyciskami
        
        refresh_button = ctk.CTkButton(actions_frame, text="🔄 Odśwież dane", 
                                      width=150,
                                      height=40,
                                      font=("Arial", 14),
                                      command=self.refresh_data)
        refresh_button.pack(side="left", padx=10)
        
        # Dodajemy przycisk diagnostyki Chrome
        diagnostic_button = ctk.CTkButton(actions_frame, text="🔍 Diagnostyka Chrome", 
                                       width=180,
                                       height=40,
                                       font=("Arial", 14),
                                       command=self.run_chrome_diagnostics,
                                       fg_color="#FF9800",  # pomarańczowy kolor dla wyróżnienia
                                       hover_color="#F57C00")
        diagnostic_button.pack(side="left")
        
        # Status operacji
        self.status_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.status_frame.pack(fill="x", pady=12, padx=15) # Dodane marginesy poziome
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="", text_color="green")
        self.status_label.pack(pady=5) # Dodany padding pionowy
        
        # Sekcja z ostatnio przetwarzanymi plikami
        recent_frame = ctk.CTkFrame(frame)
        recent_frame.pack(fill="both", expand=True, pady=15, padx=15) # Dodane marginesy poziome
        
        recent_title = ctk.CTkLabel(recent_frame, text="Ostatnio przetwarzane pliki", font=("Arial", 16, "bold"))
        recent_title.pack(anchor="w", padx=20, pady=15) # Zwiększone marginesy
        
        self.recent_list_frame = ctk.CTkFrame(recent_frame, fg_color="transparent")
        self.recent_list_frame.pack(fill="both", expand=True, padx=20, pady=10) # Zwiększone marginesy
        
        self.update_recent_files_list()

        return frame
        
    def create_powiat_page(self, title):
        """Tworzy stronę dla danego powiatu"""
        frame = ctk.CTkFrame(self.pages_container)
        
        # Header z powiększonymi marginesami
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=15, padx=15)  # Zwiększone marginesy
        
        label = ctk.CTkLabel(header, text=title, font=("Arial", 24, "bold"))
        label.pack(side="left", padx=15)  # Dodany padding poziomy
        
        # Liczba przetargów
        powiat_name = title.split(" ")[1]  # Wyciągnij nazwę powiatu
        przetargi = self.get_przetargi_for_powiat(powiat_name)
        count_label = ctk.CTkLabel(header, 
                                text=f"Liczba przetargów: {len(przetargi)}", 
                                font=("Arial", 14))
        count_label.pack(side="right", padx=15)  # Dodany padding poziomy
        
        # Separator z marginesami
        separator = ctk.CTkFrame(frame, height=2)
        separator.pack(fill="x", pady=12, padx=15)  # Zwiększone marginesy
        
        # Kontener na dane przetargów z powiększonymi marginesami
        data_container = ctk.CTkFrame(frame)
        data_container.pack(fill="both", expand=True, pady=15, padx=15)  # Zwiększone marginesy
        
        # Zapisz referencję do kontenera pod unikalną nazwą dla tego powiatu
        setattr(self, f'{powiat_name.lower()}_data_container', data_container)
        
        # Dodaj dane przetargów (będą dodane przez update_powiat_data)
        
        return frame
        
    def create_stat_card(self, parent, title, value, position):
        card = ctk.CTkFrame(parent, width=150, height=100, corner_radius=10)
        card.pack(side="left", padx=10, pady=10)
        card.pack_propagate(False)
        
        value_label = ctk.CTkLabel(card, text=value, font=("Arial", 28, "bold"))
        value_label.pack(pady=(20, 5))
        
        title_label = ctk.CTkLabel(card, text=title, font=("Arial", 14))
        title_label.pack()
        
        return value_label  # Zwracamy etykietę z wartością, aby można było ją później aktualizować
        
    def get_stats(self):
        """Pobiera statystyki z pliku przetargi_najlepsze_oferty.json"""
        try:
            if not self.przetargi_data or "przetargi" not in self.przetargi_data:
                self.load_przetargi_data()
                
            przetargi = self.przetargi_data.get("przetargi", [])
            total = len(przetargi)
            
            # Zliczamy przetargi według różnych kategorii
            active = 0
            rolne = 0
            
            # Aktualny dzień - 11 kwietnia 2025
            dzisiaj = datetime.datetime(2025, 4, 11)
            
            for p in przetargi:
                # Sprawdzamy czy przetarg jest aktywny (data przetargu jest w przyszłości)
                try:
                    data_str = p.get("data_godzina", "").split("\n")[0]
                    if data_str:
                        data_parts = data_str.split(".")
                        if len(data_parts) >= 3:
                            # Format: DD.MM.YYYY
                            dzien, miesiac, rok = map(int, data_parts)
                            data_przetargu = datetime.datetime(rok, miesiac, dzien)
                            if data_przetargu > dzisiaj:
                                active += 1
                except (ValueError, IndexError):
                    pass
                    
                # Sprawdzamy czy to nieruchomość rolna
                if p.get("typ_nieruchomości", "").lower() == "rolna":
                    rolne += 1
            
            return {
                "total": total,
                "active": active,
                "rolne": rolne
            }
        except Exception as e:
            print(f"Błąd podczas pobierania statystyk: {e}")
            return {"total": 0, "active": 0, "rolne": 0}

    def process_pdf(self):
        filepath = filedialog.askopenfilename(
            title="Wybierz plik PDF z przetargami",
            filetypes=[("Pliki PDF", "*.pdf")]
        )
        
        if filepath:
            # Pokaż progres
            self.status_label.configure(text="Przetwarzanie...", text_color="#FFB74D")
            
            # Utworzenie progress baru
            progress_frame = ctk.CTkFrame(self.status_frame)
            progress_frame.pack(pady=10, fill="x", padx=30)
            
            progress = ctk.CTkProgressBar(progress_frame)
            progress.pack(fill="x", pady=5)
            progress.set(0)
            
            # Aktualizacja UI
            self.update()
            
            try:
                # Symulacja postępu
                for i in range(11):
                    progress.set(i/10)
                    self.update()
                    self.after(100)  # Mała pauza
                
                # Uruchomienie skryptów przetwarzających
                subprocess.run(["python", "pdfToText.py", filepath], check=True)
                
                for i in range(11):
                    progress.set(0.5 + i/20)
                    self.update()
                    self.after(100)
                    
                subprocess.run(["python", "filtruj_wszystko.py"], check=True)
                
                for i in range(11):
                    progress.set(0.75 + i/40)
                    self.update()
                    self.after(100)
                
                # Zakończenie
                progress.set(1)
                self.update()
                self.after(300)
                
                # Dodaj do ostatnio przetwarzanych
                self.add_recent_file(os.path.basename(filepath))
                
                # Odśwież dane po przetworzeniu - teraz z przetargi_najlepsze_oferty.json
                self.refresh_data()
                
                # Usuń progress bar po zakończeniu
                progress_frame.destroy()
                
                self.status_label.configure(text="✓ Gotowe! Dane zaktualizowane.", text_color="#4CAF50")
                
            except subprocess.CalledProcessError:
                # Obsługa błędu
                progress_frame.destroy()
                self.status_label.configure(text="❌ Błąd podczas przetwarzania.", text_color="#F44336")

    def add_recent_file(self, filename):
        """Dodaje plik do listy ostatnio przetwarzanych"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.recent_files.insert(0, {"name": filename, "date": timestamp})
        
        # Ogranicz do 5 najnowszych plików
        if len(self.recent_files) > 5:
            self.recent_files = self.recent_files[:5]
            
        # Zapisz do pamięci
        self.save_recent_files()
        
        # Aktualizuj UI
        self.update_recent_files_list()
        
    def save_recent_files(self):
        """Zapisuje listę ostatnich plików"""
        try:
            with open(resource_path("recent_files.json"), "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd podczas zapisu ostatnich plików: {e}")
            
    def load_recent_files(self):
        """Wczytuje listę ostatnich plików"""
        try:
            with open(resource_path("recent_files.json"), "r", encoding="utf-8") as f:
                self.recent_files = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.recent_files = []
            
    def update_recent_files_list(self):
        """Aktualizuje UI z listą ostatnich plików"""
        # Usuń istniejące elementy
        for widget in self.recent_list_frame.winfo_children():
            widget.destroy()
            
        if not self.recent_files:
            no_files = ctk.CTkLabel(self.recent_list_frame, 
                                  text="Brak ostatnio przetwarzanych plików",
                                  text_color="gray50")
            no_files.pack(pady=20)
            return
            
        # Dodaj nagłówki
        header = ctk.CTkFrame(self.recent_list_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header, text="Nazwa pliku", width=350, anchor="w").pack(side="left", padx=(10, 0))
        ctk.CTkLabel(header, text="Data przetwarzania", width=200, anchor="w").pack(side="left")
        
        # Separator
        ctk.CTkFrame(self.recent_list_frame, height=1).pack(fill="x", pady=(0, 5))
        
        # Dodaj pliki
        for file_info in self.recent_files:
            file_row = ctk.CTkFrame(self.recent_list_frame, fg_color="transparent")
            file_row.pack(fill="x", pady=2)
            
            file_name = ctk.CTkLabel(file_row, text=file_info["name"], anchor="w", width=350)
            file_name.pack(side="left", padx=(10, 0))
            
            file_date = ctk.CTkLabel(file_row, text=file_info["date"], width=200, anchor="w")
            file_date.pack(side="left")

if __name__ == "__main__":
    app = PrzetargiApp()
    app.mainloop()
