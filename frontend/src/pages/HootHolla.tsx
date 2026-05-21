/** @jsxImportSource @emotion/react */
import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { Bot, Brain, Camera, Loader2, Mic, ScanBarcode, Send, ShieldCheck, Sparkles, X } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const promptChips = [
  "Why am I high right now?",
  "I'm about to eat",
  "What happened last time?",
  "How did I sleep?",
  "What's my pattern this week?",
]

export function HootHollaPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'I can help explain patterns in your glucose, meals, and activity. I will keep this educational and will not suggest dosing changes.',
      timestamp: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeConversationId, setActiveConversationId] = useState<number | undefined>(undefined)
  const [showInputModes, setShowInputModes] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text?: string) => {
    const outgoing = (text || input).trim()
    if (!outgoing || isLoading) return

    const userMessage: ChatMessage = { id: Date.now(), role: 'user', content: outgoing, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const assistantId = Date.now() + 1
      setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', timestamp: new Date().toISOString() }])

      const token = localStorage.getItem('token') || localStorage.getItem('access_token')
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: outgoing,
          conversation_id: activeConversationId,
          context_type: 'recent',
          include_patterns: true,
          include_glucose_data: true,
          stream: true,
        }),
      })
      if (!response.ok || !response.body) throw new Error('stream failed')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() ?? ''
        for (const event of events) {
          const line = event.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue
          const payload = JSON.parse(line.slice(6))
          if (payload.conversation_id && !activeConversationId) setActiveConversationId(payload.conversation_id)
          if (payload.chunk) {
            setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + payload.chunk } : m))
          }
        }
      }
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'I am in demo mode right now. Based on the sample timeline, the clearest signals are a delayed rise after higher-fat meals, a moderate exercise drop, and one overnight low trend. Treat this as educational context and discuss care changes with your diabetes team.',
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="page-shell space-y-6">
      <section className="hero-surface p-6 md:p-8">
        <div className="relative z-10">
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="signal-pill"><Sparkles className="mr-2 inline h-3.5 w-3.5" /> Pattern-aware chat</span>
            <span className="signal-pill"><ShieldCheck className="mr-2 inline h-3.5 w-3.5" /> Educational only</span>
          </div>
          <h1 className="max-w-2xl text-4xl font-black leading-[0.95] tracking-[-0.06em] md:text-5xl">Hoot & Holla</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[oklch(0.86_0.025_245)]">Ask about your patterns. Get plain-English explanations grounded in your data.</p>
        </div>
      </section>

      <Card className="mx-auto flex h-[620px] max-w-4xl flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-[oklch(0.89_0.018_250)] p-4">
          <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]">
            <Brain className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-black tracking-[-0.03em]">AI companion</h2>
            <p className="text-xs font-semibold text-[oklch(0.48_0.035_255)]">Educational insights, not medical advice</p>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.map((message) => (
            <div key={message.id} className={cn('flex items-start gap-3', message.role === 'user' && 'flex-row-reverse')}>
              <div className={cn(
                'grid h-8 w-8 shrink-0 place-items-center rounded-2xl',
                message.role === 'user'
                  ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)]'
                  : 'bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]'
              )}>
                {message.role === 'user' ? <Sparkles className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={cn('max-w-[80%]', message.role === 'user' && 'text-right')}>
                <div className={cn(
                  'rounded-[20px] px-4 py-3 text-sm leading-6',
                  message.role === 'user'
                    ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)]'
                    : 'bg-[oklch(0.96_0.012_245)] text-[oklch(0.28_0.04_255)]'
                )}>
                  {message.content}
                </div>
                <span className="mt-1 block text-[10px] font-semibold text-[oklch(0.55_0.03_255)]">
                  {format(new Date(message.timestamp), 'h:mm a')}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="grid h-8 w-8 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-[20px] bg-[oklch(0.96_0.012_245)] px-4 py-3 text-sm font-semibold text-[oklch(0.48_0.035_255)]">
                <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Thinking through your data
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-[oklch(0.89_0.018_250)] p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {promptChips.map((prompt) => (
              <button
                key={prompt}
                className="rounded-full border border-[oklch(0.86_0.02_250)] bg-[oklch(0.98_0.01_245)] px-3 py-1.5 text-xs font-bold text-[oklch(0.42_0.035_255)] transition hover:bg-[oklch(0.93_0.018_245)]"
                onClick={() => handleSend(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowInputModes(!showInputModes)}
                className="grid h-10 w-10 place-items-center rounded-2xl border border-[oklch(0.86_0.02_250)] text-[oklch(0.48_0.035_255)] transition hover:bg-[oklch(0.94_0.018_245)]"
                aria-label="Input modes"
              >
                {showInputModes ? <X className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
              </button>
              {showInputModes && (
                <div className="absolute bottom-12 left-0 z-10 flex gap-2 rounded-2xl border border-[oklch(0.86_0.02_250)] bg-white p-2 shadow-lg">
                  <button
                    className="grid h-10 w-10 place-items-center rounded-xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)] transition hover:bg-[oklch(0.88_0.03_245)]"
                    aria-label="Voice input"
                    onClick={() => { setShowInputModes(false) }}
                  >
                    <Mic className="h-4 w-4" />
                  </button>
                  <button
                    className="grid h-10 w-10 place-items-center rounded-xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)] transition hover:bg-[oklch(0.88_0.03_245)]"
                    aria-label="Camera"
                    onClick={() => { setShowInputModes(false) }}
                  >
                    <Camera className="h-4 w-4" />
                  </button>
                  <button
                    className="grid h-10 w-10 place-items-center rounded-xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)] transition hover:bg-[oklch(0.88_0.03_245)]"
                    aria-label="Barcode scanner"
                    onClick={() => { setShowInputModes(false) }}
                  >
                    <ScanBarcode className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask about your patterns..."
              className="control-input"
            />
            <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="shrink-0">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default HootHollaPage
