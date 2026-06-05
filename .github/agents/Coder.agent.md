---
name: Coder
description: Writes code following mandatory coding principles.
model: Claude Sonnet 4.6 (copilot)
tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'web', 'todo']
---

## Mandatory Coding Principles

These coding principles are mandatory:

1. Structure
- Use a consistent, predictable project layout.
- Group code by feature/screen; keep shared utilities minimal.
- Create simple, obvious entry points.
- Before scaffolding multiple files, identify shared structure first. Use framework-native composition patterns (layouts, base templates, providers, shared components) for elements that appear across pages. Duplication that requires the same fix in multiple places is a code smell, not a pattern to preserve.

2. Architecture
- Prefer flat, explicit code over abstractions or deep hierarchies.
- Avoid clever patterns, metaprogramming, and unnecessary indirection.
- Minimize coupling so files can be safely regenerated.

3. Functions and Modules
- Keep control flow linear and simple.
- Use small-to-medium functions; avoid deeply nested logic.
- Pass state explicitly; avoid globals.

4. Naming and Comments
- Use descriptive-but-simple names.
- Comment only to note invariants, assumptions, or external requirements.

5. Logging and Errors
- Emit detailed, structured logs at key boundaries.
- Make errors explicit and informative.

6. Regenerability
- Write code so any file/module can be rewritten from scratch without breaking the system.
- Prefer clear, declarative configuration (JSON/YAML/etc.).

7. Platform Use
- Use platform conventions directly and simply (e.g., WinUI/WPF) without over-abstracting.

8. Modifications
- When extending/refactoring, follow existing patterns.
- Prefer full-file rewrites over micro-edits unless told otherwise.

9. Quality
- Favor deterministic, testable behavior.
- Avoid "magic" code that is hard to understand or debug.

# Fluid & Fully Adaptive Frontend Development Prompt

## Objective

Build a truly fluid and responsive frontend that adapts smoothly to **any viewport width**, including dynamically resized browser windows.

The layout must never break, regardless of screen size — even at widths between common breakpoints.

---

## Core Principle

The UI must be:

- Fluid (not breakpoint-dependent)
- Ratio-based (relative scaling)
- Flexible (content-driven layout)
- Resize-safe (works at any arbitrary width)

Avoid rigid breakpoint-only design.

---

## Responsiveness Requirements

### 1. Fluid Layout (No Hard Breaks)

- Layout must adapt at **every possible width**
- No visual breaking between desktop and tablet sizes
- No layout jumps when resizing browser
- No horizontal scrolling

---

### 2. Use Modern Fluid Techniques

#### Units
Use relative units instead of fixed pixels:
- `%`
- `rem`
- `em`
- `vw`
- `vh`
- `clamp()`

Avoid fixed `px` values for layout sizing.

---

### 3. Layout System

Use:

- Flexbox (flex-grow, flex-wrap)
- CSS Grid with:
  - `minmax()`
  - `auto-fit`
  - `auto-fill`
- Content-based sizing instead of fixed widths

Example principle:
- Cards should wrap naturally using `grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))`
- Elements should grow/shrink proportionally

---

### 4. Fluid Typography

Use `clamp()` to scale text smoothly:

Example principle:
- Font sizes must scale continuously with viewport width
- No abrupt jumps at breakpoints

---

### 5. Breakpoints (Only When Necessary)

Breakpoints may be used only for:
- Major structural changes
- Navigation pattern shifts (e.g., hamburger menu)

Do NOT rely on breakpoints for general resizing behavior.

---

### 6. No JavaScript Resize Hacks

Do NOT:
- Manually calculate element sizes using JavaScript
- Continuously track window width to scale elements

Use CSS-native responsive capabilities.

---

### 7. Resize Testing Requirements

The layout must remain stable when:

- Shrinking browser gradually from 1440px down to 300px
- Expanding from 400px up to ultra-wide screens
- Viewing at uncommon widths (e.g., 915px, 1117px, 1366px)

There must be:
- No overlap
- No overflow
- No squished content
- No broken alignment

---

## Code Quality Standards

- Mobile-first approach
- Clean semantic HTML
- Maintainable CSS structure
- Comment explanations for fluid decisions
- No fixed container widths (except max-width for readability)

---

## Expected Outcome

The final UI must:

- Adapt proportionally at ANY viewport size
- Reflow content naturally
- Maintain spacing ratios
- Scale typography smoothly
- Never visually break during resize