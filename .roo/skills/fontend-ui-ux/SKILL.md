---
name: frontend-dify-ui
description: Build and refine the chatbot frontend using Dify-inspired product UX patterns, with a dark professional interface, restrained neon accents, strong information hierarchy, and reusable components that support real chat workflows.
---

Use this skill for chat interface, sidebar, layout, component styling, design system, settings screens, chat history, sources panel, and responsive behavior.

Reference direction:
- Product UX inspiration: Dify
- Visual mood: dark interface with restrained neon accents
- Avoid flashy DeFi landing-page patterns in functional chat screens

Translate the style carefully:
- dark surfaces
- subtle cyan/blue/magenta accent moments
- clean panel separation
- compact but readable density
- minimal glow only on primary actions or active states

Dify-inspired behaviors:
- Left sidebar for navigation, chat history, and workspace switching
- Main chat area with clear message rhythm
- Input composer fixed or anchored cleanly
- Optional right-side contextual panel for sources, settings, logs, or metadata
- Clear states for loading, streaming, empty, retry, and failure

Rules:
- Keep UI logic separate from API/model details.
- Prefer reusable layout shells and chat primitives.
- Optimize for scanning, trust, and speed.
- Support markdown, code blocks, copy, regenerate, and long responses well.
- Do not use generic AI gradients or unnecessary glassmorphism.
- No verbose comments.

Primary outcomes:
- The app feels closer to Dify than to a crypto landing page.
- New UI features can be added without redesigning the whole app.
- Claude only edits the UI layer when visual or interaction work is needed.