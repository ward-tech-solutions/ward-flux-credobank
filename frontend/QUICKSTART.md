# WARD FLUX Modern UI - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Backend API running on `localhost:5001`

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will open at [http://localhost:3000](http://localhost:3000)

## 🔐 Login

**Demo Credentials:**
- Username: `admin`
- Password: `admin`

## 📱 Features Overview

### Dashboard
- View network statistics
- Monitor device status
- Analyze trends with charts
- Quick action shortcuts

### Discovery
- Scan network for devices
- Create automated discovery rules
- Import discovered devices
- Schedule periodic scans

### Devices
- Manage all network devices
- Grid/List view toggle
- Search and filter
- Add/Edit/Delete operations

### Device Details
- Comprehensive device information
- Real-time metrics and charts
- Configuration management
- Alert history

## 🛠 Development

### Available Scripts

```bash
# Development server with HMR
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Project Structure

```
src/
├── components/
│   ├── layout/          # Main layout components
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Layout.tsx
│   └── ui/              # Reusable UI components
│       ├── Button.tsx
│       ├── Card.tsx
│       ├── Input.tsx
│       ├── Badge.tsx
│       ├── Modal.tsx
│       ├── Table.tsx
│       └── Loading.tsx
├── pages/               # Page components
│   ├── Dashboard.tsx    ✅ Complete
│   ├── Discovery.tsx    ✅ Complete
│   ├── Devices.tsx      ✅ Complete
│   ├── DeviceDetails.tsx ✅ Complete
│   ├── Login.tsx        ✅ Complete
│   ├── Topology.tsx     🚧 Placeholder
│   ├── Diagnostics.tsx  🚧 Placeholder
│   ├── Reports.tsx      🚧 Placeholder
│   ├── Users.tsx        🚧 Placeholder
│   ├── Settings.tsx     🚧 Placeholder
│   └── Config.tsx       🚧 Placeholder
├── services/
│   └── api.ts           # API client
├── types/
│   └── index.ts         # TypeScript types
├── hooks/
│   └── useWebSocket.ts  # WebSocket hook
└── lib/
    └── utils.ts         # Utility functions
```

## 🎨 Theming

WARD brand colors are configured in `tailwind.config.js`:

```javascript
colors: {
  ward: {
    green: '#5EBBA8',
    'green-light': '#72CFB8',
    'green-dark': '#4A9D8A',
    // ...
  }
}
```

Use them in components:
```tsx
<button className="bg-ward-green hover:bg-ward-green-dark">
  Click me
</button>
```

## 🔌 API Integration

The app connects to FastAPI backend via proxy configuration in `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5001',
      changeOrigin: true,
    },
  },
}
```

All API calls are in `src/services/api.ts`:

```typescript
import { devicesAPI, discoveryAPI, authAPI } from '@/services/api'

// Example usage
const { data } = await devicesAPI.getAll()
```

## 📊 State Management

Using React Query for server state:

```tsx
import { useQuery, useMutation } from '@tanstack/react-query'

// Fetch data
const { data, isLoading } = useQuery({
  queryKey: ['devices'],
  queryFn: () => devicesAPI.getAll(),
})

// Mutate data
const mutation = useMutation({
  mutationFn: devicesAPI.create,
  onSuccess: () => {
    // Invalidate and refetch
    queryClient.invalidateQueries({ queryKey: ['devices'] })
  },
})
```

## 🎭 Adding New Pages

1. Create page component in `src/pages/`:
```tsx
// src/pages/MyPage.tsx
export default function MyPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">My Page</h1>
      {/* Your content */}
    </div>
  )
}
```

2. Add route in `src/App.tsx`:
```tsx
<Route path="mypage" element={<MyPage />} />
```

3. Add navigation in `src/components/layout/Sidebar.tsx`:
```tsx
{ name: 'My Page', href: '/mypage', icon: MyIcon }
```

## 🐛 Debugging

### Check API Connection
```bash
# Ensure backend is running
curl http://localhost:5001/api/v1/health
```

### Check Browser Console
- Open DevTools (F12)
- Look for network errors
- Check React Query DevTools (bottom-left icon)

### Common Issues

**API calls fail:**
- Ensure backend is running on port 5001
- Check CORS configuration
- Verify authentication token

**Styles not loading:**
- Clear browser cache
- Rebuild: `npm run build`
- Check Tailwind config

**TypeScript errors:**
- Run `npm run type-check`
- Check `src/types/index.ts` for missing types

## 📦 Building for Production

```bash
# Build optimized bundle
npm run build

# Output in dist/ folder
# Serve with any static file server
```

Deploy the `dist/` folder to:
- Nginx
- Apache
- Vercel
- Netlify
- AWS S3 + CloudFront

## 🔄 Next Steps

1. **Connect Real Data**: Link charts to actual backend metrics
2. **WebSocket**: Enable real-time updates
3. **Topology**: Implement network visualization
4. **Diagnostics**: Add ping/traceroute tools
5. **Reports**: Build analytics dashboard
6. **Testing**: Add unit and integration tests

## 📚 Resources

- [React Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [React Query](https://tanstack.com/query/latest)
- [Framer Motion](https://www.framer.com/motion)

---

**Happy Coding! 🚀**

Need help? Check the main README or reach out to the team.
