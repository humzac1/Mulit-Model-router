# Multi-Model Router Frontend

A modern chat-style frontend for the Multi-Model Router system, designed to showcase intelligent AI model routing.

## Features

- **Chat Interface**: Clean, modern chat UI similar to Claude/ChatGPT
- **Model Routing Display**: Shows which AI model was selected for each response
- **Cost & Latency Tracking**: Displays real-time cost and latency information
- **Responsive Design**: Works on desktop and mobile devices
- **Mock API**: Includes mock responses for development and testing

## Quick Start

```bash
# Navigate to frontend directory
cd frontend/server

# Install dependencies
npm install

# Start development server
npm run dev

# Or start production server
npm start
```

The frontend will be available at `http://localhost:3000`

## Project Structure

```
frontend/
├── server/
│   ├── package.json      # Node.js dependencies and scripts
│   ├── index.js          # Express server with API endpoints
│   └── middleware.js     # Server middleware (future)
├── public/
│   ├── index.html        # Main HTML page
│   ├── css/
│   │   ├── styles.css    # Main styling
│   │   └── components.css # Component-specific styles
│   └── js/
│       ├── app.js        # Main application controller
│       ├── ui.js         # UI management and DOM manipulation
│       └── api.js        # API communication layer
└── README.md
```

## API Endpoints

### Mock API (Development)
- `POST /api/generate` - Generate response with model routing
- `GET /health` - Server health check

### Future FastAPI Integration
The frontend is designed to easily connect to your FastAPI backend:
```javascript
// Connect to FastAPI
await app.connectToFastAPI('http://localhost:8000');
```

## Demo Features

Try these example prompts to see different routing behaviors:

- **Simple QA**: "What is the capital of France?" → Fast/cheap model
- **Code Generation**: "Write a Python function..." → Code-specialized model
- **Complex Analysis**: "Analyze the economic impact..." → High-quality model
- **Creative Writing**: "Write a short story..." → Creative model

## Keyboard Shortcuts

- `Ctrl+K` (or `Cmd+K`): Focus input field
- `Escape`: Clear input when focused
- `Enter`: Send message
- `Shift+Enter`: New line

## Development

### Running the Demo
Open browser console and run:
```javascript
runDemo()
```

### Connecting to FastAPI
```javascript
// In browser console
await app.connectToFastAPI('http://localhost:8000')
```

## Technologies Used

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Node.js, Express.js
- **Styling**: Modern CSS with CSS Variables, Flexbox, Grid
- **Fonts**: Inter font family from Google Fonts

## Browser Support

- Chrome/Edge 88+
- Firefox 85+
- Safari 14+

## Future Enhancements

- Real-time streaming responses
- Chat history persistence
- Dark mode toggle
- Model comparison view
- Advanced routing configuration UI
- File upload support
- Voice input/output
