# Geoportal App

A FastAPI application for processing PDF files and integrating with the Polish geoportal system.

## Features

- **PDF Processing**: Upload PDF files to extract and filter auction data using pdfplumber
- **Geoportal Integration**: Open specific records in the geoportal using Selenium automation
- **Web Interface**: Modern, responsive web interface for easy interaction

## Endpoints

### 1. GET `/`
Serves the main HTML interface from the templates folder.

### 2. POST `/upload`
Accepts PDF file uploads, extracts auction data, filters it, and returns structured JSON.

**Request**: Multipart form data with PDF file
**Response**: JSON with extracted and processed records

Example response:
```json
{
  "filename": "example.pdf",
  "total_records": 203,
  "filtered_records": 203,
  "data": [
    {
      "id": 1,
      "category": "1",
      "location": "podkarpackie/brzozowski/Nozdrzec/Hłudno",
      "area_m2": null,
      "starting_price": null,
      "estimated_value": 50.0,
      "attributes": "SZ Krosno",
      "discount": ""
    }
    // ... more records
  ]
}
```

### 3. GET `/geoportal/{id}`
Opens a specific record in the geoportal using Selenium automation.

**Parameters**: 
- `id` (int): Record ID to open in geoportal

**Response**: JSON with operation status

Example response:
```json
{
  "success": true,
  "message": "Successfully opened record 123 in geoportal",
  "output": "Browser output..."
}
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd geoportal-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ChromeDriver** (for macOS):
   ```bash
   brew install chromedriver
   ```

## Usage

### Option 1: Use the startup script
```bash
./start.sh
```

### Option 2: Manual startup
```bash
cd app
python main.py
```

The application will start on `http://localhost:8000`.

## Project Structure

```
geoportal-app/
├── app/
│   ├── main.py              # FastAPI application
│   └── templates/
│       └── index.html       # Web interface
├── selenium_runner.py       # Selenium automation script
├── requirements.txt         # Python dependencies
├── start.sh                # Startup script
└── README.md               # This file
```

## Dependencies

- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **pdfplumber**: PDF text extraction and table parsing
- **Selenium**: Web browser automation
- **Jinja2**: Template engine for HTML rendering
- **python-multipart**: File upload support

## Data Processing

The application processes PDF auction data and extracts:

- Record ID
- Category and subcategory information
- Location details
- Area measurements (m²)
- Price information (starting price, estimated value)
- Deposit and increment amounts
- Property attributes and discounts
- Additional descriptions

## Browser Automation

The Selenium integration:

- Automatically opens Chrome browser
- Navigates to geoportal.gov.pl
- Processes record lookup requests
- Runs in headless mode for server environments
- Handles errors gracefully

## Development

To extend the application:

1. **PDF Processing**: Modify the processing functions in `main.py`
2. **Geoportal Integration**: Update the Selenium logic in `selenium_runner.py`
3. **Web Interface**: Edit the HTML template in `app/templates/index.html`
4. **API Endpoints**: Add new routes to `main.py`

## Error Handling

The application includes comprehensive error handling for:

- Invalid PDF files
- PDF processing errors
- Browser automation failures
- Network connectivity issues
- File system errors

## Security Considerations

- File uploads are validated for PDF format
- Temporary files are automatically cleaned up
- Browser automation runs in sandboxed mode
- No sensitive data is logged

## Browser Requirements

- Chrome/Chromium browser installed
- ChromeDriver installed and in PATH
- For headless operation, no display required

## Troubleshooting

1. **ChromeDriver issues**: Ensure ChromeDriver is installed and compatible with your Chrome version
2. **PDF processing errors**: Check that uploaded files are valid PDF documents
3. **Permission errors**: Ensure the application has write access to temporary directories
4. **Network errors**: Check internet connectivity for geoportal access

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
