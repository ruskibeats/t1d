/** @jsxImportSource @emotion/react */
import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { format } from 'date-fns'
import { Bot, Brain, Loader2, Send, ShieldCheck, Sparkles, TrendingUp, User, X } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  prediction?: SpikePrediction | null
}

interface SpikePrediction {
  predicted_peak_glucose: number
  predicted_peak_time_minutes: number
  confidence: number
  factors: string[]
}

const starterPrompts = [
  'Summarize my recent patterns',
  'Why do high-fat meals rise later?',
  'What happened after exercise yesterday?',
]

const spikeQuickInputs = [
  { label: 'Meal', carbs: 45, protein: 20, fat: 15 },
  { label: 'Snack', carbs: 25, protein: 5, fat: 8 },
  { label: 'High-fat', carbs: 30, protein: 25, fat: 35 },
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
  const [conversations, setConversations] = useState<any[]>([])
  const [activeConversationId, setActiveConversationId] = useState<number | undefined>(undefined)
  const [showPredictor, setShowPredictor] = useState(false)
  const [predictGlucose, setPredictGlucose] = useState(120)
  const [predictCarbs, setPredictCarbs] = useState(45)
  const [predictProtein, setPredictProtein] = useState(20)
  const [predictFat, setPredictFat] = useState(15)
  const [isPredicting, setIsPredicting] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    axios.get('/api/v1/conversations').then((res) => setConversations(res.data ?? [])).catch(() => undefined)
  }, [])

  const loadConversation = async (conversationId: number) => {
    const res = await axios.get(`/api/v1/conversations/${conversationId}/messages`)
    setActiveConversationId(conversationId)
    setMessages((res.data ?? []).map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    })))
  }

  const refreshConversations = async () => {
    const res = await axios.get('/api/v1/conversations')
    setConversations(res.data ?? [])
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const outgoing = input.trim()
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
      await refreshConversations()
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
        <div className="flex items-center justify-between gap-4 border-b border-[oklch(0.89_0.018_250)] p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[oklch(0.94_0.035_255)] text-[oklch(0.42_0.13_255)]"><Brain className="h-5 w-5" /></div>
            <div><h2 className="font-black tracking-[-0.03em]">AI companion</h2><p className="text-sm font-semibold text-[oklch(0.48_0.035_255)]">Pattern-aware chat</p></div>
          </div>
          <div className="flex max-w-sm gap-2 overflow-x-auto">
            <button className="chip" onClick={() => { setActiveConversationId(undefined); setMessages([{ id: 1, role: 'assistant', content: 'I can help explain patterns in your CGM and event timeline. I will keep this educational and will not suggest dosing changes.', timestamp: new Date().toISOString() }]) }}>New</button>
            {conversations.slice(0, 5).map((conversation) => (
              <button key={conversation.id} className="chip max-w-[140px] truncate" onClick={() => loadConversation(conversation.id)}>{conversation.title || `Chat ${conversation.id}`}</button>
            ))}
          </div>
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
                  {message.prediction && (
                    <div className="mt-3 overflow-hidden rounded-2xl border border-[oklch(0.72_0.15_178/0.25)] bg-white">
                      <div className="bg-gradient-to-r from-[oklch(0.72_0.15_178)] to-[oklch(0.56_0.19_292)] p-3 text-center text-white">
                        <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Predicted peak</p>
                        <p className="text-3xl font-black">{message.prediction.predicted_peak_glucose.toFixed(0)} <span className="text-base font-bold">mg/dL</span></p>
                        <p className="mt-1 text-sm font-semibold opacity-90">in ~{message.prediction.predicted_peak_time_minutes} min</p>
                      </div>
                      <div className="p-3 space-y-2">
                        <div>
                          <div className="flex justify-between text-[10px] font-bold text-[oklch(0.48_0.035_255)]">
                            <span>Confidence</span>
                            <span>{(message.prediction.confidence * 100).toFixed(0)}%</span>
                          </div>
                          <div className="mt-1 h-2 rounded-full bg-[oklch(0.94_0.03_245)] overflow-hidden">
                            <div className="h-full rounded-full transition-all" style={{
                              width: `${message.prediction.confidence * 100}%`,
                              backgroundColor: message.prediction.confidence > 0.7 ? 'oklch(0.72 0.15 178)' : message.prediction.confidence > 0.4 ? 'oklch(0.76 0.15 72)' : 'oklch(0.72 0.18 27)',
                            }} />
                          </div>
                        </div>
                        {message.prediction.factors.length > 0 && (
                          <div>
                            <p className="text-[10px] font-bold text-[oklch(0.48_0.035_255)]">Factors</p>
                            <ul className="mt-1 space-y-0.5">
                              {message.prediction.factors.map((f, i) => (
                                <li key={i} className="flex items-start gap-1.5 text-[11px] text-[oklch(0.4_0.03_255)]">
                                  <span className="mt-0.5 h-1 w-1 shrink-0 rounded-full bg-[oklch(0.72_0.15_178)]" />
                                  {f}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <p className="pt-1 text-[10px] font-semibold text-[oklch(0.55_0.03_255)] border-t border-[oklch(0.92_0.01_250)]">
                          Educational estimate only. Actual values depend on insulin, activity, metabolism.
                        </p>
                      </div>
                    </div>
                  )}
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
            <button className="chip !border-[oklch(0.72_0.15_178/0.3)] !text-[oklch(0.55_0.15_178)] transition hover:bg-[oklch(0.72_0.15_178/0.08)]" onClick={() => setShowPredictor(!showPredictor)}>
              <TrendingUp className="mr-1 inline h-3.5 w-3.5" /> Predict spike
            </button>
          </div>

          {showPredictor && (
            <div className="mb-3 rounded-2xl border border-[oklch(0.72_0.15_178/0.2)] bg-[oklch(0.72_0.15_178/0.06)] p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-black tracking-[-0.03em]">Spike predictor</h3>
                <button onClick={() => setShowPredictor(false)} className="rounded-lg p-1 hover:bg-[oklch(0_0_0/0.06)]"><X className="h-4 w-4" /></button>
              </div>
              <div className="mb-3 flex flex-wrap gap-2">
                {spikeQuickInputs.map(qi => (
                  <button key={qi.label} onClick={() => { setPredictCarbs(qi.carbs); setPredictProtein(qi.protein); setPredictFat(qi.fat) }}
                    className="rounded-xl border border-[oklch(0.86_0.02_250)] bg-white px-3 py-1.5 text-xs font-bold transition hover:bg-[oklch(0.94_0.03_245)]">
                    {qi.label}: {qi.carbs}g carbs
                  </button>
                ))}
              </div>
              <div className="mb-3 grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-[oklch(0.48_0.035_255)]">Current glucose</label>
                  <input type="number" value={predictGlucose} onChange={e => setPredictGlucose(parseInt(e.target.value) || 120)}
                    className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-1.5 text-sm" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-[oklch(0.48_0.035_255)]">Carbs (g)</label>
                  <input type="number" value={predictCarbs} onChange={e => setPredictCarbs(parseInt(e.target.value) || 0)}
                    className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-1.5 text-sm" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-[oklch(0.48_0.035_255)]">Protein (g)</label>
                  <input type="number" value={predictProtein} onChange={e => setPredictProtein(parseInt(e.target.value) || 0)}
                    className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-1.5 text-sm" />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-[oklch(0.48_0.035_255)]">Fat (g)</label>
                  <input type="number" value={predictFat} onChange={e => setPredictFat(parseInt(e.target.value) || 0)}
                    className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-1.5 text-sm" />
                </div>
              </div>
              <Button size="sm" disabled={isPredicting} onClick={async () => {
                setIsPredicting(true)
                const msg = `Predict spike for glucose=${predictGlucose}, carbs=${predictCarbs}g, protein=${predictProtein}g, fat=${predictFat}g`
                const userMsg: ChatMessage = { id: Date.now(), role: 'user', content: msg, timestamp: new Date().toISOString() }
                setMessages(prev => [...prev, userMsg])
                try {
                  const res = await axios.post('/api/v1/chat', { message: msg, spike_prediction: true })
                  const prediction: SpikePrediction = res.data.prediction || {
                    predicted_peak_glucose: predictGlucose + predictCarbs * 2.5,
                    predicted_peak_time_minutes: 60 + predictFat * 2,
                    confidence: Math.max(0.3, 0.9 - predictFat * 0.01),
                    factors: ['Carbohydrate content', 'Fat content (delays absorption)', 'Current glucose level'],
                  }
                  setMessages(prev => [...prev, {
                    id: Date.now() + 1, role: 'assistant',
                    content: `Based on the input, the estimated peak glucose is **${prediction.predicted_peak_glucose.toFixed(0)} mg/dL**, peaking around **${prediction.predicted_peak_time_minutes} min** after the meal. ${prediction.confidence > 0.7 ? 'Confidence is strong.' : 'Confidence is moderate due to fat content affecting absorption rate.'} This is an educational estimate — actual values depend on insulin timing, activity, and individual metabolism.`,
                    timestamp: new Date().toISOString(), prediction,
                  }])
                } catch {
                  const fallbackPrediction: SpikePrediction = {
                    predicted_peak_glucose: predictGlucose + predictCarbs * 2.5,
                    predicted_peak_time_minutes: 60 + predictFat * 2,
                    confidence: 0.7,
                    factors: ['Carbohydrate content', 'Fat content', 'Current glucose level'],
                  }
                  setMessages(prev => [...prev, {
                    id: Date.now() + 1, role: 'assistant',
                    content: `Educational estimate: peak glucose ~**${fallbackPrediction.predicted_peak_glucose.toFixed(0)} mg/dL** at ~**${fallbackPrediction.predicted_peak_time_minutes} min**. This is an illustrative calculation, not medical advice.`,
                    timestamp: new Date().toISOString(), prediction: fallbackPrediction,
                  }])
                }
                setIsPredicting(false)
                setShowPredictor(false)
              }}>
                {isPredicting ? <Loader2 className="h-3 w-3 animate-spin" /> : <TrendingUp className="h-3 w-3" />}
                Predict
              </Button>
            </div>
          )}
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
