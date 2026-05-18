# T1D Companion - Installed Agent Skills

## 🎨 Frontend & UI Design Skills (13 Total)

All skills are installed in `.agents/skills/` and available for AI coding assistants (Claude Code, Cursor, Gemini CLI, etc.)

### Core Design Skills

1. **impeccable** - Professional frontend design & polish
   - Covers: UX review, visual hierarchy, accessibility, responsive design
   - Specializes in: Typography, spacing, layout, color, motion, micro-interactions
   - Best for: Production-grade interface refinement

2. **design-taste-frontend** - Frontend taste evaluation system
   - Covers: Design system consistency, visual feedback
   - Specializes in: UI polish, taste assessment
   - Best for: Ensuring cohesive visual language

3. **gpt-taste** - AI-powered taste & design feedback
   - Covers: Aesthetic evaluation, style consistency
   - Specializes in: Visual design critique
   - Best for: Getting design feedback during development

### UI Framework & Style Skills

4. **industrial-brutalist-ui** - Industrial brutalist design system
   - Covers: Bold, functional, utilitarian interfaces
   - Specializes in: High contrast, geometric layouts
   - Best for: Dashboard-style applications

5. **minimalist-ui** - Minimalist interface design
   - Covers: Clean, sparse, essential interfaces
   - Specializes in: White space, simplicity
   - Best for: Medical/health applications (like T1D Companion)

6. **brandkit** - Brand consistency toolkit
   - Covers: Design tokens, component libraries
   - Specializes in: Theming, reusable systems
   - Best for: Maintaining visual consistency

### Specialized Design Skills

7. **high-end-visual-design** - Premium visual design
   - Covers: Sophisticated aesthetics, luxury interfaces
   - Specializes in: Polish, refinement
   - Best for: Public-facing applications

8. **redesign-existing-projects** - Legacy UI modernization
   - Covers: Refactoring old interfaces
   - Specializes in: Incremental improvements
   - Best for: Updating existing codebases

9. **stitch-design-taste** - Design integration system
   - Covers: Merging multiple design approaches
   - Specializes in: Consistency across components
   - Best for: Multi-contributor projects

### Image & Generation Skills

10. **image-to-code** - Convert images to frontend code
    - Covers: Screenshot → implementation
    - Specializes in: Figma/design mockup conversion
    - Best for: Rapid prototyping from designs

11. **imagegen-frontend-mobile** - Mobile UI generation
    - Covers: Responsive mobile interfaces
    - Specializes in: Touch-friendly components
    - Best for: Mobile-first responsive design

12. **imagegen-frontend-web** - Web UI generation
    - Covers: Desktop web interfaces
    - Specializes in: Layout systems, grids
    - Best for: Dashboard and admin panels

13. **full-output-enforcement** - Complete code generation
    - Covers: Ensuring full file outputs
    - Specializes in: Preventing partial/empty responses
    - Best for: Reliable code generation

## 🏥 T1D Companion Design System

Given the medical nature of the T1D Companion, the following skills are recommended:

### Primary Design Approach
- **minimalist-ui** - Clean, uncluttered, accessible
- **impeccable** - Professional polish
- **brandkit** - Consistent token system

### Supporting Skills
- **design-taste-frontend** - Visual consistency checks
- **industrial-brutalist-ui** - Data-dense dashboard views (optional)

## 🎯 Skill Usage Guidelines

### When to Use Which Skill

**Building Dashboard Views**
```
→ industrial-brutalist-ui (data density)
→ impeccable (polish)
→ design-taste-frontend (consistency)
```

**Mobile Health Tracking**
```
→ minimalist-ui (clarity)
→ imagegen-frontend-mobile (responsive)
→ full-output-enforcement (reliability)
```

**Brand Consistency**
```
→ brandkit (tokens)
→ stitch-design-taste (integration)
→ gpt-taste (feedback)
```

**Rapid Prototyping**
```
→ image-to-code (from mockups)
→ high-end-visual-design (polish)
→ impeccable (refinement)
```

## 🔧 Technical Details

### Installation Location
```
/Users/russellbatchelor/projects/T1D/.agents/skills/
```

### Available AI Assistants
- Claude Code
- Cursor
- Gemini CLI
- Antigravity
- Cline
- Codex
- Pi

### License Information
- All skills use permissive licenses (MIT/Apache 2.0)
- See individual skill directories for details
- NOTICE.md contains attribution information

## 💡 Best Practices for T1D Companion

1. **Medical UI Requirements**
   - Use minimalist-ui for clarity
   - High contrast for readability
   - Large touch targets
   - Color-blind safe palettes

2. **Data Visualization**
   - industrial-brutalist-ui for complex dashboards
   - impeccable for chart polish
   - Consistent color coding (red = danger, green = safe)

3. **Accessibility**
   - WCAG 2.1 AA compliance
   - Screen reader compatibility
   - Keyboard navigation
   - Focus states

4. **Responsiveness**
   - Mobile-first (minimalist-ui)
   - Tablet optimization
   - Desktop dashboard views

5. **Design Tokens**
   - Use brandkit for consistency
   - Define: colors, spacing, typography
   - Reuse across all components

## 📚 Skill Documentation

Each skill directory contains:
- `SKILL.md` - Usage instructions
- `agents/` - Agent-specific implementations
- `reference/` - Design system documentation
- `scripts/` - Helper scripts

## 🚀 Quick Start

```bash
# Review installed skills
ls .agents/skills/

# Read skill documentation
cat .agents/skills/impeccable/SKILL.md

# Use with Claude Code
# The skills auto-activate based on context
```

## 🎨 Design Principles for T1D Companion

### 1. Clarity Over Aesthetics
- Medical data must be readable
- Prioritize information hierarchy
- Avoid visual noise

### 2. Color Psychology
- Red: High glucose (danger)
- Yellow: Warning zones
- Green: In range (safe)
- Blue: Informational

### 3. Typography
- Sans-serif for readability
- Large font sizes
- High contrast ratios

### 4. Touch Targets
- Minimum 44×44px
- Generous spacing
- Thumb-friendly zones

### 5. Consistency
- Use design tokens
- Repeat patterns
- Predictable interactions

## 📊 Integration with Development Workflow

```
Design Phase
    ↓
[ image-to-code ] ← Mockups/Figma
    ↓
[ industrial-brutalist-ui ] ← Dashboard structure
    ↓
[ minimalist-ui ] ← Polish & simplify
    ↓
[ impeccable ] ← Final refinement
    ↓
[ design-taste-frontend ] ← Consistency check
    ↓
[ full-output-enforcement ] ← Complete implementation
    ↓
Production
```

## 🔍 Quality Assurance

### Security Review
- All skills run with full permissions
- Review generated code before deployment
- Security audit recommended

### License Compliance
- Apache 2.0 / MIT licensed
- Attribution in NOTICE.md
- Compatible with commercial use

### Performance
- No runtime overhead
- Development-time only
- No impact on production bundle

## 📈 Future Enhancements

Potential additions:
- **dark-mode-ui** - Dark theme support
- **accessibility-audit** - Automated WCAG checks
- **motion-design** - Micro-interactions and animations
- **responsive-testing** - Cross-device validation

---

*Last updated: May 2026*  
*Skills version: Latest*  
*Compatible with: Claude Code, Cursor, Gemini CLI*