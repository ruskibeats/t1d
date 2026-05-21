/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Mic, Save, StickyNote, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

interface Memory {
  id: number
  text: string
  date: string
  type: 'observation' | 'question' | 'clinic'
}

export function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([
    { id: 1, text: 'Pizza seems to cause a delayed rise — peaks around 3 hours after eating.', date: '2026-05-18', type: 'observation' },
    { id: 2, text: 'Ask the doctor about adjusting basal rates for overnight.', date: '2026-05-17', type: 'clinic' },
    { id: 3, text: 'Why do I go low after walking but not after cycling?', date: '2026-05-15', type: 'question' },
  ])
  const [newText, setNewText] = useState('')
  const [newType, setNewType] = useState<Memory['type']>('observation')
  const [isRecording, setIsRecording] = useState(false)

  const handleSave = () => {
    if (!newText.trim()) return
    setMemories(prev => [...prev, {
      id: Date.now(),
      text: newText.trim(),
      date: new Date().toISOString().split('T')[0],
      type: newType,
    }])
    setNewText('')
  }

  const handleDelete = (id: number) => {
    setMemories(prev => prev.filter(m => m.id !== id))
  }

  const typeLabels: Record<Memory['type'], string> = {
    observation: 'Observation',
    question: 'Question',
    clinic: 'Clinic note',
  }

  const typeColors: Record<Memory['type'], string> = {
    observation: 'bg-[oklch(0.72_0.15_178/0.12)] text-[oklch(0.43_0.13_178)]',
    question: 'bg-[oklch(0.56_0.19_255/0.12)] text-[oklch(0.42_0.13_255)]',
    clinic: 'bg-[oklch(0.85_0.12_85/0.12)] text-[oklch(0.52_0.12_73)]',
  }

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Saved notes</div>
        <h1 className="mt-2 text-3xl font-black tracking-[-0.06em] text-[oklch(0.22_0.04_255)]">Memory</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[oklch(0.48_0.035_255)]">
          Save observations, questions for your doctor, and things worth remembering.
        </p>
      </div>

      {/* Add new memory */}
      <Card className="p-5 space-y-4">
        <h3 className="font-black">Add a note</h3>
        <textarea
          value={newText}
          onChange={e => setNewText(e.target.value)}
          placeholder="What do you want to remember?"
          rows={3}
          className="w-full rounded-2xl border border-[oklch(0.86_0.02_250)] bg-[oklch(0.98_0.01_245)] p-4 text-sm font-medium outline-none focus:border-[oklch(0.6_0.12_178)]"
        />
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-2">
            {(['observation', 'question', 'clinic'] as Memory['type'][]).map(type => (
              <button
                key={type}
                onClick={() => setNewType(type)}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-bold transition',
                  newType === type ? typeColors[type] : 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.48_0.035_255)]'
                )}
              >
                {typeLabels[type]}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <button
            onClick={() => setIsRecording(!isRecording)}
            className={cn(
              'grid h-9 w-9 place-items-center rounded-xl transition',
              isRecording ? 'bg-[oklch(0.76_0.15_72/0.15)] text-[oklch(0.52_0.16_27)]' : 'bg-[oklch(0.94_0.018_245)] text-[oklch(0.48_0.035_255)] hover:bg-[oklch(0.88_0.02_245)]'
            )}
            aria-label="Voice note"
          >
            <Mic className="h-4 w-4" />
          </button>
          <Button onClick={handleSave} disabled={!newText.trim()}>
            <Save className="mr-1 h-3 w-3" /> Save
          </Button>
        </div>
        {isRecording && (
          <div className="rounded-xl bg-[oklch(0.76_0.15_72/0.08)] p-3 text-sm text-[oklch(0.48_0.035_255)]">
            Voice recording is not available in this demo. Type your note above.
          </div>
        )}
      </Card>

      {/* Memory list */}
      <div className="space-y-3">
        {memories.length === 0 && (
          <Card className="p-8 text-center">
            <StickyNote className="mx-auto h-8 w-8 text-[oklch(0.8_0.02_250)]" />
            <p className="mt-3 text-sm text-[oklch(0.48_0.035_255)]">No saved notes yet. Add your first observation above.</p>
          </Card>
        )}
        {memories.map(memory => (
          <Card key={memory.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="mb-2 flex items-center gap-2">
                  <span className={cn('rounded-full px-2 py-0.5 text-[0.65rem] font-black', typeColors[memory.type])}>
                    {typeLabels[memory.type]}
                  </span>
                  <span className="text-[0.65rem] font-semibold text-[oklch(0.55_0.03_255)]">{memory.date}</span>
                </div>
                <p className="text-sm leading-5 text-[oklch(0.28_0.04_255)]">{memory.text}</p>
              </div>
              <button
                onClick={() => handleDelete(memory.id)}
                className="shrink-0 rounded-lg p-1.5 text-[oklch(0.55_0.03_255)] transition hover:bg-[oklch(0.94_0.018_245)]"
                aria-label="Delete note"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export default MemoryPage
