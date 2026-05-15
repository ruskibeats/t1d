/# T1D Companion - Visual Design Mockups

## 🖥️ DASHBOARD SCREEN

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  🩺 Diabetes Dashboard                                          1D  3D  7D  [14D]           │
│  Your glucose overview • Updated 2:34 PM                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │  Current    │   │  Time in    │   │  Below      │   │  Above      │
  │  Glucose    │   │  Range      │   │  Range      │   │  Range      │
  │             │   │             │   │             │   │             │
  │  142 mg/dL  │   │  78%        │   │  12%        │   │  10%        │
  │             │   │             │   │             │   │             │
  │  ↑ 22       │   │  Target:    │   │  < 70       │   │  > 180      │
  │             │   │  70-180     │   │  mg/dL 🔴   │   │  mg/dL 🟡   │
  │  [Normal] 🟢 │   │  mg/dL      │   │             │   │             │
  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘

  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
  │  GLUCOSE CHART                                                                              │
  │                                                                                            │
  │   300 ┤        ....._...._...._...._...._...._...._...._...._...._....                    │
  │       │      .'               '._               '._               '._     _/\             │
  │   250 ┤     .'                     '._               '._               '._ /    \_          │
  │       │    /                          '._               '._               '._/      \       │
  │   200 ┤   /                              '._           _.-'                   \_/         │
  │       │  /         Target Range:          '._       .-'         70-180 mg/dL             │
  │   150 ┤  |                ════════════════════════════════════════════════════             │
  │       │  |                                '._   .-'                                          │
  │   100 ┤  |                                    '.-'            *  *                          │
  │       │  |                                                                                │
  │    70 ┼──┼────────────────────────────────────────────────────────────────────────────────┤
  │       │  |                                                                                │
  │    50 ┤  |                                                                                │
  │       │  |                                                                                │
  │        └──────────────────────────────────────────────────────────────────────────────────┘
  │         12AM  4AM  8AM  12PM  4PM  8PM  12AM                                                 │
  │                                                                                            │
  └──────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────┐  ┌────────────────────────────────────────────────────────────────┐
  │  RECENT EVENTS       │  │  PATTERN SUMMARIES                                               │
  │                      │  │                                                                │
  │  🍽️ Meal             │  │  🔵  Post-meal spike detected                                      │
  │    45g carbs         │  │  Yesterday, 2:30 PM - 185 mg/dL                                  │
  │    12:30 PM          │  │                                                                │
  │                      │  │  🟢  Excellent time in range                                     │
  │  💉 Insulin 8u       │  │  78% in target range this week 🎯                                │
  │    rapid             │  │                                                                │
  │    1:00 PM           │  │  🟡  Exercise impact noted                                       │
  │                      │  │  30 min run → 40 mg/dL drop                                     │
  │  🏃 Exercise 30m     │  │                                                                │
  │    run               │  │                                                                │
  │                      │  │                                                                │
  └──────────────────────┘  └────────────────────────────────────────────────────────────────┘
```

---

## 📊 GLUCOSE READINGS SCREEN

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  Glucose Readings                                                                             │
│  Your recent glucose measurements                                                             │
│                                                                                              │
│  [+ Add Reading]                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  Time                │ Value    │ Status   │ Trend    │ Source                               │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                      │          │          │          │                                      │
│  Dec 15, 2:30 PM      │ 142      │ 🟢Normal │ ↑ 22     │ Dexcom                               │
│                      │ mg/dL    │          │          │                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                      │          │          │          │                                      │
│  Dec 15, 2:00 PM      │ 120      │ 🟢Normal │ ↑ 18     │ Dexcom                               │
│                      │ mg/dL    │          │          │                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                      │          │          │          │                                      │
│  Dec 15, 1:30 PM      │ 102      │ 🟢Normal │ ↓ 5      │ Manual                               │
│                      │ mg/dL    │          │          │                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                      │          │          │          │                                      │
│  Dec 15, 1:00 PM      │ 107      │ 🟢Normal │ —        │ Nightscout                           │
│                      │ mg/dL    │          │          │                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                      │          │          │          │                                      │
│  Dec 15, 12:30 PM     │ 89       │ 🔴Low    │ —        │ Dexcom                               │
│                      │ mg/dL    │          │          │                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

Legend: 🔴 Low (<70)  🟢 Normal (70-180)  🟡 High (>180)
        ↑ Rising     ↓ Falling   — Stable
```

---

## 🧬 PATTERNS ANALYSIS SCREEN

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  Pattern Analysis                                                                             │
│  Understand your glucose patterns and trends                                                 │
│                                                                                              │
│  [ Refresh Analysis ]                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────┐ ┌────────────────────────────────────────────────────────────────────┐
│  TIME IN RANGE      │ │  STATISTICS                                                          │
│  SUMMARY            │ │                                                                      │
│                     │ │  ┌──────────────────┐  ┌──────────────────┐                        │
│  ┌─────────────┐   │ │  │  Avg Glucose     │  │  Min / Max       │                        │
│  │             │   │ │  │  142 mg/dL       │  │  85 / 210        │                        │
│  │      A      │   │ │  ├──────────────────┤  ├──────────────────┤                        │
│  │             │   │ │  │  Std Dev         │  │  Std Dev         │                        │
│  │  78% in     │   │ │  │  28.5            │  │  28.5            │                        │
│  │  range      │   │ │  ├──────────────────┤  ├──────────────────┤                        │
│  │             │   │ │  │  Readings       │  │  Readings        │                        │
│  │  Target:    │   │ │  │  1,247          │  │  1,247           │                        │
│  │  70-180     │   │ │  └──────────────────┘  └──────────────────┘                        │
│  │  mg/dL      │   │ │                                                                      │
│  │             │   │ │  Estimated A1C: 6.8%                                                  │
│  │  Below:     │   │ │                                                                      │
│  │  12%        │   │ │                                                                      │
│  │             │   │ │                                                                      │
│  │  Above:     │   │ │                                                                      │
│  │  10%        │   │ │                                                                      │
│  │             │   │ │                                                                      │
│  └─────────────┘   │ │                                                                      │
│                    │ │                                                                      │
│                    │ │                                                                      │
│                    │ │                                                                      │
│                    │ │                                                                      │
│                    │ │                                                                      │
│                    │ │                                                                      │
└────────────────────┘ └────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  POST-MEAL SPIKES (3)                                                                        │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🍕 Pizza                                                                                   │
│  45g carbs                                                                                  │
│  Severity: Moderate                                                                         │
│                                                                                             │
│  Rise: +42 mg/dL                                                                           │
│  Peak: 220 mg/dL                                                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🍝 Pasta                                                                                   │
│  65g carbs                                                                                  │
│  Severity: Severe                                                                           │
│                                                                                             │
│  Rise: +58 mg/dL                                                                           │
│  Peak: 245 mg/dL                                                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🥗 Salad                                                                                   │
│  25g carbs                                                                                  │
│  Severity: Low                                                                              │
│                                                                                             │
│  Rise: +12 mg/dL                                                                           │
│  Peak: 135 mg/dL                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  EXERCISE IMPACTS (5)                                                                        │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🏃 Running                     │  🚴 Cycling                        │  🏊 Swimming          │
│  Moderate, 30 min               │  High, 45 min                    │  Moderate, 60 min    │
│                                │                                │                      │
│  Change: -35 mg/dL             │  Change: -52 mg/dL              │  Change: -28 mg/dL  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🏋️ Weight Training                                                                         │
│  Low, 45 min                                                                                │
│                                │                                                          │
│  Change: -8 mg/dL             │                                                          │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🧘 Yoga                                                                                    │
│  Low, 60 min                                                                                │
│                                │                                                          │
│  Change: -5 mg/dL             │                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  OVERNIGHT HYPOGLYCEMIA (2 events)                                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🔴 Dec 12                                                                                  │
│                                                                                             │
│  Lowest: 62 mg/dL                                                                          │
│  15% of night low                                                                          │
│                                                                                             │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  🔴 Dec 15                                                                                  │
│                                                                                             │
│  Lowest: 58 mg/dL                                                                          │
│  22% of night low                                                                          │
│                                                                                             │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 💬 AI CHAT SCREEN

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Chat Assistant                                                                      │
│  Ask questions about your glucose patterns, meals, or exercise.                            │
│  I'll provide educational insights.                                                         │
│                                                                                            │
│  🟢 Powered by OpenRouter GPT-4o-mini                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
│                                                                                            │
│  🤖  Assistant                                                                             │
│  I'm here to help you understand your diabetes patterns! Ask me about your                 │
│  glucose data, meals, or exercise.                                                         │
│                                                                                            │
│  "Summarize my recent patterns"                                                           │
│  "Why did I spike after lunch?"                                                           │
│                                                                                            │
│  ───────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                            │
│  👤 You                                                                                    │
│  Why did I spike after lunch today?                                                       │
│  2:34 PM                                                                                   │
│                                                                                            │
│  🤖  Assistant                                                                             │
│  Based on your glucose data, I can see you had a spike to 185 mg/dL around                 │
│  2:30 PM, about 90 minutes after your lunch of 45g carbs (pizza).                          │
│                                                                                            │
│  This is a moderate post-meal spike. Common causes:                                       │
│  • High-carb meal (45g)                                                                    │
│  • Insufficient insulin coverage                                                          │
│  • Pizza has high fat content → delayed absorption                                         │
│                                                                                            │
│  Suggestions:                                                                              │
│  • Split insulin dose (pre-bolus + correction)                                            │
│  • Consider lower-carb alternatives                                                       │
│  • Add post-meal walk to help lower glucose                                               │
│                                                                                            │
│  ───────────────────────────────────────────────────────────────────────────────────────── │
│  👤 You                                                                                    │
│  How can I prevent this tomorrow?                                                        │
│  3:15 PM                                                                                   │
│                                                                                            │
│  🤖  [ Thinking... ]                                                                      │
│                                                                                            │
│  ───────────────────────────────────────────────────────────────────────────────────────── │
│                                                                                            │
│  [ Type your message...                      ]  [ Send ]                                  │
│                                                                                            │
│  💡 Tip: Ask about specific meals, time ranges, or say "summarize my week"                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 COLOR PALETTE

```
PRIMARY BRAND COLORS:
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│  Blue Primary      #2563eb  ┃  Blue Dark        #1d4ed8  ┃  Blue Light      #eff6ff          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                                              │
│  SEMANTIC COLORS:                                                                             │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐        │
│  │    Green    │    Amber    │     Red     │    Slate    │   Slate     │   Slate     │        │
│  │  Success    │  Warning    │  Danger     │    Light    │   Medium    │    Dark     │        │
│  │ #10b981     │ #f59e0b     │ #ef4444     │ #f1f5f9     │ #64748b     │ #0f172a     │        │
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘        │
│                                                                                              │
│  NEUTRAL SCALE:                                                                               │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐                                 │
│  │ 50  │ 100 │ 200 │ 300 │ 400 │ 500 │ 600 │ 700 │ 800 │ 900 │                                 │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤                                 │
│  │#f8  │#f1  │#e2  │#cbd │#94a │#647 │#475 │#334 │#1e2 │#0f1  │                                 │
│  │ fa  │ f5  │ e8  │ b5  │ 3b  │ 475 │ 556 │ 155 │ 93b │ 172a │                                 │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 MOBILE RESPONSIVE

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│  ☰                                                                🩺 T1D                      │
│                                                                                               │
│  Diabetes Dashboard                                                                          │
│  Your glucose overview                                                                        │
│                                                                                               │
│  [1D]  [3D]  [7D] [14D]                                                                       │
│                                                                                               │
│  142 mg/dL   Normal   ↑ 22                                                                    │
│  [Normal]                                    Time in Range                                    │
│              78%      Target:                                                                  │
│              Target:  70-180                                                                  │
│              70-180   mg/dL                                                                   │
│              mg/dL                                                                            │
│              Below Range          Above Range                                                 │
│              12%      < 70        10%      > 180                                              │
│              mg/dL                mg/dL                                                        │
│                                                                                               │
│  [Quick Log]  [Add Reading]                                                                   │
│                                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  Glucose Chart                                                                          │   │
│  │                                                                                         │   │
│  │   300 ┤                                    _/\_                                         │   │
│  │       │                                  _/    \_                                      │   │
│  │   200 ┤                               _/          \_                                   │   │
│  │       │                           _/                \_                                 │   │
│  │   100 ┤                        _/                      \_                              │   │
│  │       │                     _/                          \_                             │   │
│  │    70 ┼─────────────────────┴──────────────────────────────┴─────────────────────────────┤   │
│  │       │                                                                                 │   │
│  │       └─────────────────────────────────────────────────────────────────────────────────┘   │
│  │                                                                                             │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                               │
│  Recent Events →  Pattern Summaries →                                                         │
│                                                                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 COMPONENT DETAILS

### Button States
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PRIMARY       │  │   SECONDARY     │  │   GHOST         │  │   DESTRUCTIVE   │
│                 │  │                 │  │                 │  │                 │
│  [ Normal  ]    │  │  [ Normal  ]    │  │  [ Normal  ]    │  │  [ Normal  ]    │
│                 │  │                 │  │                 │  │                 │
│  [ Hover  ]     │  │  [ Hover  ]     │  │  [ Hover  ]     │  │  [ Hover  ]     │
│                 │  │                 │  │                 │  │                 │
│  [ Active ]     │  │  [ Active ]     │  │  [ Active ]     │  │  [ Active ]     │
│                 │  │                 │  │                 │  │                 │
│  [ Disabled ]   │  │  [ Disabled ]   │  │  [ Disabled ]   │  │  [ Disabled ]   │
│                 │  │                 │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Status Indicators
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   NORMAL        │  │   HIGH          │  │   LOW           │
│                 │  │                 │  │                 │
│  🟢 142 mg/dL   │  │  🟡 220 mg/dL   │  │  🔴 62 mg/dL    │
│                 │  │                 │  │                 │
│  Target Range   │  │  Hyperglycemia  │  │  Hypoglycemia   │
│  70-180 mg/dL   │  │  Action Needed  │  │  Critical!      │
│                 │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 🎨 TYPOGRAPHY SCALE

```
Display (32px)  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Page titles, major headings

Heading (24px)  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Section titles, card headers

Title (18px)    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Sub-sections, table headers

Body (14px)     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Main content, paragraphs, lists

Small (12px)    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Metadata, captions, secondary text

Tiny (11px)     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                Labels, hints, fine print
```

---

## 🎨 SPACING SYSTEM

```
4px   ━━━━━━━━━━━━━━━━━━━━━━━  Icon padding, gaps
8px   ━━━━━━━━━━━━━━━━━━━━━━━  Small gaps, compact layouts
16px  ━━━━━━━━━━━━━━━━━━━━━━━  Standard padding, margins
24px  ━━━━━━━━━━━━━━━━━━━━━━━  Section padding
32px  ━━━━━━━━━━━━━━━━━━━━━━━  Large sections, hero areas
48px  ━━━━━━━━━━━━━━━━━━━━━━━  Hero sections, major divisions
```

---

## 🎨 SHADOW HIERARCHY

```
None      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Flat, no elevation

sm        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Cards, buttons, subtle depth
          box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);

base      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Standard cards, dialogs
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

lg        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Floating elements, modals
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);

xl        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Full overlays, drawers
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

---

## 🎨 TYPOGRAPHY EXAMPLES

```
Display:  Diabetes Dashboard                                    (28px / Bold)
Heading:  Glucose Readings                                       (20px / Semibold)
Title:    Current Glucose                                        (16px / Medium)
Body:     Your recent glucose measurements                       (14px / Regular)
Small:    Updated 2:34 PM                                        (12px / Medium)
Tiny:     Dexcom • 12/15/2024                                   (11px / Regular)
```

---

## 🎨 ICONOGRAPHY

```
Medical:    🩺  💉  🏥  🏃  😴  🧘  🏊  🚴  🏋️
Food:       🍽️  🍕  🍝  🥗  🍎  🥑  🥩  🥤
Status:     🟢  🟡  🔴  🔵  ⚪  🔺  🔻  ➡️  —
Actions:    ➕  ✏️  ✅  ❌  ⚙️  🔍  📊  📈  📉
UI:         ☰  ✕  ←  →  ↑  ↓  ≡  ☰  🔄  ⏸️  ⏯️
```

---

## 🎨 ANIMATION GUIDELINES

```
Duration:   Fast    150ms  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            Base    200ms  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            Slow    300ms  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Easing:     Ease-out   (Default, natural feel)
            Ease-in    (Smooth starts)
            Ease-in-out (Balanced transitions)

Purpose:    Hover       Scale, color change, shadow
            Active      Scale down, emphasize
            Enter       Fade in, slide up
            Exit        Fade out, slide down
            Change      Smooth transition between states
```

---

## 🎨 ACCESSIBILITY CONTRAST

```
Text on White:
┌─────────────────┬─────────────┬────────────────┐
│   Color         │   Ratio     │   WCAG AA      │
├─────────────────┼─────────────┼────────────────┤
│   Slate 900     │   15.9:1    │   ✅ Pass      │
│   Slate 800     │   10.4:1    │   ✅ Pass      │
│   Slate 700     │   7.5:1     │   ✅ Pass      │
│   Blue 600      │   5.2:1     │   ✅ Pass      │
│   Green 600     │   4.8:1     │   ✅ Pass      │
│   Slate 600     │   4.5:1     │   ✅ Pass      │
└─────────────────┴─────────────┴────────────────┘

Text on Color:
┌─────────────────┬─────────────┬────────────────┐
│   Color         │   Ratio     │   WCAG AA      │
├─────────────────┼─────────────┼────────────────┤
│   White on Blue │   4.6:1     │   ✅ Pass      │
│   White on Green│   4.2:1     │   ✅ Pass      │
│   White on Red  │   4.0:1     │   ⚠️ Borderline │
└─────────────────┴─────────────┴────────────────┘
```

---

## ✨ VISUAL DESIGN PRINCIPLES

1. **Clarity First** - Data must be instantly understandable
2. **Color with Purpose** - Semantic color coding, never decorative
3. **Hierarchy Matters** - Size, weight, and spacing guide the eye
4. **Breathing Room** - Generous whitespace reduces cognitive load
5. **Consistent Patterns** - Reusable components, predictable interactions
6. **Mobile-First** - Design for small screens, scale up
7. **Accessible by Default** - WCAG AA minimum, AAA where possible
8. **Performance Conscious** - Every pixel has a purpose
9. **Professional Tone** - Clinical accuracy meets modern design
10. **Safety Through Design** - No ambiguous states, clear warnings

---

*Design System v2.0 | Comprehensive Visual Documentation* 🎨💙
