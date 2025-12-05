// UI Management Module
class UIManager {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.promptInput = document.getElementById('prompt-input');
        this.sendButton = document.getElementById('send-button');
        this.charCount = document.getElementById('char-count');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.welcomeMessage = document.querySelector('.welcome-message');

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateCharCount();
        this.scrollToBottom();
    }

    setupEventListeners() {
        // Input handling
        this.promptInput.addEventListener('input', () => {
            this.updateCharCount();
            this.updateSendButton();
        });

        this.promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        // Send button
        this.sendButton.addEventListener('click', () => this.handleSend());

        // Auto-resize textarea
        this.promptInput.addEventListener('input', this.autoResizeTextarea.bind(this));
    }

    updateCharCount() {
        const count = this.promptInput.value.length;
        this.charCount.textContent = count;
        this.charCount.style.color = count > 1800 ? '#ef4444' : 'var(--text-muted)';
    }

    updateSendButton() {
        const hasText = this.promptInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText;
    }

    autoResizeTextarea() {
        this.promptInput.style.height = 'auto';
        this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 200) + 'px';
    }

    async handleSend() {
        const prompt = this.promptInput.value.trim();
        if (!prompt) return;

        // Add user message
        this.addMessage('user', prompt);

        // Clear input
        this.promptInput.value = '';
        this.updateCharCount();
        this.updateSendButton();
        this.autoResizeTextarea();

        // Hide welcome message
        this.hideWelcomeMessage();

        // Show typing indicator
        this.showTypingIndicator();

        // Scroll to bottom
        this.scrollToBottom();

        // Trigger API call (handled by app.js)
        return prompt;
    }

    addMessage(type, content, metadata = {}) {
        const messageElement = this.createMessageElement(type, content, metadata);
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
        return messageElement;
    }

    createMessageElement(type, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';

        if (type === 'user') {
            avatarDiv.textContent = '👤';
        } else {
            avatarDiv.textContent = '🧠';
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        // Add content
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = content;
        bubbleDiv.appendChild(textDiv);

        // Add metadata for assistant messages
        if (type === 'assistant' && metadata.modelName) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';

            // Model indicator
            const modelIndicator = document.createElement('div');
            modelIndicator.className = 'model-indicator';
            modelIndicator.innerHTML = `
                <span class="model-indicator-dot" style="background-color: ${metadata.modelColor || '#6366f1'}"></span>
                <span>Routed to ${metadata.modelName}</span>
            `;

            // Routing info
            const routingInfo = document.createElement('div');
            routingInfo.className = 'routing-info';

            if (metadata.cost !== undefined) {
                const costInfo = document.createElement('div');
                costInfo.className = 'cost-info';
                costInfo.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    $${metadata.cost}
                `;
                routingInfo.appendChild(costInfo);
            }

            if (metadata.latency !== undefined) {
                const latencyInfo = document.createElement('div');
                latencyInfo.className = 'latency-info';
                latencyInfo.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/>
                        <path d="M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
                    </svg>
                    ${metadata.latency}ms
                `;
                routingInfo.appendChild(latencyInfo);
            }

            // Timestamp
            const timestamp = document.createElement('div');
            timestamp.className = 'timestamp';
            timestamp.textContent = new Date(metadata.timestamp || Date.now()).toLocaleTimeString();

            metaDiv.appendChild(modelIndicator);
            metaDiv.appendChild(routingInfo);
            metaDiv.appendChild(timestamp);
            bubbleDiv.appendChild(metaDiv);
        }

        contentDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        return messageDiv;
    }

    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    hideWelcomeMessage() {
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    showError(message) {
        const errorElement = this.createMessageElement('assistant', `Error: ${message}`);
        errorElement.classList.add('message-error');
        this.messagesContainer.appendChild(errorElement);
        this.scrollToBottom();
    }

    // Focus management
    focusInput() {
        this.promptInput.focus();
    }

    // Loading state management
    setLoading(loading) {
        this.sendButton.disabled = loading;
        this.promptInput.disabled = loading;

        if (loading) {
            this.sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" stroke-linecap="round">
                        <animate attributeName="stroke-dasharray" values="0,314;314,0" dur="1s" repeatCount="indefinite"/>
                    </circle>
                </svg>
            `;
        } else {
            this.sendButton.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22,2 15,22 11,13 2,9"></polygon>
                </svg>
            `;
        }
    }
}

// Export for use in other modules
window.UIManager = UIManager;
