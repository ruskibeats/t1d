/** @jsxImportSource @emotion/react */
import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { format } from 'date-fns'
import { Bot, Brain, Loader2, Send, ShieldCheck, Sparkles, User } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const starterPrompts = [
  'Summarize my recent patterns',
  'Why do high-fat meals rise later?',
  'What happened after exercise yesterday?',
]

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: 'assistant',
      content: 'I can help explain patterns in your CGM and event timeline. I will keep this educational and will not suggest dosing changes.',
      timestamp: new Date().toISOString(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const outgoing = input.trim()
    const userMessage: ChatMessage = { id: Date.now(), role: 'user', content: outgoing, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await axios.post('/api/v1/chat', {
        message: outgoing,
        conversation_id: undefined,
        context_type: 'recent',
        include_patterns: true,
        include_glucose_data: true,
        stream: false,
      })

      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', content: response.data.response, timestamp: new Date().toISOString() }])
    } catch (error) {
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
    <div className="page-shell space-y-7">
      <section className="hero-surface p-6 md:p-8">
        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-4 flex flex-wrap gap-2">
              <span className="signal-pill"><Sparkles className="mr-2 inline h-3.5 w-3.5" /> OpenRouter ready</span>
              <span className="signal-pill"><ShieldCheck className="mr-2 inline h-3.5 w-3.5" /> Safety guardrails</span>
            </div>
            <h1 className="max-w-2xl text-4xl font-black leading-[0.95] tracking-[-0.06em] md:text-6xl">Ask the pattern layer.</h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[oklch(0.86_0.025_245)]">Conversational explanations grounded in glucose readings, meals, movement, sleep, and safety boundaries.</p>
          </div>
          <div className="rounded-[26px] border border-[oklch(1_0_0/0.12)] bg-[oklch(1_0_0/0.08)] p-4 text-sm font-semibold text-[oklch(0.86_0.025_245)] md:max-w-sm">
            This assistant provides educational insights only. It does not diagnose, prescribe, or recommend insulin dosing.
          </div>
        </div>
      </section>

      <Card className="mx-auto flex h-[680px] max-w-5xl flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-[oklch(0.89_0.018_250)] p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]"><Brain className="h-5 w-5" /></div>
            <div><h2 className="font-black tracking-[-0.03em]">AI companion</h2><p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">Pattern-aware chat</p></div>
          </div>
          <span className="chip">v0.1.0</span>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {messages.map((message) => (
            <div key={message.id} className={cn('flex items-start gap-3', message.role === 'user' && 'flex-row-reverse')}>
              <div className={cn('grid h-9 w-9 shrink-0 place-items-center rounded-2xl', message.role === 'user' ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)]' : 'bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]')}>
                {message.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={cn('max-w-[82%]', message.role === 'user' && 'text-right')}>
                <div className={cn('rounded-[24px] px-4 py-3 text-sm leading-6 shadow-sm', message.role === 'user' ? 'bg-[oklch(0.56_0.19_255)] text-[oklch(0.98_0.01_245)]' : 'bg-[oklch(0.96_0.012_245)] text-[oklch(0.28_0.04_255)]')}>
                  {message.content}
                </div>
                <span className="mt-1 block text-xs font-semibold text-[oklch(0.55_0.03_255)]">{format(new Date(message.timestamp), 'h:mm a')}</span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]"><Bot className="h-4 w-4" /></div>
              <div className="rounded-[24px] bg-[oklch(0.96_0.012_245)] px-4 py-3 text-sm font-semibold text-[oklch(0.48_0.035_255)]"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Thinking through the timeline</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-[oklch(0.89_0.018_250)] p-4">
          <div className="mb-3 flex flex-wrap gap-2">
            {starterPrompts.map((prompt) => <button key={prompt} className="chip transition hover:bg-[oklch(0.93_0.018_245)]" onClick={() => setInput(prompt)}>{prompt}</button>)}
          </div>
          <div className="flex gap-2">
            <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleKeyPress} placeholder="Ask about patterns, meals, exercise, or overnight trends..." className="control-input" />
            <Button onClick={handleSend} disabled={isLoading || !input.trim()} className="shrink-0">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span className="hidden sm:inline">Send</span>
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default ChatPage
