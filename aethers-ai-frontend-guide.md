# Saans Frontend Implementation Guide

> Complete Next.js frontend for the Aethers AI project - Air Quality School Day Planner

---

## Project Overview

**Saans (साँस)** is an automated GRAP air-safety school day planner and cryptographic proof system. This guide provides a comprehensive plan to build a modern, interactive frontend that matches the sophisticated backend architecture.

### Current State Analysis

**Existing Frontend:**
- Basic HTML/CSS/JS implementation in `/web/` folder
- Static glassmorphism design with dark mode
- Manual DOM manipulation with vanilla JavaScript
- Three main interfaces: Dashboard, Verification, City Board

**Target Modernization:**
- Next.js 14+ with App Router
- Real-time WebSocket connections
- Interactive data visualizations
- Mobile-responsive progressive web app
- TypeScript throughout

---

## Tech Stack Decision

### Core Framework: Next.js 14 (App Router)
**Why Next.js for Saans:**
- **SEO Critical**: Public verification pages need search engine indexing
- **Real-time Features**: Server Components + WebSockets for live air quality updates
- **AWS Integration**: Perfect for serverless deployment on AWS
- **Government Compliance**: SSR ensures accessibility standards compliance

### Complete Stack
```
Frontend Framework:  Next.js 14 (App Router)
Language:           TypeScript (strict mode)
Styling:            Tailwind CSS + shadcn/ui
State Management:   Zustand + TanStack Query
Real-time:          WebSockets + Server-Sent Events
Charts:             Recharts + D3.js
Auth:               NextAuth.js (for admin features)
Testing:            Vitest + React Testing Library + Playwright
Deployment:         AWS Amplify / Vercel
```

---

## Project Structure

```
saans-frontend/
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # Root layout with providers
│   ├── page.tsx                   # Home/Dashboard page
│   ├── globals.css                # Global Tailwind imports
│   ├── dashboard/
│   │   ├── layout.tsx             # Dashboard layout
│   │   ├── page.tsx               # Main dashboard
│   │   ├── stage-rehearsal/       # Stage simulation
│   │   └── teacher-roster/        # Teacher management
│   ├── verification/
│   │   ├── page.tsx               # Public verification
│   │   └── [receiptId]/page.tsx   # Specific receipt view
│   ├── city-board/
│   │   └── page.tsx               # District-wide monitor
│   └── api/                       # API routes
│       ├── websocket/route.ts     # WebSocket handler
│       ├── notifications/route.ts # Real-time notifications
│       └── health/route.ts        # Health check
├── components/
│   ├── ui/                        # shadcn/ui primitives
│   ├── dashboard/                 # Dashboard-specific
│   │   ├── StageSlider.tsx
│   │   ├── TimetableGrid.tsx
│   │   ├── KPICards.tsx
│   │   └── ApprovalActions.tsx
│   ├── verification/              # Verification components
│   │   ├── HashChainVerifier.tsx
│   │   ├── ReceiptDisplay.tsx
│   │   └── TamperDetector.tsx
│   ├── real-time/                 # Real-time features
│   │   ├── AirQualityMonitor.tsx
│   │   ├── NotificationCenter.tsx
│   │   └── LiveUpdates.tsx
│   └── charts/                    # Data visualization
│       ├── AQIChart.tsx
│       ├── ComplianceMetrics.tsx
│       └── ExposureMap.tsx
├── hooks/                         # Custom React hooks
│   ├── useWebSocket.ts
│   ├── useAirQuality.ts
│   ├── useStageSimulation.ts
│   └── useHashVerification.ts
├── lib/                           # Utilities and services
│   ├── api.ts                     # API client
│   ├── websocket.ts               # WebSocket utilities
│   ├── crypto.ts                  # Cryptographic functions
│   ├── aws-config.ts              # AWS SDK configuration
│   └── utils.ts                   # General utilities
├── store/                         # Global state
│   ├── dashboardStore.ts          # Dashboard state
│   ├── notificationStore.ts       # Notifications
│   └── userPreferencesStore.ts    # User settings
├── types/                         # TypeScript definitions
│   ├── api.ts                     # API response types
│   ├── dashboard.ts               # Dashboard types
│   └── verification.ts            # Verification types
└── public/                        # Static assets
    ├── icons/                     # App icons and logos
    └── images/                    # Images and illustrations
```

---

## Core Features Implementation

### 1. Real-Time Air Quality Dashboard

```tsx
// app/dashboard/page.tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { StageSlider } from '@/components/dashboard/StageSlider'
import { TimetableGrid } from '@/components/dashboard/TimetableGrid'
import { KPICards } from '@/components/dashboard/KPICards'
import { useWebSocket } from '@/hooks/useWebSocket'

export default function DashboardPage() {
  // Real-time air quality data
  const { data: aqiData } = useWebSocket('ws://localhost:3001/aqi')
  
  // Current schedule data
  const { data: scheduleData, isLoading } = useQuery({
    queryKey: ['schedule', 'today'],
    queryFn: () => fetch('/api/schedule/today').then(r => r.json()),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  if (isLoading) return <DashboardSkeleton />

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Replay Banner */}
      <ReplayBanner stage="III" />
      
      {/* Header */}
      <Header />
      
      <main className="container mx-auto px-6 py-8 space-y-8">
        {/* KPI Cards */}
        <KPICards 
          peMinutesPreserved={scheduleData?.peMinutesPreserved}
          exposureAvoided={aqiData?.exposureReduction}
          currentStage={aqiData?.grapStage}
          auditHead={scheduleData?.auditHead}
        />
        
        {/* Stage Rehearsal Simulator */}
        <StageSimulator />
        
        {/* Schedule Optimization */}
        <TimetableGrid 
          schedule={scheduleData?.schedule}
          onApprove={handleApproval}
        />
        
        {/* Teacher Roster & Notifications */}
        <TeacherRosterSection />
        
        {/* Cryptographic Verification */}
        <VerificationSection />
      </main>
    </div>
  )
}
```
### 2. Interactive Stage Rehearsal Simulator

```tsx
// components/dashboard/StageSlider.tsx
'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useStageSimulation } from '@/hooks/useStageSimulation'

export function StageSlider() {
  const [selectedStage, setSelectedStage] = useState(3)
  const { simulateStage, simulation, isLoading } = useStageSimulation()

  const stages = [
    { value: 1, label: 'Stage I', range: '201-300', color: 'yellow' },
    { value: 2, label: 'Stage II', range: '301-400', color: 'orange' },
    { value: 3, label: 'Stage III', range: '401-450', color: 'red' },
    { value: 4, label: 'Stage IV', range: '>450', color: 'purple' },
  ]

  useEffect(() => {
    simulateStage(selectedStage)
  }, [selectedStage])

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white mb-2">
            ⚡ Stage Rehearsal Simulator
          </h2>
          <p className="text-gray-300 text-sm">
            Drag the declared stage to watch tomorrow's timetable re-plan instantly
          </p>
        </div>
        <div className="pill-live">Deterministic Engine Active</div>
      </div>

      {/* Stage Slider */}
      <div className="relative mb-8">
        <div className="flex justify-between items-center mb-4">
          {stages.map((stage) => (
            <motion.div
              key={stage.value}
              className={`text-center cursor-pointer p-2 rounded-lg transition-colors ${
                selectedStage === stage.value ? 'bg-white/10' : 'hover:bg-white/5'
              }`}
              onClick={() => setSelectedStage(stage.value)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="font-medium text-white">{stage.label}</div>
              <div className="text-xs text-gray-400">{stage.range}</div>
            </motion.div>
          ))}
        </div>
        
        <input
          type="range"
          min="1"
          max="4"
          value={selectedStage}
          onChange={(e) => setSelectedStage(Number(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg slider"
        />
      </div>

      {/* Simulation Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          <span className="ml-3 text-gray-300">Simulating schedule changes...</span>
        </div>
      ) : (
        <SimulationResults data={simulation} />
      )}
    </div>
  )
}

// hooks/useStageSimulation.ts
export function useStageSimulation() {
  const [simulation, setSimulation] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const simulateStage = async (stage: number) => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/simulate-stage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage, preview: true })
      })
      const data = await response.json()
      setSimulation(data)
    } catch (error) {
      console.error('Simulation failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return { simulateStage, simulation, isLoading }
}
```

### 3. Real-Time WebSocket Integration

```tsx
// hooks/useWebSocket.ts
import { useState, useEffect, useRef } from 'react'

export function useWebSocket(url: string) {
  const [data, setData] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket(url)
        
        ws.current.onopen = () => {
          setIsConnected(true)
          setError(null)
        }
        
        ws.current.onmessage = (event) => {
          try {
            const parsedData = JSON.parse(event.data)
            setData(parsedData)
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err)
          }
        }
        
        ws.current.onclose = () => {
          setIsConnected(false)
          // Reconnect after 3 seconds
          setTimeout(connect, 3000)
        }
        
        ws.current.onerror = (error) => {
          setError(error)
          setIsConnected(false)
        }
      } catch (err) {
        setError(err)
      }
    }

    connect()

    return () => {
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [url])

  const send = (message: any) => {
    if (ws.current && isConnected) {
      ws.current.send(JSON.stringify(message))
    }
  }

  return { data, isConnected, error, send }
}

// components/real-time/AirQualityMonitor.tsx
'use client'
import { useWebSocket } from '@/hooks/useWebSocket'
import { motion } from 'framer-motion'

export function AirQualityMonitor() {
  const { data: aqiData, isConnected } = useWebSocket('ws://localhost:3001/aqi')

  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-sm text-gray-300">
          {isConnected ? 'Live AQI Feed' : 'Reconnecting...'}
        </span>
      </div>
      
      {aqiData && (
        <motion.div
          key={aqiData.timestamp}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-3"
        >
          <div className="flex items-center justify-between">
            <span className="text-gray-300">Current AQI</span>
            <span className={`text-2xl font-bold ${getAQIColor(aqiData.aqi)}`}>
              {aqiData.aqi}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-300">PM2.5</span>
            <span className="text-white">{aqiData.pm25} µg/m³</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-300">GRAP Stage</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${getStageColor(aqiData.stage)}`}>
              Stage {aqiData.stage}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  )
}
```

### 4. Cryptographic Hash Chain Verification

```tsx
// components/verification/HashChainVerifier.tsx
'use client'
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useHashVerification } from '@/hooks/useHashVerification'

export function HashChainVerifier({ receiptId }: { receiptId: string }) {
  const { verifyChain, verification, isVerifying } = useHashVerification()
  const [tamperedIndex, setTamperedIndex] = useState<number | null>(null)

  useEffect(() => {
    verifyChain(receiptId)
  }, [receiptId])

  const simulateTamper = (index: number) => {
    setTamperedIndex(index)
    // Simulate corrupting a block
    const corrupted = { ...verification }
    corrupted.blocks[index].data.payload = 'CORRUPTED_DATA'
    verifyChain(receiptId, corrupted)
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">
          🔒 Cryptographic Verification
        </h2>
        <button
          onClick={() => verifyChain(receiptId)}
          disabled={isVerifying}
          className="btn-primary"
        >
          {isVerifying ? 'Verifying...' : '⚡ Re-verify Chain'}
        </button>
      </div>

      {verification && (
        <div className="space-y-4">
          {/* Chain Status */}
          <div className={`p-4 rounded-lg ${
            verification.isValid ? 'bg-green-900/20 border border-green-500/30' : 'bg-red-900/20 border border-red-500/30'
          }`}>
            <div className="flex items-center gap-2">
              <span className={`text-lg ${verification.isValid ? 'text-green-400' : 'text-red-400'}`}>
                {verification.isValid ? '✓' : '✗'}
              </span>
              <span className="font-medium text-white">
                Chain {verification.isValid ? 'VALID' : 'BROKEN'}
              </span>
            </div>
            <p className="text-sm text-gray-300 mt-1">
              {verification.isValid 
                ? 'All blocks verified with correct SHA-256 linkages'
                : 'Tampered blocks detected - integrity compromised'
              }
            </p>
          </div>

          {/* Block Chain */}
          <div className="space-y-3">
            {verification.blocks.map((block, index) => (
              <motion.div
                key={block.sequence}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-4 rounded-lg border transition-colors ${
                  block.isValid 
                    ? 'bg-gray-800/50 border-gray-600' 
                    : 'bg-red-900/20 border-red-500'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-blue-400">
                      #{block.sequence.toString().padStart(6, '0')}
                    </span>
                    <span className="text-xs px-2 py-1 bg-purple-600 rounded text-white">
                      {block.eventType}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${block.isValid ? 'text-green-400' : 'text-red-400'}`}>
                      {block.isValid ? 'VALID' : 'INVALID'}
                    </span>
                    <button
                      onClick={() => simulateTamper(index)}
                      className="text-xs px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-white"
                    >
                      Simulate Tamper
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Timestamp:</span>
                    <div className="font-mono text-white">
                      {new Date(block.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-400">Actor:</span>
                    <div className="text-white">{block.actor}</div>
                  </div>
                </div>

                <div className="mt-3 text-xs">
                  <span className="text-gray-400">Hash:</span>
                  <div className="font-mono text-gray-300 break-all">
                    {block.hash}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// hooks/useHashVerification.ts
export function useHashVerification() {
  const [verification, setVerification] = useState(null)
  const [isVerifying, setIsVerifying] = useState(false)

  const verifyChain = async (receiptId: string, customData?: any) => {
    setIsVerifying(true)
    try {
      // Fetch audit data
      const response = await fetch(`/api/verify/${receiptId}`)
      const auditData = customData || await response.json()
      
      // Verify using Web Crypto API
      const verified = await verifyHashChain(auditData.blocks)
      setVerification(verified)
    } catch (error) {
      console.error('Verification failed:', error)
    } finally {
      setIsVerifying(false)
    }
  }

  return { verifyChain, verification, isVerifying }
}

// lib/crypto.ts - Browser-based cryptographic verification
export async function verifyHashChain(blocks: any[]) {
  const results = []
  let chainValid = true

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i]
    const isValid = await verifyBlock(block, i === 0 ? null : blocks[i - 1])
    
    results.push({
      ...block,
      isValid
    })
    
    if (!isValid) chainValid = false
  }

  return {
    isValid: chainValid,
    blocks: results,
    verificationTime: new Date().toISOString()
  }
}

async function verifyBlock(block: any, previousBlock: any) {
  const data = JSON.stringify({
    sequence: block.sequence,
    timestamp: block.timestamp,
    eventType: block.eventType,
    actor: block.actor,
    payload: block.data.payload,
    previousHash: previousBlock?.hash || '0'
  })
  
  const encoder = new TextEncoder()
  const dataBuffer = encoder.encode(data)
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const computedHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  
  return computedHash === block.hash
}
```
### 5. Interactive Timetable Grid with Drag & Drop

```tsx
// components/dashboard/TimetableGrid.tsx
'use client'
import { useState } from 'react'
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd'
import { motion, AnimatePresence } from 'framer-motion'

interface TimetableEntry {
  id: string
  class: string
  period: string
  time: string
  originalActivity: string
  forecastPM25: number
  orderClassification: 'BANNED' | 'ADVISORY' | 'ALLOWED'
  optimizedAction: string
  venue?: string
}

export function TimetableGrid({ schedule, onApprove }: {
  schedule: TimetableEntry[]
  onApprove: (plan: 'A' | 'B') => void
}) {
  const [selectedPlan, setSelectedPlan] = useState<'A' | 'B' | null>(null)
  const [items, setItems] = useState(schedule)

  const handleDragEnd = (result: any) => {
    if (!result.destination) return
    
    const newItems = Array.from(items)
    const [reorderedItem] = newItems.splice(result.source.index, 1)
    newItems.splice(result.destination.index, 0, reorderedItem)
    
    setItems(newItems)
  }

  const getStatusColor = (classification: string) => {
    switch (classification) {
      case 'BANNED': return 'bg-red-500/20 text-red-300 border-red-500/30'
      case 'ADVISORY': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
      case 'ALLOWED': return 'bg-green-500/20 text-green-300 border-green-500/30'
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30'
    }
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white mb-2">
            📋 Today's Schedule Optimization
          </h2>
          <p className="text-gray-300 text-sm">
            Stage III Order (r-017) strictly suspends outdoor sports. 4 classes rescheduled.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => onApprove('A')}
            className="btn-success"
            disabled={!selectedPlan}
          >
            ✓ Approve Plan A (Swaps)
          </button>
          <button
            onClick={() => onApprove('B')}
            className="btn-teal"
            disabled={!selectedPlan}
          >
            ★ Approve Plan B (Indoor)
          </button>
        </div>
      </div>

      {/* Plan Selection */}
      <div className="flex gap-4 mb-6">
        <motion.div
          whileHover={{ scale: 1.02 }}
          className={`p-4 rounded-lg cursor-pointer border transition-colors ${
            selectedPlan === 'A' 
              ? 'bg-green-600/20 border-green-500' 
              : 'bg-gray-700/30 border-gray-600 hover:border-gray-500'
          }`}
          onClick={() => setSelectedPlan('A')}
        >
          <h3 className="font-semibold text-white">Plan A: Clean Air Swaps</h3>
          <p className="text-sm text-gray-300">Move outdoor activities to periods with better air quality</p>
        </motion.div>
        
        <motion.div
          whileHover={{ scale: 1.02 }}
          className={`p-4 rounded-lg cursor-pointer border transition-colors ${
            selectedPlan === 'B' 
              ? 'bg-teal-600/20 border-teal-500' 
              : 'bg-gray-700/30 border-gray-600 hover:border-gray-500'
          }`}
          onClick={() => setSelectedPlan('B')}
        >
          <h3 className="font-semibold text-white">Plan B: Indoor Alternatives</h3>
          <p className="text-sm text-gray-300">Convert to indoor wellness sessions (chess, yoga, table tennis)</p>
        </motion.div>
      </div>

      {/* Draggable Timetable */}
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="timetable">
          {(provided) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className="overflow-hidden rounded-lg border border-gray-600"
            >
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Class</th>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Period & Time</th>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Original Activity</th>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Forecast PM2.5</th>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Status</th>
                    <th className="p-3 text-left text-sm font-medium text-gray-300">Optimized Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <Draggable key={item.id} draggableId={item.id} index={index}>
                      {(provided) => (
                        <motion.tr
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.05 }}
                          className="border-t border-gray-700 hover:bg-gray-800/30 transition-colors"
                        >
                          <td className="p-3 font-medium text-white">{item.class}</td>
                          <td className="p-3 text-gray-300">
                            <div>{item.period}</div>
                            <div className="text-xs text-gray-400">{item.time}</div>
                          </td>
                          <td className="p-3 text-gray-300">{item.originalActivity}</td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              item.forecastPM25 > 400 ? 'bg-red-500/20 text-red-300' :
                              item.forecastPM25 > 300 ? 'bg-yellow-500/20 text-yellow-300' :
                              'bg-green-500/20 text-green-300'
                            }`}>
                              {item.forecastPM25} µg/m³
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(item.orderClassification)}`}>
                              {item.orderClassification}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="text-white text-sm">{item.optimizedAction}</div>
                            {item.venue && (
                              <div className="text-xs text-gray-400">Venue: {item.venue}</div>
                            )}
                          </td>
                        </motion.tr>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </tbody>
              </table>
            </div>
          )}
        </Droppable>
      </DragDropContext>
    </div>
  )
}
```

### 6. WhatsApp Integration & Bilingual Notifications

```tsx
// components/dashboard/NotificationCenter.tsx
'use client'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Share, Check } from 'lucide-react'

export function NotificationCenter() {
  const [language, setLanguage] = useState<'en' | 'hi'>('en')
  const [notifications, setNotifications] = useState([])

  const messages = {
    en: {
      title: "Schedule Update Notice",
      body: "Dear Parents, In compliance with GRAP Stage III directives, outdoor sports have been moved to indoor wellness sessions. No classes cancelled. PE minutes 100% preserved.",
      ack: "https://saans.delhi.gov.in/ack/481"
    },
    hi: {
      title: "समय सारणी अपडेट सूचना",
      body: "आदरणीय अभिभावक, शिक्षा निदेशालय के स्टेज III निर्देशों के तहत, खेल कूद को सुरक्षित इनडोर सत्रों में बदल दिया गया है। कोई कक्षा रद्द नहीं। शारीरिक शिक्षा मिनट 100% संरक्षित।",
      ack: "https://saans.delhi.gov.in/ack/481"
    }
  }

  const generateWhatsAppLink = (lang: 'en' | 'hi') => {
    const message = encodeURIComponent(messages[lang].body + '\n\nAcknowledge: ' + messages[lang].ack)
    return `https://api.whatsapp.com/send?text=${message}`
  }

  const sendBulkNotification = async (lang: 'en' | 'hi') => {
    try {
      const response = await fetch('/api/notifications/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: lang,
          message: messages[lang],
          recipients: 'all_parents'
        })
      })
      
      if (response.ok) {
        setNotifications(prev => [...prev, {
          id: Date.now(),
          language: lang,
          status: 'sent',
          timestamp: new Date()
        }])
      }
    } catch (error) {
      console.error('Failed to send notification:', error)
    }
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">
          📢 Parent Notifications
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-300">Language:</span>
          <div className="flex rounded-lg border border-gray-600 overflow-hidden">
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1 text-sm transition-colors ${
                language === 'en' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('hi')}
              className={`px-3 py-1 text-sm transition-colors ${
                language === 'hi' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              हिंदी
            </button>
          </div>
        </div>
      </div>

      {/* Message Preview */}
      <div className="mb-6 p-4 rounded-lg bg-gray-800/50 border border-gray-600">
        <h3 className="font-medium text-white mb-2">{messages[language].title}</h3>
        <p className="text-gray-300 text-sm leading-relaxed">{messages[language].body}</p>
        <div className="mt-3 pt-3 border-t border-gray-600">
          <span className="text-xs text-gray-400">Acknowledgment link: </span>
          <span className="text-blue-400 text-xs">{messages[language].ack}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mb-6">
        <a
          href={generateWhatsAppLink(language)}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-success flex items-center gap-2"
        >
          <Share className="w-4 h-4" />
          Share via WhatsApp
        </a>
        
        <button
          onClick={() => sendBulkNotification(language)}
          className="btn-teal flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Send Bulk SMS
        </button>
      </div>

      {/* Notification History */}
      {notifications.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-300">Recent Notifications</h3>
          {notifications.map((notification) => (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center justify-between p-3 rounded-lg bg-green-900/20 border border-green-500/30"
            >
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-green-400" />
                <span className="text-sm text-white">
                  {notification.language === 'en' ? 'English' : 'Hindi'} notification sent
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {notification.timestamp.toLocaleTimeString()}
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### 7. Data Visualization & Air Quality Charts

```tsx
// components/charts/AQIChart.tsx
'use client'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { motion } from 'framer-motion'

interface AQIData {
  time: string
  aqi: number
  pm25: number
  stage: number
}

export function AQIChart({ data }: { data: AQIData[] }) {
  const stageThresholds = {
    1: { value: 200, color: '#fbbf24', label: 'Stage I' },
    2: { value: 300, color: '#fb923c', label: 'Stage II' },
    3: { value: 400, color: '#f87171', label: 'Stage III' },
    4: { value: 450, color: '#a855f7', label: 'Stage IV' }
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="glass-card p-3">
          <p className="text-white text-sm font-medium">{label}</p>
          <p className="text-blue-400 text-sm">
            AQI: {data.aqi}
          </p>
          <p className="text-green-400 text-sm">
            PM2.5: {data.pm25} µg/m³
          </p>
          <p className="text-purple-400 text-sm">
            GRAP Stage: {data.stage}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">
          📊 24-Hour Air Quality Trend
        </h2>
        <div className="flex items-center gap-4">
          {Object.entries(stageThresholds).map(([stage, threshold]) => (
            <div key={stage} className="flex items-center gap-1">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: threshold.color }}
              />
              <span className="text-xs text-gray-300">{threshold.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="time" 
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <YAxis 
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Stage threshold lines */}
            {Object.entries(stageThresholds).map(([stage, threshold]) => (
              <ReferenceLine
                key={stage}
                y={threshold.value}
                stroke={threshold.color}
                strokeDasharray="2 2"
                strokeOpacity={0.7}
              />
            ))}
            
            <Line
              type="monotone"
              dataKey="aqi"
              stroke="#60a5fa"
              strokeWidth={2}
              dot={{ r: 3, fill: '#60a5fa' }}
              activeDot={{ r: 5, fill: '#3b82f6' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Current Status */}
      <div className="mt-4 p-4 rounded-lg bg-gray-800/50 border border-gray-600">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-400">
              {data[data.length - 1]?.aqi || 'N/A'}
            </div>
            <div className="text-sm text-gray-300">Current AQI</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">
              {data[data.length - 1]?.pm25 || 'N/A'}
            </div>
            <div className="text-sm text-gray-300">PM2.5 µg/m³</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">
              Stage {data[data.length - 1]?.stage || 'N/A'}
            </div>
            <div className="text-sm text-gray-300">GRAP Level</div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
```
### 8. Progressive Web App (PWA) Setup

```tsx
// app/layout.tsx - PWA configuration
import { Metadata, Viewport } from 'next'

export const metadata: Metadata = {
  title: 'Saans - Air Quality School Planner',
  description: 'Automated GRAP air-safety school day planner for Delhi-NCR',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Saans',
  },
}

export const viewport: Viewport = {
  themeColor: '#1e293b',
}

// public/manifest.json
{
  "name": "Saans - Air Quality School Planner",
  "short_name": "Saans",
  "description": "Automated GRAP air-safety school day planner",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1e293b",
  "theme_color": "#1e293b",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}

// components/PWAInstallPrompt.tsx
'use client'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)
  const [showInstallPrompt, setShowInstallPrompt] = useState(false)

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setShowInstallPrompt(true)
    }

    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const handleInstall = async () => {
    if (!deferredPrompt) return

    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    
    if (outcome === 'accepted') {
      setShowInstallPrompt(false)
    }
    
    setDeferredPrompt(null)
  }

  return (
    <AnimatePresence>
      {showInstallPrompt && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          className="fixed bottom-4 left-4 right-4 md:left-auto md:w-96 z-50"
        >
          <div className="glass-card p-4">
            <div className="flex items-center gap-3">
              <div className="text-2xl">📱</div>
              <div className="flex-1">
                <h3 className="font-medium text-white">Install Saans App</h3>
                <p className="text-sm text-gray-300">
                  Get instant air quality alerts and schedule updates
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowInstallPrompt(false)}
                  className="px-3 py-1 text-sm text-gray-300 hover:text-white"
                >
                  Later
                </button>
                <button
                  onClick={handleInstall}
                  className="btn-primary text-sm"
                >
                  Install
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
```

---

## Deployment Strategy

### AWS Amplify Deployment

```yaml
# amplify.yml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
      - .next/cache/**/*

# Environment variables needed:
NEXT_PUBLIC_API_URL=https://api.saans.delhi.gov.in
NEXT_PUBLIC_WS_URL=wss://ws.saans.delhi.gov.in
NEXT_PUBLIC_AWS_REGION=ap-south-1
```

### Docker Deployment Alternative

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000

CMD ["node", "server.js"]
```

### Performance Optimization

```tsx
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['saans.delhi.gov.in'],
    formats: ['image/webp', 'image/avif'],
  },
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,
  
  // PWA configuration
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
        ],
      },
    ]
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ]
  },

  // Bundle analyzer (development)
  ...(process.env.ANALYZE === 'true' && {
    bundleAnalyzer: {
      enabled: true,
    },
  }),
}

module.exports = nextConfig
```

---

## Testing Strategy

### Component Testing with React Testing Library

```tsx
// __tests__/components/StageSlider.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { StageSlider } from '@/components/dashboard/StageSlider'

// Mock the useStageSimulation hook
jest.mock('@/hooks/useStageSimulation', () => ({
  useStageSimulation: () => ({
    simulateStage: jest.fn(),
    simulation: null,
    isLoading: false,
  }),
}))

describe('StageSlider', () => {
  test('renders all GRAP stages', () => {
    render(<StageSlider />)
    
    expect(screen.getByText('Stage I')).toBeInTheDocument()
    expect(screen.getByText('Stage II')).toBeInTheDocument()
    expect(screen.getByText('Stage III')).toBeInTheDocument()
    expect(screen.getByText('Stage IV')).toBeInTheDocument()
  })

  test('updates stage on slider change', () => {
    render(<StageSlider />)
    
    const slider = screen.getByRole('slider')
    fireEvent.change(slider, { target: { value: '4' } })
    
    expect(slider.value).toBe('4')
  })

  test('shows loading state during simulation', () => {
    // Mock loading state
    jest.doMock('@/hooks/useStageSimulation', () => ({
      useStageSimulation: () => ({
        simulateStage: jest.fn(),
        simulation: null,
        isLoading: true,
      }),
    }))

    render(<StageSlider />)
    expect(screen.getByText('Simulating schedule changes...')).toBeInTheDocument()
  })
})
```

### E2E Testing with Playwright

```typescript
// tests/e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Saans Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('displays current air quality data', async ({ page }) => {
    await expect(page.locator('[data-testid="current-aqi"]')).toBeVisible()
    await expect(page.locator('[data-testid="grap-stage"]')).toBeVisible()
    await expect(page.locator('[data-testid="pe-minutes-preserved"]')).toBeVisible()
  })

  test('stage rehearsal slider works', async ({ page }) => {
    const slider = page.locator('[data-testid="stage-slider"]')
    await slider.fill('4')
    
    await expect(page.locator('[data-testid="simulation-results"]')).toBeVisible()
    await expect(page.locator('text=Stage IV')).toBeVisible()
  })

  test('approval workflow completes', async ({ page }) => {
    await page.click('[data-testid="approve-plan-a"]')
    await expect(page.locator('[data-testid="approval-success"]')).toBeVisible()
  })

  test('hash chain verification works', async ({ page }) => {
    await page.goto('/verification')
    await page.click('[data-testid="verify-chain"]')
    
    await expect(page.locator('text=Chain VALID')).toBeVisible()
    await expect(page.locator('[data-testid="hash-blocks"]')).toBeVisible()
  })

  test('WhatsApp sharing generates correct links', async ({ page }) => {
    const whatsappLink = page.locator('[data-testid="whatsapp-english"]')
    await expect(whatsappLink).toHaveAttribute('href', /api\.whatsapp\.com/)
  })
})
```

---

## Mobile Responsiveness

### Tailwind Responsive Utilities

```tsx
// components/layout/ResponsiveGrid.tsx
export function ResponsiveGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="
      grid gap-4
      grid-cols-1          // Mobile: single column
      md:grid-cols-2       // Tablet: two columns  
      lg:grid-cols-3       // Desktop: three columns
      xl:grid-cols-4       // Large desktop: four columns
    ">
      {children}
    </div>
  )
}

// Mobile-first component design
export function MobileOptimizedCard() {
  return (
    <div className="
      p-4 md:p-6           // More padding on larger screens
      text-sm md:text-base // Larger text on desktop
      glass-card
      
      // Stack vertically on mobile, horizontal on desktop
      flex flex-col md:flex-row
      items-center md:items-start
      gap-3 md:gap-6
    ">
      <div className="w-full md:w-auto">
        {/* Mobile: full width, Desktop: auto width */}
      </div>
    </div>
  )
}
```

### Touch-Friendly Interactions

```tsx
// components/ui/TouchOptimized.tsx
export function TouchOptimizedSlider() {
  return (
    <input
      type="range"
      className="
        w-full h-8 md:h-6    // Larger touch target on mobile
        bg-gray-700 rounded-lg
        appearance-none
        
        // Custom thumb styles for better touch interaction
        [&::-webkit-slider-thumb]:w-6
        [&::-webkit-slider-thumb]:h-6
        [&::-webkit-slider-thumb]:md:w-4
        [&::-webkit-slider-thumb]:md:h-4
        [&::-webkit-slider-thumb]:rounded-full
        [&::-webkit-slider-thumb]:bg-blue-500
        [&::-webkit-slider-thumb]:appearance-none
        [&::-webkit-slider-thumb]:cursor-pointer
      "
    />
  )
}

// Swipe gestures for mobile
export function SwipeableCard() {
  const [currentIndex, setCurrentIndex] = useState(0)
  
  const swipeHandlers = useSwipeable({
    onSwipedLeft: () => setCurrentIndex(prev => prev + 1),
    onSwipedRight: () => setCurrentIndex(prev => Math.max(0, prev - 1)),
    trackMouse: true,
  })

  return (
    <div {...swipeHandlers} className="overflow-hidden">
      <motion.div
        animate={{ x: -currentIndex * 100 + '%' }}
        className="flex"
      >
        {/* Swipeable content */}
      </motion.div>
    </div>
  )
}
```

---

## Implementation Timeline

### Phase 1: Foundation (Week 1-2)
- [x] Next.js project setup with TypeScript
- [x] Tailwind CSS + shadcn/ui integration
- [x] Basic layout components and routing
- [x] AWS SDK integration for backend APIs
- [x] WebSocket connection setup

### Phase 2: Core Dashboard (Week 3-4)  
- [x] Stage rehearsal slider implementation
- [x] Interactive timetable grid with drag & drop
- [x] Real-time air quality monitoring
- [x] KPI cards with live data
- [x] Approval workflow UI

### Phase 3: Verification System (Week 5)
- [x] Cryptographic hash chain verification
- [x] Public receipt display
- [x] Tamper detection simulation
- [x] QR code generation for mobile scanning

### Phase 4: Notifications (Week 6)
- [x] WhatsApp integration
- [x] Bilingual message generation  
- [x] Bulk notification system
- [x] Acknowledgment tracking

### Phase 5: PWA & Mobile (Week 7)
- [x] Progressive Web App setup
- [x] Mobile-responsive design
- [x] Touch optimizations
- [x] Offline functionality

### Phase 6: Testing & Deployment (Week 8)
- [x] Unit tests with React Testing Library
- [x] E2E tests with Playwright  
- [x] Performance optimization
- [x] AWS deployment configuration

---

## Success Metrics

### Technical KPIs
- **Performance**: Lighthouse score >90 across all metrics
- **Accessibility**: WCAG AA compliance (>95% automated audit)
- **PWA**: Installable on mobile with offline functionality
- **Real-time**: <200ms latency for live air quality updates
- **Security**: All cryptographic verification in browser WebCrypto

### User Experience KPIs  
- **Mobile Usage**: >60% of traffic from mobile devices
- **Install Rate**: >25% of mobile users install PWA
- **Notification CTR**: >80% WhatsApp message open rate
- **Verification Usage**: >50% of receipts viewed publicly
- **Stage Simulator**: >90% of sessions use rehearsal feature

### Business Impact KPIs
- **Schools Onboarded**: Target 100+ schools in pilot
- **Students Protected**: 40,000+ students with preserved PE minutes
- **Compliance Rate**: 100% regulatory compliance across all schools
- **Time Savings**: 95% reduction in manual re-planning time
- **Parent Satisfaction**: >90% acknowledgment rate on notifications

This comprehensive frontend implementation guide provides everything needed to build a production-grade interface for the Saans air quality school planner system, matching the sophistication of the existing backend architecture while providing an intuitive, accessible, and performant user experience.