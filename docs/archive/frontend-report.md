# Frontend Engineering Report: React & Next.js

> Intensive guide covering architecture, patterns, performance, UX, and tooling for production-grade frontends.

---

## Table of Contents

1. [React vs Next.js — When to Pick What](#1-react-vs-nextjs--when-to-pick-what)
2. [Project Structure](#2-project-structure)
3. [Core Architecture Patterns](#3-core-architecture-patterns)
4. [State Management](#4-state-management)
5. [Data Fetching](#5-data-fetching)
6. [Routing](#6-routing)
7. [Styling & Design System](#7-styling--design-system)
8. [Performance](#8-performance)
9. [Building Interactive Websites](#9-building-interactive-websites)
10. [Accessibility (a11y)](#10-accessibility-a11y)
11. [Security](#11-security)
12. [Testing](#12-testing)
13. [Developer Experience & Tooling](#13-developer-experience--tooling)
14. [CI/CD & Deployment](#14-cicd--deployment)
15. [What a Best-in-Class Frontend Looks Like End-to-End](#15-what-a-best-in-class-frontend-looks-like-end-to-end)

---

## 1. React vs Next.js — When to Pick What

### React (Vite + React)
Use pure React when:
- You are building a **Single Page Application (SPA)** where SEO is not critical (dashboards, internal tools, admin panels).
- You want full control over your build tooling.
- The backend is a separate service (your own API, AWS, etc.) and you're just building the client.

**Stack:** Vite + React + TypeScript + React Router + TanStack Query

### Next.js
Use Next.js when:
- You need **SEO** (marketing pages, public-facing content, product listings).
- You want **server-side rendering (SSR)** or **static site generation (SSG)**.
- You want **full-stack** capability in one repo (API routes / server actions).
- You want **incremental static regeneration (ISR)** — pages that rebuild themselves on a schedule.

**Stack:** Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui

### Summary Table

| Concern                | React (SPA)       | Next.js                     |
|------------------------|-------------------|-----------------------------|
| SEO                    | Poor (CSR only)   | Excellent (SSR/SSG/ISR)     |
| Initial load speed     | Slower (JS heavy) | Fast (pre-rendered HTML)    |
| Full-stack capability  | No                | Yes (API routes, RSC)       |
| Flexibility            | Maximum           | Opinionated but powerful    |
| Deployment             | Any static host   | Vercel, serverless, Docker  |
| Learning curve         | Lower             | Moderate                    |

**For most new projects in 2024–2026: choose Next.js.**

---

## 2. Project Structure

### Next.js App Router (recommended layout)

```
my-app/
├── app/                        # All routes live here
│   ├── layout.tsx              # Root layout (HTML shell, providers)
│   ├── page.tsx                # Home route "/"
│   ├── (marketing)/            # Route group (no URL segment)
│   │   ├── about/page.tsx
│   │   └── pricing/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx          # Nested layout for dashboard
│   │   ├── page.tsx            # /dashboard
│   │   └── settings/page.tsx   # /dashboard/settings
│   └── api/                    # API routes
│       └── health/route.ts
├── components/
│   ├── ui/                     # Primitive UI (buttons, inputs, modals)
│   ├── layout/                 # Header, Footer, Sidebar
│   └── features/               # Feature-scoped components
│       └── auth/
│           ├── LoginForm.tsx
│           └── AuthGuard.tsx
├── hooks/                      # Custom React hooks
├── lib/                        # Shared utilities, API clients
│   ├── api.ts                  # API layer
│   └── utils.ts
├── store/                      # Global state (Zustand slices, etc.)
├── types/                      # Shared TypeScript types/interfaces
├── public/                     # Static assets
├── styles/                     # Global CSS / Tailwind config
├── tests/                      # Unit + integration tests
├── .env.local                  # Local environment variables
├── next.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

### Key Rules
- **Colocation**: keep tests, types, and styles near the component they belong to.
- **Feature folders** over type folders for anything beyond small projects.
- **No barrel re-exports** from `/components/index.ts` — they cause circular dep issues and slow TS.

---

## 3. Core Architecture Patterns

### Server Components vs Client Components (Next.js App Router)

This is the most important mental model in modern Next.js.

```
Server Components (default)          Client Components ('use client')
─────────────────────────────────    ──────────────────────────────────
Render on the server                 Render in the browser
Can access DB, secrets, env vars     Cannot access server resources
Zero JS sent to browser              JS bundle sent to client
Cannot use useState / useEffect      Can use all React hooks
Cannot handle user interaction       Can handle events, forms
```

**Rule of thumb:** push as much as possible to Server Components. Only add `'use client'` when you need interactivity.

```tsx
// app/dashboard/page.tsx — Server Component (no directive needed)
import { fetchUserData } from '@/lib/api'
import { UserCard } from '@/components/features/UserCard'

export default async function DashboardPage() {
  const user = await fetchUserData() // direct DB/API call, no useEffect
  return <UserCard user={user} />
}
```

```tsx
// components/features/UserCard.tsx — Client Component
'use client'
import { useState } from 'react'

export function UserCard({ user }: { user: User }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div>
      <h2>{user.name}</h2>
      <button onClick={() => setExpanded(!expanded)}>Details</button>
      {expanded && <p>{user.bio}</p>}
    </div>
  )
}
```

### Component Design Principles

1. **Single Responsibility**: each component does one thing.
2. **Composition over inheritance**: build complex UIs by combining small components.
3. **Controlled components**: form inputs controlled by React state, not DOM.
4. **Prop drilling limit**: if props go 3+ levels deep, use Context or a state manager.
5. **Avoid premature abstraction**: duplicate twice, then extract.

---

## 4. State Management

Choose based on what type of state you have:

| State type           | Recommended tool                          |
|----------------------|-------------------------------------------|
| Server/async data    | TanStack Query (React Query)              |
| Global UI state      | Zustand                                   |
| Local component state| useState / useReducer                     |
| URL state            | next/navigation (searchParams, pathname)  |
| Form state           | React Hook Form + Zod                     |

### TanStack Query — for server state
```tsx
// hooks/useWeatherData.ts
import { useQuery } from '@tanstack/react-query'

export function useWeatherData(city: string) {
  return useQuery({
    queryKey: ['weather', city],
    queryFn: () => fetch(`/api/weather?city=${city}`).then(r => r.json()),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
```

### Zustand — for global UI state
```tsx
// store/uiStore.ts
import { create } from 'zustand'

interface UIStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: false,
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
}))
```

### React Hook Form + Zod — for forms
```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

type FormData = z.infer<typeof schema>

export function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: FormData) => { /* call API */ }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}
      <button type="submit">Login</button>
    </form>
  )
}
```

---

## 5. Data Fetching

### Next.js Server Component fetch (recommended for SSR/SSG)
```tsx
// Cached fetch — acts like SSG
const data = await fetch('https://api.example.com/data', {
  next: { revalidate: 3600 } // revalidate every hour (ISR)
})

// No cache — acts like SSR (fresh on every request)
const data = await fetch('https://api.example.com/data', {
  cache: 'no-store'
})

// Force static — cached forever until next build
const data = await fetch('https://api.example.com/data', {
  cache: 'force-cache'
})
```

### Server Actions (Next.js 14+) — replace most API routes
```tsx
// app/actions/submitForm.ts
'use server'
import { z } from 'zod'

const schema = z.object({ name: z.string().min(1) })

export async function submitForm(formData: FormData) {
  const result = schema.safeParse({ name: formData.get('name') })
  if (!result.success) return { error: result.error.flatten() }
  // save to DB, send email, etc.
  return { success: true }
}
```

```tsx
// In a component
import { submitForm } from '@/app/actions/submitForm'

export function MyForm() {
  return (
    <form action={submitForm}>
      <input name="name" />
      <button type="submit">Submit</button>
    </form>
  )
}
```

### API Client Layer (for React SPA or client-side calls)
```ts
// lib/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  get:    <T>(path: string) => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT',  body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
```

---

## 6. Routing

### Next.js App Router Concepts

```
app/
├── page.tsx                  → /
├── about/page.tsx            → /about
├── blog/
│   ├── page.tsx              → /blog
│   └── [slug]/page.tsx       → /blog/anything
├── (auth)/                   → Route group (no URL segment)
│   ├── login/page.tsx        → /login
│   └── register/page.tsx     → /register
├── dashboard/
│   ├── @sidebar/             → Parallel route (slot)
│   └── @main/
└── shop/[...slug]/page.tsx   → /shop/a/b/c (catch-all)
```

### Programmatic navigation
```tsx
'use client'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'

export function Nav() {
  const router = useRouter()
  return <button onClick={() => router.push('/dashboard')}>Go to Dashboard</button>
}
```

### Middleware — for auth guards, redirects
```ts
// middleware.ts (at project root)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
```

---

## 7. Styling & Design System

### Recommended: Tailwind CSS + shadcn/ui

**Tailwind CSS** — utility-first, no CSS context switching, excellent purging.

**shadcn/ui** — not a component library you install as a package. You copy components into your project (`/components/ui/`) and own them completely. Built on Radix UI primitives (accessible out of the box) + Tailwind.

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input card dialog
```

### Design Tokens — define once, use everywhere
```ts
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f9ff',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}
```

### CSS Architecture Rules
1. **No inline styles** except for truly dynamic values (widths from JS calculations).
2. **No global class name collisions** — Tailwind scoping handles this.
3. **Dark mode** via `dark:` variants or CSS variables.
4. **Responsive design**: mobile-first with `sm:`, `md:`, `lg:`, `xl:` breakpoints.

```tsx
// Responsive, dark-mode-aware component
<div className="
  p-4 sm:p-6 lg:p-8
  bg-white dark:bg-gray-900
  rounded-lg shadow-md
  text-gray-900 dark:text-gray-100
">
```

---

## 8. Performance

### Core Web Vitals targets (Google's metrics)
| Metric | What it measures            | Good threshold |
|--------|-----------------------------|----------------|
| LCP    | Largest Contentful Paint    | < 2.5s         |
| FID/INP| Interaction to Next Paint   | < 200ms        |
| CLS    | Cumulative Layout Shift     | < 0.1          |
| TTFB   | Time to First Byte          | < 800ms        |

### Image Optimization
```tsx
import Image from 'next/image'

// Always use next/image — it automatically:
// - Converts to WebP/AVIF
// - Lazy loads
// - Prevents CLS with width/height
// - Serves from CDN via Next.js image optimization

<Image
  src="/hero.jpg"
  alt="Hero image"
  width={1200}
  height={600}
  priority           // above-the-fold images: load eagerly
  className="rounded-lg"
/>
```

### Code Splitting & Lazy Loading
```tsx
import dynamic from 'next/dynamic'

// Heavy components that aren't needed on first load
const HeavyChart = dynamic(() => import('@/components/HeavyChart'), {
  loading: () => <div className="animate-pulse h-64 bg-gray-200 rounded" />,
  ssr: false,  // disable SSR for browser-only libs (like chart.js)
})
```

### Bundle Analysis
```bash
# Check what's eating your bundle
npm install @next/bundle-analyzer
ANALYZE=true next build
```

### Caching strategy
```ts
// React cache() for deduplicating server-side fetches
import { cache } from 'react'

export const getUser = cache(async (id: string) => {
  return db.users.findUnique({ where: { id } })
})
// Multiple components calling getUser(id) in the same render → only 1 DB query
```

### Performance Checklist
- [ ] No unused npm packages (`npx depcheck`)
- [ ] Fonts loaded with `next/font` (no layout shift, self-hosted)
- [ ] Third-party scripts via `next/script` with `strategy="lazyOnload"`
- [ ] Suspense boundaries for progressive loading
- [ ] `loading.tsx` files for each route segment
- [ ] Prefetch links with `<Link prefetch>` for common navigation paths

---

## 9. Building Interactive Websites

Interactivity is what separates modern web apps from static pages. This section provides step-by-step guidance on creating engaging, responsive user experiences with practical examples and complete implementation patterns.

### Getting Started: Interactive Website Foundation

Before diving into advanced patterns, let's establish the foundation for any interactive website:

#### Step 1: Set Up Your Interactive Stack

```bash
# Create Next.js project with essential interactive dependencies
npx create-next-app@latest my-interactive-site --typescript --tailwind --app
cd my-interactive-site

# Install core interaction libraries
npm install framer-motion @tanstack/react-query zustand react-hook-form
npm install @hookform/resolvers zod lucide-react cmdk

# Install UI primitives for advanced components
npm install @radix-ui/react-dialog @radix-ui/react-tooltip
npm install @radix-ui/react-dropdown-menu @radix-ui/react-select
```

#### Step 2: Configure Providers (app/layout.tsx)

```tsx
// app/layout.tsx - Essential providers for interactive features
'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import { useState } from 'react'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <html lang="en">
      <body>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster /> {/* For user feedback */}
        </QueryClientProvider>
      </body>
    </html>
  )
}
```

#### Step 3: Create Base Interactive Components

```tsx
// components/ui/interactive-button.tsx - Foundation interactive button
'use client'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { Loader2 } from 'lucide-react'

interface InteractiveButtonProps {
  children: React.ReactNode
  onClick?: () => void | Promise<void>
  variant?: 'primary' | 'secondary'
  disabled?: boolean
}

export function InteractiveButton({ 
  children, 
  onClick, 
  variant = 'primary',
  disabled 
}: InteractiveButtonProps) {
  const [isLoading, setIsLoading] = useState(false)

  const handleClick = async () => {
    if (!onClick || disabled || isLoading) return
    
    setIsLoading(true)
    try {
      await onClick()
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      onClick={handleClick}
      disabled={disabled || isLoading}
      className={`
        relative px-6 py-3 rounded-lg font-medium transition-colors
        ${variant === 'primary' 
          ? 'bg-blue-600 hover:bg-blue-700 text-white' 
          : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
        }
        ${disabled || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {isLoading && (
        <Loader2 className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin" />
      )}
      <span className={isLoading ? 'ml-6' : ''}>{children}</span>
    </motion.button>
  )
}
```

### How to Build Specific Interactive Features

#### Building a Live Dashboard

**Complete example: Real-time metrics dashboard**

```tsx
// app/dashboard/page.tsx - Live updating dashboard
'use client'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Metric {
  id: string
  name: string
  value: number
  change: number
  status: 'up' | 'down' | 'stable'
}

export default function LiveDashboard() {
  // Auto-refresh every 30 seconds
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: async (): Promise<Metric[]> => {
      const response = await fetch('/api/metrics')
      return response.json()
    },
    refetchInterval: 30000, // 30 seconds
  })

  if (isLoading) return <DashboardSkeleton />

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Live Dashboard</h1>
      
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ staggerChildren: 0.1 }}
      >
        {metrics?.map((metric, index) => (
          <MetricCard key={metric.id} metric={metric} index={index} />
        ))}
      </motion.div>

      <LiveChart />
    </div>
  )
}

function MetricCard({ metric, index }: { metric: Metric; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-600">{metric.name}</h3>
          <Badge variant={metric.status === 'up' ? 'default' : 'destructive'}>
            {metric.status}
          </Badge>
        </div>
        <div className="mt-2">
          <p className="text-2xl font-bold">{metric.value.toLocaleString()}</p>
          <p className={`text-sm ${metric.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {metric.change >= 0 ? '+' : ''}{metric.change}% from yesterday
          </p>
        </div>
      </Card>
    </motion.div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
    </div>
  )
}
```

#### Building Interactive Forms with Real-time Validation

```tsx
// components/forms/interactive-contact-form.tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertCircle } from 'lucide-react'
import { useState } from 'react'

const formSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email'),
  message: z.string().min(10, 'Message must be at least 10 characters'),
})

type FormData = z.infer<typeof formSchema>

export function InteractiveContactForm() {
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
    watch,
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: 'onChange', // Real-time validation
  })

  const watchedFields = watch()

  const onSubmit = async (data: FormData) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      console.log('Form submitted:', data)
      setSubmitStatus('success')
      reset()
      
      // Reset success state after 3 seconds
      setTimeout(() => setSubmitStatus('idle'), 3000)
    } catch (error) {
      setSubmitStatus('error')
    }
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-6 max-w-md mx-auto p-6 bg-white rounded-lg shadow-lg"
    >
      <h2 className="text-2xl font-bold text-center">Get in Touch</h2>

      {/* Name Field */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Name</label>
        <div className="relative">
          <input
            {...register('name')}
            className={`
              w-full px-4 py-2 border rounded-lg transition-colors
              ${errors.name ? 'border-red-500' : 'border-gray-300'}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
            placeholder="Your name"
          />
          <AnimatePresence>
            {watchedFields.name && !errors.name && (
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0 }}
                className="absolute right-3 top-1/2 transform -translate-y-1/2"
              >
                <CheckCircle className="h-5 w-5 text-green-500" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <AnimatePresence>
          {errors.name && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="text-red-500 text-sm flex items-center gap-1"
            >
              <AlertCircle className="h-4 w-4" />
              {errors.name.message}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Email Field */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Email</label>
        <div className="relative">
          <input
            {...register('email')}
            type="email"
            className={`
              w-full px-4 py-2 border rounded-lg transition-colors
              ${errors.email ? 'border-red-500' : 'border-gray-300'}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
            placeholder="your@email.com"
          />
          <AnimatePresence>
            {watchedFields.email && !errors.email && (
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0 }}
                className="absolute right-3 top-1/2 transform -translate-y-1/2"
              >
                <CheckCircle className="h-5 w-5 text-green-500" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <AnimatePresence>
          {errors.email && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="text-red-500 text-sm flex items-center gap-1"
            >
              <AlertCircle className="h-4 w-4" />
              {errors.email.message}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Message Field */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Message</label>
        <div className="relative">
          <textarea
            {...register('message')}
            rows={4}
            className={`
              w-full px-4 py-2 border rounded-lg transition-colors resize-none
              ${errors.message ? 'border-red-500' : 'border-gray-300'}
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
            placeholder="Your message..."
          />
          <div className="absolute bottom-2 right-2 text-xs text-gray-500">
            {watchedFields.message?.length || 0}/500
          </div>
        </div>
        <AnimatePresence>
          {errors.message && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="text-red-500 text-sm flex items-center gap-1"
            >
              <AlertCircle className="h-4 w-4" />
              {errors.message.message}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Submit Button */}
      <motion.button
        type="submit"
        disabled={!isValid || isSubmitting}
        whileHover={{ scale: isValid ? 1.02 : 1 }}
        whileTap={{ scale: isValid ? 0.98 : 1 }}
        className={`
          w-full py-3 px-4 rounded-lg font-medium transition-all
          ${isValid && !isSubmitting
            ? 'bg-blue-600 hover:bg-blue-700 text-white' 
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }
        `}
      >
        {isSubmitting ? (
          <div className="flex items-center justify-center gap-2">
            <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Sending...
          </div>
        ) : (
          'Send Message'
        )}
      </motion.button>

      {/* Success/Error Messages */}
      <AnimatePresence>
        {submitStatus === 'success' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded"
          >
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Message sent successfully!
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.form>
  )
}
```

### Core Interaction Patterns

Now let's explore the fundamental patterns that make websites truly interactive:

#### 1. Real-Time Updates

```tsx
// components/chat/chat-interface.tsx
'use client'
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, User, Bot } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'

interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // WebSocket connection
  const { data, isConnected, send } = useWebSocket('ws://localhost:3001/chat')

  // Handle incoming messages
  useEffect(() => {
    if (data) {
      const newMessage: Message = {
        id: Date.now().toString(),
        text: data.message,
        sender: data.sender,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, newMessage])
      setIsTyping(false)
    }
  }, [data])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = () => {
    if (!inputValue.trim() || !isConnected) return

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    send({ message: inputValue })
    setInputValue('')
    setIsTyping(true)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[600px] border rounded-lg bg-white shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold">Chat Support</h3>
        <div className={`flex items-center gap-2 text-sm ${
          isConnected ? 'text-green-600' : 'text-red-600'
        }`}>
          <div className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          {isConnected ? 'Online' : 'Connecting...'}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-start gap-3 max-w-[70%] ${
                message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  message.sender === 'user' ? 'bg-blue-500' : 'bg-gray-500'
                }`}>
                  {message.sender === 'user' ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>
                <div className={`px-4 py-2 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}>
                  <p>{message.text}</p>
                  <p className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex justify-start"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-gray-100 px-4 py-2 rounded-lg">
                  <div className="flex gap-1">
                    {[...Array(3)].map((_, i) => (
                      <motion.div
                        key={i}
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{
                          repeat: Infinity,
                          duration: 0.8,
                          delay: i * 0.2,
                        }}
                        className="w-2 h-2 bg-gray-400 rounded-full"
                      />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={!isConnected}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={sendMessage}
            disabled={!inputValue.trim() || !isConnected}
            className={`px-4 py-2 rounded-lg ${
              inputValue.trim() && isConnected
                ? 'bg-blue-500 hover:bg-blue-600 text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </div>
  )
}

// hooks/useWebSocket.ts
export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [data, setData] = useState<any>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const ws = new WebSocket(url)
    
    ws.onopen = () => {
      setIsConnected(true)
      setSocket(ws)
    }
    
    ws.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data)
        setData(parsedData)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    ws.onclose = () => {
      setIsConnected(false)
      setSocket(null)
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [url])

  const send = (message: any) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message))
    }
  }

  return { data, isConnected, send }
}
```

#### Building Interactive Data Tables with Sorting, Filtering, and Pagination

```tsx
// components/tables/interactive-table.tsx
'use client'
import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { ChevronUp, ChevronDown, Search, Filter } from 'lucide-react'

interface TableData {
  id: string
  name: string
  email: string
  role: string
  status: 'active' | 'inactive'
  joinDate: string
}

interface InteractiveTableProps {
  data: TableData[]
}

export function InteractiveTable({ data }: InteractiveTableProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState<keyof TableData>('name')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(10)

  // Filter and sort data
  const processedData = useMemo(() => {
    let filtered = data.filter(item => {
      const matchesSearch = Object.values(item)
        .join(' ')
        .toLowerCase()
        .includes(searchTerm.toLowerCase())
      
      const matchesStatus = statusFilter === 'all' || item.status === statusFilter
      
      return matchesSearch && matchesStatus
    })

    // Sort
    filtered.sort((a, b) => {
      const aValue = a[sortField]
      const bValue = b[sortField]
      
      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })

    return filtered
  }, [data, searchTerm, sortField, sortDirection, statusFilter])

  // Pagination
  const totalPages = Math.ceil(processedData.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedData = processedData.slice(startIndex, startIndex + itemsPerPage)

  const handleSort = (field: keyof TableData) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const SortIcon = ({ field }: { field: keyof TableData }) => {
    if (sortField !== field) return <div className="w-4 h-4" />
    return sortDirection === 'asc' ? 
      <ChevronUp className="w-4 h-4" /> : 
      <ChevronDown className="w-4 h-4" />
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="pl-10 pr-8 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden border rounded-lg">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {[
                { key: 'name', label: 'Name' },
                { key: 'email', label: 'Email' },
                { key: 'role', label: 'Role' },
                { key: 'status', label: 'Status' },
                { key: 'joinDate', label: 'Join Date' },
              ].map((column) => (
                <th
                  key={column.key}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort(column.key as keyof TableData)}
                >
                  <div className="flex items-center gap-2">
                    {column.label}
                    <SortIcon field={column.key as keyof TableData} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.map((item, index) => (
              <motion.tr
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="hover:bg-gray-50 transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="font-medium text-gray-900">{item.name}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-gray-600">{item.email}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-gray-900">{item.role}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                    item.status === 'active'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {item.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                  {new Date(item.joinDate).toLocaleDateString()}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, processedData.length)} of {processedData.length} results
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          
          {[...Array(totalPages)].map((_, i) => (
            <button
              key={i + 1}
              onClick={() => setCurrentPage(i + 1)}
              className={`px-3 py-1 border rounded ${
                currentPage === i + 1
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'hover:bg-gray-50'
              }`}
            >
              {i + 1}
            </button>
          ))}
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### Building a Drag-and-Drop File Upload with Progress

```tsx
// components/upload/drag-drop-upload.tsx
'use client'
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react'

interface UploadFile {
  id: string
  file: File
  progress: number
  status: 'uploading' | 'completed' | 'error'
  error?: string
}

export function DragDropUpload() {
  const [files, setFiles] = useState<UploadFile[]>([])
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      progress: 0,
      status: 'uploading' as const,
    }))
    
    setFiles(prev => [...prev, ...newFiles])
    
    // Simulate upload for each file
    newFiles.forEach(uploadFile => {
      simulateUpload(uploadFile.id)
    })
  }, [])
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'application/pdf': ['.pdf'],
      'text/*': ['.txt', '.md'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  })
  
  const simulateUpload = (fileId: string) => {
    const interval = setInterval(() => {
      setFiles(prev => prev.map(file => {
        if (file.id === fileId) {
          const newProgress = Math.min(file.progress + Math.random() * 20, 100)
          
          if (newProgress >= 100) {
            clearInterval(interval)
            return {
              ...file,
              progress: 100,
              status: Math.random() > 0.1 ? 'completed' : 'error', // 90% success rate
              error: Math.random() > 0.1 ? undefined : 'Upload failed. Please try again.',
            }
          }
          
          return { ...file, progress: newProgress }
        }
        return file
      }))
    }, 200)
  }
  
  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(file => file.id !== fileId))
  }
  
  const retryUpload = (fileId: string) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, progress: 0, status: 'uploading' as const, error: undefined }
        : file
    ))
    simulateUpload(fileId)
  }

  return (
    <div className="space-y-6">
      {/* Drop Zone */}
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
      >
        <input {...getInputProps()} />
        <Upload className={`mx-auto h-12 w-12 mb-4 ${
          isDragActive ? 'text-blue-500' : 'text-gray-400'
        }`} />
        <p className="text-lg font-medium mb-2">
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </p>
        <p className="text-sm text-gray-600">
          or click to browse • Max 10MB • PNG, JPG, PDF, TXT
        </p>
      </motion.div>

      {/* File List */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3"
          >
            <h3 className="font-medium text-gray-900">
              Uploading {files.length} file{files.length > 1 ? 's' : ''}
            </h3>
            
            {files.map((uploadFile) => (
              <motion.div
                key={uploadFile.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="border rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <File className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium">{uploadFile.file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {uploadFile.status === 'completed' && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                    {uploadFile.status === 'error' && (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    )}
                    <button
                      onClick={() => removeFile(uploadFile.id)}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                
                {/* Progress Bar */}
                {uploadFile.status === 'uploading' && (
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${uploadFile.progress}%` }}
                      className="bg-blue-500 h-2 rounded-full"
                    />
                  </div>
                )}
                
                {/* Status Messages */}
                {uploadFile.status === 'completed' && (
                  <p className="text-sm text-green-600">Upload completed</p>
                )}
                
                {uploadFile.status === 'error' && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-red-600">{uploadFile.error}</p>
                    <button
                      onClick={() => retryUpload(uploadFile.id)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

#### 1. Real-Time Updates

**WebSockets for bi-directional communication:**
```tsx
// lib/websocket.ts
import { useEffect, useState } from 'react'

export function useWebSocket(url: string) {
  const [data, setData] = useState(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const ws = new WebSocket(url)
    
    ws.onopen = () => setIsConnected(true)
    ws.onmessage = (event) => setData(JSON.parse(event.data))
    ws.onclose = () => setIsConnected(false)
    
    return () => ws.close()
  }, [url])

  const send = (message: any) => {
    if (isConnected) ws.send(JSON.stringify(message))
  }

  return { data, isConnected, send }
}
```

**Server-Sent Events (SSE) for one-way streaming:**
```tsx
// For live notifications, stock tickers, activity feeds
export function useServerEvents(endpoint: string) {
  const [events, setEvents] = useState<any[]>([])

  useEffect(() => {
    const eventSource = new EventSource(endpoint)
    
    eventSource.onmessage = (event) => {
      setEvents(prev => [JSON.parse(event.data), ...prev])
    }
    
    return () => eventSource.close()
  }, [endpoint])

  return events
}
```

**Polling with smart intervals:**
```tsx
import { useQuery } from '@tanstack/react-query'

// Polls every 5 seconds when tab is visible
export function useLiveData() {
  return useQuery({
    queryKey: ['live-data'],
    queryFn: () => fetch('/api/live').then(r => r.json()),
    refetchInterval: 5000,
    refetchIntervalInBackground: false, // pause when tab hidden
  })
}
```

#### 2. Smooth Animations & Transitions

**Framer Motion — the gold standard for React animations:**
```tsx
import { motion, AnimatePresence } from 'framer-motion'

export function FadeInCard({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  )
}

// List animations with stagger
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1 // each child animates 100ms after previous
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 }
}

export function AnimatedList({ items }) {
  return (
    <motion.ul variants={containerVariants} initial="hidden" animate="visible">
      {items.map(item => (
        <motion.li key={item.id} variants={itemVariants}>
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  )
}
```

**Page transitions in Next.js:**
```tsx
// app/template.tsx — wraps every route
'use client'
import { motion } from 'framer-motion'

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  )
}
```

**CSS-only animations for performance-critical cases:**
```css
/* Prefer transform and opacity — they don't trigger layout/paint */
@keyframes slideIn {
  from {
    transform: translateX(-100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.slide-in {
  animation: slideIn 0.3s ease-out;
}
```

#### 3. Drag & Drop

**react-beautiful-dnd for lists (Trello-style):**
```tsx
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'

export function DraggableList({ items, onReorder }) {
  const handleDragEnd = (result) => {
    if (!result.destination) return
    const reordered = Array.from(items)
    const [removed] = reordered.splice(result.source.index, 1)
    reordered.splice(result.destination.index, 0, removed)
    onReorder(reordered)
  }

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Droppable droppableId="list">
        {(provided) => (
          <ul {...provided.droppableProps} ref={provided.innerRef}>
            {items.map((item, index) => (
              <Draggable key={item.id} draggableId={item.id} index={index}>
                {(provided) => (
                  <li
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                  >
                    {item.content}
                  </li>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </ul>
        )}
      </Droppable>
    </DragDropContext>
  )
}
```

**dnd-kit for complex cases (file uploads, kanban boards):**
```tsx
import { DndContext, closestCenter, useSensor, useSensors, PointerSensor } from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'

function SortableItem({ id, children }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id })
  
  const style = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    transition,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </div>
  )
}
```

#### 4. Infinite Scroll & Virtual Lists

**TanStack Virtual for rendering huge lists efficiently:**
```tsx
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'

export function VirtualList({ items }: { items: any[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // each row ~50px
    overscan: 5, // render 5 extra rows above/below viewport
  })

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Infinite scroll with Intersection Observer:**
```tsx
import { useInfiniteQuery } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

export function InfiniteList() {
  const observerTarget = useRef<HTMLDivElement>(null)

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['items'],
    queryFn: ({ pageParam = 0 }) => fetch(`/api/items?page=${pageParam}`).then(r => r.json()),
    getNextPageParam: (lastPage, pages) => lastPage.hasMore ? pages.length : undefined,
  })

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasNextPage) fetchNextPage()
      },
      { threshold: 1.0 }
    )
    if (observerTarget.current) observer.observe(observerTarget.current)
    return () => observer.disconnect()
  }, [hasNextPage, fetchNextPage])

  return (
    <div>
      {data?.pages.map((page, i) => (
        <div key={i}>
          {page.items.map(item => <div key={item.id}>{item.name}</div>)}
        </div>
      ))}
      <div ref={observerTarget} className="h-10" />
      {isFetchingNextPage && <p>Loading more...</p>}
    </div>
  )
}
```

#### 5. Rich Text Editing

**Tiptap (modern, extensible):**
```tsx
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

export function RichTextEditor({ content, onChange }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  })

  return (
    <div>
      <div className="toolbar">
        <button onClick={() => editor.chain().focus().toggleBold().run()}>
          Bold
        </button>
        <button onClick={() => editor.chain().focus().toggleItalic().run()}>
          Italic
        </button>
        <button onClick={() => editor.chain().focus().toggleBulletList().run()}>
          List
        </button>
      </div>
      <EditorContent editor={editor} className="prose" />
    </div>
  )
}
```

#### 6. Interactive Data Visualizations

**Recharts (declarative, React-native):**
```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export function InteractiveChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="value" stroke="#0ea5e9" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

**D3.js for full control (complex custom visualizations):**
```tsx
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

export function CustomVisualization({ data }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    
    // D3 imperative code here
    svg.selectAll('circle')
      .data(data)
      .join('circle')
      .attr('cx', (d, i) => i * 50)
      .attr('cy', 100)
      .attr('r', d => d.value)
      .attr('fill', '#0ea5e9')
      .transition()
      .duration(750)
      .attr('r', d => d.value * 2)
  }, [data])

  return <svg ref={svgRef} width={600} height={200} />
}
```

#### 7. Micro-Interactions

Small details that make a UI feel alive:

**Hover effects:**
```tsx
<button className="
  transition-all duration-200
  hover:scale-105 hover:shadow-lg
  active:scale-95
">
  Click me
</button>
```

**Loading skeletons (better than spinners):**
```tsx
export function SkeletonCard() {
  return (
    <div className="animate-pulse">
      <div className="h-48 bg-gray-200 rounded-lg mb-4" />
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
    </div>
  )
}
```

**Confetti on success actions:**
```tsx
import confetti from 'canvas-confetti'

const handleSuccess = () => {
  confetti({
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 }
  })
}
```

**Haptic feedback (mobile):**
```tsx
const triggerHaptic = () => {
  if ('vibrate' in navigator) navigator.vibrate(10)
}
```

### Advanced Interaction Techniques

#### Optimistic Updates
```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'

function useLikeMutation(postId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => fetch(`/api/posts/${postId}/like`, { method: 'POST' }),
    onMutate: async () => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['post', postId] })
      
      // Snapshot previous value
      const previous = queryClient.getQueryData(['post', postId])
      
      // Optimistically update
      queryClient.setQueryData(['post', postId], (old: any) => ({
        ...old,
        likes: old.likes + 1,
        isLiked: true,
      }))
      
      return { previous }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      queryClient.setQueryData(['post', postId], context?.previous)
    },
    onSettled: () => {
      // Refetch to sync with server
      queryClient.invalidateQueries({ queryKey: ['post', postId] })
    },
  })
}
```

#### Keyboard Shortcuts
```tsx
import { useEffect } from 'react'

export function useKeyboardShortcut(key: string, callback: () => void) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === key) {
        e.preventDefault()
        callback()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [key, callback])
}

// Usage
function Editor() {
  useKeyboardShortcut('s', () => saveDocument())
  useKeyboardShortcut('k', () => openCommandPalette())
  // ...
}
```

#### Command Palette (like VS Code)
```tsx
import { Command } from 'cmdk'

export function CommandPalette({ open, onClose }) {
  return (
    <Command.Dialog open={open} onOpenChange={onClose}>
      <Command.Input placeholder="Type a command..." />
      <Command.List>
        <Command.Empty>No results found.</Command.Empty>
        <Command.Group heading="Actions">
          <Command.Item onSelect={() => { /* action */ }}>
            Create new document
          </Command.Item>
          <Command.Item onSelect={() => { /* action */ }}>
            Open settings
          </Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  )
}
```

#### Collaborative Editing (CRDT-based)
```tsx
// Using Yjs + WebRTC for real-time collaboration
import * as Y from 'yjs'
import { WebrtcProvider } from 'y-webrtc'

const ydoc = new Y.Doc()
const provider = new WebrtcProvider('room-name', ydoc)
const ytext = ydoc.getText('shared-text')

ytext.observe(() => {
  // Update UI when any peer changes text
  console.log(ytext.toString())
})

// Insert text (automatically syncs to all peers)
ytext.insert(0, 'Hello, ')
```

### User Experience Patterns

#### 1. Progressive Disclosure
Don't overwhelm users — reveal complexity gradually.

```tsx
function AdvancedSettings() {
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  return (
    <div>
      <BasicSettings />
      <button onClick={() => setShowAdvanced(!showAdvanced)}>
        {showAdvanced ? 'Hide' : 'Show'} Advanced Options
      </button>
      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <AdvancedOptions />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

#### 2. Contextual Help
```tsx
import * as Tooltip from '@radix-ui/react-tooltip'

<Tooltip.Provider>
  <Tooltip.Root>
    <Tooltip.Trigger asChild>
      <button>
        What's this? <InfoIcon />
      </button>
    </Tooltip.Trigger>
    <Tooltip.Portal>
      <Tooltip.Content className="bg-gray-900 text-white px-3 py-2 rounded">
        This setting controls how often data refreshes.
        <Tooltip.Arrow />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
</Tooltip.Provider>
```

#### 3. Undo/Redo
```tsx
function useUndoable<T>(initialState: T) {
  const [history, setHistory] = useState<T[]>([initialState])
  const [index, setIndex] = useState(0)

  const state = history[index]

  const setState = (newState: T) => {
    const newHistory = history.slice(0, index + 1)
    setHistory([...newHistory, newState])
    setIndex(newHistory.length)
  }

  const undo = () => index > 0 && setIndex(index - 1)
  const redo = () => index < history.length - 1 && setIndex(index + 1)

  return { state, setState, undo, redo, canUndo: index > 0, canRedo: index < history.length - 1 }
}
```

### Performance for Interactive UIs

**Debounce search inputs:**
```tsx
import { useDeferredValue } from 'react'

function SearchableList({ items }) {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query) // non-blocking updates

  const filtered = items.filter(item => 
    item.name.toLowerCase().includes(deferredQuery.toLowerCase())
  )

  return (
    <>
      <input value={query} onChange={e => setQuery(e.target.value)} />
      <List items={filtered} />
    </>
  )
}
```

**useTransition for non-urgent updates:**
```tsx
import { useTransition } from 'react'

const [isPending, startTransition] = useTransition()

const handleTabChange = (newTab: string) => {
  startTransition(() => {
    setTab(newTab) // marked as low priority, won't block input
  })
}
```

**Web Workers for heavy computation:**
```tsx
// worker.ts
self.onmessage = (e) => {
  const result = heavyComputation(e.data)
  self.postMessage(result)
}

// In component
useEffect(() => {
  const worker = new Worker(new URL('./worker.ts', import.meta.url))
  worker.postMessage(largeDataset)
  worker.onmessage = (e) => setResult(e.data)
  return () => worker.terminate()
}, [])
```

### Interactivity Checklist

- [ ] Instant feedback on every user action (button states, loading indicators)
- [ ] Smooth animations (60fps, prefer transform/opacity)
- [ ] Optimistic updates for perceived speed
- [ ] Real-time features where appropriate (chat, notifications, dashboards)
- [ ] Keyboard shortcuts for power users
- [ ] Drag-and-drop where it improves workflow
- [ ] Progressive disclosure for complex interfaces
- [ ] Undo/redo for destructive actions
- [ ] Contextual help (tooltips, inline hints)
- [ ] Responsive touch gestures on mobile (swipe, pinch)

---

## 10. Accessibility (a11y)

A good frontend is usable by everyone, including people using screen readers, keyboard navigation, and assistive tech.

A good frontend is usable by everyone, including people using screen readers, keyboard navigation, and assistive tech.

### Non-negotiable rules

**Semantic HTML first:**
```tsx
// Bad
<div onClick={handleClick} className="button">Submit</div>

// Good
<button type="submit" onClick={handleClick}>Submit</button>
```

**Every image has meaningful alt text:**
```tsx
<Image src="/logo.svg" alt="Aethers AI logo" width={120} height={40} />
// Decorative images: alt=""
```

**Keyboard navigability:**
```tsx
// Ensure custom components handle keyboard events
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
>
```

**Focus management in modals and dialogs:**
```tsx
// Use Radix UI Dialog — handles focus trap, aria, escape key automatically
import * as Dialog from '@radix-ui/react-dialog'

<Dialog.Root>
  <Dialog.Trigger asChild>
    <Button>Open</Button>
  </Dialog.Trigger>
  <Dialog.Content>
    <Dialog.Title>Confirm Action</Dialog.Title>
    <Dialog.Description>Are you sure?</Dialog.Description>
    <Dialog.Close asChild>
      <Button>Cancel</Button>
    </Dialog.Close>
  </Dialog.Content>
</Dialog.Root>
```

**Color contrast:** minimum 4.5:1 ratio for normal text (WCAG AA).

**ARIA labels for icon-only buttons:**
```tsx
<button aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>
```

**Form labels:**
```tsx
<label htmlFor="email">Email address</label>
<input id="email" type="email" name="email" />
```

### Tools
- `axe-core` — automated a11y auditing in tests
- `eslint-plugin-jsx-a11y` — catches a11y issues at write time
- Chrome DevTools → Lighthouse → Accessibility audit

---

## 11. Security

### Environment Variables
```bash
# .env.local
DATABASE_URL=postgres://...           # Server only — never exposed to browser
NEXT_PUBLIC_API_URL=https://api.com   # Safe for browser — prefixed with NEXT_PUBLIC_
```
**Never put secrets in `NEXT_PUBLIC_` variables.**

### Content Security Policy (CSP)
```ts
// next.config.ts
const ContentSecurityPolicy = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src * blob: data:;
  connect-src *;
`

const securityHeaders = [
  { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
  { key: 'Content-Security-Policy', value: ContentSecurityPolicy.replace(/\n/g, '') },
]

export default {
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }]
  },
}
```

### XSS Prevention
- Never use `dangerouslySetInnerHTML` with user-controlled content.
- Sanitize HTML with `DOMPurify` if you must render rich text.
- Validate and escape all user inputs server-side.

### CSRF
- Use `SameSite=Lax` or `SameSite=Strict` cookies.
- Server Actions in Next.js include CSRF protection built-in.

### Authentication
- Use an established auth library: **NextAuth.js** (open source) or **Clerk** (hosted).
- Store tokens in `httpOnly`, `Secure` cookies — never in `localStorage`.
- Implement proper session expiry and refresh token rotation.

```ts
// NextAuth.js example
import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      async authorize(credentials) {
        const user = await validateUser(credentials)
        return user ?? null
      },
    }),
  ],
})
```

---

## 12. Testing

### Testing pyramid for frontends

```
        ┌──────────────┐
        │   E2E Tests  │  (Playwright) — critical user journeys
        │   ~10–20%    │
        ├──────────────┤
        │ Integration  │  (Testing Library) — component interactions
        │   ~30–40%    │
        ├──────────────┤
        │  Unit Tests  │  (Vitest) — utilities, hooks, pure functions
        │   ~50–60%    │
        └──────────────┘
```

### Unit tests with Vitest
```ts
// lib/utils.test.ts
import { describe, it, expect } from 'vitest'
import { formatDate } from './utils'

describe('formatDate', () => {
  it('formats ISO date to readable string', () => {
    expect(formatDate('2025-01-15')).toBe('January 15, 2025')
  })
})
```

### Component tests with React Testing Library
```tsx
// components/LoginForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { LoginForm } from './LoginForm'

test('shows validation error for invalid email', async () => {
  render(<LoginForm />)
  fireEvent.input(screen.getByLabelText(/email/i), { target: { value: 'bad' } })
  fireEvent.submit(screen.getByRole('form'))
  await waitFor(() => {
    expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
  })
})
```

### E2E tests with Playwright
```ts
// tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test'

test('user can log in and reach dashboard', async ({ page }) => {
  await page.goto('/login')
  await page.fill('[name=email]', 'user@example.com')
  await page.fill('[name=password]', 'password123')
  await page.click('button[type=submit]')
  await expect(page).toHaveURL('/dashboard')
  await expect(page.locator('h1')).toContainText('Welcome')
})
```

---

## 13. Developer Experience & Tooling

### Essential config files

**TypeScript** — strict mode, always.
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

**ESLint**
```json
// .eslintrc.json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended",
    "plugin:jsx-a11y/recommended"
  ],
  "rules": {
    "no-console": "warn",
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

**Prettier**
```json
// .prettierrc
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2
}
```

### Git hooks with Husky + lint-staged
```json
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{css,md,json}": "prettier --write"
  }
}
```

### Recommended VS Code extensions
- **ESLint** — real-time linting
- **Prettier** — on-save formatting
- **Tailwind CSS IntelliSense** — class autocomplete
- **TypeScript Error Translator** — human-readable TS errors
- **Error Lens** — inline error display

---

## 14. CI/CD & Deployment

### Vercel (easiest for Next.js)
- Connect GitHub repo → auto-deploy on push
- Preview deployments on every PR
- Built-in analytics, edge functions, image optimization

### GitHub Actions pipeline
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run type-check      # tsc --noEmit
      - run: npm run lint
      - run: npm run test -- --run   # vitest --run (no watch mode in CI)
      - run: npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: quality
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run build
      - run: npx playwright test
```

### Environment strategy
| Environment | Purpose                    | Trigger              |
|-------------|----------------------------|----------------------|
| Local       | Development                | Developer machine    |
| Preview     | PR review and QA           | Every PR             |
| Staging     | Pre-production validation  | Merge to `develop`   |
| Production  | Live users                 | Merge to `main`      |

---

## 15. What a Best-in-Class Frontend Looks Like End-to-End

Here's a summary of every dimension a production-grade frontend should nail:

### Architecture ✅
- [ ] App Router (Next.js) or Vite + React for SPAs
- [ ] TypeScript strict mode throughout
- [ ] Server Components for data fetching where possible
- [ ] Clean separation: UI components / feature components / pages / hooks / lib / store

### Data & State ✅
- [ ] TanStack Query for server state (caching, refetching, loading/error states)
- [ ] Zustand for global UI state (sidebars, modals, themes)
- [ ] React Hook Form + Zod for all forms
- [ ] No prop drilling beyond 2 levels

### UI & UX ✅
- [ ] Design tokens in Tailwind config
- [ ] Consistent spacing, typography, color system
- [ ] Loading states for every async operation (Skeleton screens, not spinners)
- [ ] Empty states for every list/table
- [ ] Error states with actionable messages (not "Something went wrong")
- [ ] Optimistic updates for perceived speed
- [ ] Toast notifications for background actions

### Performance ✅
- [ ] LCP < 2.5s, CLS < 0.1, INP < 200ms
- [ ] All images via `next/image`
- [ ] Fonts via `next/font`
- [ ] Dynamic imports for heavy components
- [ ] Bundle < 100KB initial JS (exclude vendor chunks)
- [ ] No N+1 fetch waterfall on page load

### Accessibility ✅
- [ ] All interactive elements keyboard-navigable
- [ ] ARIA labels on icon-only buttons
- [ ] Color contrast ratio ≥ 4.5:1
- [ ] Focus visible (not hidden by CSS)
- [ ] Screen reader tested (VoiceOver / NVDA)
- [ ] No flashing content

### Security ✅
- [ ] CSP headers configured
- [ ] Secrets never in `NEXT_PUBLIC_` env vars
- [ ] Auth tokens in `httpOnly` cookies
- [ ] Input sanitized before rendering
- [ ] Dependencies audited (`npm audit`)

### Testing ✅
- [ ] Unit tests for all utility functions and custom hooks
- [ ] Integration tests for complex components
- [ ] E2E tests for critical user paths (login, checkout, core workflow)
- [ ] > 80% coverage on business logic

### DX & Maintainability ✅
- [ ] ESLint + Prettier enforced in CI
- [ ] Pre-commit hooks via Husky
- [ ] Absolute imports (`@/components/...`)
- [ ] No `any` types
- [ ] Storybook or similar for component documentation

---

## Recommended Stack Summary

```
Layer           | Choice
────────────────|────────────────────────────────────────
Framework       | Next.js 14+ (App Router)
Language        | TypeScript (strict)
Styling         | Tailwind CSS + shadcn/ui (Radix primitives)
State           | TanStack Query + Zustand
Forms           | React Hook Form + Zod
Auth            | NextAuth.js or Clerk
Testing         | Vitest + React Testing Library + Playwright
Linting         | ESLint + Prettier + lint-staged
Deployment      | Vercel (primary) or Docker + AWS/GCP
Monitoring      | Sentry (errors) + Vercel Analytics (vitals)
```

---

*Report written for the Aethers AI project — October 2026*
