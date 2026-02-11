/**
 * Prompt Governor - Main Application JavaScript
 */

(function() {
    'use strict';

    // State Management
    const State = {
        currentTab: 'prompts',
        prompts: [],
        configs: [],
        documents: [],
        runs: [],
        currentRun: null,
        loading: false,

        set(key, value) {
            this[key] = value;
            this.notify(key);
        },

        listeners: {},

        on(key, callback) {
            if (!this.listeners[key]) this.listeners[key] = [];
            this.listeners[key].push(callback);
        },

        notify(key) {
            if (this.listeners[key]) {
                this.listeners[key].forEach(cb => cb(this[key]));
            }
        }
    };

    // API Client
    const API = {
        baseUrl: '/api',

        async request(endpoint, options = {}) {
            const url = `${this.baseUrl}${endpoint}`;
            const config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            };

            try {
                State.set('loading', true);
                updateStatus('Loading...', 'loading');
                
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                updateStatus(`Error: ${error.message}`, 'error');
                throw error;
            } finally {
                State.set('loading', false);
            }
        },

        get(endpoint) {
            return this.request(endpoint, { method: 'GET' });
        },

        post(endpoint, data) {
            return this.request(endpoint, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },

        put(endpoint, data) {
            return this.request(endpoint, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },

        delete(endpoint) {
            return this.request(endpoint, { method: 'DELETE' });
        }
    };

    // Tab Management
    function initTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.dataset.tab;
                
                // Update button states
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Update content visibility
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === tabId) {
                        content.classList.add('active');
                    }
                });
                
                State.set('currentTab', tabId);
                updateStatus(`Switched to ${tabId} tab`);
            });
        });
    }

    // Status Updates
    function updateStatus(message, type = 'ready') {
        const statusText = document.getElementById('status-text');
        const statusIndicator = document.getElementById('status-indicator');
        
        if (statusText) statusText.textContent = message;
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator';
            if (type) statusIndicator.classList.add(type);
        }
    }

    // Check API Status
    async function checkAPIStatus() {
        const apiStatus = document.getElementById('api-status');
        try {
            const response = await fetch('/api/health');
            if (response.ok) {
                if (apiStatus) apiStatus.textContent = 'API: Connected';
                updateStatus('Ready');
            } else {
                throw new Error('Health check failed');
            }
        } catch (error) {
            if (apiStatus) apiStatus.textContent = 'API: Disconnected';
            updateStatus('API unavailable', 'error');
        }
    }

    // Initialization
    function init() {
        console.log('Prompt Governor initialized');
        
        // Initialize tabs
        initTabs();
        
        // Check API status
        checkAPIStatus();
        
        // Set up periodic API status check
        setInterval(checkAPIStatus, 30000);
        
        updateStatus('Ready');
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose to global scope for debugging
    window.PromptGovernor = { State, API, updateStatus };

})();
