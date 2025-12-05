// Main Application Controller
class App {
    constructor() {
        this.ui = new UIManager();
        this.api = new APIManager();
        this.isProcessing = false;

        this.init();
    }

    init() {
        console.log('🚀 Multi-Model Router Frontend initialized');

        // Check server health on startup
        this.checkServerHealth();

        // Set up global error handling
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.ui.showError('An unexpected error occurred. Please try again.');
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.ui.showError('An unexpected error occurred. Please try again.');
        });
    }

    async checkServerHealth() {
        try {
            const health = await this.api.checkHealth();
            if (health.status === 'healthy') {
                console.log('✅ Server is healthy');
            } else {
                console.warn('⚠️ Server health check returned:', health);
            }
        } catch (error) {
            console.error('❌ Server health check failed:', error);
            this.ui.showError('Unable to connect to server. Please check your connection.');
        }
    }

    async handleSendMessage(prompt) {
        if (this.isProcessing) return;

        this.isProcessing = true;
        this.ui.setLoading(true);

        try {
            // Call the API
            const result = await this.api.generateResponse(prompt);

            // Hide typing indicator
            this.ui.hideTypingIndicator();

            // Add assistant response with metadata
            this.ui.addMessage('assistant', result.response, {
                modelName: result.modelName,
                modelColor: result.modelColor,
                cost: result.cost,
                latency: result.latency,
                timestamp: result.timestamp
            });

            console.log('✅ Response generated:', {
                model: result.selectedModel,
                cost: result.cost,
                latency: result.latency
            });

        } catch (error) {
            console.error('❌ Failed to generate response:', error);
            this.ui.hideTypingIndicator();
            this.ui.showError(error.message || 'Failed to generate response. Please try again.');
        } finally {
            this.isProcessing = false;
            this.ui.setLoading(false);
            this.ui.focusInput();
        }
    }

    // Method to connect to FastAPI (for future use)
    async connectToFastAPI(fastApiUrl) {
        try {
            const connected = await this.api.connectToFastAPI(fastApiUrl);
            if (connected) {
                console.log('🔗 Connected to FastAPI successfully');
                this.api.setUseFastAPI(true);
                return true;
            } else {
                console.error('❌ Failed to connect to FastAPI');
                return false;
            }
        } catch (error) {
            console.error('❌ FastAPI connection error:', error);
            return false;
        }
    }

    // Demo method to show different routing scenarios
    async runDemo() {
        const demoPrompts = [
            "What is the capital of France?",
            "Write a Python function to calculate fibonacci numbers",
            "Analyze the economic impact of artificial intelligence on employment",
            "Explain quantum computing in simple terms",
            "Debug this JavaScript code: function add(a,b) { return a + b }"
        ];

        for (const prompt of demoPrompts) {
            await this.delay(2000); // Wait between requests
            await this.handleSendMessage(prompt);
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Global message handler for UI
window.handleSendMessage = function(prompt) {
    if (window.app) {
        window.app.handleSendMessage(prompt);
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            window.app.ui.focusInput();
        }

        // Escape to clear input
        if (e.key === 'Escape') {
            if (document.activeElement === window.app.ui.promptInput) {
                window.app.ui.promptInput.value = '';
                window.app.ui.updateCharCount();
                window.app.ui.updateSendButton();
            }
        }
    });

    // Add demo button functionality (can be triggered from console)
    window.runDemo = () => {
        if (window.app) {
            window.app.runDemo();
        }
    };

    console.log('💡 Tips:');
    console.log('- Press Ctrl+K to focus input');
    console.log('- Press Escape to clear input when focused');
    console.log('- Run runDemo() in console to see routing examples');
});
