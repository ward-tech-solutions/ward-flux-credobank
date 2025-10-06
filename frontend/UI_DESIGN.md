# 🎨 WARD FLUX - Modern UI/UX Design System

## Brand Identity (Preserved!)

### Colors
```
WARD Green (Primary): #5EBBA8  ✅
WARD Green Light:     #72CFB8  ✅  
WARD Green Dark:      #4A9D8A  ✅
WARD Silver:          #DFDFDF  ✅
WARD Dark:            #2C3E50  ✅
WARD Darker:          #1A252F  ✅
```

### Logos
- `logo-ward.svg` - Main logo (header)
- `favicon.svg` - Browser tab icon

### Typography
- **Font**: Roboto (300, 400, 500, 600, 700, 900)
- **Base size**: 16px
- **Headings**: Bold (700)
- **Body**: Regular (400)

---

## Modern Design Principles

### 1. **Glassmorphism** (Subtle backdrop blur)
```css
background: rgba(255, 255, 255, 0.95);
backdrop-filter: blur(10px);
border: 1px solid rgba(94, 187, 168, 0.2);
```

### 2. **Soft Shadows** (WARD-branded)
```css
shadow-ward: 0 4px 6px rgba(94, 187, 168, 0.1);
shadow-ward-lg: 0 10px 15px rgba(94, 187, 168, 0.1);
```

### 3. **Smooth Animations**
```
- Page transitions: 300ms ease-out
- Hover effects: 200ms ease
- Click feedback: scale(0.95)
- Loading states: Skeleton screens
```

### 4. **Rounded Corners**
```
- Cards: 12px
- Buttons: 8px
- Inputs: 6px
- Modals: 16px
```

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [WARD Logo]    🔍 Global Search     👤 Profile  🔔 🌙     │
├──────┬──────────────────────────────────────────────────────┤
│      │                                                       │
│  📊  │  📊 DASHBOARD                                        │
│  📡  │  ┌──────┬──────┬──────┬──────┐                      │
│  🔍  │  │ 342  │ 98.5%│  12  │ 2.4TB│  Stat Cards         │
│  ⚙️  │  │Devs  │Uptime│Alerts│Traf  │                      │
│  👥  │  └──────┴──────┴──────┴──────┘                      │
│  📈  │                                                       │
│      │  ┌─────────────────┬──────────────────┐            │
│  🌙  │  │ Device Health   │ Recent Alerts    │            │
│      │  │ (Area Chart)    │ (Timeline)       │            │
│      │  └─────────────────┴──────────────────┘            │
│      │                                                       │
│      │  ┌────────────────────────────────────────┐        │
│      │  │ Network Topology (Interactive D3.js)   │        │
│      │  └────────────────────────────────────────┘        │
└──────┴──────────────────────────────────────────────────────┘
```

---

## Page Designs

### 1. Dashboard (Home)

**Stats Cards** (Top Row)
```
┌──────────────────┐  ┌──────────────────┐
│ 📡 Total Devices │  │ ✅ Uptime        │
│                  │  │                  │
│      342         │  │     98.5%        │
│  ↑ 12 this week  │  │  ↑ 0.3% vs last  │
└──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐
│ ⚠️ Active Alerts │  │ 📊 Traffic       │
│                  │  │                  │
│       12         │  │    2.4 TB        │
│  ↓ 5 vs yesterday│  │  ↑ 15% vs last   │
└──────────────────┘  └──────────────────┘
```

**Charts Section**
- Device Health Timeline (Area chart, WARD green gradient)
- Alert Frequency (Bar chart)
- Top Devices by Traffic (Horizontal bar)
- Network Latency Heatmap

### 2. Discovery (NEW!)

```
┌─────────────────────────────────────────────────┐
│  🔍 Network Discovery                           │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────────────────────────────┐       │
│  │ ⚡ Quick Scan                        │       │
│  │                                      │       │
│  │ Network Range:                       │       │
│  │ [192.168.1.0/24        🔽]          │       │
│  │                                      │       │
│  │ ☑ ICMP Ping  ☑ SNMP  ☐ SSH         │       │
│  │                                      │       │
│  │ SNMP Communities:                    │       │
│  │ [public, private       + Add]        │       │
│  │                                      │       │
│  │       [Scan Network]                 │       │
│  └─────────────────────────────────────┘       │
│                                                  │
│  Active Scans                                   │
│  ┌───────────────────────────────────┐         │
│  │ Office Network    ████████░░ 85%  │         │
│  │ 210/245 IPs scanned                │         │
│  │ 45 devices discovered              │         │
│  │ ⏱ 00:02:34                         │         │
│  └───────────────────────────────────┘         │
│                                                  │
│  Discovered Devices (Live Updates)              │
│  ┌─┬──────────────┬─────────┬──────────┬───┐  │
│  │✓│ 192.168.1.1  │ Cisco   │ Switch   │ ⋯ │  │
│  │✓│ 192.168.1.2  │ HP      │ Switch   │ ⋯ │  │
│  │✓│ 192.168.1.3  │ Fortinet│ Firewall │ ⋯ │  │
│  │⏳│ 192.168.1.4  │ ...     │ ...      │ ⋯ │  │
│  └─┴──────────────┴─────────┴──────────┴───┘  │
│                                                  │
│  [Import Selected (3)]  [Ignore All]            │
└─────────────────────────────────────────────────┘
```

### 3. Devices

**List View** (Default)
```
┌────────────────────────────────────────────────┐
│  📡 Devices              [+ Add Device]        │
├────────────────────────────────────────────────┤
│                                                 │
│  🔍 Search  [All Vendors 🔽] [All Types 🔽]   │
│                                                 │
│  ┌───────────────────────────────────────┐    │
│  │ ● Core-Switch-01        192.168.1.1   │    │
│  │   Cisco • Switch                       │    │
│  │   ✅ Online • 99.8% uptime • 2.1 Gbps │    │
│  │   [Details] [Configure] [⋯]           │    │
│  └───────────────────────────────────────┘    │
│                                                 │
│  ┌───────────────────────────────────────┐    │
│  │ ● Firewall-Main         192.168.1.254 │    │
│  │   Fortinet • Firewall                  │    │
│  │   ✅ Online • 99.9% uptime • 850 Mbps │    │
│  │   [Details] [Configure] [⋯]           │    │
│  └───────────────────────────────────────┘    │
│                                                 │
│  ┌───────────────────────────────────────┐    │
│  │ ● Access-SW-Floor2      192.168.1.15  │    │
│  │   HP Aruba • Switch                    │    │
│  │   ⚠️ Warning • CPU 85% • 450 Mbps     │    │
│  │   [Details] [Configure] [⋯]           │    │
│  └───────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
```

**Card View** (Toggle)
```
┌─────────┐  ┌─────────┐  ┌─────────┐
│ ● SW-01 │  │ ● FW-01 │  │ ● SW-02 │
│ Cisco   │  │Fortinet │  │ HP      │
│ 99.8%   │  │ 99.9%   │  │ 98.5%   │
│ ✅      │  │ ✅      │  │ ⚠️      │
└─────────┘  └─────────┘  └─────────┘
```

### 4. Settings

**Tabbed Interface**
```
┌──────────────────────────────────────┐
│  General | Monitoring | SNMP | Users │
├──────────────────────────────────────┤
│                                       │
│  General Settings                     │
│                                       │
│  Organization Name                    │
│  [WARD Tech Solutions        ]        │
│                                       │
│  Primary Color                        │
│  [#5EBBA8] ████                      │
│                                       │
│  Time Zone                            │
│  [UTC +0        🔽]                  │
│                                       │
│  Language                             │
│  [English (US)  🔽]                  │
│                                       │
│  ☑ Enable Dark Mode                  │
│  ☑ Show Desktop Notifications         │
│  ☐ Send Email Alerts                  │
│                                       │
│           [Save Changes]              │
└──────────────────────────────────────┘
```

---

## Component Library

### Buttons

```tsx
// Primary (WARD Green)
<button className="btn-ward">
  <Plus size={16} /> Add Device
</button>

// Outline
<button className="btn-ward-outline">
  Cancel
</button>

// Icon only
<button className="p-2 rounded-lg hover:bg-gray-100">
  <Settings size={20} />
</button>
```

### Cards

```tsx
// Standard card
<div className="card-ward">
  <h3 className="text-lg font-semibold mb-4">Device Health</h3>
  {/* content */}
</div>

// Stat card
<div className="card-ward text-center">
  <div className="text-4xl font-bold text-ward-green">342</div>
  <div className="text-sm text-gray-500 mt-2">Total Devices</div>
  <div className="text-xs text-green-600 mt-1">↑ 12 this week</div>
</div>
```

### Inputs

```tsx
// Text input
<input 
  className="w-full px-4 py-2 rounded-lg border border-gray-200 focus:border-ward-green focus:ring-2 focus:ring-ward-green/20 outline-none transition"
  placeholder="Search devices..."
/>

// Select
<select className="px-4 py-2 rounded-lg border border-gray-200 focus:border-ward-green">
  <option>All Vendors</option>
  <option>Cisco</option>
  <option>HP</option>
</select>
```

### Status Badges

```tsx
// Success
<span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
  ● Online
</span>

// Warning
<span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
  ⚠️ Warning
</span>

// Error
<span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
  ● Offline
</span>
```

### Loading States

```tsx
// Skeleton card
<div className="card-ward animate-pulse">
  <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
</div>

// Spinner (WARD green)
<div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-200 border-t-ward-green"></div>
```

---

## Dark Mode

**Toggle Button**
```tsx
<button onClick={toggleDarkMode}>
  {isDark ? <Sun size={20} /> : <Moon size={20} />}
</button>
```

**Dark Mode Colors**
```
Background: #111827 (gray-900)
Cards: #1F2937 (gray-800)
Text: #F9FAFB (gray-50)
Borders: #374151 (gray-700)
WARD Green: Same (#5EBBA8) - looks beautiful on dark!
```

---

## Responsive Breakpoints

```css
sm: 640px   - Mobile
md: 768px   - Tablet
lg: 1024px  - Desktop
xl: 1280px  - Large Desktop
2xl: 1536px - Extra Large
```

**Mobile Navigation**
- Hamburger menu (☰)
- Bottom tab bar
- Swipe gestures

---

## Animations

### Page Transitions
```tsx
<motion.div
  initial={{ opacity: 0, y: -20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: 20 }}
  transition={{ duration: 0.3 }}
>
  {children}
</motion.div>
```

### Card Hover
```css
.card-ward:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(94, 187, 168, 0.15);
}
```

### Button Click
```css
.btn-ward:active {
  transform: scale(0.95);
}
```

---

## Accessibility

- ✅ ARIA labels on all interactive elements
- ✅ Keyboard navigation (Tab, Enter, Esc)
- ✅ Focus indicators (WARD green ring)
- ✅ Screen reader support
- ✅ Contrast ratio AAA (WCAG 2.1)

---

## Tech Stack

```
Frontend:
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Framer Motion (animations)
- Recharts (charts)
- Lucide React (icons)
- React Query (data fetching)
- Zustand (state)
- Axios (API)

Integration:
- FastAPI backend (http://localhost:5001)
- WebSocket (real-time updates)
- JWT authentication
```

---

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Layout.tsx
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Badge.tsx
│   │   └── features/
│   │       ├── DeviceCard.tsx
│   │       ├── DiscoveryScanner.tsx
│   │       └── StatsCard.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Discovery.tsx
│   │   ├── Devices.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useDevices.ts
│   │   ├── useDiscovery.ts
│   │   └── useDarkMode.ts
│   ├── services/
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── lib/
│   │   └── utils.ts
│   └── types/
│       └── index.ts
└── public/
    ├── logo-ward.svg
    └── favicon.svg
```

---

## Next Steps

1. Install dependencies: `npm install`
2. Run dev server: `npm run dev`
3. Open: http://localhost:3000
4. Login with WARD credentials
5. Experience the modern UI!

🎨 **The new WARD FLUX UI will be stunning while keeping your beautiful brand identity!**
