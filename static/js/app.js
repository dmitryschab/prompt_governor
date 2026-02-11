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
                btn.setAttribute('tabindex', isTarget ? '0' : '-1');
            });

            // Update content visibility
            tabContents.forEach(content => {
                const isTarget = content.id === tabName;
                content.classList.toggle('active', isTarget);
                content.setAttribute('aria-hidden', !isTarget);

                // Use hidden attribute for better accessibility
                if (isTarget) {
                    content.removeAttribute('hidden');
                    content.setAttribute('tabindex', '-1');
                } else {
                    content.setAttribute('hidden', '');
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

            // Announce tab change to screen readers
            AccessibilityManager.announce(`Switched to ${tabName} tab`, 'polite');

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
         * @param {number} duration - Duration in ms (default 5000ms)
         */
        showToast(message, type = 'info', duration = 5000) {
            // Get or create toast container
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'toast-container';
                container.setAttribute('role', 'region');
                container.setAttribute('aria-label', 'Notifications');
                document.body.appendChild(container);
            }
            
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
                <span class="toast-icon" aria-hidden="true">${icons[type] || icons.info}</span>
                <span class="toast-message">${this.escapeHtml(message)}</span>
                <button class="toast-close" aria-label="Close notification">×</button>
                <div class="toast-progress" aria-hidden="true">
                    <div class="toast-progress-bar"></div>
                </div>
            `;
            
            // Add to container
            container.appendChild(toast);
            
            // Close button handler
            const closeBtn = toast.querySelector('.toast-close');
            closeBtn.addEventListener('click', () => {
                this.hideToast(toast);
            });
            
            // Auto-hide
            const autoHideTimer = setTimeout(() => {
                this.hideToast(toast);
            }, duration);
            
            // Pause auto-hide on hover
            toast.addEventListener('mouseenter', () => {
                const progressBar = toast.querySelector('.toast-progress-bar');
                if (progressBar) {
                    progressBar.style.animationPlayState = 'paused';
                }
            });
            
            toast.addEventListener('mouseleave', () => {
                const progressBar = toast.querySelector('.toast-progress-bar');
                if (progressBar) {
                    progressBar.style.animationPlayState = 'running';
                }
            });
            
            // Limit number of toasts (max 3)
            const toasts = container.querySelectorAll('.toast-notification');
            if (toasts.length > 3) {
                toasts[0].remove();
            }
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
    // MODEL CONFIG MANAGER
    // ============================================
    const ConfigManager = {
        currentConfigId: null,
        isEditing: false,
        
        // Provider-specific model suggestions
        modelSuggestions: {
            openai: [
                'gpt-5',
                'gpt-5-mini',
                'gpt-5-nano',
                'gpt-4o',
                'gpt-4o-mini',
                'gpt-4-turbo',
                'gpt-4',
                'gpt-3.5-turbo'
            ],
            anthropic: [
                'claude-3-5-sonnet-20241022',
                'claude-3-5-haiku-20241022',
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ],
            openrouter: [
                'openai/gpt-4o',
                'openai/gpt-4-turbo',
                'anthropic/claude-3.5-sonnet',
                'anthropic/claude-3-opus',
                'google/gemini-1.5-pro',
                'google/gemini-1.5-flash',
                'meta-llama/llama-3.1-70b-instruct'
            ]
        },
        
        /**
         * Initialize the config manager
         */
        init() {
            this.setupEventListeners();
            this.setupTemperatureSlider();
            this.setupProviderDropdown();
            this.setupFormValidation();
        },
        
        /**
         * Setup event listeners for config management
         */
        setupEventListeners() {
            // New config button
            const newBtn = document.getElementById('new-config-btn');
            if (newBtn) {
                newBtn.addEventListener('click', () => this.startNewConfig());
            }
            
            // Cancel button
            const cancelBtn = document.getElementById('cancel-config-btn');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => this.cancelEdit());
            }
            
            // Delete button
            const deleteBtn = document.getElementById('delete-config-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => this.deleteCurrentConfig());
            }
            
            // Form submission
            const form = document.getElementById('config-form');
            if (form) {
                form.addEventListener('submit', (e) => this.handleFormSubmit(e));
            }
            
            // Load configs when tab is shown
            window.addEventListener('tabchange', (e) => {
                if (e.detail.tab === 'configs') {
                    this.loadConfigs();
                }
            });
        },
        
        /**
         * Setup temperature slider with value display
         */
        setupTemperatureSlider() {
            const slider = document.getElementById('config-temperature');
            const display = document.getElementById('temp-value');
            
            if (slider && display) {
                slider.addEventListener('input', (e) => {
                    display.textContent = e.target.value;
                });
            }
        },
        
        /**
         * Setup provider dropdown with model suggestions
         */
        setupProviderDropdown() {
            const providerSelect = document.getElementById('config-provider');
            const modelInput = document.getElementById('config-model');
            
            if (providerSelect && modelInput) {
                providerSelect.addEventListener('change', (e) => {
                    const provider = e.target.value;
                    this.updateModelSuggestions(provider);
                });
            }
        },
        
        /**
         * Update model suggestions based on provider
         */
        updateModelSuggestions(provider) {
            const modelInput = document.getElementById('config-model');
            const suggestions = this.modelSuggestions[provider] || [];
            
            // Remove existing datalist
            const existingDatalist = document.getElementById('model-suggestions');
            if (existingDatalist) {
                existingDatalist.remove();
            }
            
            if (suggestions.length > 0) {
                const datalist = document.createElement('datalist');
                datalist.id = 'model-suggestions';
                
                suggestions.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    datalist.appendChild(option);
                });
                
                document.body.appendChild(datalist);
                modelInput.setAttribute('list', 'model-suggestions');
            } else {
                modelInput.removeAttribute('list');
            }
        },
        
        /**
         * Setup form validation
         */
        setupFormValidation() {
            const form = document.getElementById('config-form');
            if (!form) return;
            
            // Real-time validation for temperature
            const tempInput = document.getElementById('config-temperature');
            if (tempInput) {
                tempInput.addEventListener('change', () => this.validateTemperature());
            }
            
            // Real-time validation for extra params JSON
            const extraInput = document.getElementById('config-extra');
            if (extraInput) {
                extraInput.addEventListener('blur', () => this.validateExtraParams());
            }
        },
        
        /**
         * Validate temperature value
         */
        validateTemperature() {
            const input = document.getElementById('config-temperature');
            const value = parseFloat(input.value);
            
            if (isNaN(value) || value < 0 || value > 1) {
                this.showFieldError(input, 'Temperature must be between 0.0 and 1.0');
                return false;
            }
            
            this.clearFieldError(input);
            return true;
        },
        
        /**
         * Validate extra params JSON
         */
        validateExtraParams() {
            const input = document.getElementById('config-extra');
            const value = input.value.trim();
            
            if (!value) return true; // Empty is valid
            
            try {
                JSON.parse(value);
                this.clearFieldError(input);
                return true;
            } catch (e) {
                this.showFieldError(input, 'Invalid JSON format');
                return false;
            }
        },
        
        /**
         * Show field error
         */
        showFieldError(field, message) {
            field.classList.add('error');
            
            // Find or create error message element
            let errorEl = field.parentElement.querySelector('.field-error');
            if (!errorEl) {
                errorEl = document.createElement('span');
                errorEl.className = 'field-error';
                field.parentElement.appendChild(errorEl);
            }
            errorEl.textContent = message;
        },
        
        /**
         * Clear field error
         */
        clearFieldError(field) {
            field.classList.remove('error');
            const errorEl = field.parentElement.querySelector('.field-error');
            if (errorEl) {
                errorEl.remove();
            }
        },
        
        /**
         * Validate entire form
         */
        validateForm() {
            const form = document.getElementById('config-form');
            let isValid = true;
            
            // Required fields
            const requiredFields = ['config-name', 'config-provider', 'config-model'];
            requiredFields.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (!field.value.trim()) {
                    this.showFieldError(field, 'This field is required');
                    isValid = false;
                } else {
                    this.clearFieldError(field);
                }
            });
            
            // Temperature validation
            if (!this.validateTemperature()) {
                isValid = false;
            }
            
            // Extra params validation
            if (!this.validateExtraParams()) {
                isValid = false;
            }
            
            return isValid;
        },
        
        /**
         * Load configurations from API
         */
        async loadConfigs() {
            try {
                Utils.updateStatus('Loading configurations...', 'loading');
                
                const response = await API.get('/configs');
                const configs = response.data || response || [];
                
                State.set('configs', configs);
                this.renderConfigList(configs);
                
                // Update run config selector
                this.updateRunConfigSelector(configs);
                
                Utils.updateStatus('Configurations loaded');
                return configs;
            } catch (error) {
                Utils.handleError(error, { context: 'Loading configurations' });
                this.renderConfigList([]);
                return [];
            }
        },
        
        /**
         * Render config list
         */
        renderConfigList(configs) {
            const container = document.getElementById('config-list');
            if (!container) return;
            
            if (!configs || configs.length === 0) {
                container.innerHTML = '<div class="empty-state">No configurations yet. Create one to get started.</div>';
                return;
            }
            
            container.innerHTML = configs.map(config => `
                <div class="config-card ${this.currentConfigId === config.id ? 'selected' : ''}" 
                     data-id="${config.id}"
                     onclick="PromptGovernor.ConfigManager.selectConfig('${config.id}')">
                    <div class="config-card-header">
                        <span class="config-name">${Utils.escapeHtml(config.name)}</span>
                        <span class="config-provider badge">${config.provider}</span>
                    </div>
                    <div class="config-card-details">
                        <span class="config-model">${Utils.escapeHtml(config.model_id)}</span>
                        <span class="config-temp">Temp: ${config.temperature}</span>
                    </div>
                </div>
            `).join('');
        },
        
        /**
         * Update run config selector
         */
        updateRunConfigSelector(configs) {
            const selector = document.getElementById('run-config-select');
            if (!selector) return;
            
            const currentValue = selector.value;
            
            selector.innerHTML = '<option value="">Select config...</option>' +
                configs.map(config => `
                    <option value="${config.id}">${Utils.escapeHtml(config.name)} (${config.provider})</option>
                `).join('');
            
            // Restore selection if still valid
            if (currentValue && configs.find(c => c.id === currentValue)) {
                selector.value = currentValue;
            }
        },
        
        /**
         * Select a config for editing
         */
        selectConfig(configId) {
            const configs = State.get('configs', []);
            const config = configs.find(c => c.id === configId);
            
            if (!config) return;
            
            this.currentConfigId = configId;
            this.isEditing = true;
            
            // Populate form
            document.getElementById('config-name').value = config.name || '';
            document.getElementById('config-provider').value = config.provider || '';
            document.getElementById('config-model').value = config.model_id || '';
            document.getElementById('config-reasoning').value = config.reasoning_effort || 'medium';
            document.getElementById('config-temperature').value = config.temperature !== undefined ? config.temperature : 0.7;
            document.getElementById('temp-value').textContent = config.temperature !== undefined ? config.temperature : 0.7;
            document.getElementById('config-max-tokens').value = config.max_tokens || '';
            document.getElementById('config-extra').value = config.extra_params ? JSON.stringify(config.extra_params, null, 2) : '';
            
            // Update suggestions for selected provider
            this.updateModelSuggestions(config.provider);
            
            // Update UI state
            this.updateFormState();
            this.renderConfigList(configs);
            
            Utils.updateStatus(`Editing configuration: ${config.name}`);
        },
        
        /**
         * Start creating a new config
         */
        startNewConfig() {
            this.currentConfigId = null;
            this.isEditing = false;
            
            // Clear form
            document.getElementById('config-form').reset();
            document.getElementById('temp-value').textContent = '0.7';
            
            // Clear any errors
            document.querySelectorAll('#config-form .error').forEach(el => {
                el.classList.remove('error');
            });
            document.querySelectorAll('#config-form .field-error').forEach(el => {
                el.remove();
            });
            
            // Remove model suggestions
            const datalist = document.getElementById('model-suggestions');
            if (datalist) datalist.remove();
            
            // Update UI state
            this.updateFormState();
            
            Utils.updateStatus('Creating new configuration');
        },
        
        /**
         * Cancel editing
         */
        cancelEdit() {
            if (this.currentConfigId) {
                // Re-select current to reset form
                this.selectConfig(this.currentConfigId);
            } else {
                // Clear form
                document.getElementById('config-form').reset();
                document.getElementById('temp-value').textContent = '0.7';
            }
            
            // Clear errors
            document.querySelectorAll('#config-form .error').forEach(el => {
                el.classList.remove('error');
            });
            document.querySelectorAll('#config-form .field-error').forEach(el => {
                el.remove();
            });
        },
        
        /**
         * Update form UI state
         */
        updateFormState() {
            const deleteBtn = document.getElementById('delete-config-btn');
            if (deleteBtn) {
                deleteBtn.style.display = this.isEditing ? 'inline-block' : 'none';
            }
        },
        
        /**
         * Handle form submission
         */
        async handleFormSubmit(e) {
            e.preventDefault();
            
            if (!this.validateForm()) {
                Utils.showToast('Please fix the errors in the form', 'error');
                return;
            }
            
            const formData = {
                name: document.getElementById('config-name').value.trim(),
                provider: document.getElementById('config-provider').value,
                model_id: document.getElementById('config-model').value.trim(),
                reasoning_effort: document.getElementById('config-reasoning').value,
                temperature: parseFloat(document.getElementById('config-temperature').value),
                max_tokens: document.getElementById('config-max-tokens').value ? 
                    parseInt(document.getElementById('config-max-tokens').value) : null,
                extra_params: null
            };
            
            // Parse extra params JSON
            const extraJson = document.getElementById('config-extra').value.trim();
            if (extraJson) {
                try {
                    formData.extra_params = JSON.parse(extraJson);
                } catch (e) {
                    Utils.showToast('Invalid JSON in extra parameters', 'error');
                    return;
                }
            }
            
            try {
                if (this.isEditing && this.currentConfigId) {
                    // Update existing
                    await API.put(`/configs/${this.currentConfigId}`, formData);
                    Utils.showToast('Configuration updated successfully', 'success');
                } else {
                    // Create new
                    const response = await API.post('/configs', formData);
                    this.currentConfigId = response.data?.id || response.id;
                    this.isEditing = true;
                    Utils.showToast('Configuration created successfully', 'success');
                }
                
                // Reload configs to refresh list
                await this.loadConfigs();
                this.updateFormState();
                
            } catch (error) {
                Utils.handleError(error, { 
                    context: this.isEditing ? 'Updating configuration' : 'Creating configuration'
                });
            }
        },
        
        /**
         * Delete current configuration
         */
        async deleteCurrentConfig() {
            if (!this.currentConfigId) return;
            
            const configs = State.get('configs', []);
            const config = configs.find(c => c.id === this.currentConfigId);
            const configName = config ? config.name : 'this configuration';
            
            if (!confirm(`Are you sure you want to delete "${configName}"? This action cannot be undone.`)) {
                return;
            }
            
            try {
                await API.delete(`/configs/${this.currentConfigId}`);
                Utils.showToast('Configuration deleted successfully', 'success');
                
                // Reset form
                this.startNewConfig();
                
                // Reload configs
                await this.loadConfigs();
                
            } catch (error) {
                Utils.handleError(error, { context: 'Deleting configuration' });
            }
        }
    };

    // ============================================
    // RUN & RESULTS MANAGER (Phase E3)
    // ============================================
    const RunManager = {
        currentRunId: null,
        pollInterval: null,
        pollIntervalMs: 2000,

        /**
         * Initialize the Run & Results tab
         */
        init() {
            this.bindEvents();
            this.setupTabListener();
        },

        /**
         * Set up tab change listener to load dropdowns when runs tab is activated
         */
        setupTabListener() {
            window.addEventListener('tabchange', (e) => {
                if (e.detail.tab === 'runs') {
                    this.loadDropdowns();
                    this.loadRunHistory();
                }
            });
        },

        /**
         * Bind event listeners
         */
        bindEvents() {
            // Run extraction button
            const runBtn = document.getElementById('run-extraction-btn');
            if (runBtn) {
                runBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handleRunExtraction();
                });
            }

            // Reset button
            const resetBtn = document.getElementById('reset-run-btn');
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    this.resetForm();
                });
            }

            // Refresh history button
            const refreshBtn = document.getElementById('refresh-history-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    this.loadRunHistory();
                });
            }

            // Export results button
            const exportBtn = document.getElementById('export-results-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', () => {
                    this.exportResults();
                });
            }

            // Dropdown change listeners for validation
            ['run-prompt-select', 'run-config-select', 'run-document-select'].forEach(id => {
                const select = document.getElementById(id);
                if (select) {
                    select.addEventListener('change', () => {
                        this.clearFieldError(id);
                    });
                }
            });
        },

        /**
         * Load all dropdowns (prompts, configs, documents)
         */
        async loadDropdowns() {
            try {
                Utils.updateStatus('Loading dropdowns...', 'loading');

                await Promise.all([
                    this.loadPrompts(),
                    this.loadConfigs(),
                    this.loadDocuments()
                ]);

                Utils.updateStatus('Ready');
            } catch (error) {
                Utils.handleError(error, { context: 'Loading dropdowns' });
            }
        },

        /**
         * Load prompts into dropdown
         */
        async loadPrompts() {
            const select = document.getElementById('run-prompt-select');
            if (!select) return;

            try {
                const response = await API.get('/prompts');
                const prompts = response.data || response || [];

                // Clear existing options except first
                select.innerHTML = '<option value="">Select prompt...</option>';

                prompts.forEach(prompt => {
                    const option = document.createElement('option');
                    option.value = prompt.id;
                    option.textContent = prompt.name || prompt.id;
                    if (prompt.description) {
                        option.title = prompt.description;
                    }
                    select.appendChild(option);
                });

                State.set('prompts', prompts);
            } catch (error) {
                console.warn('Failed to load prompts:', error);
                select.innerHTML = '<option value="">Error loading prompts</option>';
            }
        },

        /**
         * Load configs into dropdown
         */
        async loadConfigs() {
            const select = document.getElementById('run-config-select');
            if (!select) return;

            try {
                const response = await API.get('/configs');
                const configs = response.data || response || [];

                // Clear existing options except first
                select.innerHTML = '<option value="">Select config...</option>';

                configs.forEach(config => {
                    const option = document.createElement('option');
                    option.value = config.id;
                    option.textContent = config.name || `${config.provider} - ${config.model_id}`;
                    if (config.description) {
                        option.title = config.description;
                    }
                    select.appendChild(option);
                });

                State.set('configs', configs);
            } catch (error) {
                console.warn('Failed to load configs:', error);
                select.innerHTML = '<option value="">Error loading configs</option>';
            }
        },

        /**
         * Load documents into dropdown
         */
        async loadDocuments() {
            const select = document.getElementById('run-document-select');
            if (!select) return;

            try {
                const response = await API.get('/documents');
                const documents = response.data || response || [];

                // Clear existing options except first
                select.innerHTML = '<option value="">Select document...</option>';

                documents.forEach(doc => {
                    const option = document.createElement('option');
                    option.value = doc.name || doc.id;
                    option.textContent = doc.name || doc.id;
                    if (doc.word_count) {
                        option.textContent += ` (${doc.word_count} words)`;
                    }
                    select.appendChild(option);
                });

                State.set('documents', documents);
            } catch (error) {
                console.warn('Failed to load documents:', error);
                select.innerHTML = '<option value="">Error loading documents</option>';
            }
        },

        /**
         * Handle run extraction button click
         */
        async handleRunExtraction() {
            // Validate form
            if (!this.validateForm()) {
                Utils.showToast('Please fill in all required fields', 'warning');
                return;
            }

            const promptId = document.getElementById('run-prompt-select').value;
            const configId = document.getElementById('run-config-select').value;
            const documentName = document.getElementById('run-document-select').value;

            try {
                this.setLoading(true);
                this.showProgress();
                this.hideResults();

                // Create run
                const response = await API.post('/runs', {
                    prompt_id: promptId,
                    config_id: configId,
                    document_name: documentName
                });

                const run = response.data || response;
                this.currentRunId = run.id;

                Utils.showToast('Extraction started', 'info');

                // Start polling for status
                this.startPolling(run.id);

            } catch (error) {
                this.setLoading(false);
                this.hideProgress();
                Utils.handleError(error, { context: 'Starting extraction run' });
            }
        },

        /**
         * Validate form inputs
         */
        validateForm() {
            let isValid = true;

            const fields = [
                { id: 'run-prompt-select', errorId: 'prompt-error', name: 'Prompt' },
                { id: 'run-config-select', errorId: 'config-error', name: 'Configuration' },
                { id: 'run-document-select', errorId: 'document-error', name: 'Document' }
            ];

            fields.forEach(field => {
                const select = document.getElementById(field.id);
                if (!select || !select.value) {
                    this.showFieldError(field.id, field.errorId, `${field.name} is required`);
                    isValid = false;
                } else {
                    this.clearFieldError(field.id);
                }
            });

            return isValid;
        },

        /**
         * Show field error
         */
        showFieldError(fieldId, errorId, message) {
            const field = document.getElementById(fieldId);
            const error = document.getElementById(errorId);

            if (field) {
                field.classList.add('error');
            }
            if (error) {
                error.textContent = message;
            }
        },

        /**
         * Clear field error
         */
        clearFieldError(fieldId) {
            const field = document.getElementById(fieldId);
            const errorId = fieldId.replace('select', 'error');
            const error = document.getElementById(errorId);

            if (field) {
                field.classList.remove('error');
            }
            if (error) {
                error.textContent = '';
            }
        },

        /**
         * Set loading state on run button
         */
        setLoading(loading) {
            const btn = document.getElementById('run-extraction-btn');
            if (!btn) return;

            const btnText = btn.querySelector('.btn-text');
            const btnSpinner = btn.querySelector('.btn-spinner');

            btn.disabled = loading;

            if (btnText) {
                btnText.textContent = loading ? 'Running...' : 'Run Extraction';
            }
            if (btnSpinner) {
                btnSpinner.style.display = loading ? 'inline-block' : 'none';
            }
        },

        /**
         * Show progress indicator
         */
        showProgress() {
            const progress = document.getElementById('run-progress');
            if (progress) {
                progress.style.display = 'block';
            }

            // Set indeterminate animation
            const fill = document.getElementById('progress-fill');
            if (fill) {
                fill.classList.add('indeterminate');
                fill.style.width = '0%';
            }

            const text = document.getElementById('progress-text');
            if (text) {
                text.textContent = 'Initializing extraction...';
            }
        },

        /**
         * Hide progress indicator
         */
        hideProgress() {
            const progress = document.getElementById('run-progress');
            if (progress) {
                progress.style.display = 'none';
            }
        },

        /**
         * Update progress display
         */
        updateProgress(status, progress) {
            const fill = document.getElementById('progress-fill');
            const text = document.getElementById('progress-text');

            if (fill) {
                fill.classList.remove('indeterminate');
                fill.style.width = `${progress}%`;
            }

            if (text) {
                const statusMessages = {
                    'pending': 'Waiting to start...',
                    'running': 'Extracting data...',
                    'completed': 'Complete!',
                    'failed': 'Failed'
                };
                text.textContent = statusMessages[status] || status;
            }
        },

        /**
         * Start polling for run status
         */
        startPolling(runId) {
            // Clear any existing polling
            this.stopPolling();

            this.pollInterval = setInterval(async () => {
                try {
                    const response = await API.get(`/runs/${runId}`);
                    const run = response.data || response;

                    // Calculate progress based on status (API doesn't have explicit progress field)
                    const progressMap = {
                        'pending': 10,
                        'running': 50,
                        'completed': 100,
                        'failed': 100
                    };
                    const progress = run.progress || progressMap[run.status] || 0;

                    this.updateProgress(run.status, progress);

                    if (run.status === 'completed') {
                        this.stopPolling();
                        this.setLoading(false);
                        this.hideProgress();
                        this.displayResults(run);
                        this.loadRunHistory();
                        Utils.showToast('Extraction completed!', 'success');
                    } else if (run.status === 'failed') {
                        this.stopPolling();
                        this.setLoading(false);
                        this.hideProgress();
                        this.displayError(run);
                        this.loadRunHistory();
                        Utils.showToast('Extraction failed', 'error');
                    }

                } catch (error) {
                    console.error('Polling error:', error);
                }
            }, this.pollIntervalMs);
        },

        /**
         * Stop polling
         */
        stopPolling() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        },

        /**
         * Display run results
         */
        displayResults(run) {
            // The run object structure from API:
            // - metrics: { recall, precision, f1, ... }
            // - output: extracted data
            // - tokens: { input, output, total }
            // - cost_usd: cost
            // - status: completion status

            // Show results panel
            const panel = document.getElementById('results-panel');
            if (panel) {
                panel.style.display = 'block';
            }

            // Update metrics (from run.metrics)
            const metrics = run.metrics || {};
            this.updateMetric('metric-recall', metrics.recall, true);
            this.updateMetric('metric-precision', metrics.precision, true);
            this.updateMetric('metric-f1', metrics.f1 || metrics.f1_score, true);

            // Cost and tokens
            this.updateMetric('metric-cost', run.cost_usd, false, '$');
            const totalTokens = run.tokens ? (run.tokens.total || run.tokens.input + run.tokens.output) : null;
            this.updateMetric('metric-tokens', totalTokens, false);

            // Update missing fields (from metrics.missing_fields)
            this.displayMissingFields(metrics.missing_fields || []);

            // Display diff (output vs ground_truth from metrics)
            this.displayDiff(run.output, metrics.ground_truth || {});

            // Store current run
            State.set('currentRun', run);
        },

        /**
         * Update a metric display
         */
        updateMetric(elementId, value, isPercentage = false, prefix = '') {
            const element = document.getElementById(elementId);
            if (!element) return;

            if (value === null || value === undefined || isNaN(value)) {
                element.textContent = isPercentage ? '--%' : `${prefix}--`;
                return;
            }

            const numValue = parseFloat(value);

            if (isPercentage) {
                // Convert 0-1 to percentage if needed
                const pct = numValue <= 1 ? numValue * 100 : numValue;
                element.textContent = `${pct.toFixed(1)}%`;

                // Color code based on value
                const card = element.closest('.metric-card');
                if (card) {
                    card.classList.remove('success', 'warning', 'error');
                    if (pct >= 80) {
                        card.classList.add('success');
                    } else if (pct >= 50) {
                        card.classList.add('warning');
                    } else {
                        card.classList.add('error');
                    }
                }
            } else {
                element.textContent = prefix + Utils.formatNumber(numValue, 2);
            }
        },

        /**
         * Display missing fields
         */
        displayMissingFields(fields) {
            const list = document.getElementById('missing-fields-list');
            const count = document.getElementById('missing-fields-count');

            if (!list) return;

            if (count) {
                count.textContent = fields.length;
                count.className = 'badge' + (fields.length > 0 ? ' warning' : '');
            }

            if (fields.length === 0) {
                list.innerHTML = '<li class="empty">No missing fields</li>';
                return;
            }

            list.innerHTML = fields.map(field =>
                `<li>${Utils.escapeHtml(field)}</li>`
            ).join('');
        },

        /**
         * Display JSON diff
         */
        displayDiff(output, groundTruth) {
            const content = document.getElementById('diff-content');
            if (!content) return;

            if (!output || !groundTruth) {
                content.innerHTML = '<div class="empty-state">No diff data available</div>';
                return;
            }

            const diff = DiffViewer.compare(output, groundTruth);
            content.innerHTML = DiffViewer.render(diff);
        },

        /**
         * Display error state
         */
        displayError(run) {
            const panel = document.getElementById('results-panel');
            if (panel) {
                panel.style.display = 'block';
                panel.innerHTML = `
                    <div class="error-state">
                        <h3>❌ Extraction Failed</h3>
                        <p>${Utils.escapeHtml(run.error || 'Unknown error occurred')}</p>
                    </div>
                `;
            }
        },

        /**
         * Hide results panel
         */
        hideResults() {
            const panel = document.getElementById('results-panel');
            if (panel) {
                panel.style.display = 'none';
            }
        },

        /**
         * Load run history
         */
        async loadRunHistory() {
            const list = document.getElementById('history-list');
            if (!list) return;

            try {
                const response = await API.get('/runs?limit=20');
                const runs = response.data || response || [];

                State.set('runs', runs);
                this.renderRunHistory(runs);
            } catch (error) {
                console.warn('Failed to load run history:', error);
                list.innerHTML = '<div class="empty-state">Failed to load history</div>';
            }
        },

        /**
         * Render run history list
         */
        renderRunHistory(runs) {
            const list = document.getElementById('history-list');
            if (!list) return;

            if (runs.length === 0) {
                list.innerHTML = '<div class="empty-state">No runs yet</div>';
                return;
            }

            list.innerHTML = runs.map(run => {
                const statusIcon = {
                    'pending': '⏳',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }[run.status] || '❓';

                const isActive = run.id === this.currentRunId;

                // Handle both API response formats:
                // - run.metrics for full run objects
                // - run.recall, run.precision for RunMetadata (from list endpoint)
                let recall = null;
                if (run.metrics && run.status === 'completed') {
                    recall = run.metrics.recall;
                } else if (run.recall !== undefined) {
                    recall = run.recall;
                }

                let metrics = '';
                if (recall !== null && recall !== undefined) {
                    const recallPct = recall <= 1 ? (recall * 100).toFixed(0) : recall.toFixed(0);
                    metrics = `
                        <div class="history-metrics">
                            <div class="history-metric">
                                <div class="history-metric-value">${recallPct}%</div>
                                <div class="history-metric-label">Recall</div>
                            </div>
                            <span class="status-badge ${run.status}">${run.status}</span>
                        </div>
                    `;
                } else {
                    metrics = `
                        <div class="history-metrics">
                            <span class="status-badge ${run.status}">${run.status}</span>
                        </div>
                    `;
                }

                // Use started_at (API format) or created_at (frontend format)
                const dateField = run.started_at || run.created_at;

                return `
                    <div class="history-item ${isActive ? 'active' : ''}" data-run-id="${run.id}">
                        <div class="history-status ${run.status}">${statusIcon}</div>
                        <div class="history-info">
                            <div class="history-title">${Utils.escapeHtml(run.document_name || 'Unknown')}</div>
                            <div class="history-meta">
                                ${Utils.formatRelativeTime(dateField)} •
                                ${Utils.escapeHtml(run.prompt_id ? run.prompt_id.substring(0, 8) + '...' : 'Unknown')}
                            </div>
                        </div>
                        ${metrics}
                    </div>
                `;
            }).join('');

            // Add click handlers
            list.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', () => {
                    const runId = item.dataset.runId;
                    this.loadRunDetails(runId);
                });
            });
        },

        /**
         * Load and display run details
         */
        async loadRunDetails(runId) {
            try {
                Utils.showLoading();
                const response = await API.get(`/runs/${runId}`);
                const run = response.data || response;

                this.currentRunId = run.id;

                // Update form with run's selections (handle both UUID and string formats)
                const promptSelect = document.getElementById('run-prompt-select');
                const configSelect = document.getElementById('run-config-select');
                const docSelect = document.getElementById('run-document-select');

                if (promptSelect) promptSelect.value = run.prompt_id || '';
                if (configSelect) configSelect.value = run.config_id || '';
                if (docSelect) docSelect.value = run.document_name || '';

                // Display results based on status
                if (run.status === 'completed' && run.metrics) {
                    this.displayResults(run);
                } else if (run.status === 'failed') {
                    this.displayError(run);
                } else {
                    // For pending/running, just show progress
                    this.showProgress();
                    if (run.status === 'running') {
                        this.startPolling(run.id);
                    }
                }

                // Update active state in history
                this.renderRunHistory(State.get('runs', []));

                Utils.hideLoading();
            } catch (error) {
                Utils.hideLoading();
                Utils.handleError(error, { context: 'Loading run details' });
            }
        },

        /**
         * Reset the form
         */
        resetForm() {
            document.getElementById('run-form').reset();
            this.hideResults();
            this.hideProgress();
            this.stopPolling();
            this.setLoading(false);
            this.currentRunId = null;

            // Clear field errors
            ['run-prompt-select', 'run-config-select', 'run-document-select'].forEach(id => {
                this.clearFieldError(id);
            });

            // Update history active state
            this.renderRunHistory(State.get('runs', []));

            Utils.showToast('Form reset', 'info');
        },

        /**
         * Export results as JSON
         */
        exportResults() {
            const run = State.get('currentRun');
            if (!run) {
                Utils.showToast('No results to export', 'warning');
                return;
            }

            const data = JSON.stringify(run, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `run-${run.id}-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            URL.revokeObjectURL(url);
            Utils.showToast('Results exported', 'success');
        }
    };

    // ============================================
    // DIFF VIEWER UTILITY
    // ============================================
    const DiffViewer = {
        /**
         * Compare two objects and generate diff
         */
        compare(output, groundTruth) {
            const diffs = [];

            const allKeys = new Set([
                ...Object.keys(output || {}),
                ...Object.keys(groundTruth || {})
            ]);

            allKeys.forEach(key => {
                const outVal = output?.[key];
                const gtVal = groundTruth?.[key];

                if (!(key in output)) {
                    diffs.push({ key, type: 'removed', value: gtVal, groundTruth: gtVal });
                } else if (!(key in groundTruth)) {
                    diffs.push({ key, type: 'added', value: outVal, output: outVal });
                } else if (JSON.stringify(outVal) !== JSON.stringify(gtVal)) {
                    diffs.push({
                        key,
                        type: 'modified',
                        value: outVal,
                        output: outVal,
                        groundTruth: gtVal
                    });
                }
            });

            return diffs;
        },

        /**
         * Render diff as HTML
         */
        render(diffs) {
            if (diffs.length === 0) {
                return '<div class="empty-state">No differences found</div>';
            }

            return diffs.map((diff, index) => {
                const typeClass = diff.type;
                const icon = {
                    'added': '+',
                    'removed': '-',
                    'modified': '~'
                }[diff.type];

                let content = '';
                if (diff.type === 'modified') {
                    content = `
                        <div class="diff-old">- ${Utils.escapeHtml(JSON.stringify(diff.groundTruth))}</div>
                        <div class="diff-new">+ ${Utils.escapeHtml(JSON.stringify(diff.output))}</div>
                    `;
                } else {
                    content = `<div>${icon} ${Utils.escapeHtml(JSON.stringify(diff.value))}</div>
                    `;
                }

                return `
                    <div class="diff-line ${typeClass}">
                        <span class="diff-line-number">${index + 1}</span>
                        <div class="diff-line-content">
                            <span class="diff-key">"${Utils.escapeHtml(diff.key)}"</span>:
                            ${content}
                        </div>
                    </div>
                `;
            }).join('');
        }
    };

    // ============================================
    // KEYBOARD SHORTCUTS MANAGER
    // ============================================
    const KeyboardShortcuts = {
        shortcuts: new Map(),
        isEnabled: true,

        /**
         * Initialize keyboard shortcuts
         */
        init() {
            this.registerDefaults();
            this.setupGlobalListener();
            this.addHelpButton();
        },

        /**
         * Register default keyboard shortcuts
         */
        registerDefaults() {
            // Tab switching: Cmd/Ctrl + 1/2/3
            this.register('1', (e) => {
                e.preventDefault();
                Tabs.showTab('prompts');
                Utils.showToast('Switched to Prompts tab', 'info', 2000);
            }, { ctrl: true, description: 'Switch to Prompts tab' });

            this.register('2', (e) => {
                e.preventDefault();
                Tabs.showTab('configs');
                Utils.showToast('Switched to Configs tab', 'info', 2000);
            }, { ctrl: true, description: 'Switch to Configs tab' });

            this.register('3', (e) => {
                e.preventDefault();
                Tabs.showTab('runs');
                Utils.showToast('Switched to Run & Results tab', 'info', 2000);
            }, { ctrl: true, description: 'Switch to Run tab' });

            // Save: Cmd/Ctrl + S
            this.register('s', (e) => {
                e.preventDefault();
                const currentTab = Tabs.getCurrentTab();
                if (currentTab === 'prompts') {
                    const saveBtn = document.getElementById('save-version-btn');
                    if (saveBtn) saveBtn.click();
                } else if (currentTab === 'configs') {
                    const form = document.getElementById('config-form');
                    if (form) form.dispatchEvent(new Event('submit'));
                }
            }, { ctrl: true, description: 'Save current form' });

            // Run extraction: Cmd/Ctrl + Enter
            this.register('Enter', (e) => {
                if (Tabs.getCurrentTab() === 'runs') {
                    e.preventDefault();
                    const runBtn = document.getElementById('run-extraction-btn');
                    if (runBtn && !runBtn.disabled) {
                        runBtn.click();
                    }
                }
            }, { ctrl: true, description: 'Run extraction' });

            // Close modals: Escape
            this.register('Escape', (e) => {
                const modals = document.querySelectorAll('.modal');
                let closed = false;
                modals.forEach(modal => {
                    if (modal.style.display !== 'none' && window.getComputedStyle(modal).display !== 'none') {
                        modal.style.display = 'none';
                        closed = true;
                    }
                });
                if (closed) {
                    Utils.showToast('Modal closed', 'info', 1500);
                }
            }, { description: 'Close modals' });

            // Refresh data: F5 or Cmd/Ctrl + R
            this.register('r', (e) => {
                e.preventDefault();
                const currentTab = Tabs.getCurrentTab();
                if (currentTab === 'prompts') {
                    PromptManager.loadPrompts();
                } else if (currentTab === 'configs') {
                    ConfigManager.loadConfigs();
                } else if (currentTab === 'runs') {
                    RunManager.loadDropdowns();
                    RunManager.loadRunHistory();
                }
                Utils.showToast('Data refreshed', 'success', 2000);
            }, { ctrl: true, description: 'Refresh data' });

            // Focus search: Cmd/Ctrl + F
            this.register('f', (e) => {
                if (Tabs.getCurrentTab() === 'prompts') {
                    e.preventDefault();
                    const searchInput = document.getElementById('prompt-search');
                    if (searchInput) {
                        searchInput.focus();
                        searchInput.select();
                    }
                }
            }, { ctrl: true, description: 'Focus search' });

            // New item: Cmd/Ctrl + N
            this.register('n', (e) => {
                e.preventDefault();
                const currentTab = Tabs.getCurrentTab();
                if (currentTab === 'prompts') {
                    const newBtn = document.getElementById('new-prompt-btn');
                    if (newBtn) newBtn.click();
                } else if (currentTab === 'configs') {
                    const newBtn = document.getElementById('new-config-btn');
                    if (newBtn) newBtn.click();
                }
            }, { ctrl: true, description: 'Create new item' });
        },

        /**
         * Register a keyboard shortcut
         * @param {string} key - Key to listen for
         * @param {Function} handler - Handler function
         * @param {Object} options - Options (ctrl, shift, alt, description)
         */
        register(key, handler, options = {}) {
            const shortcut = { key, handler, ...options };
            this.shortcuts.set(`${options.ctrl ? 'ctrl+' : ''}${options.shift ? 'shift+' : ''}${options.alt ? 'alt+' : ''}${key.toLowerCase()}`, shortcut);
        },

        /**
         * Setup global keydown listener
         */
        setupGlobalListener() {
            document.addEventListener('keydown', (e) => {
                if (!this.isEnabled) return;

                // Don't trigger shortcuts when typing in inputs/textareas
                if (e.target.matches('input, textarea, select, [contenteditable]')) {
                    // Allow Escape and Cmd/Ctrl shortcuts even in inputs
                    if (e.key !== 'Escape' && !e.ctrlKey && !e.metaKey) {
                        return;
                    }
                }

                const key = e.key.toLowerCase();
                const modifier = `${e.ctrlKey || e.metaKey ? 'ctrl+' : ''}${e.shiftKey ? 'shift+' : ''}${e.altKey ? 'alt+' : ''}${key}`;

                const shortcut = this.shortcuts.get(modifier);
                if (shortcut) {
                    shortcut.handler(e);
                }
            });
        },

        /**
         * Add help button with keyboard shortcuts info
         */
        addHelpButton() {
            const helpDiv = document.createElement('div');
            helpDiv.className = 'keyboard-shortcuts-help';
            helpDiv.innerHTML = `
                <button class="help-trigger" aria-label="Keyboard shortcuts" title="Keyboard shortcuts">
                    ⌘
                </button>
                <div class="help-content">
                    <h4>Keyboard Shortcuts</h4>
                    <ul class="shortcut-list">
                        ${Array.from(this.shortcuts.values())
                            .filter(s => s.description)
                            .map(s => `
                                <li>
                                    <span>${s.description}</span>
                                    <kbd>${s.ctrl ? (navigator.platform.indexOf('Mac') > -1 ? '⌘' : 'Ctrl+') : ''}${s.key === 'Enter' ? '↵' : s.key}</kbd>
                                </li>
                            `).join('')}
                    </ul>
                </div>
            `;
            document.body.appendChild(helpDiv);
        },

        /**
         * Enable/disable keyboard shortcuts
         * @param {boolean} enabled - Whether shortcuts are enabled
         */
        setEnabled(enabled) {
            this.isEnabled = enabled;
        }
    };

    // ============================================
    // LOADING SKELETON UTILITIES
    // ============================================
    const SkeletonLoader = {
        /**
         * Show skeleton loading state for a container
         * @param {string} containerId - Container element ID
         * @param {string} type - Skeleton type: 'text', 'card', 'list', 'table'
         * @param {number} count - Number of skeleton items
         */
        show(containerId, type = 'card', count = 3) {
            const container = document.getElementById(containerId);
            if (!container) return;

            container.dataset.originalContent = container.innerHTML;
            container.innerHTML = this.generate(type, count);
            container.classList.add('skeleton-active');
        },

        /**
         * Hide skeleton and restore original content
         * @param {string} containerId - Container element ID
         */
        hide(containerId) {
            const container = document.getElementById(containerId);
            if (!container) return;

            if (container.dataset.originalContent !== undefined) {
                container.innerHTML = container.dataset.originalContent;
                delete container.dataset.originalContent;
            }
            container.classList.remove('skeleton-active');
        },

        /**
         * Generate skeleton HTML
         * @param {string} type - Skeleton type
         * @param {number} count - Number of items
         * @returns {string} Skeleton HTML
         */
        generate(type, count) {
            const items = [];
            for (let i = 0; i < count; i++) {
                items.push(this.getSkeletonHtml(type));
            }
            return items.join('');
        },

        /**
         * Get skeleton HTML for a specific type
         * @param {string} type - Skeleton type
         * @returns {string} Skeleton HTML
         */
        getSkeletonHtml(type) {
            switch (type) {
                case 'text':
                    return `
                        <div class="skeleton skeleton-text long"></div>
                        <div class="skeleton skeleton-text medium"></div>
                        <div class="skeleton skeleton-text short"></div>
                    `;
                case 'card':
                    return `<div class="skeleton skeleton-card"></div>`;
                case 'list':
                    return `
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                            <div class="skeleton skeleton-circle"></div>
                            <div style="flex: 1;">
                                <div class="skeleton skeleton-text medium"></div>
                                <div class="skeleton skeleton-text short"></div>
                            </div>
                        </div>
                    `;
                case 'table':
                    return `
                        <div style="display: flex; gap: 16px; margin-bottom: 12px;">
                            <div class="skeleton" style="width: 30%; height: 20px;"></div>
                            <div class="skeleton" style="width: 40%; height: 20px;"></div>
                            <div class="skeleton" style="width: 30%; height: 20px;"></div>
                        </div>
                    `;
                default:
                    return `<div class="skeleton skeleton-card"></div>`;
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
                
                // Update config list and run selector
                if (configs) {
                    ConfigManager.renderConfigList(configs);
                    ConfigManager.updateRunConfigSelector(configs);
                }
                
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
    // ACCESSIBILITY MANAGER
    // ============================================
    const AccessibilityManager = {
        /**
         * Initialize accessibility features
         */
        init() {
            this.addSkipLink();
            this.enhanceFocusManagement();
            this.addAriaLabels();
            this.setupFocusTrapForModals();
        },

        /**
         * Add skip to main content link
         */
        addSkipLink() {
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = 'Skip to main content';
            document.body.insertBefore(skipLink, document.body.firstChild);

            // Add main-content ID to main content area
            const mainContent = document.querySelector('.main-content') || document.querySelector('main');
            if (mainContent && !mainContent.id) {
                mainContent.id = 'main-content';
                mainContent.setAttribute('tabindex', '-1');
            }
        },

        /**
         * Enhance focus management
         */
        enhanceFocusManagement() {
            // Track previously focused element before opening modals
            document.querySelectorAll('.modal').forEach(modal => {
                modal.addEventListener('show', () => {
                    modal.dataset.previousFocus = document.activeElement?.id || '';
                });

                modal.addEventListener('hide', () => {
                    const previousId = modal.dataset.previousFocus;
                    if (previousId) {
                        const previousElement = document.getElementById(previousId);
                        if (previousElement) {
                            previousElement.focus();
                        }
                    }
                });
            });

            // Add focus indicators to interactive elements
            document.querySelectorAll('.version-item, .config-card, .history-item').forEach(el => {
                el.setAttribute('tabindex', '0');
                el.setAttribute('role', 'button');
            });
        },

        /**
         * Add ARIA labels to elements that need them
         */
        addAriaLabels() {
            // Tab buttons
            document.querySelectorAll('.tab-button').forEach((btn, index) => {
                if (!btn.getAttribute('aria-label')) {
                    const label = btn.querySelector('.tab-label')?.textContent || `Tab ${index + 1}`;
                    btn.setAttribute('aria-label', label);
                }
                btn.setAttribute('role', 'tab');
            });

            // Tab panels
            document.querySelectorAll('.tab-content').forEach((panel, index) => {
                panel.setAttribute('role', 'tabpanel');
                if (!panel.getAttribute('aria-labelledby')) {
                    panel.setAttribute('aria-labelledby', `tab-${index}`);
                }
            });

            // Form inputs
            document.querySelectorAll('.form-group input, .form-group select, .form-group textarea').forEach(input => {
                const label = input.closest('.form-group')?.querySelector('label');
                if (label && !input.getAttribute('aria-describedby')) {
                    const helpId = input.id + '-help';
                    const helpText = input.closest('.form-group')?.querySelector('.field-error, .help-text');
                    if (helpText) {
                        helpText.id = helpId;
                        input.setAttribute('aria-describedby', helpId);
                    }
                }
            });

            // Buttons without text
            document.querySelectorAll('button:not([aria-label])').forEach(btn => {
                const text = btn.textContent?.trim();
                const icon = btn.querySelector('.btn-icon')?.textContent;
                if (!text && icon) {
                    btn.setAttribute('aria-label', icon);
                }
            });

            // Status indicators
            document.querySelectorAll('.status-indicator').forEach(el => {
                el.setAttribute('role', 'status');
                el.setAttribute('aria-live', 'polite');
            });

            // Loading states
            document.querySelectorAll('.loading, [data-loading]').forEach(el => {
                el.setAttribute('aria-busy', 'true');
            });
        },

        /**
         * Setup focus trap for modals
         */
        setupFocusTrapForModals() {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.addEventListener('keydown', (e) => {
                    if (e.key !== 'Tab') return;

                    const focusableElements = modal.querySelectorAll(
                        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    const firstElement = focusableElements[0];
                    const lastElement = focusableElements[focusableElements.length - 1];

                    if (e.shiftKey && document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    } else if (!e.shiftKey && document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                });
            });
        },

        /**
         * Announce message to screen readers
         * @param {string} message - Message to announce
         * @param {string} priority - Priority: 'polite' or 'assertive'
         */
        announce(message, priority = 'polite') {
            let announcer = document.getElementById('sr-announcer');
            if (!announcer) {
                announcer = document.createElement('div');
                announcer.id = 'sr-announcer';
                announcer.setAttribute('aria-live', priority);
                announcer.setAttribute('aria-atomic', 'true');
                announcer.style.position = 'absolute';
                announcer.style.left = '-10000px';
                announcer.style.width = '1px';
                announcer.style.height = '1px';
                announcer.style.overflow = 'hidden';
                document.body.appendChild(announcer);
            }

            announcer.setAttribute('aria-live', priority);
            announcer.textContent = '';
            setTimeout(() => {
                announcer.textContent = message;
            }, 100);
        }
    };

    // ============================================
    // JSON EDITOR MANAGER
    // ============================================
    const JSONEditorManager = {
        editor: null,
        
        /**
         * Initialize the JSON Editor
         */
        init() {
            const container = document.getElementById('prompt-editor-container');
            if (!container) return;
            
            try {
                this.editor = new JSONEditor('prompt-editor-container', {
                    readOnly: false,
                    lineNumbers: true,
                    height: '450px',
                    onChange: (value) => {
                        // Track unsaved changes
                        if (value !== this.lastSavedValue) {
                            Utils.updateStatus('Unsaved changes', 'loading');
                        }
                    },
                    onValidation: (result) => {
                        if (!result.isValid) {
                            console.log('JSON validation error:', result.error);
                        }
                    }
                });
                
                // Set initial example content
                this.editor.setValue({
                    name: "My Prompt",
                    description: "Example prompt for extraction",
                    blocks: [
                        {
                            type: "system",
                            content: "You are a helpful assistant that extracts information from documents."
                        },
                        {
                            type: "user",
                            content: "Extract the following fields from the document:..."
                        }
                    ],
                    version: "1.0.0"
                });
                
                console.log('✅ JSON Editor initialized');
                
            } catch (error) {
                console.error('Failed to initialize JSON Editor:', error);
            }
        },
        
        /**
         * Get the editor instance
         */
        getEditor() {
            return this.editor;
        },
        
        /**
         * Get current prompt value
         */
        getPromptValue() {
            return this.editor ? this.editor.getParsedValue() : null;
        },
        
        /**
         * Set prompt value
         */
        setPromptValue(value) {
            if (this.editor) {
                this.editor.setValue(value);
                this.lastSavedValue = typeof value === 'string' ? value : JSON.stringify(value);
            }
        },
        
        /**
         * Check if content is valid
         */
        isValid() {
            return this.editor ? this.editor.isValid() : false;
        }
    };

    // ============================================
    // PROMPT MANAGER
    // ============================================
    const PromptManager = {
        currentPromptId: null,
        prompts: [],
        filteredPrompts: [],
        
        /**
         * Initialize the Prompt Manager
         */
        init() {
            this.attachEventListeners();
            this.loadPrompts();
        },
        
        /**
         * Attach event listeners
         */
        attachEventListeners() {
            // Search input
            const searchInput = document.getElementById('prompt-search');
            if (searchInput) {
                searchInput.addEventListener('input', Utils.debounce(() => {
                    this.applyFilters();
                }, 300));
            }
            
            // Tag filter
            const tagFilter = document.getElementById('tag-filter');
            if (tagFilter) {
                tagFilter.addEventListener('change', () => {
                    this.applyFilters();
                });
            }
            
            // Clear filters
            const clearBtn = document.getElementById('clear-filters-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearFilters();
                });
            }
            
            // Prompt selector
            const selector = document.getElementById('prompt-selector');
            if (selector) {
                selector.addEventListener('change', (e) => {
                    if (e.target.value) {
                        this.loadPrompt(e.target.value);
                    }
                });
            }
            
            // New prompt button
            const newBtn = document.getElementById('new-prompt-btn');
            if (newBtn) {
                newBtn.addEventListener('click', () => {
                    this.newPrompt();
                });
            }
            
            // Save version button
            const saveBtn = document.getElementById('save-version-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => {
                    this.showSaveVersionModal();
                });
            }
            
            // Fork button
            const forkBtn = document.getElementById('fork-prompt-btn');
            if (forkBtn) {
                forkBtn.addEventListener('click', () => {
                    this.forkPrompt();
                });
            }
            
            // Delete button
            const deleteBtn = document.getElementById('delete-prompt-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => {
                    this.deletePrompt();
                });
            }
            
            // Compare button
            const compareBtn = document.getElementById('compare-btn');
            if (compareBtn) {
                compareBtn.addEventListener('click', () => {
                    this.showDiffModal();
                });
            }
            
            // Tree view toggle
            const treeToggle = document.getElementById('show-tree-view');
            if (treeToggle) {
                treeToggle.addEventListener('change', () => {
                    this.renderVersionList();
                });
            }
            
            // Modal close buttons
            this.setupModalListeners();
            
            // Load prompts when prompts tab is shown
            window.addEventListener('tabchange', (e) => {
                if (e.detail.tab === 'prompts') {
                    this.loadPrompts();
                }
            });
        },
        
        /**
         * Setup modal event listeners
         */
        setupModalListeners() {
            // Diff modal
            const diffModal = document.getElementById('diff-modal');
            const closeDiffBtn = document.getElementById('close-diff-modal');
            const loadDiffBtn = document.getElementById('load-diff-btn');
            
            if (closeDiffBtn) {
                closeDiffBtn.addEventListener('click', () => {
                    if (diffModal) diffModal.style.display = 'none';
                });
            }
            
            if (loadDiffBtn) {
                loadDiffBtn.addEventListener('click', () => {
                    this.loadDiff();
                });
            }
            
            // Save version modal
            const saveModal = document.getElementById('save-version-modal');
            const closeSaveBtn = document.getElementById('close-save-modal');
            const cancelSaveBtn = document.getElementById('cancel-save-btn');
            const saveVersionForm = document.getElementById('save-version-form');
            
            if (closeSaveBtn) {
                closeSaveBtn.addEventListener('click', () => {
                    if (saveModal) saveModal.style.display = 'none';
                });
            }
            
            if (cancelSaveBtn) {
                cancelSaveBtn.addEventListener('click', () => {
                    if (saveModal) saveModal.style.display = 'none';
                });
            }
            
            if (saveVersionForm) {
                saveVersionForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.saveNewVersion();
                });
            }
            
            // Close modals on overlay click
            document.querySelectorAll('.modal-overlay').forEach(overlay => {
                overlay.addEventListener('click', (e) => {
                    e.target.closest('.modal').style.display = 'none';
                });
            });
        },
        
        /**
         * Load all prompts from API
         */
        async loadPrompts() {
            try {
                Utils.updateStatus('Loading prompts...', 'loading');
                
                const response = await API.get('/prompts');
                this.prompts = response.prompts || [];
                this.filteredPrompts = [...this.prompts];
                
                State.set('prompts', this.prompts);
                
                this.updateTagFilter();
                this.renderVersionList();
                this.updatePromptSelector();
                
                Utils.updateStatus(`Loaded ${this.prompts.length} prompts`);
            } catch (error) {
                Utils.handleError(error, { context: 'Loading prompts' });
                this.prompts = [];
                this.filteredPrompts = [];
                this.renderVersionList();
            }
        },
        
        /**
         * Load a specific prompt by ID
         * @param {string} promptId - Prompt ID to load
         */
        async loadPrompt(promptId) {
            try {
                Utils.updateStatus('Loading prompt...', 'loading');
                
                const prompt = await API.get(`/prompts/${promptId}`);
                this.currentPromptId = promptId;
                State.set('currentPrompt', prompt);
                
                // Update editor
                JSONEditorManager.setPromptValue(prompt);
                
                // Update UI
                this.updatePromptInfo(prompt);
                this.highlightSelectedVersion(promptId);
                this.updatePromptSelectorValue(promptId);
                
                Utils.updateStatus(`Loaded prompt: ${prompt.name}`);
            } catch (error) {
                Utils.handleError(error, { context: 'Loading prompt' });
            }
        },
        
        /**
         * Update tag filter dropdown
         */
        updateTagFilter() {
            const tagFilter = document.getElementById('tag-filter');
            if (!tagFilter) return;
            
            // Collect all unique tags
            const allTags = new Set();
            this.prompts.forEach(prompt => {
                (prompt.tags || []).forEach(tag => allTags.add(tag));
            });
            
            // Save current selection
            const currentValue = tagFilter.value;
            
            // Rebuild options
            tagFilter.innerHTML = '<option value="">All tags</option>';
            Array.from(allTags).sort().forEach(tag => {
                const option = document.createElement('option');
                option.value = tag;
                option.textContent = tag;
                tagFilter.appendChild(option);
            });
            
            // Restore selection if still valid
            if (currentValue && allTags.has(currentValue)) {
                tagFilter.value = currentValue;
            }
        },
        
        /**
         * Apply search and tag filters
         */
        applyFilters() {
            const searchInput = document.getElementById('prompt-search');
            const tagFilter = document.getElementById('tag-filter');
            
            const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
            const selectedTag = tagFilter ? tagFilter.value : '';
            
            this.filteredPrompts = this.prompts.filter(prompt => {
                // Search filter
                const matchesSearch = !searchTerm || 
                    prompt.name.toLowerCase().includes(searchTerm) ||
                    (prompt.description && prompt.description.toLowerCase().includes(searchTerm));
                
                // Tag filter
                const matchesTag = !selectedTag || 
                    (prompt.tags || []).includes(selectedTag);
                
                return matchesSearch && matchesTag;
            });
            
            this.renderVersionList();
        },
        
        /**
         * Clear all filters
         */
        clearFilters() {
            const searchInput = document.getElementById('prompt-search');
            const tagFilter = document.getElementById('tag-filter');
            
            if (searchInput) searchInput.value = '';
            if (tagFilter) tagFilter.value = '';
            
            this.filteredPrompts = [...this.prompts];
            this.renderVersionList();
        },
        
        /**
         * Render version list in sidebar
         */
        renderVersionList() {
            const listContainer = document.getElementById('prompt-list');
            if (!listContainer) return;
            
            if (this.filteredPrompts.length === 0) {
                listContainer.innerHTML = '<div class="empty-state">No prompts found</div>';
                return;
            }
            
            const showTree = document.getElementById('show-tree-view')?.checked || false;
            
            if (showTree) {
                this.renderTreeView(listContainer);
            } else {
                this.renderFlatList(listContainer);
            }
        },
        
        /**
         * Render flat list view
         * @param {HTMLElement} container - Container element
         */
        renderFlatList(container) {
            container.innerHTML = '';
            
            this.filteredPrompts.forEach(prompt => {
                const item = this.createVersionItem(prompt);
                container.appendChild(item);
            });
        },
        
        /**
         * Render tree view showing parent/child relationships
         * @param {HTMLElement} container - Container element
         */
        renderTreeView(container) {
            container.innerHTML = '';
            
            // Build parent-child map
            const childrenMap = new Map();
            const rootPrompts = [];
            
            this.filteredPrompts.forEach(prompt => {
                if (prompt.parent_id) {
                    if (!childrenMap.has(prompt.parent_id)) {
                        childrenMap.set(prompt.parent_id, []);
                    }
                    childrenMap.get(prompt.parent_id).push(prompt);
                } else {
                    rootPrompts.push(prompt);
                }
            });
            
            // Render tree recursively
            const renderNode = (prompt, level = 0) => {
                const item = this.createVersionItem(prompt, level);
                container.appendChild(item);
                
                const children = childrenMap.get(prompt.id) || [];
                children.forEach(child => renderNode(child, level + 1));
            };
            
            rootPrompts.forEach(prompt => renderNode(prompt));
        },
        
        /**
         * Create a version list item element
         * @param {Object} prompt - Prompt data
         * @param {number} treeLevel - Tree level for indentation
         * @returns {HTMLElement}
         */
        createVersionItem(prompt, treeLevel = 0) {
            const item = document.createElement('div');
            item.className = 'version-item';
            item.dataset.id = prompt.id;
            
            if (prompt.id === this.currentPromptId) {
                item.classList.add('selected', 'current');
            }
            
            // Tree indicator
            let treeIndicator = '';
            if (treeLevel > 0) {
                treeIndicator = `
                    <div class="version-tree-indicator">
                        ${'<span class="version-tree-line"></span>'.repeat(treeLevel - 1)}
                        <span class="version-tree-branch"></span>
                    </div>
                `;
            }
            
            // Tags
            const tagsHtml = (prompt.tags || []).slice(0, 3).map(tag => 
                `<span class="version-tag">${Utils.escapeHtml(tag)}</span>`
            ).join('');
            
            item.innerHTML = `
                ${treeIndicator}
                <div class="version-content">
                    <div class="version-name">${Utils.escapeHtml(prompt.name)}</div>
                    <div class="version-meta">
                        ${Utils.formatRelativeTime(prompt.created_at)}
                        ${prompt.parent_id ? '• forked' : ''}
                    </div>
                    <div class="version-tags">${tagsHtml}</div>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.loadPrompt(prompt.id);
            });
            
            return item;
        },
        
        /**
         * Update prompt selector dropdown
         */
        updatePromptSelector() {
            const selector = document.getElementById('prompt-selector');
            if (!selector) return;
            
            const currentValue = selector.value;
            
            selector.innerHTML = '<option value="">Select a prompt...</option>';
            
            this.prompts.forEach(prompt => {
                const option = document.createElement('option');
                option.value = prompt.id;
                option.textContent = prompt.name;
                selector.appendChild(option);
            });
            
            if (currentValue) {
                selector.value = currentValue;
            }
        },
        
        /**
         * Update prompt selector value
         * @param {string} promptId - Selected prompt ID
         */
        updatePromptSelectorValue(promptId) {
            const selector = document.getElementById('prompt-selector');
            if (selector) {
                selector.value = promptId;
            }
        },
        
        /**
         * Highlight selected version in list
         * @param {string} promptId - Selected prompt ID
         */
        highlightSelectedVersion(promptId) {
            document.querySelectorAll('.version-item').forEach(item => {
                item.classList.toggle('selected', item.dataset.id === promptId);
                item.classList.toggle('current', item.dataset.id === promptId);
            });
        },
        
        /**
         * Update prompt info bar
         * @param {Object} prompt - Prompt data
         */
        updatePromptInfo(prompt) {
            const infoBar = document.getElementById('prompt-info-bar');
            const idDisplay = document.getElementById('prompt-id-display');
            const createdDisplay = document.getElementById('prompt-created-display');
            const parentDisplay = document.getElementById('prompt-parent-display');
            const tagsDisplay = document.getElementById('prompt-tags-display');
            
            if (infoBar) infoBar.style.display = 'flex';
            
            if (idDisplay) {
                idDisplay.textContent = prompt.id.substring(0, 8) + '...';
                idDisplay.title = prompt.id;
            }
            
            if (createdDisplay) {
                createdDisplay.textContent = Utils.formatDate(prompt.created_at);
            }
            
            if (parentDisplay) {
                if (prompt.parent_id) {
                    parentDisplay.innerHTML = `<span class="info-value clickable" data-parent="${prompt.parent_id}">${prompt.parent_id.substring(0, 8)}...</span>`;
                    parentDisplay.querySelector('.clickable').addEventListener('click', () => {
                        this.loadPrompt(prompt.parent_id);
                    });
                } else {
                    parentDisplay.textContent = 'None (root)';
                }
            }
            
            if (tagsDisplay) {
                const tagsHtml = (prompt.tags || []).map(tag => 
                    `<span class="tag">${Utils.escapeHtml(tag)}</span>`
                ).join('');
                tagsDisplay.innerHTML = tagsHtml || '<span class="text-muted">No tags</span>';
            }
        },
        
        /**
         * Show save version modal
         */
        showSaveVersionModal() {
            // Validate current content first
            const content = JSONEditorManager.getPromptValue();
            if (!content) {
                Utils.showToast('Please fix JSON errors before saving', 'error');
                return;
            }
            
            const modal = document.getElementById('save-version-modal');
            const nameInput = document.getElementById('new-version-name');
            const descInput = document.getElementById('new-version-description');
            const tagsInput = document.getElementById('new-version-tags');
            const forkCheck = document.getElementById('fork-from-current');
            
            // Pre-fill with current prompt data if available
            if (this.currentPromptId && State.get('currentPrompt')) {
                const current = State.get('currentPrompt');
                nameInput.value = current.name || '';
                descInput.value = current.description || '';
                tagsInput.value = (current.tags || []).join(', ');
            } else {
                nameInput.value = '';
                descInput.value = '';
                tagsInput.value = '';
            }
            
            forkCheck.checked = !!this.currentPromptId;
            
            modal.style.display = 'flex';
            nameInput.focus();
        },
        
        /**
         * Save new version
         */
        async saveNewVersion() {
            const nameInput = document.getElementById('new-version-name');
            const descInput = document.getElementById('new-version-description');
            const tagsInput = document.getElementById('new-version-tags');
            const forkCheck = document.getElementById('fork-from-current');
            const modal = document.getElementById('save-version-modal');
            
            const name = nameInput.value.trim();
            if (!name) {
                Utils.showToast('Please enter a name', 'error');
                return;
            }
            
            // Get editor content
            const content = JSONEditorManager.getPromptValue();
            if (!content) {
                Utils.showToast('Invalid JSON in editor', 'error');
                return;
            }
            
            // Build request
            const request = {
                name: name,
                description: descInput.value.trim() || undefined,
                blocks: content.blocks || [],
                tags: tagsInput.value.split(',').map(t => t.trim()).filter(t => t),
                parent_id: forkCheck.checked ? this.currentPromptId : undefined
            };
            
            try {
                Utils.showLoading();
                
                const response = await API.post('/prompts', request);
                
                modal.style.display = 'none';
                Utils.showToast('Version saved successfully', 'success');
                
                // Reload prompts and select the new one
                await this.loadPrompts();
                this.loadPrompt(response.id);
                
            } catch (error) {
                Utils.handleError(error, { context: 'Saving version' });
            } finally {
                Utils.hideLoading();
            }
        },
        
        /**
         * Fork current prompt
         */
        forkPrompt() {
            if (!this.currentPromptId) {
                Utils.showToast('Please select a prompt to fork', 'warning');
                return;
            }
            
            this.showSaveVersionModal();
            const forkCheck = document.getElementById('fork-from-current');
            if (forkCheck) forkCheck.checked = true;
        },
        
        /**
         * Delete current prompt
         */
        async deletePrompt() {
            if (!this.currentPromptId) {
                Utils.showToast('Please select a prompt to delete', 'warning');
                return;
            }
            
            const prompt = State.get('currentPrompt');
            if (!confirm(`Are you sure you want to delete "${prompt.name}"?\n\nThis action cannot be undone.`)) {
                return;
            }
            
            try {
                Utils.showLoading();
                
                await API.delete(`/prompts/${this.currentPromptId}`);
                
                Utils.showToast('Prompt deleted successfully', 'success');
                
                // Clear current selection
                this.currentPromptId = null;
                State.set('currentPrompt', null);
                
                // Reset editor
                JSONEditorManager.setPromptValue({
                    name: "My Prompt",
                    description: "Example prompt for extraction",
                    blocks: [
                        { type: "system", content: "You are a helpful assistant..." },
                        { type: "user", content: "Extract the following fields..." }
                    ],
                    tags: ["extraction"]
                });
                
                // Hide info bar
                const infoBar = document.getElementById('prompt-info-bar');
                if (infoBar) infoBar.style.display = 'none';
                
                // Reload list
                await this.loadPrompts();
                
            } catch (error) {
                Utils.handleError(error, { context: 'Deleting prompt' });
            } finally {
                Utils.hideLoading();
            }
        },
        
        /**
         * Create new prompt
         */
        newPrompt() {
            this.currentPromptId = null;
            State.set('currentPrompt', null);
            
            // Reset editor to example
            JSONEditorManager.setPromptValue({
                name: "My Prompt",
                description: "Example prompt for extraction",
                blocks: [
                    { type: "system", content: "You are a helpful assistant that extracts information from documents." },
                    { type: "user", content: "Extract the following fields from the document:..." }
                ],
                tags: ["extraction"]
            });
            
            // Clear selection
            document.querySelectorAll('.version-item').forEach(item => {
                item.classList.remove('selected', 'current');
            });
            
            // Reset selector
            const selector = document.getElementById('prompt-selector');
            if (selector) selector.value = '';
            
            // Hide info bar
            const infoBar = document.getElementById('prompt-info-bar');
            if (infoBar) infoBar.style.display = 'none';
            
            Utils.updateStatus('New prompt - edit and save as new version');
        },
        
        /**
         * Show diff modal
         */
        showDiffModal() {
            if (this.prompts.length < 2) {
                Utils.showToast('Need at least 2 prompts to compare', 'warning');
                return;
            }
            
            const modal = document.getElementById('diff-modal');
            const selectA = document.getElementById('diff-version-a');
            const selectB = document.getElementById('diff-version-b');
            
            // Populate selectors
            const options = this.prompts.map(p => 
                `<option value="${p.id}">${Utils.escapeHtml(p.name)} (${p.id.substring(0, 8)})</option>`
            ).join('');
            
            selectA.innerHTML = options;
            selectB.innerHTML = options;
            
            // Pre-select current prompt and previous one
            if (this.currentPromptId) {
                selectA.value = this.currentPromptId;
                const currentIndex = this.prompts.findIndex(p => p.id === this.currentPromptId);
                if (currentIndex > 0) {
                    selectB.value = this.prompts[currentIndex - 1].id;
                }
            }
            
            modal.style.display = 'flex';
        },
        
        /**
         * Load and display diff
         */
        async loadDiff() {
            const selectA = document.getElementById('diff-version-a');
            const selectB = document.getElementById('diff-version-b');
            const resultsDiv = document.getElementById('diff-results');
            
            const idA = selectA.value;
            const idB = selectB.value;
            
            if (!idA || !idB) {
                Utils.showToast('Please select two versions to compare', 'warning');
                return;
            }
            
            if (idA === idB) {
                Utils.showToast('Please select different versions', 'warning');
                return;
            }
            
            try {
                Utils.showLoading();
                
                const diff = await API.get(`/prompts/${idA}/diff/${idB}`);
                this.renderDiff(diff, resultsDiv);
                
            } catch (error) {
                Utils.handleError(error, { context: 'Loading diff' });
            } finally {
                Utils.hideLoading();
            }
        },
        
        /**
         * Render diff results
         * @param {Object} diff - Diff data
         * @param {HTMLElement} container - Container element
         */
        renderDiff(diff, container) {
            let html = '';
            
            // Name change
            if (diff.name_changed) {
                html += `
                    <div class="diff-section">
                        <div class="diff-section-title">Name Changed</div>
                        <div class="diff-block modified">
                            <div class="diff-block-content">Name was modified between versions</div>
                        </div>
                    </div>
                `;
            }
            
            // Description change
            if (diff.description_changed) {
                html += `
                    <div class="diff-section">
                        <div class="diff-section-title">Description Changed</div>
                        <div class="diff-block modified">
                            <div class="diff-block-content">Description was modified between versions</div>
                        </div>
                    </div>
                `;
            }
            
            // Tags change
            if (diff.tags_changed) {
                html += `
                    <div class="diff-section">
                        <div class="diff-section-title">Tags Changed</div>
                        <div class="diff-block modified">
                            <div class="diff-block-content">Tags were modified between versions</div>
                        </div>
                    </div>
                `;
            }
            
            // Block differences
            if (diff.blocks_diff && diff.blocks_diff.length > 0) {
                html += `
                    <div class="diff-section">
                        <div class="diff-section-title">Block Changes (${diff.blocks_diff.length})</div>
                `;
                
                diff.blocks_diff.forEach(blockDiff => {
                    const statusClass = blockDiff.status;
                    const statusLabel = blockDiff.status.charAt(0).toUpperCase() + blockDiff.status.slice(1);
                    
                    html += `
                        <div class="diff-block ${statusClass}">
                            <div class="diff-block-header">Block ${blockDiff.index + 1} - ${statusLabel}</div>
                    `;
                    
                    if (blockDiff.status === 'modified') {
                        html += `
                            <div class="diff-block-comparison">
                                <div class="diff-old">
                                    <strong>Old:</strong><br>
                                    <pre>${Utils.escapeHtml(JSON.stringify(blockDiff.old_block, null, 2))}</pre>
                                </div>
                                <div class="diff-new">
                                    <strong>New:</strong><br>
                                    <pre>${Utils.escapeHtml(JSON.stringify(blockDiff.new_block, null, 2))}</pre>
                                </div>
                            </div>
                        `;
                    } else if (blockDiff.status === 'added') {
                        html += `
                            <div class="diff-block-content">
                                <pre>${Utils.escapeHtml(JSON.stringify(blockDiff.new_block, null, 2))}</pre>
                            </div>
                        `;
                    } else if (blockDiff.status === 'removed') {
                        html += `
                            <div class="diff-block-content">
                                <pre>${Utils.escapeHtml(JSON.stringify(blockDiff.old_block, null, 2))}</pre>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                });
                
                html += '</div>';
            }
            
            if (!html) {
                html = '<div class="empty-state">No differences found between versions</div>';
            }
            
            container.innerHTML = html;
        }
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    function init() {
        console.log('🚀 Prompt Governor initialized');
        console.log('💡 Press ⌘/Ctrl + ? for keyboard shortcuts help');

        // Restore state from localStorage
        State.restore();

        // Initialize accessibility first
        AccessibilityManager.init();

        // Initialize tabs
        Tabs.init();

        // Initialize JSON Editor
        JSONEditorManager.init();

        // Initialize Prompt Manager
        PromptManager.init();

        // Initialize Config Manager
        ConfigManager.init();

        // Initialize Run Manager
        RunManager.init();

        // Initialize keyboard shortcuts
        KeyboardShortcuts.init();

        // Start API status monitoring
        APIStatus.start();

        // Load initial data
        DataLoader.loadInitialData();

        Utils.updateStatus('Ready');

        // Show welcome toast
        setTimeout(() => {
            Utils.showToast('Welcome to Prompt Governor! Press ⌘+1/2/3 to switch tabs', 'info', 6000);
        }, 1000);
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
        JSONEditorManager,
        PromptManager,
        ConfigManager,
        RunManager,
        DiffViewer,
        CONFIG,

        // UI Polish modules
        KeyboardShortcuts,
        SkeletonLoader,
        AccessibilityManager,

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
