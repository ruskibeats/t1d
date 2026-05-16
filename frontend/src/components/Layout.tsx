/** @jsxImportSource @emotion/react */
import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Activity, BarChart3, Bot, Calendar, Dumbbell, LayoutDashboard, Menu, Moon, Settings, ShieldCheck, Sparkles, Utensils, X } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/glucose', icon: Activity, label: 'Glucose' },
  { to: '/food', icon: Utensils, label: 'Food' },
  { to: '/exercise', icon: Dumbbell, label: 'Exercise' },
  { to: '/sleep', icon: Moon, label: 'Sleep' },
  { to: '/events', icon: Calendar, label: 'Events' },
  { to: '/patterns', icon: BarChart3, label: 'Patterns' },
  { to: '/chat', icon: Bot, label: 'AI chat' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function BrandMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid h-11 w-11 place-items-center rounded-2xl bg-[oklch(0.23_0.055_255)] shadow-[0_16px_36px_oklch(0.23_0.055_255/0.22)]">
        <div className="absolute inset-1 rounded-[14px] border border-[oklch(1_0_0/0.12)]" />
        <Activity className="h-5 w-5 text-[oklch(0.78_0.12_178)]" />
      </div>
      <div>
        <div className="text-lg font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">T1D Companion</div>
        <div className="text-xs font-semibold text-[oklch(0.48_0.035_255)]">Pattern aware, safety first</div>
      </div>
    </div>
  )
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="space-y-1.5">
      {navItems.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) => cn(
              'group flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-bold transition-all duration-200',
              isActive
                ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)] shadow-[0_16px_34px_oklch(0.56_0.19_255/0.22)]'
                : 'text-[oklch(0.43_0.035_255)] hover:bg-[oklch(0.94_0.018_245)] hover:text-[oklch(0.25_0.04_255)]'
            )}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        )
      })}
    </nav>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="app-backdrop min-h-screen">
      <div className="lg:hidden sticky top-0 z-40 border-b border-[oklch(0.88_0.02_250)] bg-[oklch(0.98_0.01_245/0.88)] px-4 py-3 backdrop-blur-xl">
        <div className="flex items-center justify-between">
          <button
            className="rounded-2xl p-2 text-[oklch(0.35_0.04_255)] transition hover:bg-[oklch(0.93_0.018_245)]"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Open navigation"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <BrandMark />
          <button className="text-xs font-bold text-[oklch(0.54_0.15_27)]" onClick={logout}>Sign out</button>
        </div>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-[oklch(0.18_0.04_255/0.42)]" onClick={() => setMobileOpen(false)}>
          <div className="h-full w-80 max-w-[86vw] bg-[oklch(0.98_0.01_245)] p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <BrandMark />
            <div className="mt-8"><Navigation onNavigate={() => setMobileOpen(false)} /></div>
          </div>
        </div>
      )}

      <div className="flex min-h-screen">
        <aside className="hidden w-[286px] shrink-0 border-r border-[oklch(0.88_0.02_250)] bg-[oklch(0.98_0.01_245/0.76)] px-4 py-5 backdrop-blur-xl lg:sticky lg:top-0 lg:block lg:h-screen">
          <BrandMark />
          <div className="mt-8"><Navigation /></div>

          <div className="absolute bottom-5 left-4 right-4 space-y-4">
            <div className="rounded-[24px] border border-[oklch(0.88_0.02_250)] bg-[oklch(0.99_0.008_245/0.78)] p-4">
              <div className="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[oklch(0.46_0.04_255)]">
                <ShieldCheck className="h-4 w-4 text-[oklch(0.56_0.16_178)]" /> Safety mode
              </div>
              <p className="text-xs leading-5 text-[oklch(0.44_0.035_255)]">Educational insights only. No autonomous dosing or treatment changes.</p>
            </div>

            <div className="flex items-center justify-between rounded-[20px] bg-[oklch(0.23_0.045_255)] p-3 text-[oklch(0.96_0.01_245)]">
              <div className="min-w-0">
                <div className="truncate text-xs font-bold">{user?.email ?? 'Demo workspace'}</div>
                <div className="mt-1 flex items-center gap-1 text-[0.68rem] text-[oklch(0.78_0.08_178)]"><Sparkles className="h-3 w-3" /> v0.1.0 running</div>
              </div>
              <button className="rounded-xl px-2 py-1 text-xs font-bold text-[oklch(0.86_0.08_27)] hover:bg-[oklch(1_0_0/0.08)]" onClick={logout}>Out</button>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
