// Geoportal App - Main JavaScript Functionality
// Modern ES6+ code for handling PDF uploads, filtering, and geoportal integration

class GeoportalApp {
    constructor() {
        this.init();
    }

    init() {
        console.log('🔧 Setting up event listeners...');
        this.setupEventListeners();
        console.log('🔄 Setting up drag and drop...');
        this.setupDragAndDrop();
        console.log('⚙️ Initializing filters...');
        this.initializeFilters();
        console.log('✅ GeoportalApp initialization complete');
    }

    setupEventListeners() {
        // File upload
        const fileInput = document.getElementById('pdf-file');
        const uploadArea = document.querySelector('.upload-area');
        const uploadBtn = document.getElementById('upload-btn');
        
        console.log('📁 Setting up file input listener...');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                console.log('📄 File selected:', e.target.files[0]?.name);
                if (e.target.files.length > 0) {
                    this.handleFileUpload(e.target.files[0]);
                }
            });
        } else {
            console.warn('⚠️ File input element not found');
        }

        if (uploadArea) {
            uploadArea.addEventListener('click', () => {
                console.log('🖱️ Upload area clicked');
                fileInput?.click();
            });
        } else {
            console.warn('⚠️ Upload area element not found');
        }

        if (uploadBtn) {
            uploadBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent upload area click
                console.log('🖱️ Upload button clicked');
                fileInput?.click();
            });
        } else {
            console.warn('⚠️ Upload button element not found');
        }

        // Button event listeners
        this.setupButtonListeners();
    }

    setupButtonListeners() {
        console.log('🔘 Setting up button listeners...');
        
        const bestOffersBtn = document.getElementById('best-offers-btn');
        const filterToggleBtn = document.getElementById('filter-toggle');
        const applyFiltersBtn = document.getElementById('apply-filters-btn');
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        const openGeoportalBtn = document.getElementById('open-geoportal-btn');

        if (bestOffersBtn) {
            bestOffersBtn.addEventListener('click', () => {
                console.log('⭐ Best offers button clicked');
                this.handleBestOffers();
            });
        }

        if (filterToggleBtn) {
            filterToggleBtn.addEventListener('click', () => {
                console.log('🔧 Filter toggle button clicked');
                this.toggleFilters();
            });
        }

        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                console.log('✅ Apply filters button clicked');
                this.handleFileUploadWithFilters();
            });
        }

        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                console.log('🧹 Clear filters button clicked');
                this.clearFilters();
            });
        }

        if (openGeoportalBtn) {
            openGeoportalBtn.addEventListener('click', () => {
                console.log('🌍 Open geoportal button clicked');
                this.openGeoportal();
            });
        }

        console.log('✅ Button listeners setup complete');
    }

    setupDragAndDrop() {
        const uploadArea = document.querySelector('.upload-area');
        
        if (!uploadArea) return;

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
    }

    initializeFilters() {
        // Set default values for filters
        const minDaysInput = document.getElementById('filter-min-days');
        if (minDaysInput && !minDaysInput.value) {
            minDaysInput.value = '7';
        }
    }

    async handleFileUpload(file) {
        if (!file.name.endsWith('.pdf')) {
            this.showError('Proszę wybrać plik PDF');
            return;
        }

        this.showLoading();
        this.hideMessages();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(`Przetworzono ${data.filtered_records} rekordów z pliku ${data.filename}`);
                this.displayResults(data);
            } else {
                this.showError(data.detail || 'Błąd podczas przetwarzania pliku');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Błąd połączenia z serwerem');
        } finally {
            this.hideLoading();
        }
    }

    async handleFileUploadWithFilters() {
        const fileInput = document.getElementById('pdf-file');
        if (!fileInput?.files.length) {
            this.showError('Proszę wybrać plik PDF');
            return;
        }
        
        const file = fileInput.files[0];
        if (!file.name.endsWith('.pdf')) {
            this.showError('Proszę wybrać plik PDF');
            return;
        }

        this.showLoading();
        this.hideMessages();

        const formData = new FormData();
        formData.append('file', file);

        // Build query parameters from filters
        const params = this.buildFilterParams();

        try {
            const response = await fetch(`/upload?${params.toString()}`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(`Przetworzono ${data.filtered_records} z ${data.total_records} rekordów z pliku ${data.filename}`);
                this.displayResults(data);
            } else {
                this.showError(data.detail || 'Błąd podczas przetwarzania pliku');
            }
        } catch (error) {
            console.error('Filtered upload error:', error);
            this.showError('Błąd połączenia z serwerem');
        } finally {
            this.hideLoading();
        }
    }

    buildFilterParams() {
        const params = new URLSearchParams();
        
        const filterMappings = [
            ['filter-location', 'location'],
            ['filter-counties', 'counties'],
            ['filter-min-area', 'min_area'],
            ['filter-max-area', 'max_area'],
            ['filter-min-price', 'min_price'],
            ['filter-max-price', 'max_price'],
            ['filter-property-types', 'property_types'],
            ['filter-min-days', 'min_days_from_now'],
            ['filter-max-days', 'max_days_from_now'],
            ['filter-min-discount', 'min_discount']
        ];

        filterMappings.forEach(([elementId, paramName]) => {
            const element = document.getElementById(elementId);
            if (element?.value.trim()) {
                params.append(paramName, element.value.trim());
            }
        });

        return params;
    }

    async handleBestOffers() {
        const fileInput = document.getElementById('pdf-file');
        if (!fileInput?.files.length) {
            this.showError('Proszę najpierw wybrać plik PDF');
            return;
        }
        
        const file = fileInput.files[0];
        if (!file.name.endsWith('.pdf')) {
            this.showError('Proszę wybrać plik PDF');
            return;
        }

        this.showLoading();
        this.hideMessages();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/best-offers', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(`Znaleziono ${data.best_offers_count} najlepszych ofert z ${data.total_records} rekordów`);
                this.displayBestOffers(data);
            } else {
                this.showError(data.detail || 'Błąd podczas przetwarzania pliku');
            }
        } catch (error) {
            console.error('Best offers error:', error);
            this.showError('Błąd połączenia z serwerem');
        } finally {
            this.hideLoading();
        }
    }

    toggleFilters() {
        const filtersDiv = document.getElementById('advanced-filters');
        const toggleBtn = document.getElementById('filter-toggle');
        
        if (!filtersDiv || !toggleBtn) return;

        const isHidden = filtersDiv.classList.contains('hidden');
        
        if (isHidden) {
            filtersDiv.classList.remove('hidden');
            toggleBtn.textContent = '🔧 Ukryj filtry';
        } else {
            filtersDiv.classList.add('hidden');
            toggleBtn.textContent = '🔧 Filtry zaawansowane';
        }
    }

    clearFilters() {
        const filterIds = [
            'filter-location',
            'filter-counties',
            'filter-min-area',
            'filter-max-area',
            'filter-min-price',
            'filter-max-price',
            'filter-property-types',
            'filter-max-days',
            'filter-min-discount'
        ];

        filterIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.value = '';
            }
        });

        // Reset min days to default
        const minDaysElement = document.getElementById('filter-min-days');
        if (minDaysElement) {
            minDaysElement.value = '7';
        }
    }

    async openGeoportal() {
        const recordId = document.getElementById('record-id')?.value;
        if (!recordId) {
            this.showGeoportalError('Proszę wprowadzić ID rekordu');
            return;
        }

        this.showGeoportalLoading();
        this.hideGeoportalMessages();

        try {
            const response = await fetch(`/geoportal/${recordId}`);
            const data = await response.json();

            if (response.ok && data.success) {
                this.showGeoportalSuccess(data.message);
            } else {
                this.showGeoportalError(data.message || data.detail || 'Błąd podczas otwierania rekordu');
            }
        } catch (error) {
            console.error('Geoportal error:', error);
            this.showGeoportalError('Błąd połączenia z serwerem');
        } finally {
            this.hideGeoportalLoading();
        }
    }

    async openGeoportalRecord(recordId) {
        console.log('🌍 Opening geoportal record with ID:', recordId);
        
        if (!recordId || recordId === 'undefined' || recordId === 'N/A') {
            console.error('❌ Invalid record ID:', recordId);
            alert('Błąd: Nieprawidłowy ID rekordu');
            return;
        }
        
        try {
            console.log('📡 Making request to /geoportal/' + recordId);
            const response = await fetch(`/geoportal/${recordId}`);
            const data = await response.json();
            
            console.log('📥 Geoportal response:', data);
            
            if (data.success) {
                alert(`Otwarto rekord ${recordId} w geoportalu`);
            } else {
                alert(`Błąd: ${data.message || 'Nieznany błąd'}`);
            }
        } catch (error) {
            console.error('❌ Geoportal record error:', error);
            alert('Błąd połączenia z serwerem');
        }
    }

    displayResults(data) {
        const resultsContent = document.getElementById('results-content');
        const resultsSummary = document.getElementById('results-summary');
        const results = document.getElementById('results');
        
        if (!resultsContent || !resultsSummary || !results) return;

        resultsContent.innerHTML = '';
        
        // Display statistics if available
        if (data.statistics) {
            resultsSummary.innerHTML = this.generateStatisticsHTML(data.statistics, data.applied_filters);
        }

        if (data.data && data.data.length > 0) {
            data.data.forEach(record => {
                const recordDiv = this.createRecordElement(record);
                resultsContent.appendChild(recordDiv);
            });
        } else {
            resultsContent.innerHTML = '<p class="text-white text-center">Brak danych do wyświetlenia</p>';
        }

        results.classList.remove('hidden');
        results.classList.add('block');
    }

    displayBestOffers(data) {
        const resultsContent = document.getElementById('results-content');
        const resultsSummary = document.getElementById('results-summary');
        const results = document.getElementById('results');
        
        if (!resultsContent || !resultsSummary || !results) return;

        resultsContent.innerHTML = '';
        
        // Display statistics for best offers
        if (data.statistics) {
            const stats = data.statistics;
            resultsSummary.innerHTML = `
                <h4 class="text-xl font-bold text-white mb-4">⭐ Najlepsze oferty - Statystyki</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
                    <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Najlepszych ofert:</strong><br><span class="text-green-300">${stats.count}</span></div>
                    <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia powierzchnia:</strong><br><span class="text-blue-300">${stats.avg_area?.toFixed(2) || 0} ha</span></div>
                    <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia cena:</strong><br><span class="text-yellow-300">${stats.avg_price?.toLocaleString() || 0} PLN</span></div>
                    <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Cena min-max:</strong><br><span class="text-purple-300">${stats.min_price?.toLocaleString() || 0} - ${stats.max_price?.toLocaleString() || 0} PLN</span></div>
                    <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia cena/ha:</strong><br><span class="text-pink-300">${stats.avg_price_per_hectare?.toLocaleString() || 0} PLN/ha</span></div>
                </div>
                <div class="bg-yellow-500/20 p-4 rounded-lg border border-yellow-400/30">
                    <strong class="text-yellow-200">Kryteria najlepszych ofert:</strong>
                    <span class="text-yellow-100">Trzebownisko, powiaty: łańcucki/ropczycko sędziszowski/rzeszowski, sprzedaż, min 0.08 ha, max 20,000 PLN, min 7 dni od dziś</span>
                </div>
            `;
        }

        if (data.best_offers && data.best_offers.length > 0) {
            data.best_offers.forEach(record => {
                const recordDiv = this.createRecordElement(record, true);
                resultsContent.appendChild(recordDiv);
            });
        } else {
            resultsContent.innerHTML = '<p class="text-white text-center">Brak najlepszych ofert spełniających kryteria</p>';
        }

        results.classList.remove('hidden');
        results.classList.add('block');
    }

    generateStatisticsHTML(stats, appliedFilters) {
        let html = `
            <h4 class="text-xl font-bold text-white mb-4">📊 Statystyki</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Liczba rekordów:</strong><br><span class="text-green-300">${stats.count}</span></div>
                <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia powierzchnia:</strong><br><span class="text-blue-300">${stats.avg_area?.toFixed(2) || 0} ha</span></div>
                <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia cena:</strong><br><span class="text-yellow-300">${stats.avg_price?.toLocaleString() || 0} PLN</span></div>
                <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Cena min-max:</strong><br><span class="text-purple-300">${stats.min_price?.toLocaleString() || 0} - ${stats.max_price?.toLocaleString() || 0} PLN</span></div>
                <div class="bg-white/10 p-3 rounded-lg"><strong class="text-white">Średnia cena/ha:</strong><br><span class="text-pink-300">${stats.avg_price_per_hectare?.toLocaleString() || 0} PLN/ha</span></div>
            </div>
        `;
        
        // Display applied filters if available
        if (appliedFilters && Object.keys(appliedFilters).length > 0) {
            const filtersHtml = Object.entries(appliedFilters)
                .map(([key, value]) => `<span class="bg-blue-500/20 px-3 py-1 rounded-full text-blue-200 text-sm border border-blue-400/30">${key}: ${value}</span>`)
                .join(' ');
            html += `<div class="mt-4"><strong class="text-white">Zastosowane filtry:</strong><br><div class="flex flex-wrap gap-2 mt-2">${filtersHtml}</div></div>`;
        }

        return html;
    }

    createRecordElement(record, isBestOffer = false) {
        const recordDiv = document.createElement('div');
        recordDiv.className = 'record-item';
        
        if (isBestOffer) {
            recordDiv.style.border = '2px solid #48bb78';
            recordDiv.classList.add('bg-green-500/10');
        }
        
        // Try different possible ID fields, prioritizing 'lp' which is the line number
        const recordId = record.lp || record.id || record.nr_sprawy || record.record_id || record.ID || 'N/A';
        console.log('🔍 Record ID extracted:', recordId, 'from record with lp:', record.lp);
        
        const headerText = isBestOffer ? `⭐ NAJLEPSZA OFERTA - ID: ${recordId}` : `ID: ${recordId}`;
        
        recordDiv.innerHTML = `
            <div class="record-header">
                <div class="record-id">${headerText}</div>
                <button class="open-geoportal" onclick="window.geoportalApp?.openGeoportalRecord('${recordId}')">
                    Otwórz w geoportalu
                </button>
            </div>
            <div class="record-details">
                ${this.createDetailItem('Typ nieruchomości', record.typ_nieruchomości || record.category || 'N/A')}
                ${this.createDetailItem('Położenie', record.położenie || record.location || 'N/A')}
                ${this.createDetailItem('Powierzchnia ogólna', this.formatArea(record))}
                ${this.createDetailItem('Cena wywoławcza', this.formatPrice(record))}
                ${isBestOffer ? this.createDetailItem('Cena za hektar', this.formatPricePerHectare(record)) : ''}
                ${this.createDetailItem('Data i godzina', record.data_godzina || 'N/A')}
                ${this.createDetailItem('Forma', record.forma || 'N/A')}
                ${this.createDetailItem('Obniżka', record.obniżka || record.discount || (isBestOffer ? 'Brak' : 'N/A'))}
                ${record.miejsce ? this.createDetailItem('Miejsce', record.miejsce) : ''}
            </div>
        `;
        
        return recordDiv;
    }

    createDetailItem(label, value) {
        return `
            <div class="detail-item">
                <div class="detail-label">${label}</div>
                <div class="detail-value">${value}</div>
            </div>
        `;
    }

    formatArea(record) {
        if (record.powierzchnia_ogolna) {
            return record.powierzchnia_ogolna.toFixed(4) + ' ha';
        } else if (record.area_m2) {
            return record.area_m2 + ' m²';
        }
        return 'N/A';
    }

    formatPrice(record) {
        if (record.cena_wywoławcza) {
            return record.cena_wywoławcza.toLocaleString() + ' PLN';
        } else if (record.starting_price) {
            return record.starting_price.toLocaleString() + ' PLN';
        }
        return 'N/A';
    }

    formatPricePerHectare(record) {
        if (record.powierzchnia_ogolna && record.cena_wywoławcza) {
            return Math.round(record.cena_wywoławcza / record.powierzchnia_ogolna).toLocaleString() + ' PLN/ha';
        }
        return 'N/A';
    }

    // Loading and message methods
    showLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.remove('hidden');
            loading.classList.add('block');
        }
    }

    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.add('hidden');
            loading.classList.remove('block');
        }
    }

    showError(message) {
        const errorMessage = document.getElementById('error-message');
        if (errorMessage) {
            errorMessage.textContent = message;
            errorMessage.classList.remove('hidden');
            errorMessage.classList.add('block');
        }
    }

    showSuccess(message) {
        const successMessage = document.getElementById('success-message');
        if (successMessage) {
            successMessage.textContent = message;
            successMessage.classList.remove('hidden');
            successMessage.classList.add('block');
        }
    }

    hideMessages() {
        const errorMessage = document.getElementById('error-message');
        const successMessage = document.getElementById('success-message');
        
        if (errorMessage) {
            errorMessage.classList.add('hidden');
            errorMessage.classList.remove('block');
        }
        if (successMessage) {
            successMessage.classList.add('hidden');
            successMessage.classList.remove('block');
        }
    }

    // Geoportal section methods
    showGeoportalLoading() {
        const loading = document.getElementById('geoportal-loading');
        if (loading) {
            loading.classList.remove('hidden');
            loading.classList.add('block');
        }
    }

    hideGeoportalLoading() {
        const loading = document.getElementById('geoportal-loading');
        if (loading) {
            loading.classList.add('hidden');
            loading.classList.remove('block');
        }
    }

    showGeoportalError(message) {
        const errorEl = document.getElementById('geoportal-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
            errorEl.classList.add('block');
        }
    }

    showGeoportalSuccess(message) {
        const successEl = document.getElementById('geoportal-success');
        if (successEl) {
            successEl.textContent = message;
            successEl.classList.remove('hidden');
            successEl.classList.add('block');
        }
    }

    hideGeoportalMessages() {
        const errorEl = document.getElementById('geoportal-error');
        const successEl = document.getElementById('geoportal-success');
        
        if (errorEl) {
            errorEl.classList.add('hidden');
            errorEl.classList.remove('block');
        }
        if (successEl) {
            successEl.classList.add('hidden');
            successEl.classList.remove('block');
        }
    }
}

// Initialize the app when DOM is loaded
let geoportalApp;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Geoportal App...');
    try {
        geoportalApp = new GeoportalApp();
        // Export for global access after initialization
        window.geoportalApp = geoportalApp;
        console.log('✅ Geoportal App initialized successfully');
    } catch (error) {
        console.error('❌ Error initializing Geoportal App:', error);
    }
});
