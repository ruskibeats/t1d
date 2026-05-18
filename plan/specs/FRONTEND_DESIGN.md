# T1D Companion - Frontend Dashboard Design System

## 📱 App Screen Architecture

### Core Screens (Consolidated)

| Final Screen | Merges These | Purpose |
|---|---|---|
| **Home** | Home Dashboard | Main landing: status line, 3 key insights, main CTA |
| **Welcome** | Ready to Start | Short onboarding intro |
| **Hoot & Holla** | Talk to Hoot & Holla, Ask Companion, AI Advice & Chat, Hoot & Holla Intro | Unified conversational interface: mic, text, camera, barcode, prompt chips |
| **Meal Capture** | Take a Picture, Show it to Hoot & Holla | Front door to meal logging |
| **Analysing Meal** | Analysing Plate | Processing state with light copy |
| **Review Meal** | Review Found Items | User corrects AI food detection before saving |
| **Meal Review** | Food Log with Memory, Meal Context Review, Meal History Context, Food Log & Coaching, Meal Coaching | Shows past context for similar meals |
| **Patterns** | Patterns Overview, Weekly Patterns (all variants), Gentle Patterns Overview, Historical Patterns, Understanding Grades | Card-led pattern system with light grading (Good / Worth watching / Needs attention) |
| **Pattern Detail** | Pattern Card Detail | Deep dive: why noticed, when started, what may matter, actions |
| **Coach** | Personalized Coaching, Humanized Health Advice, Simple Coaching Examples | Progress page: gentle gamification, goals, improvement |
| **Memory** | Personal Memory & Patterns, Store as Memory | Saved observations, stored questions, clinic notes |
| **Voice Notes** | Voice Notes | Speak instead of typing, transcribed and saved |
| **Discuss** | Discuss & Share | Frame for real conversations: talk to parent, bring to doctor |

### Copy Rules

- **Plain English** over product language
- **Observation** over instruction ("You've been going high around 6pm" not "You should adjust your dose")
- **"May" and "worth reviewing"** over authoritative treatment suggestions
- **No dosing language** — never "Continue to Dosage", use "Review what happened last time"
- **No marketing fluff** — cut "calm precision", "optimal state", "humanized health advice"
- **Tone**: calm, useful, observational, trusted companion

### Example Copy

**Home:**
- "Today looks steadier than yesterday."
- "You are going high around 6pm most days."
- "You are waking up around 5 mmol/L most mornings."
- CTA: "Ask about my glucose."

**Patterns (card-led):**
- "You have been on a good pattern for 10 days now."
- "You are waking up low most mornings."
- "You had a low and your heart rate was unusually low at the same time."

**Pattern Detail actions:**
- Save as note | Add voice note | Talk to mummy | Bring to doctor | Compare with last time

**Coach:**
- "10 days of steadier mornings"
- "Evening highs improved this week"
- "3 meal reviews completed this week"
- "Fewer lows after lunch than last week"

### Photo Meal Ingest UX

The photo flow must assume the model is a **starting guess**, not a truth engine.

**Flow:**

1. **Meal Capture**
   - Camera action
   - Barcode fallback
   - Manual add fallback

2. **Analysing Meal**
   - "Looking at your meal..."
   - "Recognising foods and estimating portions..."
   - "You can review this before saving."

3. **Review Meal**
   - Image with overlays / bounding boxes / masks
   - Per-item chips with label, portion, confidence
   - Actions: edit, remove, add missing item, adjust portion
   - Confidence shown gently, not as certainty

4. **Meal Review**
   - Each detected item shows ranked food database matches
   - User picks/edits the match and portion
   - Confirmed items mapped to nutrition database
   - Approximate macros/carbs shown as editable
   - Graph/history card: "Last time you logged a meal like this..."

**Copy rules:**

- Use "We found" / "Looks like" / "Review before saving"
- Avoid "Detected with certainty" or "carbs calculated"
- Use "estimated" for macros until confirmed
- Always allow user correction before writing final meal metrics

**Implementation direction:**

- Treat vision as a proposal step inside our ingestion pipeline, not as the whole feature.
- V1 may use a hosted vision model with a strict JSON contract.
- Later we can swap to FoodSAM or YOLO-style self-hosted detection/segmentation behind the same backend interface.
- Prefer detection/segmentation over single-label Food-101 classifiers.
- Vision proposes coarse labels only; our food resolver maps each label to ranked nutrition candidates.
- Source priority: prior user-confirmed foods → curated/Sparky DB → standardized DBs → open community DBs → model fallback.
- Nutrition estimate happens after user confirmation via food database mapping.
- Confirmed meal creates one `event_group_id` across macros and links into graph history.
- If confidence is low, the UI should say "I’m not sure — add this manually" rather than pretending certainty.

---

## 🎨 Visual Design Overview

### Color Palette

**Primary Brand Colors**
- **Blue Primary**: `#2563eb` (Main actions, active states)
- **Blue Dark**: `#1d4ed8` (Hover states)
- **Blue Light**: `#eff6ff` (Background accents)

**Semantic Colors**
- **Success (Green)**: `#10b981` - Normal glucose, positive states
- **Warning (Amber)**: `#f59e0b` - Elevated glucose, caution
- **Danger (Red)**: `#ef4444` - Low glucose, critical alerts
- **Info (Blue)**: `#2563eb` - Informational messages

**Neutral Scale**
- **Slate 50**: `#f8fafc` - Page background
- **Slate 100**: `#f1f5f9` - Card backgrounds
- **Slate 200**: `#e2e8f0` - Borders, dividers
- **Slate 300**: `#cbd5e1` - Disabled states
- **Slate 400**: `#94a3b8` - Secondary text
- **Slate 500**: `#64748b` - Body text
- **Slate 600**: `#475569` - Primary text
- **Slate 700**: `#334155` - Bold text
- **Slate 800**: `#1e293b` - Titles
- **Slate 900**: `#0f172a` - Dark text

### Typography

**Font Family**
- System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`

**Type Scale**
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Page Title | 24-32px | Bold | Slate 900 |
| Section Title | 18-20px | Semibold | Slate 800 |
| Body Large | 16px | Regular | Slate 600 |
| Body Regular | 14px | Regular | Slate 600 |
| Body Small | 12px | Regular | Slate 400 |
| Label | 11-12px | Medium | Slate 500 |

**Line Heights**
- Tight: 1.25 (titles)
- Normal: 1.5 (body)
- Relaxed: 1.75 (descriptions)

### Spacing System

**Base Unit**: 4px (0.25rem)

| Size | Pixels | Usage |
|------|--------|-------|
| xs | 4px | Icon padding, gaps |
| sm | 8px | Small gaps |
| md | 16px | Standard padding |
| lg | 24px | Section padding |
| xl | 32px | Large sections |
| 2xl | 48px | Hero sections |

### Border Radius

| Size | Pixels | Usage |
|------|--------|-------|
| sm | 4px | Buttons, badges |
| base | 8px | Cards, inputs |
| lg | 12px | Large cards |
| xl | 16px | Hero elements |
| 2xl | 24px | Full width containers |

### Shadows

| Level | CSS |
|-------|-----|
| sm | `0 1px 2px 0 rgba(0, 0, 0, 0.05)` |
| base | `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)` |
| lg | `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)` |
| xl | `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)` |

---

## 💻 Dashboard Page Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Title + Time Range Filters (1D 3D 7D 14D)         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────┐ │
│  │ Stat Card   │ │ Stat Card   │ │ Stat Card   │ │ Stat  │ │
│  │ Current     │ │ Time in     │ │ Below       │ │ Above │ │
│  │ Glucose     │ │ Range       │ │ Range       │ │ Range │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┐ ┌────────────────────┐   │
│  │  Glucose Chart                │ │  Quick Log         │   │
│  │  (Line chart with target      │ │  (Meal, Insulin,   │   │
│  │   bands, gradient fill)       │ │   Exercise, etc)   │   │
│  └──────────────────────────────┘ └────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌────────────────────────────────────┐   │
│  │ Recent       │ │ Pattern Summaries                   │   │
│  │ Events       │ │ - Spike detected                    │   │
│  │ (List)       │ │ - Excellent TIR                    │   │
│  │              │ │ - Exercise impact                   │   │
│  └──────────────┘ └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Stat Cards Design

**Current Glucose Card**
```
┌─────────────────────────────────────┐
│  Current Glucose          ↑ 22       │
│  142 mg/dL               
│                                         │
│  [Blue/Gray/Green badge]             │
│  Normal (70-180)                     │
└─────────────────────────────────────┘
```

**Variant States:**
- **Success (Green)**: Glucose 70-180 mg/dL
  - Background: `#ecfdf5` (green-50)
  - Text: `#065f46` (green-700)
  - Icon: Trending up

- **Warning (Amber)**: Glucose >180 mg/dL
  - Background: `#fffbeb` (amber-50)
  - Text: `#92400e` (amber-700)
  - Icon: Warning

- **Danger (Red)**: Glucose <70 mg/dL
  - Background: `#fef2f2` (red-50)
  - Text: `#991b1b` (red-700)
  - Icon: Alert

### Glucose Chart Design

![Glucose Chart Concept](https://via.placeholder.com/800x400/1e293b/ffffff?text=Glucose+Chart+Visualization)

**Visual Elements:**
1. **Main Line**: Blue (`#2563eb`), 3px width
   - Data points: Circular, 4px radius
   - Border: White, 2px
   - Hover: Enlarges to 6px

2. **Gradient Fill**: Blue translucent (`rgba(37, 99, 235, 0.3)`)
   - Fades from solid to transparent

3. **Target Bands**: Green dashed lines
   - Upper: 180 mg/dL
   - Lower: 70 mg/dL
   - Style: Dashed, 2px

4. **Y-Axis**: 40-300 mg/dL range
   - Label: "mg/dL"
   - Grid lines: Subtle gray

5. **Tooltips**:
   - Background: Dark slate (`rgba(15, 23, 42, 0.95)`)
   - Text: White
   - Status indicator: ✅ Normal / ⚠️ Low / ⚠️ High

### Color-Coded Status System

| Glucose Range | Color | Icon | Meaning |
|---------------|-------|------|---------|
| < 70 mg/dL | Red | 🔴 | Low - Hypoglycemia risk |
| 70-180 mg/dL | Green | 🟢 | Normal - Target range |
| > 180 mg/dL | Amber | 🟡 | High - Hyperglycemia |

**Badge Styles:**
```css
/* Normal */
.bg-green-100 { background: #dcfce7; }
.text-green-700 { color: #166534; }

/* High */
.bg-amber-100 { background: #fef3c7; }
.text-amber-700 { color: #92400e; }

/* Low */
.bg-red-100 { background: #fee2e2; }
.text-red-700 { color: #991b1b; }
```

---

## 📱 Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 768px | Single column, drawer nav |
| Tablet | 768-1024px | 2-column grid |
| Desktop | > 1024px | Full sidebar, 3-4 columns |

**Mobile Adaptations:**
- Sidebar → Slide-out drawer
- Stat cards → Single column
- Chart → Full width
- Quick log → Collapsible section

---

## 🔘 Button Design System

### Variants

**Primary (Blue)**
```
Background: #2563eb
Hover: #1d4ed8
Text: White
Use: Main actions, CTAs
```

**Secondary (Gray)**
```
Background: #f1f5f9
Hover: #e2e8f0
Text: #475569
Use: Secondary actions
```

**Ghost (Transparent)**
```
Background: Transparent
Hover: #f1f5f9
Text: #475569
Use: Low-priority actions
```

**Destructive (Red)**
```
Background: #ef4444
Hover: #dc2626
Text: White
Use: Delete, danger actions
```

**Outline (Bordered)**
```
Background: Transparent
Border: #e2e8f0
Hover: #f1f5f9
Text: #475569
Use: Alternative actions
```

### Sizes

| Size | Padding | Font | Use Case |
|------|---------|------|----------|
| sm | 8px 12px | 12px | Compact UI |
| md | 12px 16px | 14px | Standard buttons |
| lg | 16px 24px | 16px | Hero CTAs |

### Interactions

```css
/* Hover */
transform: scale(1.02);
transition: all 0.2s ease-out;

/* Active */
transform: scale(0.98);

/* Focus */
outline: 2px solid #2563eb;
outline-offset: 2px;

/* Disabled */
opacity: 0.5;
cursor: not-allowed;
```

---

## 🎴 Card Design

**Standard Card**
```
┌─────────────────────────────────────┐
│  ┌─────────────────────────────┐   │
│  │  Card Title                 │   │
│  └─────────────────────────────┘   │
│  Content area                      │
│  - Lists                           │
│  - Tables                          │
│  - Forms                           │
│                                    │
│  ┌─────────────┐ ┌─────────────┐   │
│  │ Action 1    │ │ Action 2    │   │
│  └─────────────┘ └─────────────┘   │
└─────────────────────────────────────┘
```

**Properties:**
- Background: White (`#ffffff`)
- Border: `#e2e8f0` (1px solid)
- Shadow: `0 4px 6px -1px rgba(0, 0, 0, 0.1)`
- Radius: `0.5rem` (8px)
- Padding: `1.5rem` (24px)

**Hover State:**
```css
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
transition: box-shadow 0.2s ease;
```

---

## 📑 Pages Detail

### 1. Dashboard Page

**Hero Section**
```
┌─────────────────────────────────────────────────────┐
│  🩺 Diabetes Dashboard                              │
│  Your glucose overview • Updated 2:34 PM            │
└─────────────────────────────────────────────────────┘
  [1D] [3D] [7D] [14D]  ← Time filters
```

**Stat Grid (2×2 on mobile, 4×1 on desktop)**
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Current    │ │ Time in     │ │ Below       │ │ Above       │
│  Glucose    │ │ Range       │ │ Range       │ │ Range       │
│  142 mg/dL  │ │ 78%         │ │ 12%         │ │ 10%         │
│  ↑ 22       │ │             │ │             │ │             │
│  [Normal]   │ │ Target      │ │ < 70 mg/dL  │ │ > 180 mg/dL │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

**Main Content (2 columns on desktop)**
```
┌──────────────────────┬──────────────────┐
│  Glucose Chart       │  Quick Log       │
│                      │                  │
│  [Line chart with    │  ┌──────────┐    │
│   gradient fill,     │  │  Meal    │    │
│   target bands]      │  ├──────────┤    │
│                      │  │  Insulin │    │
│                      │  ├──────────┤    │
│                      │  │  Exercise│    │
│                      │  └──────────┘    │
│                      │                  │
└──────────────────────┴──────────────────┘
```

**Bottom Section**
```
┌────────────────────┬─────────────────────────────────┐
│  Recent Events     │  Pattern Summaries              │
│                    │                                 │
│  • Meal @ 12:30    │  🔵 Post-meal spike detected    │
│    45g carbs       │  Yesterday, 2:30 PM - 185 mg/dL │
│                    │                                 │
│  • Insulin 8u      │  🟢 Excellent TIR               │
│    rapid           │  78% in target range this week  │
│                    │                                 │
│  • Exercise 30m    │  🟡 Exercise impact noted       │
│    run             │  30 min run → 40 mg/dL drop     │
└────────────────────┴─────────────────────────────────┘
```

---

### 2. Glucose Page

**Header**
```
┌─────────────────────────────────────────────────────┐
│  Glucose Readings                                    │
│  Your recent glucose measurements                    │
│                                                       │
│  [+ Add Reading]                                      │
└─────────────────────────────────────────────────────┘
```

**Table View**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Time              │  Value   │  Status  │  Trend  │  Source  │     │
├─────────────────────────────────────────────────────────────────────┤
│  Dec 15, 2:30 PM   │  142     │  Normal  │  ↑ 22   │  Dexcom  │ ... │
│  Dec 15, 2:00 PM   │  120     │  Normal  │  ↑ 18   │  Dexcom  │ ... │
│  Dec 15, 1:30 PM   │  102     │  Normal  │  ↓ 5    │  Manual  │ ... │
│  Dec 15, 1:00 PM   │  107     │  Normal  │  -      │  Nightsc │ ... │
└─────────────────────────────────────────────────────────────────────┘
```

**Status Indicators**
- 🟢 Normal: 70-180 mg/dL
- 🟡 High: >180 mg/dL  
- 🔴 Low: <70 mg/dL

**Trend Arrows**
- 🔺 Rising (↗)
- 🔻 Falling (↘)
- → Stable

---

### 3. Events Page

**Layout**
```
┌─────────────────────┬──────────────────────────────────────┐
│  Filter by Type     │  Today                               │
│                     │                                      │
│  [All Events]       │  Calendar Icon                       │
│  [🍽️ Meals]         │                                      │
│  [💉 Insulin]       │  No events today                     │
│  [🏃 Exercise]       │  [Add your first event]              │
│  [😴 Sleep]         │                                      │
│                     │  Week View                           │
│  Quick Add:         │                                      │
│  [+] Meal           │                                      │
│  [+] Insulin        │                                      │
│  [+] Exercise       │                                      │
└─────────────────────┴──────────────────────────────────────┘
```

---

### 4. Patterns Page

**Header**
```
┌─────────────────────────────────────────────────────┐
│  Pattern Analysis                                   │
│  Understand your glucose patterns and trends        │
│                                                       │
│  [Refresh Analysis]                                  │
└─────────────────────────────────────────────────────┘
```

**Analysis Results (2 columns)**
```
┌─────────────────────────┬──────────────────────────┐
│  Time in Range          │  Statistics              │
│  Summary                │                          │
│                         │  ┌──────────────────┐    │
│  Grade: A               │  │  Avg Glucose     │    │
│                         │  │  142 mg/dL       │    │
│  ┌─────────────────┐   │  ├──────────────────┤    │
│  │  78% in range   │   │  │  Min / Max      │    │
│  │                 │   │  │  85 / 210       │    │
│  │  Target:        │   │  ├──────────────────┤    │
│  │  70-180 mg/dL   │   │  │  Std Dev        │    │
│  │                 │   │  │  28.5           │    │
│  │  Below: 12%     │   │  ├──────────────────┤    │
│  │  Above: 10%     │   │  │  Readings       │    │
│  │                 │   │  │  1,247          │    │
│  └─────────────────┘   │  └──────────────────┘    │
│                         │                           │
│  ┌─────────────────┐   │  Est. A1C: 6.8%            │
│  │  Control Grade  │   │                           │
│  │                 │   │                           │
│  │      A          │   │                           │
│  │                 │   │                           │
│  └─────────────────┘   │                           │
└────────────────────────┴────────────────────────────┘
```

**Spike Detection**
```
┌─────────────────────────────────────────────────────┐
│  Post-Meal Spikes (3)                                  │
├─────────────────────────────────────────────────────┤
│  🍕 Pizza                                          │
│  45g carbs                                          │
│  Severity: Moderate                                │
│                                                     │
│  Rise: +42 mg/dL                                    │
│  Peak: 220 mg/dL                                    │
├─────────────────────────────────────────────────────┤
│  🍝 Pasta                                          │
│  65g carbs                                          │
│  Severity: Severe                                   │
│                                                     │
│  Rise: +58 mg/dL                                    │
│  Peak: 245 mg/dL                                    │
└─────────────────────────────────────────────────────┘
```

**Exercise Impact**
```
┌─────────────────────────────────────────────────────┐
│  Exercise Impacts (5)                                  │
├─────────────────────────────────────────────────────┤
│  🏃 Running                                           │
│  Intensity: Moderate, 30 min                         │
│                                                     │
│  Change: -35 mg/dL                                  │
├─────────────────────────────────────────────────────┤
│  🚴 Cycling                                          │
│  Intensity: High, 45 min                            │
│                                                     │
│  Change: -52 mg/dL                                  │
└─────────────────────────────────────────────────────┘
```

**Overnight Hypoglycemia**
```
┌─────────────────────────────────────────────────────┐
│  Overnight Hypoglycemia (2 events)                     │
├─────────────────────────────────────────────────────┤
│  🔴 Dec 12                                          │
│                                                     │
│  Lowest: 62 mg/dL                                   │
│  15% of night low                                   │
│                                                     │
├─────────────────────────────────────────────────────┤
│  🔴 Dec 15                                          │
│                                                     │
│  Lowest: 58 mg/dL                                   │
│  22% of night low                                   │
└─────────────────────────────────────────────────────┘
```

---

### 5. Chat Page

**Header**
```
┌─────────────────────────────────────────────────────┐
│  AI Chat Assistant                                  │
│  Ask questions about your glucose patterns, meals,  │
│  or exercise. I'll provide educational insights.    │
│                                                       │
│  🟢 Powered by OpenRouter GPT-4o-mini                │
└─────────────────────────────────────────────────────┘
```

**Chat Interface**
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  🤖 Assistant                                       │
│  I'm here to help you understand your diabetes      │
│  patterns! Ask me about your glucose data, meals,   │
│  or exercise.                                       │
│                                                     │
│  "Summarize my recent patterns"                     │
│  "Why did I spike after lunch?"                     │
│                                                     │
│  ────────────────────────────────────────────────── │
│                                                     │
│  👤 You                                             │
│  Why did I spike after lunch today?                 │
│  2:34 PM                                            │
│                                                     │
│  🤖 Assistant                                       │
│  Based on your glucose data, I can see you had a    │
│  spike to 185 mg/dL around 2:30 PM, about 90        │
│  minutes after your lunch of 45g carbs (pizza).     │
│                                                     │
│  This is a moderate post-meal spike. Common causes: │
│  • High-carb meal (45g)                             │
│  • Insufficient insulin coverage                   │
│  • Pizza has high fat content → delayed absorption  │
│                                                     │
│  Suggestions:                                       │
│  • Split insulin dose (pre-bolus + correction)      │
│  • Consider lower-carb alternatives                 │
│  • Add post-meal walk to help lower glucose         │
│                                                     │
│  [Thinking...]                                      │
│                                                     │
│  ────────────────────────────────────────────────── │
│                                                     │
│  [Type your message...]  [Send]                     │
│                                                     │
│  💡 Tip: Ask about specific meals, time ranges, or  │
│  say "summarize my week"                            │
└─────────────────────────────────────────────────────┘
```

---

### 6. Login Page

**Hero Section**
```
┌─────────────────────────────────────────────────────┐
│  🩺 T1D Companion                                   │
│  Sign in to your account                            │
└─────────────────────────────────────────────────────┘
```

**Login Form**
```
┌─────────────────────────────────────────────────────┐
│  Email                                              │
│  [____________________]                             │
│                                                     │
│  Password                                           │
│  [____________________]                             │
│                                                     │
│  [Sign In]                                          │
└─────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Try Demo]                                            
                                                      
Don't have an account? [Sign up]                      
└─────────────────────────────────────────────────────┘
```

---

### 7. Settings Page

**Profile Section**
```
┌─────────────────────────────────────────────────────┐
│  Profile                                            │
├─────────────────────────────────────────────────────┤
│  First Name: [John_________]                       │
│  Last Name:  [Smith________]                       │
│                                                     │
│  Email:    john@example.com                         │
│  [Save Changes]                                     │
└─────────────────────────────────────────────────────┘
```

**CGM Settings**
```
┌─────────────────────────────────────────────────────┐
│  CGM Settings                                       │
│  Manage your connected CGM devices                  │
│                                                     │
│  [Connect Dexcom]  [Connect Nightscout]             │
└─────────────────────────────────────────────────────┘
```

**Notifications**
```
┌─────────────────────────────────────────────────────┐
│  Notifications                                      │
├─────────────────────────────────────────────────────┤
│  ☑ High glucose alerts                              │
│  ☑ Low glucose alerts                               │
│  ☐ Pattern updates                                  │
└─────────────────────────────────────────────────────┘
```

**Danger Zone**
```
┌─────────────────────────────────────────────────────┐
│  Danger Zone ⚠️                                     │
│  Be careful with these actions                      │
├─────────────────────────────────────────────────────┤
│  [Sign Out]                                         │
│  [Delete Account] (red)                             │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Design Principles

### 1. Clarity First
- Medical data presented clearly and unambiguously
- Color coding for quick status recognition
- Large, readable type sizes
- High contrast for accessibility

### 2. Safety Through Design
- Red used only for critical alerts (low glucose)
- Green for positive/normal states
- No autonomous action buttons
- Clear disclaimers throughout

### 3. Information Hierarchy
- Most important data largest and most prominent
- Secondary information smaller and subtler
- Tertiary details available on interaction

### 4. Responsive by Default
- Mobile-first approach
- Touch-friendly targets (min 44px)
- Content reflows gracefully

### 5. Calm & Clinical
- Professional color palette
- Ample white space
- No aggressive animations
- Focus on data and insights

---

## 📐 Grid System

**Breakpoints:**
```css
/* Mobile */
@media (max-width: 767px) {
  .grid { grid-template-columns: 1fr; }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Desktop */
@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(4, 1fr); }
}
```

**Gutters:**
- Mobile: 16px
- Tablet: 24px
- Desktop: 32px

---

## 🖼️ Iconography

**Lucide Icons Used:**
- `LayoutDashboard` - Dashboard
- `Activity` - Glucose
- `Calendar` - Events
- `BarChart3` - Patterns
- `Bot` - Chat
- `Settings` - Settings
- `TrendingUp` / `TrendingDown` - Trends
- `Clock` - Time

**Emoji Icons:**
- 🍽️ Meal
- 💉 Insulin
- 🏃 Exercise
- 😴 Sleep
- 🩺 Medical

---

## 🌐 Dark Mode (Future)

Planned dark mode implementation:
```css
:root[data-theme='dark'] {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
}
```

---

## ✨ Micro-interactions

### Button Hover
```
transform: scale(1.02);
transition: all 0.2s ease-out;
```

### Button Active
```
transform: scale(0.98);
transition: all 0.1s ease-in;
```

### Card Hover
```
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
transition: box-shadow 0.2s ease;
```

### Chart Tooltip
```
opacity: 0 → 1;
transition: opacity 0.15s ease;
```

---

## 📱 Touch Targets

**Minimum Sizes:**
- Buttons: 44×44px
- Checkboxes: 44×44px
- Navigation items: 48×48px

**Spacing:**
- 8px between touch targets

---

## 🎨 Chart Colors

**Line Chart:**
- Main line: `#2563eb` (blue)
- Target upper: `#10b981` (green, dashed)
- Target lower: `#10b981` (green, dashed)
- Gradient fill: `rgba(37, 99, 235, 0.3)`

**Status Colors:**
- Normal: `#10b981` (green)
- High: `#f59e0b` (amber)
- Low: `#ef4444` (red)

---

## 🏗️ Component Architecture

```
src/
├── pages/              # Page components
├── components/         # Reusable components
│   ├── ui/            # Basic UI (Button, Card)
│   ├── charts/        # Chart components
│   └── dashboard/     # Dashboard widgets
├── contexts/          # React contexts
├── hooks/             # Custom hooks
└── types/             # TypeScript types
```

---

## ✨ Polish Details

### Focus Rings
```css
:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
```

### Disabled States
```css
:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

### Smooth Scrolling
```css
html {
  scroll-behavior: smooth;
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 🎯 Design Tokens

```css
:root {
  /* Colors */
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  
  /* Neutrals */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #475569;
  --color-text-dark: #0f172a;
  
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  
  /* Typography */
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  
  /* Borders */
  --radius-sm: 0.25rem;
  --radius-base: 0.5rem;
  --radius-lg: 0.75rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-base: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-base: 0.2s ease;
  --transition-slow: 0.3s ease;
}
```

---

## 📊 Data Visualization Guidelines

### Color Encoding
| Value Range | Color | Meaning |
|-------------|-------|---------|
| < 70 mg/dL | Red | Hypoglycemia - Critical |
| 70-180 mg/dL | Green | Target Range - Normal |
| 180-250 mg/dL | Amber | Hyperglycemia - Warning |
| > 250 mg/dL | Red | Severe Hyperglycemia |

### Chart Best Practices
- Y-axis always starts at 40 mg/dL (safety margin)
- Target range always visible
- Grid lines subtle (10% opacity)
- Data points emphasized
- Tooltips contextual

---

## 🎨 Brand Identity

### Logo Concept
```
┌─────┐
│  🩺 │
│  T1D│
└─────┘
```

### Typography
- **Headings**: System sans-serif, Bold
- **Body**: System sans-serif, Regular
- **Monospace**: SF Mono, Consolas (data display)

### Voice & Tone
- **Professional**: Clinical accuracy
- **Empathetic**: Understanding, supportive
- **Educational**: Clear, actionable
- **Reassuring**: Calm, confident

---

## 🎯 Accessibility Checklist

- [x] Color contrast ≥ 4.5:1
- [x] Focus indicators visible
- [x] Semantic HTML structure
- [x] ARIA labels on interactive elements
- [x] Keyboard navigation supported
- [x] Screen reader friendly
- [x] Alt text on images
- [x] Form labels properly associated
- [x] Error messages clear and specific
- [x] Skip navigation link

---

## 📱 Mobile Optimizations

### Touch Gestures
- Swipe left/right on events to reveal actions
- Pull down to refresh data
- Pinch to zoom on charts (future)

### Performance
- Lazy load images
- Virtual scroll long lists (future)
- Debounced search inputs
- Optimized re-renders

### Battery
- Reduced motion respected
- Background sync optimized
- WebSocket efficient

---

## 🌍 Internationalization (Future)

Planned i18n support:
```javascript
const locales = {
  en: require('./locales/en.json'),
  es: require('./locales/es.json'),
  fr: require('./locales/fr.json'),
  de: require('./locales/de.json')
};
```

---

## 🎬 Animation Guidelines

### Duration
- **Fast**: 150ms (micro-interactions)
- **Base**: 200ms (default)
- **Slow**: 300ms (emphasis)

### Easing
- **Enter**: `ease-out`
- **Exit**: `ease-in`
- **Change**: `ease-in-out`

### Principles
- Purposeful animations only
- No excessive motion
- Respect `prefers-reduced-motion`
- Consistent timing

---

## 🏗️ Design System Components

### Atoms
- Button
- Input
- Label
- Badge
- Icon

### Molecules
- StatCard
- Card
- FormField
- NavItem

### Organisms
- Header
- Sidebar
- DashboardGrid
- ChartContainer

### Templates
- Dashboard Layout
- Page Layout
- Auth Layout

### Pages
- Dashboard
- Glucose
- Events
- Patterns
- Chat
- Login
- Settings

---

## 🎨 Inspiration & References

### Design Systems
- Apple Health (clarity, typography)
- Google Fit (data viz)
- MyFitnessPal (color coding)
- Dexcom Clarity (medical UI)

### Color Palettes
- Tailwind CSS (utility-first)
- GitHub (neutral professionalism)
- Stripe (brand consistency)

### Typography
- Inter (system-like)
- SF Pro (Apple ecosystem)
- Roboto (Android)

---

## ✨ Final Thoughts

The T1D Companion frontend design prioritizes:

1. **Clarity** - Medical data must be understood instantly
2. **Safety** - No confusion about danger levels
3. **Accessibility** - Usable by all, including vision impaired
4. **Responsiveness** - Works on phone, tablet, desktop
5. **Performance** - Fast loads, smooth interactions
6. **Professionalism** - Clinical accuracy meets modern design

**Design Principle**: *"Make the invisible visible"*  
Turn complex glucose patterns into clear, actionable insights.

---

*Design System v1.0 | T1D Companion | 2024*