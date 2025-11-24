# E-Commerce Agent Frontend (Next.js)

Modern web interface cho Amazon Smart Shopping Assistant được xây dựng với Next.js 14, React, và Tailwind CSS.

## ✨ Features

- 🎨 Modern UI với Tailwind CSS
- ⚡ Real-time search với loading states
- 🎯 AI-powered recommendations
- 📱 Responsive design (mobile-friendly)
- 🔍 Product cards với ratings & prices
- 🎭 Error handling & validation
- 🚀 Next.js 14 App Router
- 💪 TypeScript cho type safety

## 📋 Prerequisites

- Node.js 18+ (khuyến nghị 20+)
- npm hoặc yarn
- Backend API đang chạy tại `http://localhost:4000`

## 🚀 Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Edit .env.local với API URL của bạn
# NEXT_PUBLIC_API_URL=http://localhost:4000
```

## 🔧 Development

```bash
# Start development server
npm run dev
```

Frontend sẽ chạy tại `http://localhost:3000`

## 🏗️ Build for Production

```bash
# Build optimized production bundle
npm run build

# Start production server
npm start
```

## 📁 Project Structure

```
frontend/
├── ai_server/
│   ├── app/                   # Next.js 14 app router
│   │   ├── page.tsx          # Home page
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Global styles
│   ├── components/            # React components
│   │   ├── SearchForm.tsx    # Search input
│   │   ├── ProductCard.tsx   # Product display
│   │   ├── LoadingState.tsx  # Loading spinner
│   │   ├── ErrorMessage.tsx  # Error display
│   │   └── ResultsSection.tsx # Results layout
│   ├── lib/                   # Utilities
│   │   └── api.ts            # API client
│   └── types/                 # TypeScript types
│       └── index.ts
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.mjs
```

## 🎨 Components

### SearchForm
- Input field với suggestions
- Quick search buttons
- Loading state handling

### ProductCard
- Product title & image
- Price display
- Rating stars
- Review count
- Amazon link
- ASIN badge

### ResultsSection
- AI summary
- Top 3 recommendations
- Analysis highlights (cheapest, highest rated, best value)
- Noteworthy insights
- All products grid

### LoadingState
- Animated spinner
- Loading message

### ErrorMessage
- Error icon
- Error description
- User-friendly messaging

## 🌐 API Integration

Frontend giao tiếp với backend qua REST API:

```typescript
// Search products
POST http://localhost:4000/api/shopping/search
{
  "query": "wireless earbuds under $100"
}

// Health check
GET http://localhost:4000/health
```

## 🎨 Styling

- **Tailwind CSS** cho utility-first styling
- **Lucide React** cho icons
- Responsive breakpoints:
  - Mobile: < 768px
  - Tablet: 768px - 1024px
  - Desktop: > 1024px

## 🔑 Environment Variables

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:4000
```

## 🧪 Testing

```bash
# Run linter
npm run lint

# Type checking
npx tsc --noEmit
```

## 📦 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL
```

### Netlify

```bash
# Build
npm run build

# Deploy dist folder
netlify deploy --prod
```

### Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🐛 Troubleshooting

### Backend connection failed
- Kiểm tra backend có chạy tại `http://localhost:4000`
- Verify `NEXT_PUBLIC_API_URL` trong `.env.local`
- Check CORS settings trong backend

### Port 3000 already in use
```bash
# Find process
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 npm run dev
```

### Build errors
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

## 🎯 Usage Examples

### Basic Search
1. Mở `http://localhost:3000`
2. Nhập query: "wireless earbuds under $100"
3. Click search hoặc nhấn Enter
4. Xem kết quả với AI recommendations

### Quick Search
1. Click vào suggestion buttons
2. Kết quả hiển thị ngay lập tức

### View Product Details
1. Click "Xem trên Amazon" trên product card
2. Mở sản phẩm trên Amazon trong tab mới

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs)
- [Lucide Icons](https://lucide.dev)

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License

---

Built with ❤️ using Next.js, React, and Tailwind CSS
