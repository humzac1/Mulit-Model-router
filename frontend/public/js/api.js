// API Communication Module
class APIManager {
    constructor(baseURL = '') {
        this.baseURL = baseURL || window.location.origin;
    }

    async generateResponse(prompt) {
        try {
            const response = await fetch(`${this.baseURL}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    user_id: this.getUserId(),
                    session_id: this.getSessionId(),
                    temperature: 0.7,
                    max_tokens: 1000
                })
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            return {
                id: data.id,
                prompt: data.prompt,
                response: data.response,
                selectedModel: data.selectedModel,
                modelName: data.modelName,
                modelColor: data.modelColor,
                cost: data.cost,
                latency: data.latency,
                timestamp: data.timestamp
            };
        } catch (error) {
            console.error('API Error:', error);
            throw new Error(`Failed to generate response: ${error.message}`);
        }
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            if (!response.ok) {
                throw new Error(`Health check failed: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unhealthy', error: error.message };
        }
    }

    // Generate or retrieve user ID (simple implementation)
    getUserId() {
        let userId = localStorage.getItem('mmr_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('mmr_user_id', userId);
        }
        return userId;
    }

    // Generate or retrieve session ID
    getSessionId() {
        let sessionId = sessionStorage.getItem('mmr_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('mmr_session_id', sessionId);
        }
        return sessionId;
    }

    // Future methods for connecting to FastAPI
    async connectToFastAPI(fastApiUrl) {
        this.fastApiURL = fastApiUrl;
        // Test connection
        try {
            const health = await this.checkFastAPIHealth();
            console.log('Connected to FastAPI:', health);
            return true;
        } catch (error) {
            console.error('Failed to connect to FastAPI:', error);
            return false;
        }
    }

    async checkFastAPIHealth() {
        if (!this.fastApiURL) return null;

        try {
            const response = await fetch(`${this.fastApiURL}/health`);
            if (!response.ok) throw new Error(`FastAPI health check failed: ${response.status}`);
            return await response.json();
        } catch (error) {
            throw new Error(`FastAPI connection failed: ${error.message}`);
        }
    }

    // Method to switch between mock API and real FastAPI
    setUseFastAPI(useFastAPI = false) {
        this.useFastAPI = useFastAPI;
        if (useFastAPI && !this.fastApiURL) {
            console.warn('FastAPI URL not set. Use connectToFastAPI() first.');
        }
    }
}

// Export for use in other modules
window.APIManager = APIManager;
