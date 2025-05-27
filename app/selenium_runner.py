#!/usr/bin/env python3
"""
Selenium runner script for opening geoportal records
Comprehensive powiat-specific implementation for Polish geoportal automation
"""

import json
import webbrowser
import re
import sys
import time
import argparse
import os
import tempfile
import stat
import platform
import subprocess
import importlib
import traceback
from typing import Dict, Optional, Callable, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException

# Try to import webdriver_manager if available
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

def resource_path(relative_path: str) -> str:
    """Return absolute path to resource, works for development and PyInstaller packaging"""
    try:
        # PyInstaller creates temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def _log(message: str, callback: Optional[Callable] = None) -> None:
    """Helper function for logging messages"""
    if callback:
        callback(message)
    else:
        print(message)

def get_chrome_path() -> Optional[str]:
    """Return path to Chrome browser on different operating systems"""
    system = platform.system()
    
    if system == "Windows":
        # Try Windows registry first
        try:
            import winreg
            # Check for user installation first
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            chrome_path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            return chrome_path
        except:
            # Try system installation
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                chrome_path, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                return chrome_path
            except:
                # Try common locations as fallback
                common_locations = [
                    os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
                ]
                for location in common_locations:
                    if os.path.exists(location):
                        return location
                return None
                
    elif system == "Darwin":  # macOS
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path
        return None
        
    else:  # Linux and others
        for chrome_cmd in ["google-chrome", "chrome", "chromium", "chromium-browser"]:
            try:
                chrome_path = subprocess.check_output(["which", chrome_cmd]).decode("utf-8").strip()
                if chrome_path:
                    return chrome_path
            except:
                pass
        return None


def create_chrome_driver(chrome_path: Optional[str] = None, log_callback: Optional[Callable] = None) -> Optional[webdriver.Chrome]:
    """Create and configure ChromeDriver for automation"""
    try:
        _log("Configuring ChromeDriver...", log_callback)
        
        # Chrome options for better compatibility
        chrome_options = Options()
        chrome_options.add_argument("--disable-features=DataUrlSupport")
        chrome_options.add_argument("--allow-file-access-from-files")
        chrome_options.add_argument("--allow-file-access")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Create custom Chrome profile
        user_data_dir = os.path.join(tempfile.gettempdir(), "geoportal_chrome_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Set Chrome binary location if provided
        if chrome_path:
            _log(f"Using Chrome from location: {chrome_path}", log_callback)
            chrome_options.binary_location = chrome_path

        driver = None
        system = platform.system()
        
        # macOS specific method using local ChromeDriver
        if system == "Darwin":
            try:
                _log("Trying macOS method: Using local ChromeDriver", log_callback)
                
                driver_name = "chromedriver"
                chrome_driver_path = resource_path(driver_name)
                
                # If not found locally, try to find system ChromeDriver
                if not os.path.exists(chrome_driver_path):
                    _log("ChromeDriver not found locally, trying system ChromeDriver", log_callback)
                    try:
                        driver_path = subprocess.check_output(["which", "chromedriver"]).decode().strip()
                        if driver_path:
                            chrome_driver_path = driver_path
                            _log(f"Found system ChromeDriver: {chrome_driver_path}", log_callback)
                    except:
                        _log("System ChromeDriver not found", log_callback)
                else:
                    _log(f"Found local ChromeDriver at: {chrome_driver_path}", log_callback)
                
                # Set execution permissions for ChromeDriver
                if os.path.exists(chrome_driver_path):
                    try:
                        os.chmod(chrome_driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                        _log("Set execution permissions for ChromeDriver", log_callback)
                    except Exception as e:
                        _log(f"Warning: Could not set permissions: {e}", log_callback)
                
                # Initialize ChromeDriver
                service = Service(executable_path=chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log("Success! ChromeDriver initialized on macOS", log_callback)
                return driver
            except Exception as e:
                _log(f"macOS method failed: {e}", log_callback)
                _log("Hint: Try installing ChromeDriver via brew: `brew install --cask chromedriver`", log_callback)
        
        # Method 1: Use WebDriverManager if available
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                _log("Trying method 1: WebDriverManager", log_callback)
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log("Success! ChromeDriver initialized with WebDriverManager", log_callback)
                return driver
            except Exception as e:
                _log(f"WebDriverManager method failed: {e}", log_callback)
        
        # Method 2: Try system ChromeDriver
        try:
            _log("Trying method 2: System ChromeDriver", log_callback)
            driver = webdriver.Chrome(options=chrome_options)
            _log("Success! ChromeDriver initialized from system PATH", log_callback)
            return driver
        except Exception as e:
            _log(f"System ChromeDriver method failed: {e}", log_callback)
        
        # Method 3: Try local ChromeDriver
        try:
            _log("Trying method 3: Local ChromeDriver", log_callback)
            driver_name = "chromedriver.exe" if system == "Windows" else "chromedriver"
            local_driver_path = resource_path(driver_name)
            
            if os.path.exists(local_driver_path):
                _log(f"Found local ChromeDriver: {local_driver_path}", log_callback)
                service = Service(executable_path=local_driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                _log("Success! ChromeDriver initialized from local path", log_callback)
                return driver
            else:
                _log(f"Local ChromeDriver not found at: {local_driver_path}", log_callback)
        except Exception as e:
            _log(f"Local ChromeDriver method failed: {e}", log_callback)
        
        _log("All ChromeDriver initialization methods failed", log_callback)
        return None
        
    except Exception as e:
        _log(f"Error configuring ChromeDriver: {e}", log_callback)
        
        # Show detailed traceback in console mode
        if log_callback is None:
            traceback.print_exc()
        else:
            # In GUI mode show shortened traceback
            tb_lines = traceback.format_exc().split('\n')
            for line in tb_lines[-10:]:  # Show only last 10 lines
                _log(line, log_callback)
                
        return None


def _log(message: str, callback: Optional[Callable] = None) -> None:
    """Helper function for logging messages"""
    if callback:
        callback(message)
    else:
        print(message)


def get_powiat_from_polozenie(polozenie_str: str) -> Optional[str]:
    """Extract powiat name from 'położenie' field"""
    if not polozenie_str:
        return None
    
    # Try to match powiat - second part after "/"
    match = re.search(r'podkarpackie/\s*(\w+(?:[-\s]+\w+)*)', polozenie_str)
    if match:
        return match.group(1).strip()
    return None


def get_geoportal_url(powiat: str) -> str:
    """Return geoportal URL for given powiat"""
    # Dictionary mapping powiat names to their respective URLs
    powiat_urls = {
        "łańcucki": "https://lancut.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice+OSM+",
        "ropczycko sędziszowski": "https://spropczyce.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice1,granice2+OSM+",
        "rzeszowski": "https://powiatrzeszowski.geoportal2.pl/map/www/mapa.php?CFGF=wms&mylayers=+granice+OSM+"
        # Add more powiaty as needed
    }
    
    # Normalize powiat name (lowercase, strip whitespace)
    powiat_norm = powiat.lower().strip() if powiat else ""
    
    # Return URL for given powiat or default URL if not found
    return powiat_urls.get(powiat_norm, "https://mapy.geoportal.gov.pl")


def parse_dzialka_info(polozenie: str) -> Dict[str, str]:
    """Extract plot information: województwo, powiat, gmina, obręb, numer działki"""
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
    
    # Obręb (locality) - often after gmina
    obreb_match = re.search(r'(?:podkarpackie/\s*\w+(?:[-\s]+\w+)*/\s*[^/]+/\s*)([^/\(]+)', polozenie)
    if obreb_match:
        info['obreb'] = obreb_match.group(1).strip()
    
    # Plot number (last part after '/')
    dzialka_match = re.search(r'(\d+(?:/\d+)*(?:\s*i\s*\d+(?:/\d+)*)*)\s*(?:\(kompleks\))?$', polozenie)
    if dzialka_match:
        info['nr_dzialki'] = dzialka_match.group(1).strip()
    
    return info


def search_lancut(driver: webdriver.Chrome, dzialka_info: Dict[str, str], log_callback: Optional[Callable] = None) -> None:
    """Search for plot on Łańcut powiat geoportal with improved error handling and waits"""
    try:
        _log("Waiting for geoportal page to load...", log_callback)
        
        # Use WebDriverWait for better reliability
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to be fully loaded
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)  # Additional wait for JavaScript to initialize
        
        # Click on "Szukaj" header if collapsed - with better selectors
        _log("Looking for 'Szukaj' header...", log_callback)
        search_header_found = False
        
        # Try multiple selectors for the search header
        search_selectors = [
            (By.ID, "szukaj_id"),
            (By.XPATH, "//a[contains(text(), 'Szukaj')]"),
            (By.XPATH, "//div[contains(@class, 'menu')]//a[contains(text(), 'Szukaj')]"),
            (By.XPATH, "//*[contains(@onclick, 'szukaj') or contains(@href, 'szukaj')]")
        ]
        
        for selector_by, selector_value in search_selectors:
            try:
                search_header = wait.until(EC.element_to_be_clickable((selector_by, selector_value)))
                _log(f"Found 'Szukaj' header using selector: {selector_by} = {selector_value}", log_callback)
                search_header.click()
                _log("Clicked 'Szukaj' header", log_callback)
                search_header_found = True
                time.sleep(2)
                break
            except TimeoutException:
                continue
            except Exception as e:
                _log(f"Error with selector {selector_by}={selector_value}: {e}", log_callback)
                continue
        
        if not search_header_found:
            _log("'Szukaj' header not found with any selector. Menu might already be expanded.", log_callback)
        
        # Click on "Działka" button with improved selectors
        _log("Looking for 'Działka' button...", log_callback)
        dzialka_button_found = False
        
        # Try multiple selectors for the plot search button
        dzialka_selectors = [
            (By.ID, "szukaj_dzialki"),
            (By.XPATH, "//button[@title='Wyszukiwanie numeru działki']"),
            (By.XPATH, "//button[contains(text(), 'Działka')]"),
            (By.XPATH, "//input[@value='Działka']"),
            (By.XPATH, "//*[contains(@onclick, 'dzialka') or contains(@onclick, 'działka')]"),
            (By.XPATH, "//a[contains(@href, 'dzialka') or contains(text(), 'Działka')]")
        ]
        
        for selector_by, selector_value in dzialka_selectors:
            try:
                dzialka_button = wait.until(EC.element_to_be_clickable((selector_by, selector_value)))
                _log(f"Found 'Działka' button using selector: {selector_by} = {selector_value}", log_callback)
                dzialka_button.click()
                _log("Clicked 'Działka' button", log_callback)
                dzialka_button_found = True
                time.sleep(2)
                break
            except TimeoutException:
                continue
            except Exception as e:
                _log(f"Error with selector {selector_by}={selector_value}: {e}", log_callback)
                continue
        
        if not dzialka_button_found:
            _log("'Działka' button not found with any selector. Try searching manually.", log_callback)
            return
        
        # Wait for dialog/iframe to load with improved detection
        _log("Waiting for search dialog to load...", log_callback)
        time.sleep(3)
        
        # Look for iframe containing the search form with multiple strategies
        _log("Looking for iframe with search form...", log_callback)
        iframe = None
        
        # Try different iframe selectors
        iframe_selectors = [
            (By.ID, "frame_szukaj_dzialki"),
            (By.NAME, "frame_szukaj_dzialki"),
            (By.XPATH, "//iframe[contains(@src, 'dzialka') or contains(@name, 'dzialka')]"),
            (By.TAG_NAME, "iframe")  # Fallback to any iframe
        ]
        
        for selector_by, selector_value in iframe_selectors:
            try:
                if selector_by == By.TAG_NAME:
                    # For the fallback case, get all iframes and find the right one
                    iframes = driver.find_elements(selector_by, selector_value)
                    if iframes:
                        iframe = iframes[0]  # Take the first iframe
                        _log(f"Found iframe using fallback (one of {len(iframes)} iframes)", log_callback)
                        break
                else:
                    iframe = wait.until(EC.presence_of_element_located((selector_by, selector_value)))
                    _log(f"Found iframe using selector: {selector_by} = {selector_value}", log_callback)
                    break
            except TimeoutException:
                continue
            except Exception as e:
                _log(f"Error finding iframe with {selector_by}={selector_value}: {e}", log_callback)
                continue
                        
        if iframe is None:
            _log("No iframe found. Trying to search in main page...", log_callback)
            # Try to search in the main page if no iframe is found
            iframe_context = False
        else:
            # Switch to iframe
            driver.switch_to.frame(iframe)
            _log("Switched to iframe", log_callback)
            iframe_context = True
            time.sleep(2)
        
        # Fill search form with improved error handling
        try:
            form_wait = WebDriverWait(driver, 5)
            
            # Fill gmina with better error handling
            if dzialka_info.get('gmina'):
                try:
                    gmina_element = form_wait.until(EC.presence_of_element_located((By.NAME, "gmina")))
                    gmina_select = Select(gmina_element)
                    
                    # First try exact match
                    try:
                        gmina_select.select_by_visible_text(dzialka_info['gmina'])
                        _log(f"Selected gmina (exact match): {dzialka_info['gmina']}", log_callback)
                    except Exception:
                        # Try partial match
                        found_match = False
                        options = gmina_select.options
                        for option in options:
                            if dzialka_info['gmina'].lower() in option.text.lower() or option.text.lower() in dzialka_info['gmina'].lower():
                                gmina_select.select_by_visible_text(option.text)
                                _log(f"Selected gmina (partial match): {option.text}", log_callback)
                                found_match = True
                                break
                        
                        if not found_match:
                            _log(f"Could not find any gmina matching '{dzialka_info['gmina']}'", log_callback)
                            _log(f"Available options: {[opt.text for opt in options[:5]]}", log_callback)  # Show first 5 options
                    
                    time.sleep(1)
                    
                except Exception as e:
                    _log(f"Error with gmina selection: {e}", log_callback)
            
            # Fill obręb with better error handling
            if dzialka_info.get('obreb'):
                try:
                    obreb_element = form_wait.until(EC.presence_of_element_located((By.NAME, "obreb")))
                    obreb_select = Select(obreb_element)
                    
                    # First try exact match
                    try:
                        obreb_select.select_by_visible_text(dzialka_info['obreb'])
                        _log(f"Selected obręb (exact match): {dzialka_info['obreb']}", log_callback)
                    except Exception:
                        # Try partial match
                        found_match = False
                        options = obreb_select.options
                        for option in options:
                            if dzialka_info['obreb'].lower() in option.text.lower() or option.text.lower() in dzialka_info['obreb'].lower():
                                obreb_select.select_by_visible_text(option.text)
                                _log(f"Selected obręb (partial match): {option.text}", log_callback)
                                found_match = True
                                break
                        
                        if not found_match:
                            _log(f"Could not find any obręb matching '{dzialka_info['obreb']}'", log_callback)
                            _log(f"Available options: {[opt.text for opt in options[:5]]}", log_callback)  # Show first 5 options
                    
                    time.sleep(1)
                    
                except Exception as e:
                    _log(f"Error with obręb selection: {e}", log_callback)
            
            # Fill plot number with improved selectors
            if dzialka_info.get('nr_dzialki'):
                plot_number_found = False
                plot_selectors = [
                    (By.NAME, "nr_dzialki"),
                    (By.NAME, "dzialka"),
                    (By.ID, "nr_dzialki"),
                    (By.ID, "dzialka"),
                    (By.XPATH, "//input[@type='text' and (contains(@name, 'dzialka') or contains(@placeholder, 'działka'))]")
                ]
                
                for selector_by, selector_value in plot_selectors:
                    try:
                        nr_dzialki_input = form_wait.until(EC.presence_of_element_located((selector_by, selector_value)))
                        nr_dzialki_input.clear()
                        nr_dzialki_input.send_keys(dzialka_info['nr_dzialki'])
                        _log(f"Entered plot number: {dzialka_info['nr_dzialki']} using {selector_by}={selector_value}", log_callback)
                        plot_number_found = True
                        break
                    except TimeoutException:
                        continue
                    except Exception as e:
                        _log(f"Error entering plot number with {selector_by}={selector_value}: {e}", log_callback)
                        continue
                
                if not plot_number_found:
                    _log(f"Could not find plot number input field", log_callback)
            
            # Click search button with improved selectors
            search_button_found = False
            search_button_selectors = [
                (By.XPATH, "//input[@type='submit' and @value='Szukaj']"),
                (By.XPATH, "//button[contains(text(), 'Szukaj')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//*[contains(@onclick, 'search') or contains(@onclick, 'szukaj')]")
            ]
            
            for selector_by, selector_value in search_button_selectors:
                try:
                    search_button = form_wait.until(EC.element_to_be_clickable((selector_by, selector_value)))
                    search_button.click()
                    _log(f"Clicked search button using {selector_by}={selector_value}", log_callback)
                    search_button_found = True
                    break
                except TimeoutException:
                    continue
                except Exception as e:
                    _log(f"Error clicking search button with {selector_by}={selector_value}: {e}", log_callback)
                    continue
            
            if not search_button_found:
                _log("Could not find or click search button", log_callback)
            else:
                # Wait for results with timeout
                _log("Waiting for search results...", log_callback)
                time.sleep(5)
                _log("Search completed", log_callback)
                
        except Exception as e:
            _log(f"Error filling search form: {e}", log_callback)
            
        finally:
            # Switch back to main frame if we were in an iframe
            if iframe_context:
                try:
                    driver.switch_to.default_content()
                    _log("Switched back to main frame", log_callback)
                except Exception as e:
                    _log(f"Error switching back to main frame: {e}", log_callback)
                
    except Exception as e:
        _log(f"Error in Łańcut search: {e}", log_callback)
        if log_callback is None:  # Console mode - show detailed error
            traceback.print_exc()

def search_ropczyce(driver: webdriver.Chrome, dzialka_info: Dict[str, str], log_callback: Optional[Callable] = None) -> None:
    """Search for plot on Ropczyce-Sędziszów powiat geoportal"""
    try:
        _log("Waiting for Ropczyce geoportal to load...", log_callback)
        time.sleep(5)
        
        # Implementation for Ropczyce-Sędziszów powiat
        # This would need to be customized based on their specific interface
        _log("Ropczyce geoportal automation - implementation needed", log_callback)
        _log(f"Please manually search for plot {dzialka_info.get('nr_dzialki')} in {dzialka_info.get('obreb')}", log_callback)
        
    except Exception as e:
        _log(f"Error in Ropczyce search: {e}", log_callback)

def search_rzeszowski(driver: webdriver.Chrome, dzialka_info: Dict[str, str], log_callback: Optional[Callable] = None) -> None:
    """Search for plot on Rzeszów powiat geoportal"""
    try:
        _log("Waiting for Rzeszów powiat geoportal to load...", log_callback)
        time.sleep(5)
        
        # Implementation for Rzeszów powiat
        # This would need to be customized based on their specific interface
        _log("Rzeszów powiat geoportal automation - implementation needed", log_callback)
        _log(f"Please manually search for plot {dzialka_info.get('nr_dzialki')} in {dzialka_info.get('obreb')}", log_callback)
        
    except Exception as e:
        _log(f"Error in Rzeszów powiat search: {e}", log_callback)

def search_dzialka_selenium(powiat: str, dzialka_info: Dict[str, str], log_callback: Optional[Callable] = None) -> None:
    """Search for plot on geoportal using Selenium automation"""
    url = get_geoportal_url(powiat)
    log_message = f"Automatic search for plot nr {dzialka_info.get('nr_dzialki')} in {dzialka_info.get('obreb')}"
    _log(log_message, log_callback)
    _log(f"Opening geoportal for powiat {powiat}: {url}", log_callback)
    
    try:
        # Find Chrome and initialize ChromeDriver
        chrome_path = get_chrome_path()
        if chrome_path:
            _log(f"Found Chrome at: {chrome_path}", log_callback)
        else:
            _log("WARNING: Google Chrome not found! Trying default location...", log_callback)
        
        # Use new function to create WebDriver
        driver = create_chrome_driver(chrome_path, log_callback)
        
        if not driver:
            _log("ERROR: Could not initialize ChromeDriver!", log_callback)
            _log("Try installing Chrome and run the application again.", log_callback)
            if not log_callback:  # Console mode
                webbrowser.open(url)  # Open URL in default browser
                return
        
        # Open URL in browser
        _log(f"Opening URL: {url}", log_callback)
        driver.get(url)
        
        # Wait for page to load
        _log("Waiting for page to load...", log_callback)
        time.sleep(5)
        
        # Different implementations for different powiaty
        if "łańcucki" in powiat.lower():
            search_lancut(driver, dzialka_info, log_callback)
        elif "ropczycko sędziszowski" in powiat.lower():
            search_ropczyce(driver, dzialka_info, log_callback)
        elif "rzeszowski" in powiat.lower():
            search_rzeszowski(driver, dzialka_info, log_callback)
        else:
            _log(f"Automatic search for powiat {powiat} is not yet implemented.", log_callback)
            _log("Geoportal page opened, you can manually search for the plot.", log_callback)
        
        # Keep browser open for manual verification
        _log("\nBrowser will remain open for manual verification. Close it manually when finished.", log_callback)
        
        # For web interface mode, keep browser open but set up cleanup
        if log_callback:  # Web interface mode
            _log("Note: Browser will remain open. Please close manually when finished.", log_callback)
            # Don't quit driver immediately in web mode to allow manual verification
        else:  # Console mode
            input("\nPress Enter to close browser and exit program...")
            driver.quit()
        
    except Exception as e:
        error_message = f"Error during automatic search: {e}"
        _log(error_message, log_callback)
        
        # In console mode show full error
        if log_callback is None:
            traceback.print_exc()
            
        _log("Try searching manually in the already opened browser.", log_callback)
def open_in_geoportal(record: Dict[str, Any]) -> None:
    """
    Main function to open a record in geoportal using Selenium automation.
    
    Args:
        record: Dictionary containing record data with 'położenie' field
    """
    if not record or 'położenie' not in record:
        print("Error: Record must contain 'położenie' field")
        return
    
    polozenie = record['położenie']
    print(f"Opening geoportal for record: {polozenie}")
    
    # Parse plot information
    dzialka_info = parse_dzialka_info(polozenie)
    powiat = dzialka_info.get('powiat', '')
    
    if not powiat:
        print("Error: Could not extract county from location data")
        # Try to open default geoportal
        try:
            webbrowser.open("https://mapy.geoportal.gov.pl")
        except:
            pass
        return
    
    print(f"Extracted data:")
    print(f"  County: {dzialka_info.get('powiat', 'Not specified')}")
    print(f"  Municipality: {dzialka_info.get('gmina', 'Not specified')}")
    print(f"  Precinct: {dzialka_info.get('obreb', 'Not specified')}")
    print(f"  Plot number: {dzialka_info.get('nr_dzialki', 'Not specified')}")
    
    # Get geoportal URL for county
    url = get_geoportal_url(powiat)
    log_message = f"Automatic search for plot nr {dzialka_info.get('nr_dzialki')} in precinct {dzialka_info.get('obreb')}"
    print(log_message)
    print(f"Opening geoportal for county {powiat}: {url}")
    
    try:
        # Find Chrome and initialize ChromeDriver
        chrome_path = get_chrome_path()
        if chrome_path:
            print(f"Found Chrome at location: {chrome_path}")
        else:
            print("WARNING: Google Chrome not found! Trying default location...")
        
        # Use new function to create WebDriver
        driver = create_chrome_driver(chrome_path, None)
        
        if not driver:
            print("ERROR: Could not initialize ChromeDriver!")
            print("Try installing Chrome and restart the application.")
            # Fallback to opening URL in default browser
            try:
                webbrowser.open(url)
            except:
                pass
            return
        
        # Open URL in browser
        print(f"Opening URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(5)
        
        # Different implementations for different counties
        supported_counties = ["łańcucki", "ropczycko sędziszowski", "rzeszowski"]
        
        if any(county.lower() in powiat.lower() for county in supported_counties):
            if "łańcucki" in powiat.lower():
                # Implementation for Łańcut county
                search_lancut(driver, dzialka_info, None)
            elif "ropczycko sędziszowski" in powiat.lower():
                # Implementation for Ropczyce-Sędziszów county
                search_ropczyce(driver, dzialka_info, None)
            elif "rzeszowski" in powiat.lower():
                # Implementation for Rzeszów county
                search_rzeszowski(driver, dzialka_info, None)
        else:
            # For other counties just open the page
            print(f"Automatic search for county {powiat} is not yet implemented.")
            print("Geoportal page opened, you can manually search for the plot.")
        
        # Keep browser open
        print("\nBrowser will remain open. Close it manually when finished browsing.")
        
        # In non-GUI mode we don't wait for key press, but leave browser open
        input("\nPress Enter to close browser and exit program...")
        driver.quit()
        
    except Exception as e:
        error_message = f"Error during automatic search: {e}"
        print(error_message)
        
        # In console mode show full error
        traceback.print_exc()
            
        print("Try searching for the plot manually in the already opened browser.")


def open_in_geoportal(record: Dict[str, Any], log_callback: Optional[Callable] = None) -> bool:
    """
    Open geoportal for a record using comprehensive powiat-specific automation
    
    Args:
        record: Dictionary containing record data with 'położenie' field
        log_callback: Optional callback function for logging messages
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        polozenie = record.get('położenie', '')
        if not polozenie:
            _log("No 'położenie' field found in record", log_callback)
            return False
        
        _log(f"Processing location: {polozenie}", log_callback)
        
        # Extract plot information
        dzialka_info = parse_dzialka_info(polozenie)
        powiat = dzialka_info.get('powiat', '')
        
        if not powiat:
            _log("Could not extract powiat from location", log_callback)
            # Fallback to default geoportal
            url = get_geoportal_url('')
            _log(f"Opening default geoportal: {url}", log_callback)
            webbrowser.open(url)
            return True
        
        _log(f"Extracted powiat: {powiat}", log_callback)
        _log(f"Gmina: {dzialka_info.get('gmina', 'Not specified')}", log_callback)
        _log(f"Obręb: {dzialka_info.get('obreb', 'Not specified')}", log_callback)
        _log(f"Plot number: {dzialka_info.get('nr_dzialki', 'Not specified')}", log_callback)
        
        # Check if automatic search is supported for this powiat
        supported_powiaty = ["łańcucki", "ropczycko sędziszowski", "rzeszowski"]
        
        if powiat and any(p.lower() in powiat.lower() for p in supported_powiaty):
            _log(f"Powiat {powiat} supports automatic search!", log_callback)
            
            # For web interface, always use automatic search
            # For console mode, this could be made configurable
            if log_callback:  # Web interface mode
                search_dzialka_selenium(powiat, dzialka_info, log_callback)
            else:  # Console mode - could ask user
                _log("Using automatic plot search...", log_callback)
                search_dzialka_selenium(powiat, dzialka_info, log_callback)
        else:
            _log(f"Automatic search for powiat {powiat} not yet implemented.", log_callback)
            url = get_geoportal_url(powiat)
            _log(f"Opening geoportal for powiat {powiat}: {url}", log_callback)
            _log(f"Please manually search for plot nr {dzialka_info.get('nr_dzialki', '')} in {dzialka_info.get('obreb', '')}", log_callback)
            webbrowser.open(url)
        
        return True
        
    except Exception as e:
        error_message = f"Error opening geoportal: {e}"
        _log(error_message, log_callback)
        
        if log_callback is None:  # Console mode
            traceback.print_exc()
        
        return False

def open_geoportal_record(record_id: int) -> bool:
    """
    Legacy function to open a specific record in geoportal.
    Updated to use comprehensive powiat-specific implementation.
    """
    print(f"Opening geoportal record {record_id}...")
    
    # This is a placeholder - in real implementation you would:
    # 1. Load record data from database/file using record_id
    # 2. Call open_in_geoportal(record) with the loaded data
    
    # For now, create a sample record to demonstrate the new functionality
    sample_record = {
        'lp': record_id,
        'położenie': 'podkarpackie/łańcucki/Łańcut/Łańcut/123'  # Sample location
    }
    
    return open_in_geoportal(sample_record)


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Open geoportal record using Selenium")
    parser.add_argument("--record-id", type=int, help="Record ID to open in geoportal (legacy mode)")
    parser.add_argument("--record-file", type=str, help="JSON file containing record data")
    parser.add_argument("--polozenie", type=str, help="Location string for direct search")
    
    args = parser.parse_args()
    
    if args.record_id:
        # Legacy mode
        success = open_geoportal_record(args.record_id)
        if success:
            print(f"Successfully processed record {args.record_id}")
            sys.exit(0)
        else:
            print(f"Failed to process record {args.record_id}")
            sys.exit(1)
            
    elif args.record_file:
        # Load record from JSON file
        try:
            with open(args.record_file, 'r', encoding='utf-8') as f:
                record = json.load(f)
            open_in_geoportal(record)
            print("Successfully processed record from file")
            sys.exit(0)
        except Exception as e:
            print(f"Error loading record file: {e}")
            sys.exit(1)
            
    elif args.polozenie:
        # Direct location search
        record = {'położenie': args.polozenie}
        open_in_geoportal(record)
        print("Successfully processed location")
        sys.exit(0)
        
    else:
        # No arguments provided
        print("Usage examples:")
        print("  python selenium_runner.py --record-id 123")
        print("  python selenium_runner.py --record-file record.json")
        print("  python selenium_runner.py --polozenie 'podkarpackie/łańcucki/gmina/obręb/123'")
        sys.exit(1)

if __name__ == "__main__":
    main()
