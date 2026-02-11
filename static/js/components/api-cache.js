/**
 * API Cache Manager for frontend performance
 * Caches API responses in memory with TTL support
 */

(function() {
    'use strict';

    class APICache {
        constructor() {
            this.cache = new Map();
            this.defaultTTL = 30000; // 30 seconds default
            
            // TTLs for different endpoints
            this.ttls = {
                'prompts': 60000,      // 1 minute
                'configs': 300000,     // 5 minutes
                'runs': 30000,         // 30 seconds
                'documents': 600000,   // 10 minutes
                'default': 30000       // 30 seconds
            };
        }
        
        /**
         * Generate cache key from endpoint and params
         */
        generateKey(endpoint, params = {}) {
            const sortedParams = Object.keys(params)
                .sort()
                .map(k => `${k}=${params[k]}`)
                .join('&');
            return sortedParams ? `${endpoint}?${sortedParams}` : endpoint;
        }
        
        /**
         * Get TTL for an endpoint
         */
        getTTL(endpoint) {
            for (const [key, ttl] of Object.entries(this.ttls)) {
                if (endpoint.includes(key)) {
                    return ttl;
                }
            }
            return this.defaultTTL;
        }
        
        /**
         * Get cached data if not expired
         */
        get(endpoint, params = {}) {
            const key = this.generateKey(endpoint, params);
            const entry = this.cache.get(key);
            
            if (!entry) {
                return null;
            }
            
            // Check if expired
            if (Date.now() > entry.expiresAt) {
                this.cache.delete(key);
                return null;
            }
            
            return entry.data;
        }
        
        /**
         * Store data in cache
         */
        set(endpoint, params = {}, data, ttl = null) {
            const key = this.generateKey(endpoint, params);
            const cacheTTL = ttl || this.getTTL(endpoint);
            
            this.cache.set(key, {
                data: data,
                expiresAt: Date.now() + cacheTTL,
                createdAt: Date.now()
            });
        }
        
        /**
         * Invalidate specific cache entry
         */
        invalidate(endpoint, params = {}) {
            const key = this.generateKey(endpoint, params);
            this.cache.delete(key);
        }
        
        /**
         * Invalidate all cache entries matching a pattern
         */
        invalidatePattern(pattern) {
            for (const key of this.cache.keys()) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        }
        
        /**
         * Invalidate all cache
         */
        invalidateAll() {
            this.cache.clear();
        }
        
        /**
         * Get cache statistics
         */
        getStats() {
            const now = Date.now();
            let valid = 0;
            let expired = 0;
            
            for (const entry of this.cache.values()) {
                if (now <= entry.expiresAt) {
                    valid++;
                } else {
                    expired++;
                }
            }
            
            return {
                total: this.cache.size,
                valid: valid,
                expired: expired
            };
        }
        
        /**
         * Clean up expired entries
         */
        cleanup() {
            const now = Date.now();
            for (const [key, entry] of this.cache.entries()) {
                if (now > entry.expiresAt) {
                    this.cache.delete(key);
                }
            }
        }
        
        /**
         * Wrap an API call with caching
         */
        async wrap(apiCall, endpoint, params = {}, options = {}) {
            const { 
                skipCache = false, 
                ttl = null,
                onUpdate = null 
            } = options;
            
            // Try to get from cache
            if (!skipCache) {
                const cached = this.get(endpoint, params);
                if (cached !== null) {
                    // If onUpdate callback provided, still make the API call
                    // but return cached data immediately
                    if (onUpdate) {
                        apiCall().then(data => {
                            this.set(endpoint, params, data, ttl);
                            onUpdate(data);
                        }).catch(() => {
                            // Silently fail background update
                        });
                    }
                    return cached;
                }
            }
            
            // Make API call
            const data = await apiCall();
            
            // Cache the result
            this.set(endpoint, params, data, ttl);
            
            return data;
        }
    }
    
    // Create global instance
    window.APICache = new APICache();
})();
