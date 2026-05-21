/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Search, Utensils, ArrowRight, Brain, Clock } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useFood, FoodItem } from '@/hooks/useFood'

const mealTypes = ['breakfast', 'lunch', 'dinner', 'snack'] as const

type Step = 'capture' | 'analysing' | 'review' | 'memory'

export function FoodLogPage() {
  const { foods, entries, searchFoods, createEntry } = useFood()
  const [step, setStep] = useState<Step>('capture')
  const [query, setQuery] = useState('')
  const [selectedFood, setSelectedFood] = useState<FoodItem | null>(null)
  const [mealType, setMealType] = useState<typeof mealTypes[number]>('lunch')
  const [quantity, setQuantity] = useState(1)

  const handleSearch = (q: string) => {
    setQuery(q)
    if (q.length > 1) searchFoods(q)
  }

  const handleSelectFood = (food: FoodItem) => {
    setSelectedFood(food)
    setQuantity(1)
    setStep('analysing')
  }

  const handleAnalyse = () => {
    setStep('review')
  }

  const handleLog = async () => {
    if (!selectedFood) return
    await createEntry({
      food_id: selectedFood.id,
      quantity,
      unit: selectedFood.serving_unit || 'serving',
      entry_date: new Date().toISOString(),
      meal_type: mealType,
      food_name: selectedFood.name,
      calories: selectedFood.calories ? selectedFood.calories * quantity : undefined,
      protein: selectedFood.protein ? selectedFood.protein * quantity : undefined,
      carbs: selectedFood.carbs ? selectedFood.carbs * quantity : undefined,
      fat: selectedFood.fat ? selectedFood.fat * quantity : undefined,
    })
    setStep('memory')
  }

  const handleReset = () => {
    setStep('capture')
    setQuery('')
    setSelectedFood(null)
    setQuantity(1)
  }

  const todayEntries = entries.filter(e =>
    e.entry_date.startsWith(new Date().toISOString().split('T')[0])
  )
  const totals = todayEntries.reduce((acc, e) => ({
    calories: acc.calories + (e.calories || 0),
    protein: acc.protein + (e.protein || 0),
    carbs: acc.carbs + (e.carbs || 0),
    fat: acc.fat + (e.fat || 0),
  }), { calories: 0, protein: 0, carbs: 0, fat: 0 })

  const stepLabels: Record<Step, string> = {
    capture: 'Find food',
    analysing: 'Checking nutrition',
    review: 'Review meal',
    memory: 'Meal logged',
  }

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Meal review</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Log a meal</h2>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {(['capture', 'analysing', 'review', 'memory'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={cn(
              'grid h-7 w-7 place-items-center rounded-full text-xs font-black',
              step === s ? 'bg-[oklch(0.56_0.19_255)] text-white' :
              i < ['capture', 'analysing', 'review', 'memory'].indexOf(step) ? 'bg-[oklch(0.72_0.15_178)] text-white' :
              'bg-[oklch(0.92_0.01_250)] text-[oklch(0.48_0.035_255)]'
            )}>
              {i + 1}
            </div>
            <span className={cn('text-xs font-bold', step === s ? 'text-[oklch(0.22_0.04_255)]' : 'text-[oklch(0.48_0.035_255)]')}>
              {stepLabels[s]}
            </span>
            {i < 3 && <ArrowRight className="h-3 w-3 text-[oklch(0.7_0.035_255)]" />}
          </div>
        ))}
      </div>

      {/* Today's summary */}
      <div className="grid grid-cols-4 gap-3">
        <Card className="p-3 text-center"><p className="text-xl font-black">{totals.calories.toFixed(0)}</p><p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Calories</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-black">{totals.carbs.toFixed(0)}g</p><p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Carbs</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-black">{totals.protein.toFixed(0)}g</p><p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Protein</p></Card>
        <Card className="p-3 text-center"><p className="text-xl font-black">{totals.fat.toFixed(0)}g</p><p className="text-[0.65rem] font-bold text-[oklch(0.48_0.035_255)]">Fat</p></Card>
      </div>

      {/* Step: Capture */}
      {step === 'capture' && (
        <Card className="p-5 space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[oklch(0.55_0.03_255)]" />
            <input
              type="text" placeholder="Search foods to log..."
              value={query} onChange={e => handleSearch(e.target.value)}
              className="w-full rounded-2xl border border-[oklch(0.86_0.02_250)] bg-white py-3 pl-11 pr-4 text-sm font-medium outline-none focus:border-[oklch(0.6_0.12_178)]"
            />
          </div>
          {query.length > 1 && (
            <div className="divide-y divide-[oklch(0.92_0.01_250)] rounded-2xl border border-[oklch(0.92_0.01_250)]">
              {foods.map(food => (
                <div key={food.id} className="flex items-center justify-between p-4">
                  <div>
                    <p className="font-black text-[oklch(0.22_0.04_255)]">{food.name}</p>
                    <p className="text-xs font-medium text-[oklch(0.48_0.035_255)]">
                      {food.calories ? `${food.calories} kcal` : ''}
                      {food.carbs ? ` · ${food.carbs}g carbs` : ''}
                      {food.protein ? ` · ${food.protein}g protein` : ''}
                    </p>
                  </div>
                  <Button size="sm" onClick={() => handleSelectFood(food)}>Select</Button>
                </div>
              ))}
              {foods.length === 0 && (
                <p className="p-4 text-sm text-[oklch(0.48_0.035_255)]">No foods found. Try a different search.</p>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Step: Analysing */}
      {step === 'analysing' && selectedFood && (
        <Card className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.72_0.15_178/0.12)]">
              <Brain className="h-5 w-5 text-[oklch(0.55_0.15_178)]" />
            </div>
            <div>
              <h3 className="font-black">Checking nutrition</h3>
              <p className="text-xs text-[oklch(0.48_0.035_255)]">{selectedFood.name}</p>
            </div>
          </div>
          <div className="rounded-2xl bg-[oklch(0.96_0.02_245)] p-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="font-bold">Calories:</span> {selectedFood.calories ? `${selectedFood.calories * quantity} kcal` : '—'}</div>
              <div><span className="font-bold">Carbs:</span> {selectedFood.carbs ? `${(selectedFood.carbs * quantity).toFixed(0)}g` : '—'}</div>
              <div><span className="font-bold">Protein:</span> {selectedFood.protein ? `${(selectedFood.protein * quantity).toFixed(0)}g` : '—'}</div>
              <div><span className="font-bold">Fat:</span> {selectedFood.fat ? `${(selectedFood.fat * quantity).toFixed(0)}g` : '—'}</div>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Quantity</label>
              <input type="number" value={quantity} min={0.25} step={0.25} onChange={e => setQuantity(parseFloat(e.target.value) || 1)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
            <div className="flex-1">
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Meal</label>
              <select value={mealType} onChange={e => setMealType(e.target.value as typeof mealTypes[number])}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm">
                {mealTypes.map(mt => <option key={mt} value={mt}>{mt}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleAnalyse}>Continue <ArrowRight className="ml-1 h-3 w-3" /></Button>
            <Button variant="ghost" onClick={handleReset}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* Step: Review */}
      {step === 'review' && selectedFood && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">Review your meal</h3>
          <div className="rounded-2xl bg-[oklch(0.96_0.02_245)] p-4 space-y-2">
            <div className="flex justify-between text-sm"><span className="font-bold">Food</span><span>{selectedFood.name} × {quantity}</span></div>
            <div className="flex justify-between text-sm"><span className="font-bold">Meal</span><span className="capitalize">{mealType}</span></div>
            <div className="flex justify-between text-sm"><span className="font-bold">Carbs</span><span>{selectedFood.carbs ? `${(selectedFood.carbs * quantity).toFixed(0)}g` : '—'}</span></div>
            <div className="flex justify-between text-sm"><span className="font-bold">Calories</span><span>{selectedFood.calories ? `${selectedFood.calories * quantity} kcal` : '—'}</span></div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleLog}><Utensils className="mr-1 h-4 w-4" /> Log this meal</Button>
            <Button variant="ghost" onClick={() => setStep('capture')}>Go back</Button>
          </div>
        </Card>
      )}

      {/* Step: Memory */}
      {step === 'memory' && (
        <Card className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[oklch(0.72_0.15_178/0.12)]">
              <Clock className="h-5 w-5 text-[oklch(0.55_0.15_178)]" />
            </div>
            <div>
              <h3 className="font-black">Meal logged</h3>
              <p className="text-xs text-[oklch(0.48_0.035_255)]">We will remember this for next time.</p>
            </div>
          </div>
          <div className="rounded-2xl bg-[oklch(0.72_0.15_178/0.06)] p-4">
            <p className="text-sm text-[oklch(0.36_0.035_255)]">
              Last time you logged a meal like this, your glucose peaked about 2 hours later.
              Worth watching how your body responds this time.
            </p>
          </div>
          <Button onClick={handleReset}>Log another meal</Button>
        </Card>
      )}

      {/* Today's entries */}
      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Today's meals</h3>
        <div className="space-y-3">
          {todayEntries.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded-xl bg-[oklch(0.96_0.02_245)] p-3">
              <div className="flex items-center gap-3">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-[oklch(0.72_0.15_178/0.15)]">
                  <Utensils className="h-4 w-4 text-[oklch(0.48_0.12_255)]" />
                </div>
                <div>
                  <p className="font-bold text-sm">{entry.food_name || 'Food'}</p>
                  <p className="text-xs text-[oklch(0.48_0.035_255)]">{entry.meal_type} · {entry.quantity}x</p>
                </div>
              </div>
              <div className="text-right text-sm">
                {entry.calories && <p className="font-bold">{entry.calories.toFixed(0)} kcal</p>}
                {entry.carbs && <p className="text-xs text-[oklch(0.48_0.035_255)]">{entry.carbs.toFixed(0)}g carbs</p>}
              </div>
            </div>
          ))}
          {todayEntries.length === 0 && (
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No meals logged today.</p>
          )}
        </div>
      </Card>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
