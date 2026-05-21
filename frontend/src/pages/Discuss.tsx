/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Calendar, Heart, MessageCircle, Share2, ShieldCheck, UserCircle } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

interface DiscussionItem {
  id: number
  title: string
  description: string
  status: 'draft' | 'shared' | 'discussed'
  recipient: 'doctor' | 'caregiver'
}

export function DiscussPage() {
  const [items, setItems] = useState<DiscussionItem[]>([
    { id: 1, title: 'Overnight lows this week', description: 'I had 3 overnight lows this week. Should we adjust my basal rate?', status: 'draft', recipient: 'doctor' },
    { id: 2, title: 'Evening patterns', description: 'My evenings have been more stable this week.', status: 'shared', recipient: 'caregiver' },
  ])
  const [showNew, setShowNew] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newRecipient, setNewRecipient] = useState<'doctor' | 'caregiver'>('doctor')

  const handleAdd = () => {
    if (!newTitle.trim()) return
    setItems(prev => [...prev, {
      id: Date.now(),
      title: newTitle.trim(),
      description: newDesc.trim(),
      status: 'draft',
      recipient: newRecipient,
    }])
    setNewTitle('')
    setNewDesc('')
    setShowNew(false)
  }

  const handleShare = (id: number) => {
    setItems(prev => prev.map(item => item.id === id ? { ...item, status: 'shared' } : item))
  }

  const statusColors: Record<DiscussionItem['status'], string> = {
    draft: 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.48_0.035_255)]',
    shared: 'bg-[oklch(0.72_0.15_178/0.12)] text-[oklch(0.43_0.13_178)]',
    discussed: 'bg-[oklch(0.56_0.19_255/0.12)] text-[oklch(0.42_0.13_255)]',
  }

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Share patterns</div>
        <h1 className="mt-2 text-3xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Discuss</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">
          Share patterns with your doctor or caregiver. Mark topics for your next diabetes review.
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.56_0.19_255/0.1)]">
              <Calendar className="h-5 w-5 text-[oklch(0.42_0.13_255)]" />
            </div>
            <div>
              <p className="font-black text-sm">Mark for review</p>
              <p className="text-xs text-[oklch(0.48_0.035_255)]">Save for your next appointment</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.72_0.15_178/0.1)]">
              <UserCircle className="h-5 w-5 text-[oklch(0.43_0.13_178)]" />
            </div>
            <div>
              <p className="font-black text-sm">Share with caregiver</p>
              <p className="text-xs text-[oklch(0.48_0.035_255)]">Send a pattern summary</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.85_0.12_85/0.1)]">
              <Heart className="h-5 w-5 text-[oklch(0.52_0.12_73)]" />
            </div>
            <div>
              <p className="font-black text-sm">Talk to mummy</p>
              <p className="text-xs text-[oklch(0.48_0.035_255)]">Share with a parent or partner</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Add new */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black tracking-[-0.03em]">Discussion items</h2>
        <Button size="sm" onClick={() => setShowNew(!showNew)}>
          <Share2 className="mr-1 h-3 w-3" /> New item
        </Button>
      </div>

      {showNew && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">New discussion item</h3>
          <input
            type="text"
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="What do you want to discuss?"
            className="w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-4 py-2.5 text-sm font-medium outline-none focus:border-[oklch(0.6_0.12_178)]"
          />
          <textarea
            value={newDesc}
            onChange={e => setNewDesc(e.target.value)}
            placeholder="Add more detail..."
            rows={2}
            className="w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-4 py-2.5 text-sm font-medium outline-none focus:border-[oklch(0.6_0.12_178)]"
          />
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Share with:</span>
            <button
              onClick={() => setNewRecipient('doctor')}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-bold',
                newRecipient === 'doctor' ? 'bg-[oklch(0.56_0.19_255/0.12)] text-[oklch(0.42_0.13_255)]' : 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.48_0.035_255)]'
              )}
            >
              Doctor
            </button>
            <button
              onClick={() => setNewRecipient('caregiver')}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-bold',
                newRecipient === 'caregiver' ? 'bg-[oklch(0.72_0.15_178/0.12)] text-[oklch(0.43_0.13_178)]' : 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.48_0.035_255)]'
              )}
            >
              Caregiver
            </button>
            <div className="flex-1" />
            <Button size="sm" onClick={handleAdd} disabled={!newTitle.trim()}>Add</Button>
          </div>
        </Card>
      )}

      {/* Items list */}
      <div className="space-y-3">
        {items.length === 0 && (
          <Card className="p-8 text-center">
            <MessageCircle className="mx-auto h-8 w-8 text-[oklch(0.8_0.02_250)]" />
            <p className="mt-3 text-sm text-[oklch(0.48_0.035_255)]">No discussion items yet.</p>
          </Card>
        )}
        {items.map(item => (
          <Card key={item.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <span className={cn('rounded-full px-2 py-0.5 text-[0.65rem] font-black', statusColors[item.status])}>
                    {item.status === 'draft' ? 'Draft' : item.status === 'shared' ? 'Shared' : 'Discussed'}
                  </span>
                  <span className="text-[0.65rem] font-semibold text-[oklch(0.55_0.03_255)]">
                    {item.recipient === 'doctor' ? 'Doctor' : 'Caregiver'}
                  </span>
                </div>
                <p className="font-bold text-sm">{item.title}</p>
                {item.description && (
                  <p className="mt-1 text-xs text-[oklch(0.48_0.035_255)]">{item.description}</p>
                )}
              </div>
              {item.status === 'draft' && (
                <Button size="sm" variant="outline" onClick={() => handleShare(item.id)}>
                  <Share2 className="mr-1 h-3 w-3" /> Share
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* Safety note */}
      <Card className="p-4">
        <div className="flex items-start gap-2">
          <ShieldCheck className="h-4 w-4 shrink-0 text-[oklch(0.56_0.16_178)]" />
          <p className="text-xs text-[oklch(0.44_0.035_255)]">
            Shared pattern summaries are for discussion with your care team. They do not replace medical advice.
          </p>
        </div>
      </Card>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export default DiscussPage
