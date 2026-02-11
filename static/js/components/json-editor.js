/**
 * JSON Editor Component
 * Phase D4: JSON Editor Component - Reusable JSON editing with validation
 * 
 * Features:
 * - Line numbers with synchronized scrolling
 * - Real-time JSON validation with error indicators
 * - Format/Compact actions
 * - Status indicator and character count
 * - Performant for large files
 */

(function() {
    'use strict';

    /**
     * JSONEditor Component
     * @class
     */
    class JSONEditor {
        /**
         * Create a JSONEditor instance
         * @param {string} containerId - ID of the container element
         * @param {Object} options - Editor options
         * @param {boolean} [options.readOnly=false] - Whether the editor is read-only
         * @param {boolean} [options.lineNumbers=true] - Show line numbers
         * @param {string} [options.height='400px'] - Editor height (CSS value)
         * @param {Function} [options.onChange] - Callback when content changes
         * @param {Function} [options.onValidation] - Callback with validation status
         * @param {number} [options.maxFileSize=10485760] - Max file size in bytes (10MB default)
         */
        constructor(containerId, options = {}) {
            this.containerId = containerId;
            this.container = document.getElementById(containerId);
            
            if (!this.container) {
                throw new Error(`JSONEditor: Container with id "${containerId}" not found`);
            }

            // Default options
            this.options = {
                readOnly: false,
                lineNumbers: true,
                height: '400px',
                maxFileSize: 10485760, // 10MB
                ...options
            };

            // State
            this.state = {
                isValid: true,
                errorMessage: null,
                errorLine: null,
                charCount: 0,
                lineCount: 1,
                currentLine: 1,
                lastValidValue: null
            };

            // Debounced validation
            this.validateTimeout = null;
            
            // Initialize
            this.init();
        }

        /**
         * Initialize the editor
         * @private
         */
        init() {
            this.createDOM();
            this.attachEventListeners();
            this.updateLineNumbers();
            this.updateStatus();
            this.updateCharCount();
        }

        /**
         * Create the editor DOM structure
         * @private
         */
        createDOM() {
            const id = this.containerId;
            
            this.container.className = 'json-editor-wrapper';
            this.container.innerHTML = `
                <div class="json-editor-toolbar">
                    <div class="toolbar-left">
                        <button type="button" class="btn btn-small" id="${id}-format-btn" title="Format JSON">
                            <span class="btn-icon">✨</span> Format
                        </button>
                        <button type="button" class="btn btn-small" id="${id}-compact-btn" title="Compact JSON">
                            <span class="btn-icon">📦</span> Compact
                        </button>
                    </div>
                    <div class="toolbar-right">
                        <span class="json-status-indicator" id="${id}-status">
                            <span class="status-dot valid"></span>
                            <span class="status-text">Valid JSON</span>
                        </span>
                        <span class="char-count" id="${id}-chars">0 chars</span>
                    </div>
                </div>
                <div class="json-editor-main" style="height: ${this.options.height}">
                    ${this.options.lineNumbers ? `
                    <div class="line-numbers-container">
                        <div class="line-numbers" id="${id}-line-numbers">1</div>
                    </div>
                    ` : ''}
                    <div class="editor-textarea-wrapper">
                        <textarea 
                            id="${id}-textarea"
                            class="json-textarea"
                            ${this.options.readOnly ? 'readonly' : ''}
                            spellcheck="false"
                            autocomplete="off"
                            autocapitalize="off"
                            placeholder="Enter JSON here..."
                        ></textarea>
                        ${this.options.lineNumbers ? `
                        <div class="error-tooltip" id="${id}-error-tooltip"></div>
                        ` : ''}
                    </div>
                </div>
                <div class="json-editor-footer">
                    <span class="line-count" id="${id}-lines">Line 1 of 1</span>
                </div>
            `;

            // Cache DOM references
            this.elements = {
                textarea: document.getElementById(`${id}-textarea`),
                lineNumbers: document.getElementById(`${id}-line-numbers`),
                status: document.getElementById(`${id}-status`),
                chars: document.getElementById(`${id}-chars`),
                lines: document.getElementById(`${id}-lines`),
                formatBtn: document.getElementById(`${id}-format-btn`),
                compactBtn: document.getElementById(`${id}-compact-btn`),
                errorTooltip: document.getElementById(`${id}-error-tooltip`)
            };
        }

        /**
         * Attach event listeners
         * @private
         */
        attachEventListeners() {
            const { textarea, lineNumbers, formatBtn, compactBtn } = this.elements;

            // Text input - debounced validation
            textarea.addEventListener('input', (e) => {
                this.handleInput(e);
            });

            // Scroll synchronization
            if (lineNumbers) {
                textarea.addEventListener('scroll', () => {
                    lineNumbers.scrollTop = textarea.scrollTop;
                });
            }

            // Keydown handling for special keys
            textarea.addEventListener('keydown', (e) => {
                this.handleKeydown(e);
            });

            // Cursor position tracking
            textarea.addEventListener('click', () => this.updateCurrentLine());
            textarea.addEventListener('keyup', () => this.updateCurrentLine());

            // Toolbar buttons
            if (formatBtn) {
                formatBtn.addEventListener('click', () => this.format());
            }
            if (compactBtn) {
                compactBtn.addEventListener('click', () => this.compact());
            }

            // Window resize for line numbers
            window.addEventListener('resize', () => {
                if (lineNumbers) {
                    this.updateLineNumbers();
                }
            });
        }

        /**
         * Handle input events
         * @private
         */
        handleInput(e) {
            this.updateCharCount();
            this.updateLineNumbers();
            this.updateCurrentLine();
            
            // Debounced validation
            clearTimeout(this.validateTimeout);
            this.validateTimeout = setTimeout(() => {
                this.validate();
            }, 300);

            // Trigger onChange callback
            if (this.options.onChange) {
                this.options.onChange(this.getValue());
            }
        }

        /**
         * Handle special key combinations
         * @private
         */
        handleKeydown(e) {
            // Tab key - insert spaces instead of changing focus
            if (e.key === 'Tab' && !this.options.readOnly) {
                e.preventDefault();
                this.insertText('  ');
            }

            // Auto-indent on Enter
            if (e.key === 'Enter' && !this.options.readOnly) {
                e.preventDefault();
                this.handleEnter();
            }
        }

        /**
         * Insert text at cursor position
         * @private
         */
        insertText(text) {
            const textarea = this.elements.textarea;
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const value = textarea.value;

            textarea.value = value.substring(0, start) + text + value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + text.length;
            textarea.focus();
            
            this.handleInput();
        }

        /**
         * Handle Enter key with auto-indent
         * @private
         */
        handleEnter() {
            const textarea = this.elements.textarea;
            const start = textarea.selectionStart;
            const value = textarea.value;
            
            // Find current line
            const lineStart = value.lastIndexOf('\n', start - 1) + 1;
            const currentLine = value.substring(lineStart, start);
            
            // Calculate indentation
            const indentMatch = currentLine.match(/^[\s]*/);
            const currentIndent = indentMatch ? indentMatch[0] : '';
            
            // Check if we need extra indent (after { or [)
            const trimmedLine = currentLine.trim();
            const lastChar = trimmedLine.charAt(trimmedLine.length - 1);
            const extraIndent = (lastChar === '{' || lastChar === '[') ? '  ' : '';
            
            // Insert newline with indentation
            const insertText = '\n' + currentIndent + extraIndent;
            this.insertText(insertText);
            
            // If we added extra indent and the next char is } or ], add closing indent
            const nextChar = value.charAt(start);
            if (extraIndent && (nextChar === '}' || nextChar === ']')) {
                const cursorPos = textarea.selectionStart;
                textarea.value = textarea.value.substring(0, cursorPos) + '\n' + currentIndent + textarea.value.substring(cursorPos);
                textarea.selectionStart = textarea.selectionEnd = cursorPos;
                textarea.focus();
            }
        }

        /**
         * Update line numbers display
         * @private
         */
        updateLineNumbers() {
            if (!this.options.lineNumbers || !this.elements.lineNumbers) return;

            const { textarea, lineNumbers } = this.elements;
            const lines = textarea.value.split('\n');
            const lineCount = lines.length;

            // Limit for very large files
            const maxLines = 100000;
            if (lineCount > maxLines) {
                console.warn(`JSONEditor: File has ${lineCount} lines, showing first ${maxLines}`);
            }

            // Generate line numbers HTML
            let lineNumbersHTML = '';
            const displayCount = Math.min(lineCount, maxLines);
            
            for (let i = 1; i <= displayCount; i++) {
                const isCurrent = i === this.state.currentLine;
                lineNumbersHTML += `<div class="line-number ${isCurrent ? 'current' : ''}" data-line="${i}">${i}</div>`;
            }

            // Calculate line height based on textarea
            const computedStyle = window.getComputedStyle(textarea);
            const lineHeight = parseInt(computedStyle.lineHeight) || 21;
            
            lineNumbers.innerHTML = lineNumbersHTML;
            lineNumbers.style.lineHeight = `${lineHeight}px`;

            // Update state
            this.state.lineCount = lineCount;
            this.updateLineCount();
        }

        /**
         * Update current line tracking
         * @private
         */
        updateCurrentLine() {
            const { textarea } = this.elements;
            const cursorPosition = textarea.selectionStart;
            const textBeforeCursor = textarea.value.substring(0, cursorPosition);
            const currentLine = textBeforeCursor.split('\n').length;

            if (currentLine !== this.state.currentLine) {
                this.state.currentLine = currentLine;
                this.highlightCurrentLine();
                this.updateLineCount();
            }
        }

        /**
         * Highlight the current line number
         * @private
         */
        highlightCurrentLine() {
            if (!this.elements.lineNumbers) return;

            const lineNumberElements = this.elements.lineNumbers.querySelectorAll('.line-number');
            lineNumberElements.forEach(el => {
                const line = parseInt(el.dataset.line);
                el.classList.toggle('current', line === this.state.currentLine);
            });
        }

        /**
         * Update line count display
         * @private
         */
        updateLineCount() {
            if (this.elements.lines) {
                this.elements.lines.textContent = `Line ${this.state.currentLine} of ${this.state.lineCount}`;
            }
        }

        /**
         * Update character count display
         * @private
         */
        updateCharCount() {
            const count = this.elements.textarea.value.length;
            this.state.charCount = count;
            
            // Format large numbers
            let displayCount;
            if (count >= 1000000) {
                displayCount = (count / 1000000).toFixed(1) + 'M';
            } else if (count >= 1000) {
                displayCount = (count / 1000).toFixed(1) + 'K';
            } else {
                displayCount = count.toString();
            }
            
            if (this.elements.chars) {
                this.elements.chars.textContent = `${displayCount} chars`;
            }
        }

        /**
         * Validate JSON in real-time
         * @returns {Object} Validation result { isValid, error, line }
         */
        validate() {
            const value = this.elements.textarea.value.trim();

            if (!value) {
                this.state.isValid = true;
                this.state.errorMessage = null;
                this.state.errorLine = null;
                this.updateStatus();
                this.clearErrorIndicators();
                
                if (this.options.onValidation) {
                    this.options.onValidation({ isValid: true });
                }
                
                return { isValid: true };
            }

            // Check file size
            if (value.length > this.options.maxFileSize) {
                this.state.isValid = false;
                this.state.errorMessage = `File exceeds maximum size of ${this.formatBytes(this.options.maxFileSize)}`;
                this.state.errorLine = null;
                this.updateStatus();
                
                if (this.options.onValidation) {
                    this.options.onValidation({ isValid: false, error: this.state.errorMessage });
                }
                
                return { isValid: false, error: this.state.errorMessage };
            }

            try {
                JSON.parse(value);
                
                this.state.isValid = true;
                this.state.errorMessage = null;
                this.state.errorLine = null;
                this.state.lastValidValue = value;
                
                this.updateStatus();
                this.clearErrorIndicators();
                
                if (this.options.onValidation) {
                    this.options.onValidation({ isValid: true });
                }
                
                return { isValid: true };
                
            } catch (error) {
                // Parse error line from message
                const lineMatch = error.message.match(/line\s*(\d+)/i);
                const errorLine = lineMatch ? parseInt(lineMatch[1]) : null;
                
                this.state.isValid = false;
                this.state.errorMessage = error.message;
                this.state.errorLine = errorLine;
                
                this.updateStatus();
                this.showErrorIndicator(errorLine, error.message);
                
                if (this.options.onValidation) {
                    this.options.onValidation({ 
                        isValid: false, 
                        error: error.message,
                        line: errorLine 
                    });
                }
                
                return { isValid: false, error: error.message, line: errorLine };
            }
        }

        /**
         * Check if current content is valid JSON
         * @returns {boolean}
         */
        isValid() {
            return this.state.isValid;
        }

        /**
         * Show error indicator on a specific line
         * @private
         */
        showErrorIndicator(line, message) {
            if (!this.elements.lineNumbers || !line) return;

            const lineElement = this.elements.lineNumbers.querySelector(`[data-line="${line}"]`);
            if (lineElement) {
                lineElement.classList.add('error');
                lineElement.setAttribute('title', message);
                
                // Show tooltip
                if (this.elements.errorTooltip) {
                    this.elements.errorTooltip.textContent = message;
                    this.elements.errorTooltip.style.display = 'block';
                    
                    // Position tooltip
                    const lineHeight = 21; // Approximate line height
                    const scrollOffset = this.elements.textarea.scrollTop;
                    const top = ((line - 1) * lineHeight) - scrollOffset + 5;
                    this.elements.errorTooltip.style.top = `${top}px`;
                }
            }
        }

        /**
         * Clear all error indicators
         * @private
         */
        clearErrorIndicators() {
            if (!this.elements.lineNumbers) return;

            const errorElements = this.elements.lineNumbers.querySelectorAll('.line-number.error');
            errorElements.forEach(el => {
                el.classList.remove('error');
                el.removeAttribute('title');
            });

            if (this.elements.errorTooltip) {
                this.elements.errorTooltip.style.display = 'none';
            }
        }

        /**
         * Update status indicator
         * @private
         */
        updateStatus() {
            if (!this.elements.status) return;

            const statusDot = this.elements.status.querySelector('.status-dot');
            const statusText = this.elements.status.querySelector('.status-text');

            if (this.state.isValid) {
                statusDot.className = 'status-dot valid';
                statusText.textContent = 'Valid JSON';
                this.elements.status.classList.remove('invalid');
            } else {
                statusDot.className = 'status-dot invalid';
                statusText.textContent = 'Invalid JSON';
                this.elements.status.classList.add('invalid');
            }
        }

        /**
         * Format JSON with pretty printing
         */
        format() {
            const value = this.elements.textarea.value.trim();
            
            if (!value) return;

            try {
                const parsed = JSON.parse(value);
                const formatted = JSON.stringify(parsed, null, 2);
                this.elements.textarea.value = formatted;
                
                this.updateLineNumbers();
                this.updateCharCount();
                this.validate();
                
                // Show success feedback
                this.showActionFeedback('Formatted');
                
            } catch (error) {
                // Invalid JSON, can't format
                this.showActionFeedback('Cannot format invalid JSON', 'error');
            }
        }

        /**
         * Compact JSON (minify)
         */
        compact() {
            const value = this.elements.textarea.value.trim();
            
            if (!value) return;

            try {
                const parsed = JSON.parse(value);
                const compacted = JSON.stringify(parsed);
                this.elements.textarea.value = compacted;
                
                this.updateLineNumbers();
                this.updateCharCount();
                this.validate();
                
                // Show success feedback
                this.showActionFeedback('Compacted');
                
            } catch (error) {
                // Invalid JSON, can't compact
                this.showActionFeedback('Cannot compact invalid JSON', 'error');
            }
        }

        /**
         * Show action feedback
         * @private
         */
        showActionFeedback(message, type = 'success') {
            const feedback = document.createElement('div');
            feedback.className = `editor-feedback ${type}`;
            feedback.textContent = message;
            
            this.container.appendChild(feedback);
            
            setTimeout(() => {
                feedback.classList.add('show');
            }, 10);
            
            setTimeout(() => {
                feedback.classList.remove('show');
                setTimeout(() => feedback.remove(), 200);
            }, 1500);
        }

        /**
         * Set editor value
         * @param {*} json - JSON value (object, array, or string)
         */
        setValue(json) {
            let value;
            
            if (typeof json === 'string') {
                value = json;
            } else {
                value = JSON.stringify(json, null, 2);
            }

            // Check size before setting
            if (value.length > this.options.maxFileSize) {
                console.warn('JSONEditor: Value exceeds max file size');
                // Truncate with warning
                value = value.substring(0, this.options.maxFileSize);
            }

            this.elements.textarea.value = value;
            this.handleInput();
            this.validate();
        }

        /**
         * Get editor value
         * @returns {string} Raw text content
         */
        getValue() {
            return this.elements.textarea.value;
        }

        /**
         * Get parsed JSON value
         * @returns {*} Parsed JSON or null if invalid
         */
        getParsedValue() {
            const value = this.getValue().trim();
            if (!value) return null;
            
            try {
                return JSON.parse(value);
            } catch (error) {
                return null;
            }
        }

        /**
         * Get editor state
         * @returns {Object} Current state
         */
        getState() {
            return { ...this.state };
        }

        /**
         * Enable/disable read-only mode
         * @param {boolean} readOnly
         */
        setReadOnly(readOnly) {
            this.options.readOnly = readOnly;
            this.elements.textarea.readOnly = readOnly;
            this.container.classList.toggle('read-only', readOnly);
        }

        /**
         * Focus the editor
         */
        focus() {
            this.elements.textarea.focus();
        }

        /**
         * Clear the editor
         */
        clear() {
            this.elements.textarea.value = '';
            this.handleInput();
        }

        /**
         * Destroy the editor instance
         */
        destroy() {
            // Clear timeouts
            clearTimeout(this.validateTimeout);
            
            // Remove event listeners (simplified - in production, use named functions)
            this.container.innerHTML = '';
            this.container.className = '';
        }

        /**
         * Format bytes to human readable
         * @private
         */
        formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }
    }

    // Make available globally
    window.JSONEditor = JSONEditor;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = JSONEditor;
    }

})();
