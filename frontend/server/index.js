const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from public directory
app.use(express.static(path.join(__dirname, '../public')));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'multi-model-router-frontend',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// Mock API endpoints for development (will be replaced with FastAPI calls)
app.post('/api/generate', async (req, res) => {
  const { prompt } = req.body;

  // Simulate processing delay
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

  // Mock model selection based on prompt characteristics
  const models = [
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', color: '#10a37f' },
    { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', color: '#d97706' },
    { id: 'codellama-13b', name: 'CodeLlama 13B', color: '#7c3aed' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', color: '#10a37f' },
    { id: 'llama3-8b', name: 'Llama 3 8B', color: '#059669' }
  ];

  // Simple routing logic based on prompt content
  let selectedModel;
  if (prompt.toLowerCase().includes('code') || prompt.toLowerCase().includes('function') || prompt.toLowerCase().includes('program')) {
    selectedModel = models.find(m => m.id === 'codellama-13b');
  } else if (prompt.length > 200 || prompt.toLowerCase().includes('analyze') || prompt.toLowerCase().includes('explain')) {
    selectedModel = models.find(m => m.id === 'gpt-4-turbo');
  } else if (prompt.toLowerCase().includes('creative') || prompt.toLowerCase().includes('write')) {
    selectedModel = models.find(m => m.id === 'claude-3-sonnet');
  } else {
    selectedModel = models[Math.floor(Math.random() * 3)]; // Random selection for simple queries
  }

  // Generate mock response
  const mockResponses = [
    "This is a comprehensive response to your query. The model has analyzed your request and provided detailed information based on the available knowledge.",
    "Here's what I found regarding your question. The routing system selected this model because it specializes in this type of query.",
    "Based on your prompt, I've generated a response that addresses your specific needs. The model selection was optimized for accuracy and relevance.",
    "Your query has been processed successfully. This model was chosen for its expertise in handling similar requests efficiently."
  ];

  const response = mockResponses[Math.floor(Math.random() * mockResponses.length)];
  const cost = (Math.random() * 0.05 + 0.01).toFixed(4);
  const latency = Math.floor(Math.random() * 1000 + 500);

  res.json({
    id: `msg_${Date.now()}`,
    prompt,
    response,
    selectedModel: selectedModel.id,
    modelName: selectedModel.name,
    modelColor: selectedModel.color,
    cost: parseFloat(cost),
    latency,
    timestamp: new Date().toISOString()
  });
});

// Catch all handler - serve index.html for SPA routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Something went wrong!',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Internal server error'
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Multi-Model Router Frontend Server running on http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`💻 Development mode - Mock API responses enabled`);
});
