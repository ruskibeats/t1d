/** @jsxImportSource @emotion/react */
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Bell, DatabaseZap, ShieldCheck, UserRound } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'

export function SettingsPage() {
  const { user, logout } = useAuth()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [status, setStatus] = useState('')
  const [nightscoutUrl, setNightscoutUrl] = useState('')
  const [nightscoutToken, setNightscoutToken] = useState('')
  const [nightscoutConnected, setNightscoutConnected] = useState(false)

  useEffect(() => {
    axios.get('/api/v1/me/nightscout').then((res) => {
      setNightscoutConnected(Boolean(res.data.connected))
      setNightscoutUrl(res.data.url ?? '')
    }).catch(() => undefined)
  }, [])

  const handleSaveProfile = async () => {
    const firstName = (document.querySelector<HTMLInputElement>('[data-profile-first-name]')?.value ?? '').trim()
    const lastName = (document.querySelector<HTMLInputElement>('[data-profile-last-name]')?.value ?? '').trim()
    const full_name = [firstName, lastName].filter(Boolean).join(' ')

    try {
      await axios.patch('/auth/me', { full_name })
      localStorage.setItem('t1d_first_name', firstName)
      localStorage.setItem('t1d_last_name', lastName)
      setStatus('Profile saved')
    } catch {
      setStatus('Could not save profile')
    }
  }

  const handleDexcomConnect = () => {
    setStatus('Dexcom OAuth requires a Dexcom authorization code callback. Use /auth/dexcom/callback after authorizing in Dexcom.')
  }

  const handleNightscoutConnect = async () => {
    if (!nightscoutUrl.trim()) {
      setStatus('Enter a Nightscout URL first')
      return
    }
    try {
      await axios.post('/api/v1/me/nightscout', { url: nightscoutUrl.trim(), api_token: nightscoutToken.trim() || null })
      setNightscoutConnected(true)
      setStatus('Nightscout connected')
    } catch (error: any) {
      setStatus(error?.response?.data?.detail ?? 'Nightscout connection failed')
    }
  }

  const handleNightscoutDisconnect = async () => {
    try {
      await axios.delete('/api/v1/me/nightscout')
      setNightscoutConnected(false)
      setNightscoutToken('')
      setStatus('Nightscout disconnected')
    } catch {
      setStatus('Could not disconnect Nightscout')
    }
  }

  const handleNightscoutSync = async () => {
    try {
      await axios.post('/api/v1/me/nightscout/sync')
      setStatus('Nightscout sync started')
    } catch {
      setStatus('Nightscout sync failed')
    }
  }

  const handleDeleteAccount = () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    localStorage.clear()
    logout()
  }

  return (
    <div className="page-shell space-y-7">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Workspace</div>
        <h1 className="mt-2 text-4xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">Configure profile, CGM sources, notifications, and safety preferences.</p>
        {status && <p className="mt-3 rounded-2xl bg-[oklch(0.94_0.03_245)] px-4 py-2 text-sm font-bold text-[oklch(0.34_0.04_255)]">{status}</p>}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><UserRound className="h-5 w-5 text-[oklch(0.46_0.15_255)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Profile</h2></div>
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">Email</label>
              <input type="email" defaultValue={user?.email} className="control-input" disabled />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div><label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">First name</label><input data-profile-first-name type="text" defaultValue={user?.first_name ?? localStorage.getItem('t1d_first_name') ?? ''} className="control-input" /></div>
              <div><label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">Last name</label><input data-profile-last-name type="text" defaultValue={user?.last_name ?? localStorage.getItem('t1d_last_name') ?? ''} className="control-input" /></div>
            </div>
            <Button data-save-profile onClick={handleSaveProfile}>Save changes</Button>
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><DatabaseZap className="h-5 w-5 text-[oklch(0.43_0.13_178)]" /><h2 className="text-lg font-black tracking-[-0.03em]">CGM sources</h2></div>
          <p className="mb-5 text-sm leading-6 text-[oklch(0.48_0.035_255)]">Connect Dexcom or Nightscout. Manual readings remain available for testing.</p>
          <div className="space-y-3">
            <Button variant="outline" data-connect-dexcom onClick={handleDexcomConnect}>Connect Dexcom</Button>
            <div className="space-y-2 rounded-2xl border border-[oklch(0.88_0.02_250)] p-3">
              <div className="text-xs font-black uppercase tracking-[0.12em] text-[oklch(0.46_0.04_255)]">Nightscout {nightscoutConnected ? 'connected' : 'not connected'}</div>
              <input className="control-input" placeholder="https://your-site.herokuapp.com" value={nightscoutUrl} onChange={(e) => setNightscoutUrl(e.target.value)} />
              <input className="control-input" placeholder="API token (optional)" type="password" value={nightscoutToken} onChange={(e) => setNightscoutToken(e.target.value)} />
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" data-connect-nightscout onClick={handleNightscoutConnect}>{nightscoutConnected ? 'Update Nightscout' : 'Connect Nightscout'}</Button>
                <Button variant="outline" onClick={handleNightscoutSync}>Sync now</Button>
                {nightscoutConnected && <Button variant="ghost" onClick={handleNightscoutDisconnect}>Disconnect</Button>}
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><Bell className="h-5 w-5 text-[oklch(0.52_0.12_73)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Notifications</h2></div>
          <div className="space-y-3">
            {['High glucose alerts', 'Low glucose alerts', 'Pattern updates'].map((label, index) => (
              <label key={label} className="panel-subtle flex cursor-pointer items-center justify-between p-4 text-sm font-bold">
                {label}
                <input type="checkbox" defaultChecked={index < 2} className="h-4 w-4 accent-[oklch(0.56_0.19_255)]" />
              </label>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-[oklch(0.52_0.16_27)]" /><h2 className="text-lg font-black tracking-[-0.03em]">Safety</h2></div>
          <p className="mb-5 text-sm leading-6 text-[oklch(0.48_0.035_255)]">The app is constrained to educational insights, emergency escalation, and clinician-friendly language.</p>
          <div className="flex flex-wrap gap-3">
            <Button variant="destructive" onClick={logout}>Sign out</Button>
            <Button variant="outline" className={confirmDelete ? 'text-[oklch(0.52_0.16_27)] bg-[oklch(0.96_0.035_27/0.2)]' : 'text-[oklch(0.52_0.16_27)]'} onClick={handleDeleteAccount}>{confirmDelete ? 'Confirm delete?' : 'Delete account'}</Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default SettingsPage
