/**
 * Virtual Scrolling Manager for handling large lists efficiently
 * Only renders visible items + buffer, updates on scroll
 */

(function() {
    'use strict';

    class VirtualScroller {
        constructor(container, options = {}) {
            this.container = container;
            this.options = {
                itemHeight: options.itemHeight || 50,
                bufferSize: options.bufferSize || 5,
                renderItem: options.renderItem || this.defaultRenderItem,
                onItemClick: options.onItemClick || null,
                emptyMessage: options.emptyMessage || 'No items',
                ...options
            };
            
            this.items = [];
            this.visibleItems = new Map();
            this.scrollTop = 0;
            this.containerHeight = 0;
            
            this.init();
        }
        
        init() {
            // Create scroll container structure
            this.container.innerHTML = `
                <div class="virtual-scroll-viewport" style="position: relative; overflow: auto; height: 100%;">
                    <div class="virtual-scroll-content" style="position: relative;">
                        <div class="virtual-scroll-spacer" style="height: 0px;"></div>
                    </div>
                </div>
            `;
            
            this.viewport = this.container.querySelector('.virtual-scroll-viewport');
            this.content = this.container.querySelector('.virtual-scroll-content');
            this.spacer = this.container.querySelector('.virtual-scroll-spacer');
            
            // Bind scroll handler with throttling
            this.scrollHandler = this.throttle(this.handleScroll.bind(this), 16); // ~60fps
            this.viewport.addEventListener('scroll', this.scrollHandler);
            
            // Handle resize
            this.resizeObserver = new ResizeObserver(entries => {
                for (let entry of entries) {
                    this.containerHeight = entry.contentRect.height;
                    this.updateVisibleItems();
                }
            });
            this.resizeObserver.observe(this.viewport);
            
            // Initial container height
            this.containerHeight = this.viewport.clientHeight;
        }
        
        setItems(items) {
            this.items = items || [];
            this.updateSpacerHeight();
            this.updateVisibleItems();
        }
        
        updateSpacerHeight() {
            const totalHeight = this.items.length * this.options.itemHeight;
            this.spacer.style.height = `${totalHeight}px`;
        }
        
        handleScroll() {
            this.scrollTop = this.viewport.scrollTop;
            this.updateVisibleItems();
        }
        
        updateVisibleItems() {
            if (!this.items.length) {
                this.renderEmpty();
                return;
            }
            
            const startIndex = Math.floor(this.scrollTop / this.options.itemHeight);
            const visibleCount = Math.ceil(this.containerHeight / this.options.itemHeight);
            
            // Add buffer
            const renderStart = Math.max(0, startIndex - this.options.bufferSize);
            const renderEnd = Math.min(
                this.items.length,
                startIndex + visibleCount + this.options.bufferSize
            );
            
            // Determine which items to add/remove
            const newVisibleItems = new Map();
            
            for (let i = renderStart; i < renderEnd; i++) {
                const item = this.items[i];
                const itemId = this.getItemId(item, i);
                
                if (this.visibleItems.has(itemId)) {
                    // Reuse existing element
                    newVisibleItems.set(itemId, this.visibleItems.get(itemId));
                    this.visibleItems.delete(itemId);
                } else {
                    // Create new element
                    const element = this.createItemElement(item, i);
                    newVisibleItems.set(itemId, element);
                    this.content.appendChild(element);
                }
            }
            
            // Remove items that are no longer visible
            this.visibleItems.forEach(element => {
                element.remove();
            });
            
            this.visibleItems = newVisibleItems;
            
            // Update positions
            this.visibleItems.forEach((element, itemId) => {
                const index = parseInt(element.dataset.index);
                element.style.transform = `translateY(${index * this.options.itemHeight}px)`;
            });
        }
        
        createItemElement(item, index) {
            const element = document.createElement('div');
            element.className = 'virtual-scroll-item';
            element.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: ${this.options.itemHeight}px;
                transform: translateY(${index * this.options.itemHeight}px);
            `;
            element.dataset.index = index;
            element.dataset.id = this.getItemId(item, index);
            
            // Render content
            element.innerHTML = this.options.renderItem(item, index);
            
            // Add click handler
            if (this.options.onItemClick) {
                element.addEventListener('click', () => {
                    this.options.onItemClick(item, index);
                });
            }
            
            return element;
        }
        
        getItemId(item, index) {
            return item.id || item.uuid || `item-${index}`;
        }
        
        defaultRenderItem(item, index) {
            return `<div style="padding: 10px; border-bottom: 1px solid #eee;">
                ${item.name || item.id || `Item ${index}`}
            </div>`;
        }
        
        renderEmpty() {
            this.content.innerHTML = `
                <div class="virtual-scroll-empty" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: #999;
                    text-align: center;
                ">
                    ${this.options.emptyMessage}
                </div>
            `;
        }
        
        scrollToIndex(index) {
            const scrollTop = index * this.options.itemHeight;
            this.viewport.scrollTop = scrollTop;
        }
        
        scrollToItem(item) {
            const index = this.items.findIndex(i => this.getItemId(i) === this.getItemId(item));
            if (index !== -1) {
                this.scrollToIndex(index);
            }
        }
        
        refresh() {
            this.updateVisibleItems();
        }
        
        destroy() {
            this.viewport.removeEventListener('scroll', this.scrollHandler);
            this.resizeObserver.disconnect();
            this.container.innerHTML = '';
        }
        
        throttle(func, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        }
    }
    
    // Expose globally
    window.VirtualScroller = VirtualScroller;
})();
