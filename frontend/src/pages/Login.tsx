/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err?.response?.data?.message || err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDemo = async () => {
    setLoading(true)
    setError('')
    try {
      await login('demo@t1d.com', 'demo123')
      navigate('/dashboard')
    } catch (err: any) {
      setError('Demo login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-backdrop grid min-h-screen place-items-center p-4">
      <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
        <section className="hero-surface flex min-h-[560px] flex-col justify-between p-7 md:p-9">
          <div className="relative z-10">
            <div className="mb-8 flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[oklch(1_0_0/0.1)]"><Activity className="h-6 w-6 text-[oklch(0.74_0.13_178)]" /></div>
              <div><div className="text-xl font-black tracking-[-0.04em]">T1D Companion</div><div className="text-sm font-semibold text-[oklch(0.76_0.04_245)]">v0.1.0 development</div></div>
            </div>
            <h1 className="max-w-xl text-5xl font-black leading-[0.94] tracking-[-0.07em] md:text-7xl">Understand what your glucose usually does.</h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-[oklch(0.86_0.025_245)]">Connect CGM data, log real-life context, and ask an AI companion to explain patterns without crossing into medical advice.</p>
          </div>
          <div className="relative z-10 grid gap-3 md:grid-cols-3">
            <div className="rounded-[24px] bg-[oklch(1_0_0/0.08)] p-4"><Sparkles className="mb-3 h-5 w-5 text-[oklch(0.78_0.12_178)]" /><div className="text-sm font-black">Pattern first</div><p className="mt-1 text-xs leading-5 text-[oklch(0.76_0.04_245)]">Meals, exercise, sleep, stress.</p></div>
            <div className="rounded-[24px] bg-[oklch(1_0_0/0.08)] p-4"><ShieldCheck className="mb-3 h-5 w-5 text-[oklch(0.78_0.12_178)]" /><div className="text-sm font-black">Safety first</div><p className="mt-1 text-xs leading-5 text-[oklch(0.76_0.04_245)]">No dosing instructions.</p></div>
            <div className="rounded-[24px] bg-[oklch(1_0_0/0.08)] p-4"><Activity className="mb-3 h-5 w-5 text-[oklch(0.78_0.12_178)]" /><div className="text-sm font-black">Sensor agnostic</div><p className="mt-1 text-xs leading-5 text-[oklch(0.76_0.04_245)]">Dexcom, Nightscout, manual.</p></div>
          </div>
        </section>

        <Card className="flex flex-col justify-center p-6 md:p-9">
          <div className="mb-8">
            <div className="kicker"><span className="kicker-dot" /> Welcome back</div>
            <h2 className="mt-2 text-3xl font-black tracking-[-0.05em] text-[oklch(0.22_0.04_255)]">Sign in</h2>
            <p className="mt-2 text-sm leading-6 text-[oklch(0.48_0.035_255)]">Use the demo account if the local database has not been seeded yet.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">Email</label>
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="control-input" placeholder="you@example.com" required />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">Password</label>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="control-input" placeholder="Enter password" required />
            </div>

            {error && <div className="rounded-2xl bg-[oklch(0.96_0.035_27)] p-3 text-sm font-semibold text-[oklch(0.48_0.13_27)]">{error}</div>}

            <Button type="submit" className="w-full" disabled={loading}>{loading ? 'Signing in' : 'Sign in'} <ArrowRight className="h-4 w-4" /></Button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs font-black uppercase tracking-[0.12em] text-[oklch(0.55_0.03_255)]"><div className="h-px flex-1 bg-[oklch(0.88_0.02_250)]" /> Or <div className="h-px flex-1 bg-[oklch(0.88_0.02_250)]" /></div>

          <Button type="button" variant="outline" onClick={handleDemo} disabled={loading} className="w-full">Try demo workspace</Button>
          <p className="mt-5 text-center text-xs font-semibold text-[oklch(0.52_0.035_255)]">Demo: demo@t1d.com / demo123</p>
        </Card>
      </div>
    </div>
  )
}
