/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import { Search, Utensils, Plus } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useFood, FoodItem } from '@/hooks/useFood'

const mealTypes = ['breakfast', 'lunch', 'dinner', 'snack'] as const

export function FoodLogPage() {
  const { foods, entries, searchFoods, createEntry } = useFood()
  const [query, setQuery] = useState('')
  const [selectedFood, setSelectedFood] = useState<FoodItem | null>(null)
  const [mealType, setMealType] = useState<typeof mealTypes[number]>('lunch')
  const [quantity, setQuantity] = useState(1)
  const [showForm, setShowForm] = useState(false)

  const handleSearch = (q: string) => {
    setQuery(q)
    if (q.length > 1) searchFoods(q)
  }

  const handleLog = async (food: FoodItem) => {
    setSelectedFood(food)
    setQuantity(1)
    setShowForm(true)
  }

  const handleSubmitEntry = async () => {
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
    setShowForm(false)
    setSelectedFood(null)
    setQuery('')
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

  return (
    <div className="page-shell space-y-6">
      <div>
        <div className="kicker"><span className="kicker-dot" /> Nutrition tracking</div>
        <h2 className="mt-2 text-2xl font-black tracking-[-0.04em] text-[oklch(0.22_0.04_255)]">Food log</h2>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <Card className="p-4 text-center"><p className="text-2xl font-black">{totals.calories.toFixed(0)}</p><p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Calories</p></Card>
        <Card className="p-4 text-center"><p className="text-2xl font-black">{totals.carbs.toFixed(0)}g</p><p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Carbs</p></Card>
        <Card className="p-4 text-center"><p className="text-2xl font-black">{totals.protein.toFixed(0)}g</p><p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Protein</p></Card>
        <Card className="p-4 text-center"><p className="text-2xl font-black">{totals.fat.toFixed(0)}g</p><p className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Fat</p></Card>
      </div>

      <div className="relative">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[oklch(0.55_0.03_245)]" />
        <input
          type="text" placeholder="Search foods..."
          value={query} onChange={e => handleSearch(e.target.value)}
          className="w-full rounded-2xl border border-[oklch(0.86_0.02_250)] bg-white py-3 pl-11 pr-4 text-sm font-medium outline-none focus:border-[oklch(0.6_0.12_178)]"
        />
      </div>

      {query.length > 1 && (
        <Card className="divide-y divide-[oklch(0.92_0.01_250)]">
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
              <Button size="sm" onClick={() => handleLog(food)}><Plus className="h-3 w-3" /> Log</Button>
            </div>
          ))}
        </Card>
      )}

      {showForm && selectedFood && (
        <Card className="p-5 space-y-4">
          <h3 className="font-black">Log: {selectedFood.name}</h3>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Quantity</label>
              <input type="number" value={quantity} min={0.25} step={0.25} onChange={e => setQuantity(parseFloat(e.target.value) || 1)}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm" />
            </div>
            <div className="flex-1">
              <label className="text-xs font-bold text-[oklch(0.48_0.035_255)]">Meal type</label>
              <select value={mealType} onChange={e => setMealType(e.target.value as typeof mealTypes[number])}
                className="mt-1 w-full rounded-xl border border-[oklch(0.86_0.02_250)] px-3 py-2 text-sm">
                {mealTypes.map(mt => <option key={mt} value={mt}>{mt}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSubmitEntry}><Plus className="h-4 w-4" /> Log entry</Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      <Card className="p-5">
        <h3 className="mb-4 text-lg font-black tracking-[-0.03em]">Today's entries</h3>
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
            <p className="text-sm text-[oklch(0.48_0.035_255)]">No entries logged today.</p>
          )}
        </div>
      </Card>
    </div>
  )
}
