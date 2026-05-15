/** @jsxImportSource @emotion/react */
import { Bell, DatabaseZap, ShieldCheck, UserRound } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/contexts/AuthContext'

export function SettingsPage() {
  const { user, logout } = useAuth()

  return (
    <div className="page-shell space-y-7">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Workspace</div>
        <h1 className="mt-2 text-4xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">Configure profile, CGM sources, notifications, and safety preferences.</p>
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
              <div><label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">First name</label><input type="text" defaultValue={user?.first_name} className="control-input" /></div>
              <div><label className="mb-1.5 block text-sm font-bold text-[oklch(0.34_0.035_255)]">Last name</label><input type="text" defaultValue={user?.last_name} className="control-input" /></div>
            </div>
            <Button>Save changes</Button>
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3"><DatabaseZap className="h-5 w-5 text-[oklch(0.43_0.13_178)]" /><h2 className="text-lg font-black tracking-[-0.03em]">CGM sources</h2></div>
          <p className="mb-5 text-sm leading-6 text-[oklch(0.48_0.035_255)]">Connect Dexcom or Nightscout when credentials are ready. Manual readings remain available for testing.</p>
          <div className="flex flex-wrap gap-3"><Button variant="outline">Connect Dexcom</Button><Button variant="outline">Connect Nightscout</Button></div>
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
          <div className="flex flex-wrap gap-3"><Button variant="destructive" onClick={logout}>Sign out</Button><Button variant="outline" className="text-[oklch(0.52_0.16_27)]">Delete account</Button></div>
        </Card>
      </div>
    </div>
  )
}

export default SettingsPage
