/**
 * Prompt Governor - Core JavaScript Application
 * Phase D3: JavaScript Core - Enhanced utilities and modules
 */

(function() {
    'use strict';

    // ============================================
    // CONFIGURATION
    // ============================================
    const CONFIG = {
        API_BASE_URL: '/api',
        API_TIMEOUT: 30000,
        API_RETRIES: 3,
        API_RETRY_DELAY: 1000,
        STORAGE_KEY: 'prompt_governor_state',
        ENABLE_PERSISTENCE: true,
        TOAST_DURATION: 3000,
        LOADING_DELAY: 100
    };

    // ============================================
    // STATE MANAGEMENT
    // ============================================
    const State = {
        // Core state
        currentTab: 'prompts',
        prompts: [],
        configs: [],
        documents: [],
        runs: [],
        currentRun: null,
        loading: false,
        loadingCount: 0,
        
        // Metadata
        lastSync: null,
        userPreferences: {},
        
        // Listeners system
        listeners: {},
        
        /**
         * Set a state value and notify listeners
         * @param {string} key - State key
         * @param {*} value - Value to set
         */
        set(key, value) {
            const oldValue = this[key];
            this[key] = value;
            this.notify(key, value, oldValue);
            
            // Persist to localStorage if enabled
            if (CONFIG.ENABLE_PERSISTENCE && this._isPersistent(key)) {
                this._persist();
            }
        },
        
        /**
         * Get a state value
         * @param {string} key - State key
         * @param {*} defaultValue - Default if key doesn't exist
         * @returns {*} State value
         */
        get(key, defaultValue = null) {
            return this[key] !== undefined ? this[key] : defaultValue;
        },
        
        /**
         * Subscribe to state changes
         * @param {string} key - State key to watch
         * @param {Function} callback - Callback function(newVal, oldVal)
         * @returns {Function} Unsubscribe function
         */
        on(key, callback) {
            if (!this.listeners[key]) this.listeners[key] = [];
            this.listeners[key].push(callback);
            
            // Return unsubscribe function
            return () => {
                const idx = this.listeners[key].indexOf(callback);
                if (idx > -1) this.listeners[key].splice(idx, 1);
            };
        },
        
        /**
         * Notify listeners of state change
         * @param {string} key - Changed key
         * @param {*} newValue - New value
         * @param {*} oldValue - Old value
         */
        notify(key, newValue, oldValue) {
            if (this.listeners[key]) {
                this.listeners[key].forEach(cb => {
                    try {
                        cb(newValue, oldValue);
                    } catch (err) {
                        console.error(`State listener error for ${key}:`, err);
                    }
                });
            }
            
            // Also notify wildcard listeners
            if (this.listeners['*']) {
                this.listeners['*'].forEach(cb => {
                    try {
                        cb(key, newValue, oldValue);
                    } catch (err) {
                        console.error('Wildcard state listener error:', err);
                    }
                });
            }
        },
        
        /**
         * Check if key should be persisted
         * @private
         */
        _isPersistent(key) {
            const persistentKeys = ['currentTab', 'userPreferences'];
            return persistentKeys.includes(key);
        },
        
        /**
         * Persist state to localStorage
         * @private
         */
        _persist() {
            try {
                const data = {
                    currentTab: this.currentTab,
                    userPreferences: this.userPreferences,
                    timestamp: Date.now()
                };
                localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(data));
            } catch (err) {
                console.warn('Failed to persist state:', err);
            }
        },
        
        /**
         * Restore state from localStorage
         */
        restore() {
            try {
                const data = localStorage.getItem(CONFIG.STORAGE_KEY);
                if (data) {
                    const parsed = JSON.parse(data);
                    if (parsed.currentTab) this.currentTab = parsed.currentTab;
                    if (parsed.userPreferences) this.userPreferences = parsed.userPreferences;
                    console.log('State restored from localStorage');
                }
            } catch (err) {
                console.warn('Failed to restore state:', err);
            }
        },
        
        /**
         * Clear persisted state
         */
        clear() {
            try {
                localStorage.removeItem(CONFIG.STORAGE_KEY);
            } catch (err) {
                console.warn('Failed to clear state:', err);
            }
        },
        
        /**
         * Reset all state to defaults
         */
        reset() {
            this.currentTab = 'prompts';
            this.prompts = [];
            this.configs = [];
            this.documents = [];
            this.runs = [];
            this.currentRun = null;
            this.loading = false;
            this.loadingCount = 0;
            this.userPreferences = {};
            this.clear();
        }
    };

    // ============================================
    // API CLIENT
    // ============================================
    const API = {
        baseUrl: CONFIG.API_BASE_URL,
        
        /**
         * Make an API request with retries and error handling
         * @param {string} endpoint - API endpoint
         * @param {Object} options - Fetch options
         * @returns {Promise} Response data
         */
        async request(endpoint, options = {}) {
            const url = `${this.baseUrl}${endpoint}`;
            let attempt = 0;
            let lastError;
            
            // Build request config
            const config = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...options.headers
                },
                ...options
            };
            
            // Add body if provided
            if (options.body && typeof options.body === 'object') {
                config.body = JSON.stringify(options.body);
            }
            
            // Show loading state
            Utils.showLoading();
            
            while (attempt < CONFIG.API_RETRIES) {
                attempt++;
                
                try {
                    // Create abort controller for timeout
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);
                    
                    const response = await fetch(url, {
                        ...config,
                        signal: controller.signal
                    });
                    
                    clearTimeout(timeoutId);
                    
                    // Handle non-OK responses
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new APIError(
                            errorData.message || `HTTP ${response.status}: ${response.statusText}`,
                            response.status,
                            errorData
                        );
                    }
                    
                    // Parse response
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return await response.json();
                    }
                    return await response.text();
                    
                } catch (error) {
                    lastError = error;
                    
                    // Don't retry on 4xx errors (client errors)
                    if (error instanceof APIError && error.status >= 400 && error.status < 500) {
                        break;
                    }
                    
                    // Don't retry on abort (timeout)
                    if (error.name === 'AbortError') {
                        lastError = new APIError('Request timeout', 408);
                        break;
                    }
                    
                    // Wait before retry
                    if (attempt < CONFIG.API_RETRIES) {
                        await Utils.delay(CONFIG.API_RETRY_DELAY * attempt);
                    }
                }
            }
            
            // All retries exhausted
            throw lastError;
        },
        
        /**
         * GET request
         * @param {string} endpoint - API endpoint
         * @param {Object} options - Additional options
         */
        async get(endpoint, options = {}) {
            return this.request(endpoint, { ...options, method: 'GET' });
        },
        
        /**
         * POST request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @param {Object} options - Additional options
         */
        async post(endpoint, data, options = {}) {
            return this.request(endpoint, { ...options, method: 'POST', body: data });
        },
        
        /**
         * PUT request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @param {Object} options - Additional options
         */
        async put(endpoint, data, options = {}) {
            return this.request(endpoint, { ...options, method: 'PUT', body: data });
        },
        
        /**
         * PATCH request
         * @param {string} endpoint - API endpoint
         * @param {Object} data - Request body
         * @param {Object} options - Additional options
         */
        async patch(endpoint, data, options = {}) {
            return this.request(endpoint, { ...options, method: 'PATCH', body: data });
        },
        
        /**
         * DELETE request
         * @param {string} endpoint - API endpoint
         * @param {Object} options - Additional options
         */
        async delete(endpoint, options = {}) {
            return this.request(endpoint, { ...options, method: 'DELETE' });
        }
    };

    /**
     * Custom API Error class
     */
    class APIError extends Error {
        constructor(message, status, data = {}) {
            super(message);
            this.name = 'APIError';
            this.status = status;
            this.data = data;
        }
    }

    // ============================================
    // TAB MANAGEMENT
    // ============================================
    const Tabs = {
        /**
         * Show a specific tab
         * @param {string} tabName - Tab ID to show
         * @param {boolean} updateHash - Whether to update URL hash
         */
        showTab(tabName, updateHash = true) {
            const tabButtons = document.querySelectorAll('.tab-button');
            const tabContents = document.querySelectorAll('.tab-content');
            
            // Validate tab exists
            const targetContent = document.getElementById(tabName);
            if (!targetContent) {
                console.warn(`Tab '${tabName}' not found`);
                return false;
            }
            
            // Update button states
            tabButtons.forEach(btn => {
                const isTarget = btn.dataset.tab === tabName;
                btn.classList.toggle('active', isTarget);
                btn.setAttribute('aria-selected', isTarget);
            });
            
            // Update content visibility
            tabContents.forEach(content => {
                const isTarget = content.id === tabName;
                content.classList.toggle('active', isTarget);
                content.setAttribute('aria-hidden', !isTarget);
                
                // Focus management for accessibility
                if (isTarget) {
                    content.setAttribute('tabindex', '-1');
                }
            });
            
            // Update state
            State.set('currentTab', tabName);
            
            // Update URL hash for deep linking
            if (updateHash) {
                window.location.hash = tabName;
            }
            
            // Trigger tab change event
            window.dispatchEvent(new CustomEvent('tabchange', {
                detail: { tab: tabName }
            }));
            
            Utils.updateStatus(`Switched to ${tabName} tab`);
            return true;
        },
        
        /**
         * Get current active tab
         * @returns {string} Current tab name
         */
        getCurrentTab() {
            return State.get('currentTab', 'prompts');
        },
        
        /**
         * Initialize tab system
         */
        init() {
            const tabButtons = document.querySelectorAll('.tab-button');
            
            // Add click handlers
            tabButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    const tabId = e.currentTarget.dataset.tab;
                    this.showTab(tabId);
                });
            });
            
            // Handle URL hash changes
            window.addEventListener('hashchange', () => {
                const hash = window.location.hash.slice(1);
                if (hash && hash !== this.getCurrentTab()) {
                    this.showTab(hash, false);
                }
            });
            
            // Handle initial hash or restored state
            const initialHash = window.location.hash.slice(1);
            const savedTab = State.get('currentTab');
            
            if (initialHash && document.getElementById(initialHash)) {
                this.showTab(initialHash, false);
            } else if (savedTab && savedTab !== 'prompts') {
                this.showTab(savedTab);
            }
        }
    };

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    const Utils = {
        /**
         * Format a date
         * @param {Date|string|number} date - Date to format
         * @param {Object} options - Intl.DateTimeFormat options
         * @returns {string} Formatted date
         */
        formatDate(date, options = {}) {
            const d = date instanceof Date ? date : new Date(date);
            
            if (isNaN(d.getTime())) {
                return 'Invalid date';
            }
            
            const defaultOptions = {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                ...options
            };
            
            return new Intl.DateTimeFormat('en-US', defaultOptions).format(d);
        },
        
        /**
         * Format a relative time (e.g., "2 hours ago")
         * @param {Date|string|number} date - Date to format
         * @returns {string} Relative time string
         */
        formatRelativeTime(date) {
            const d = date instanceof Date ? date : new Date(date);
            const now = new Date();
            const diffMs = now - d;
            const diffSecs = Math.floor(diffMs / 1000);
            const diffMins = Math.floor(diffSecs / 60);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);
            
            if (diffSecs < 60) return 'just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return this.formatDate(date, { month: 'short', day: 'numeric' });
        },
        
        /**
         * Format a number with decimals
         * @param {number} num - Number to format
         * @param {number} decimals - Decimal places
         * @returns {string} Formatted number
         */
        formatNumber(num, decimals = 0) {
            if (num === null || num === undefined || isNaN(num)) {
                return '--';
            }
            
            const n = parseFloat(num);
            
            // Use compact notation for large numbers
            if (Math.abs(n) >= 1000000) {
                return n.toLocaleString('en-US', {
                    notation: 'compact',
                    maximumFractionDigits: decimals
                });
            }
            
            return n.toLocaleString('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        },
        
        /**
         * Format currency
         * @param {number} amount - Amount to format
         * @param {string} currency - Currency code
         * @returns {string} Formatted currency
         */
        formatCurrency(amount, currency = 'USD') {
            if (amount === null || amount === undefined || isNaN(amount)) {
                return '--';
            }
            
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 4
            }).format(amount);
        },
        
        /**
         * Format percentage
         * @param {number} value - Value to format (0-1 or 0-100)
         * @param {number} decimals - Decimal places
         * @returns {string} Formatted percentage
         */
        formatPercent(value, decimals = 1) {
            if (value === null || value === undefined || isNaN(value)) {
                return '--%';
            }
            
            // Convert from 0-1 to 0-100 if needed
            const pct = value <= 1 ? value * 100 : value;
            
            return `${pct.toFixed(decimals)}%`;
        },
        
        /**
         * Show a toast notification
         * @param {string} message - Message to display
         * @param {string} type - Type: 'success', 'error', 'warning', 'info'
         * @param {number} duration - Duration in ms
         */
        showToast(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
            // Remove existing toasts
            const existing = document.querySelector('.toast-notification');
            if (existing) existing.remove();
            
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast-notification toast-${type}`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'polite');
            
            // Icon based on type
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ'
            };
            
            toast.innerHTML = `
                <span class="toast-icon">${icons[type] || icons.info}</span>
                <span class="toast-message">${this.escapeHtml(message)}</span>
                <button class="toast-close" aria-label="Close notification">×</button>
            `;
            
            // Add styles if not present
            if (!document.getElementById('toast-styles')) {
                const style = document.createElement('style');
                style.id = 'toast-styles';
                style.textContent = `
                    .toast-notification {
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        padding: 12px 20px;
                        background: #333;
                        color: white;
                        border-radius: 6px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        z-index: 10000;
                        animation: slideIn 0.3s ease;
                        max-width: 400px;
                    }
                    .toast-notification.toast-success { background: #28a745; }
                    .toast-notification.toast-error { background: #dc3545; }
                    .toast-notification.toast-warning { background: #ffc107; color: #333; }
                    .toast-notification.toast-info { background: #17a2b8; }
                    .toast-icon { font-weight: bold; font-size: 16px; }
                    .toast-message { flex: 1; }
                    .toast-close {
                        background: none;
                        border: none;
                        color: inherit;
                        font-size: 20px;
                        cursor: pointer;
                        padding: 0;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    @keyframes slideIn {
                        from { transform: translateX(100%); opacity: 0; }
                        to { transform: translateX(0); opacity: 1; }
                    }
                    @keyframes slideOut {
                        from { transform: translateX(0); opacity: 1; }
                        to { transform: translateX(100%); opacity: 0; }
                    }
                `;
                document.head.appendChild(style);
            }
            
            // Add to DOM
            document.body.appendChild(toast);
            
            // Close button handler
            toast.querySelector('.toast-close').addEventListener('click', () => {
                this.hideToast(toast);
            });
            
            // Auto-hide
            setTimeout(() => this.hideToast(toast), duration);
        },
        
        /**
         * Hide a toast notification
         * @param {HTMLElement} toast - Toast element
         */
        hideToast(toast) {
            if (!toast || toast.dataset.closing) return;
            toast.dataset.closing = 'true';
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        },
        
        /**
         * Show loading indicator
         */
        showLoading() {
            State.loadingCount++;
            State.set('loading', true);
            
            // Add loading class to body for global loading state
            document.body.classList.add('loading');
            
            // Show loading overlay if not already shown
            let overlay = document.getElementById('loading-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'loading-overlay';
                overlay.innerHTML = '<div class="spinner"></div>';
                
                // Add styles if not present
                if (!document.getElementById('loading-styles')) {
                    const style = document.createElement('style');
                    style.id = 'loading-styles';
                    style.textContent = `
                        #loading-overlay {
                            position: fixed;
                            top: 0;
                            left: 0;
                            right: 0;
                            bottom: 0;
                            background: rgba(255,255,255,0.7);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            z-index: 9999;
                            opacity: 0;
                            transition: opacity 0.2s;
                        }
                        #loading-overlay.visible { opacity: 1; }
                        .spinner {
                            width: 40px;
                            height: 40px;
                            border: 4px solid #e0e0e0;
                            border-top-color: #3498db;
                            border-radius: 50%;
                            animation: spin 0.8s linear infinite;
                        }
                        @keyframes spin {
                            to { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(style);
                }
                
                document.body.appendChild(overlay);
            }
            
            // Show after delay to prevent flickering for fast requests
            setTimeout(() => {
                if (State.loading && overlay) {
                    overlay.classList.add('visible');
                }
            }, CONFIG.LOADING_DELAY);
        },
        
        /**
         * Hide loading indicator
         */
        hideLoading() {
            State.loadingCount = Math.max(0, State.loadingCount - 1);
            
            if (State.loadingCount === 0) {
                State.set('loading', false);
                document.body.classList.remove('loading');
                
                const overlay = document.getElementById('loading-overlay');
                if (overlay) {
                    overlay.classList.remove('visible');
                    setTimeout(() => overlay.remove(), 200);
                }
            }
        },
        
        /**
         * Handle errors gracefully
         * @param {Error} error - Error object
         * @param {Object} options - Handler options
         */
        handleError(error, options = {}) {
            const { 
                showToast = true, 
                logToConsole = true,
                context = ''
            } = options;
            
            let message = 'An unexpected error occurred';
            let type = 'error';
            
            if (error instanceof APIError) {
                switch (error.status) {
                    case 400:
                        message = error.message || 'Invalid request';
                        break;
                    case 401:
                        message = 'Authentication required. Please log in.';
                        break;
                    case 403:
                        message = 'You don\'t have permission to perform this action';
                        break;
                    case 404:
                        message = 'The requested resource was not found';
                        break;
                    case 408:
                        message = 'Request timed out. Please try again.';
                        break;
                    case 422:
                        message = error.message || 'Validation failed. Please check your input.';
                        type = 'warning';
                        break;
                    case 429:
                        message = 'Too many requests. Please wait a moment.';
                        type = 'warning';
                        break;
                    case 500:
                    case 502:
                    case 503:
                    case 504:
                        message = 'Server error. Please try again later.';
                        break;
                    default:
                        message = error.message || `Error ${error.status}`;
                }
            } else if (error instanceof TypeError && error.message.includes('fetch')) {
                message = 'Network error. Please check your connection.';
            } else if (error.message) {
                message = error.message;
            }
            
            // Add context prefix
            if (context) {
                message = `${context}: ${message}`;
            }
            
            if (logToConsole) {
                console.error('[Error]', context, error);
            }
            
            if (showToast) {
                this.showToast(message, type);
            }
            
            // Update status
            this.updateStatus(message, 'error');
            
            return message;
        },
        
        /**
         * Update status bar
         * @param {string} message - Status message
         * @param {string} type - Status type: 'ready', 'loading', 'error', 'success'
         */
        updateStatus(message, type = 'ready') {
            const statusText = document.getElementById('status-text');
            const statusIndicator = document.getElementById('status-indicator');
            
            if (statusText) statusText.textContent = message;
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator';
                if (type) statusIndicator.classList.add(type);
            }
        },
        
        /**
         * Escape HTML to prevent XSS
         * @param {string} text - Text to escape
         * @returns {string} Escaped text
         */
        escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        /**
         * Debounce a function
         * @param {Function} func - Function to debounce
         * @param {number} wait - Wait time in ms
         * @returns {Function} Debounced function
         */
        debounce(func, wait = 300) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        /**
         * Create a promise that resolves after delay
         * @param {number} ms - Milliseconds to wait
         * @returns {Promise} Promise that resolves after delay
         */
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },
        
        /**
         * Generate a unique ID
         * @returns {string} Unique ID
         */
        generateId() {
            return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        }
    };

    // ============================================
    // API STATUS MONITORING
    // ============================================
    const APIStatus = {
        isConnected: false,
        checkInterval: null,
        
        /**
         * Check API connectivity
         */
        async check() {
            const apiStatusEl = document.getElementById('api-status');
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);
                
                const response = await fetch('/api/health', {
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    this.isConnected = true;
                    if (apiStatusEl) {
                        apiStatusEl.textContent = 'API: Connected';
                        apiStatusEl.className = 'api-status connected';
                    }
                    Utils.updateStatus('Ready');
                    return true;
                } else {
                    throw new Error('Health check failed');
                }
            } catch (error) {
                this.isConnected = false;
                if (apiStatusEl) {
                    apiStatusEl.textContent = 'API: Disconnected';
                    apiStatusEl.className = 'api-status disconnected';
                }
                Utils.updateStatus('API unavailable', 'error');
                return false;
            }
        },
        
        /**
         * Start periodic status checks
         */
        start() {
            // Initial check
            this.check();
            
            // Periodic checks every 30 seconds
            this.checkInterval = setInterval(() => this.check(), 30000);
        },
        
        /**
         * Stop periodic status checks
         */
        stop() {
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
        }
    };

    // ============================================
    // DATA LOADING
    // ============================================
    const DataLoader = {
        /**
         * Load initial application data
         */
        async loadInitialData() {
            try {
                Utils.updateStatus('Loading data...', 'loading');
                
                // Load all initial data in parallel
                const [prompts, configs] = await Promise.all([
                    this.loadPrompts(),
                    this.loadConfigs()
                ]).catch(() => [null, null]);
                
                if (prompts) State.set('prompts', prompts);
                if (configs) State.set('configs', configs);
                
                Utils.updateStatus('Ready');
                
            } catch (error) {
                Utils.handleError(error, { context: 'Loading initial data' });
            }
        },
        
        /**
         * Load prompts
         */
        async loadPrompts() {
            try {
                return await API.get('/prompts');
            } catch (error) {
                console.warn('Failed to load prompts:', error);
                return [];
            }
        },
        
        /**
         * Load configurations
         */
        async loadConfigs() {
            try {
                return await API.get('/configs');
            } catch (error) {
                console.warn('Failed to load configs:', error);
                return [];
            }
        }
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    function init() {
        console.log('🚀 Prompt Governor initialized');
        
        // Restore state from localStorage
        State.restore();
        
        // Initialize tabs
        Tabs.init();
        
        // Start API status monitoring
        APIStatus.start();
        
        // Load initial data
        DataLoader.loadInitialData();
        
        // Set up keyboard shortcuts
        setupKeyboardShortcuts();
        
        Utils.updateStatus('Ready');
    }
    
    /**
     * Set up keyboard shortcuts
     */
    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Alt+1, Alt+2, Alt+3 for tab switching
            if (e.altKey && e.key >= '1' && e.key <= '3') {
                const tabs = ['prompts', 'configs', 'runs'];
                const tabIndex = parseInt(e.key) - 1;
                if (tabs[tabIndex]) {
                    Tabs.showTab(tabs[tabIndex]);
                    e.preventDefault();
                }
            }
            
            // Escape to close modals/toasts
            if (e.key === 'Escape') {
                const toast = document.querySelector('.toast-notification');
                if (toast) Utils.hideToast(toast);
            }
        });
    }

    // ============================================
    // BOOTSTRAP
    // ============================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ============================================
    // PUBLIC API
    // ============================================
    window.PromptGovernor = {
        // Core modules
        State,
        API,
        Tabs,
        Utils,
        APIStatus,
        DataLoader,
        CONFIG,
        
        // Utility shortcuts
        formatDate: Utils.formatDate.bind(Utils),
        formatNumber: Utils.formatNumber.bind(Utils),
        showToast: Utils.showToast.bind(Utils),
        showLoading: Utils.showLoading.bind(Utils),
        hideLoading: Utils.hideLoading.bind(Utils),
        handleError: Utils.handleError.bind(Utils),
        
        // Version
        version: '1.0.0'
    };

})();
