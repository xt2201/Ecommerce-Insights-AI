# E-Commerce Agent Backend (Node.js + TypeScript)

Backend API cho Amazon Smart Shopping Assistant được xây dựng với Node.js, Express, và TypeScript.

## Tính năng

- 🤖 Multi-agent workflow với 4 agents:
  - **Planning Agent**: Phân tích query và tạo search plan
  - **Collection Agent**: Thu thập dữ liệu từ SerpAPI
  - **Analysis Agent**: Phân tích và so sánh sản phẩm
  - **Response Agent**: Tạo recommendations cho user

- 🔌 RESTful API endpoints
- 🌐 CORS enabled cho frontend integration
- 🔑 Environment-based configuration
- 🚀 TypeScript cho type safety
- ⚡ Fast development với tsx

## Prerequisites

- Node.js 18+ (khuyến nghị 20+)
- npm hoặc yarn
- SerpAPI API key
- Google Gemini API key

## Cài đặt

```bash
# Cài đặt dependencies
npm install

# Tạo file .env từ template
cp .env.example .env

# Chỉnh sửa .env với API keys của bạn
# PORT=4000
# SERPAPI_API_KEY=your_serpapi_key
# GOOGLE_API_KEY=your_google_gemini_key
```

## Development

```bash
# Chạy development server với hot reload
npm run dev
```

Server sẽ chạy tại `http://localhost:4000`

## Production

```bash
# Build TypeScript code
npm run build

# Start production server
npm start
```

## API Endpoints

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2025-01-20T10:00:00.000Z"
}
```

### Shopping Search
```bash
POST /api/shopping/search
Content-Type: application/json

{
  "query": "Find me budget wireless earbuds under $100"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "summary": "...",
    "recommendations": [...],
    "analysis": {...},
    "raw_products": [...]
  },
  "debug_notes": [...],
  "llm_usage": [...]
}
```

## Project Structure

```
backend/
├── ai_server/
│   ├── agents/              # AI agents
│   │   ├── planning-agent.ts
│   │   ├── collection-agent.ts
│   │   ├── analysis-agent.ts
│   │   ├── response-agent.ts
│   │   └── index.ts
│   ├── clients/             # External API clients
│   │   ├── serpapi.ts
│   │   └── gemini.ts
│   ├── utils/               # Helper functions
│   │   └── helpers.ts
│   ├── config.ts            # Configuration
│   ├── types.ts             # TypeScript types
│   └── server.ts            # Express server
├── dist/                    # Compiled JavaScript (generated)
├── package.json
├── tsconfig.json
└── README.md
```

## Testing API với curl

```bash
# Health check
curl http://localhost:4000/health

# Shopping search
curl -X POST http://localhost:4000/api/shopping/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Find me budget wireless earbuds under $100"}'
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | Server port (default: 4000) |
| `SERPAPI_API_KEY` | Yes | SerpAPI key cho Amazon searches |
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |

## Troubleshooting

### Port already in use
```bash
# Tìm process đang dùng port 4000
lsof -i :4000

# Kill process
kill -9 <PID>
```

### API key errors
- Kiểm tra file `.env` có tồn tại và chứa đúng keys
- Đảm bảo không có spaces xung quanh `=` trong `.env`
- Restart server sau khi thay đổi `.env`

## Next Steps

- [ ] Add request validation với Zod
- [ ] Implement rate limiting
- [ ] Add logging middleware
- [ ] Add unit tests
- [ ] Add API documentation với Swagger
- [ ] Implement caching layer
