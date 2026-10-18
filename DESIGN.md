# AMD Hardware Advisor — Frontend Design Specification

**Status:** Proposed frontend direction  
**Scope:** Visual and interaction design for the React frontend; this document does not change the backend architecture or existing project files.

## 1. Design principles

- **Premium engineering tool, not a generic chatbot.** Lead with hardware research, traceability, comparison, and workload decisions.
- **Evidence before decoration.** Product facts, missing values, citations, and provider state must remain easy to scan.
- **One visual concept.** Use the original futuristic dark-dashboard direction: restrained AMD-inspired red, subtle violet light, glass-like surfaces, thin glowing edges, and a quiet particle/beam hero.
- **MVP restraint.** Prefer a few high-quality effects over many competing animations. Avoid animation behind dense tables or long answers.
- **Honest status.** Never imply that hardware, specifications, citations, or AMD execution are verified unless the underlying evidence supports that state.

## 2. Visual system

### Color tokens

Use these as initial design tokens; tune them against the actual display and accessibility checks during implementation.

| Token | Suggested value | Use |
|---|---|---|
| `bg-canvas` | `#090A0F` | Main application background |
| `bg-elevated` | `#10121A` | Main panels and page sections |
| `surface-card` | `rgba(24, 26, 38, 0.78)` | Glass-like cards |
| `surface-strong` | `#1A1C28` | Inputs, selected rows, dense content |
| `border-subtle` | `rgba(190, 196, 220, 0.14)` | Default card and divider borders |
| `border-glow` | `rgba(255, 55, 75, 0.52)` | Focused or highlighted edges |
| `accent-red` | `#F04452` | Primary action, active navigation, key emphasis |
| `accent-red-hover` | `#FF5967` | Hover state for primary actions |
| `accent-violet` | `#8B72D9` | Secondary glow and small decorative highlights |
| `text-primary` | `#F4F5FA` | Headings and primary content |
| `text-secondary` | `#B7BBCB` | Supporting copy |
| `text-muted` | `#858B9E` | Hints and nonessential metadata |
| `state-success` | `#55C99A` | Confirmed success only |
| `state-warning` | `#F2C66D` | Unverified or caution states |
| `state-error` | `#FF6B76` | Errors |

Do not use color alone to communicate a status. Pair colors with labels and/or icons. Avoid red text for large paragraphs.

### Typography

- Use a clean UI sans-serif such as **Inter** or the system sans-serif fallback.
- Use a restrained display treatment for the hero heading; body and technical content remain neutral and highly legible.
- Suggested scale: hero 48–64 px desktop / 34–42 px mobile; page title 28–36 px; section title 18–22 px; body 14–16 px; metadata 12–13 px.
- Use tabular numerals for specifications and align units consistently.
- Keep line lengths comfortable; long answers and source excerpts should not span the entire ultrawide viewport.

### Spacing, borders, glass, and shadows

- Use a 4 px base spacing scale; common gaps are 8, 12, 16, 24, 32, and 48 px.
- Cards use 14–20 px corner radii; controls use 10–14 px.
- Default borders are thin and low-contrast. Use red or violet glow only for focused, selected, or hero elements.
- Glassmorphism is limited to hero overlays, navigation surfaces, and a few feature cards. Maintain a sufficiently opaque backing behind text and tables.
- Use soft, layered shadows rather than large neon halos. Glow should define edges, not blur content.

### Icon style

Use a consistent thin-line icon set (for example, Lucide) with restrained stroke weight. Use icons alongside text labels, not as the only means of identifying navigation or status. Avoid mixing emoji, filled icons, and several unrelated icon families in the final interface.

## 3. Landing page and hero

The landing experience should feel like the entrance to an AI engineering workspace.

### Header

- Left: AMD Hardware Advisor wordmark and a small abstract hardware/compute mark.
- Right: navigation for **Ask**, **Compare**, **Recommend**, and **Catalogue**; a compact provider/status indicator may appear at the far right.
- On scroll, the header may become a slightly more opaque glass surface. Keep it readable and stable.

### Hero

- Dark canvas with a subtle animated particle field or slow-moving light beams, mostly behind and around the headline.
- Accent the scene with a restrained red beam and faint violet light; avoid a bright rainbow gradient.
- Headline direction: **“Choose AMD hardware with evidence.”**
- Supporting copy: “Ask questions, compare products, and explore workload recommendations grounded in official AMD documentation.”
- Place a prominent question input below the copy, with a clear submit action.
- Add three or four example query chips, such as:
  - “What does the MI300X documentation say?”
  - “Compare these two Instinct products”
  - “What hardware fits my inference workload?”
  - “Which specifications are still unverified?”
- Show four feature shortcuts below or beside the hero input: **Ask AMD Docs**, **Compare Hardware**, **Recommend for a Workload**, **Browse Catalogue**.

Do not imply that an example query can be answered if the current indexed corpus does not support it. Example chips may prefill the input rather than automatically submit.

## 4. Application layout and navigation

Use a shared application shell across all four areas:

- **Ask** — RAG question-and-answer workspace.
- **Compare** — side-by-side product comparison.
- **Recommend** — workload-to-hardware recommendations.
- **Catalogue** — searchable product catalogue.

### Desktop

- A compact top navigation or narrow left rail; keep the main content area wide enough for comparison tables.
- Use a consistent page title, one-sentence description, and primary action location.
- Main content max-width should be comfortable for reading; dense comparison tables may use more width.
- Keep provider and verification state visible in a compact status area, without letting it dominate the interface.

### Mobile

- Collapse navigation to an accessible menu or horizontally scrollable tab row with visible active state.
- Stack cards and form fields in one column.
- Comparison tables may scroll horizontally, but keep the specification name visible where practical.
- Reduce or disable decorative background animation on small or low-power devices.
- Ensure the primary question input and submit button remain easy to reach without horizontal scrolling.

## 5. Ask interface

The Ask workspace is the core RAG experience. It should emphasize clarity and provenance rather than chat theatrics.

### Question entry

- Large, clearly labelled question input with a visible submit button.
- Support Enter to submit and Shift+Enter for a newline if multiline input is used.
- Show example queries when the conversation is empty.
- Keep the input usable while previous answers remain visible.

### Answer presentation

- Render the user's question and the assistant response as distinct, readable message blocks.
- Use a narrow reading column for long responses.
- Separate answer prose from evidence. Number citations inline as `[1]`, `[2]`, etc., only when the backend can map those markers to real retrieved sources.
- Under each answer, show source cards with source title, source URL, page/section when available, and a short relevant excerpt when available.
- Clicking a source opens the official source in a new tab with safe link behavior. Do not fabricate page numbers or source excerpts.
- Keep chunk IDs available as technical provenance, but visually subordinate them to the source title and link.

### States

- **Loading:** show a small progress indicator and “Searching official AMD documentation…” followed by “Preparing a cited answer…” if these stages can be accurately distinguished.
- **Error:** concise message, retry action, and a non-sensitive diagnostic detail if useful. Never show stack traces or API keys in the user interface.
- **Insufficient evidence:** show a distinct neutral/warning panel stating that the available indexed documentation does not support a reliable answer. Do not fill the gap with model knowledge or invented citations.
- **Empty retrieval:** explain that no relevant source passages were found and invite a narrower or differently phrased question.
- **No citations:** if the backend answer has no valid citation references, do not style it as a fully grounded answer. Display the appropriate limitation or insufficient-evidence state.

## 6. Compare interface

### Product selection

- Searchable multi-select control for two or more catalogue products.
- Display selected products as removable chips with family and model names.
- Provide a clear “Compare products” action and a helpful empty state before selection.
- Prevent unknown products from being added and show an actionable validation message when fewer than two products are selected.

### Comparison table

- Use rows for specification fields and columns for each selected product.
- Include only real catalogue fields; show unknown or unverified values as **“Not verified”** or **“Not available in source”**, according to backend metadata. Never turn null into zero or infer missing specifications.
- Display units in column values or field labels consistently.
- Highlight differences only when the underlying values are comparable and known.
- Attach source links to the relevant product/specification provenance. If the data model only supplies one source URL per product, label it as the product source rather than implying field-level provenance.
- On narrow screens, allow horizontal scrolling and keep row labels readable.

## 7. Recommend interface

### Workload form

Collect only fields supported by the current recommendation logic. Possible inputs include:
- Workload type or free-text description.
- Minimum memory requirement, if applicable.
- Preferred framework or software stack.
- Optional preference such as APU/unified memory, only if the backend supports it.

Mark optional fields clearly. Explain that recommendations are catalogue-based and do not represent benchmark results or guaranteed performance.

### Recommendation results

- Present a ranked set of product cards.
- Each card includes product family/model, recommendation rank, known relevant specifications, match explanation, and source links.
- Separate **known matching facts**, **assumptions**, and **limitations**. Do not present a score as a probability or benchmark.
- If products have tied scores or insufficient known specifications, say so; do not invent a winner.
- Show alternatives with a short explanation of when each might be suitable.
- If no catalogue product satisfies the stated constraints, show an explicit no-match state rather than silently relaxing constraints.

## 8. Catalogue interface

### Search and filters

- Search by product/model name.
- Filter by family: **Instinct**, **EPYC**, **Ryzen AI**, and **Radeon Pro**.
- Optional filters for architecture or other fields should appear only when the data actually exists and is reliable.
- Provide a reset-filters action and a clear empty state.

### Product cards

Each card may show:
- Family and exact model name.
- Architecture or platform only when sourced.
- A small number of known, verified key specifications.
- A visible data-quality label such as **Verified fields**, **Partial data**, or **Unverified fields**, based on explicit metadata—not a guess.
- Official source link(s).

Unknown numeric fields should remain unknown. Do not populate placeholder products or claim broad family coverage until the catalogue actually contains verified records for those families.

## 9. ReactBits component plan

ReactBits provides copy/installable animated React components in JavaScript or TypeScript variants, including Tailwind-oriented variants. Treat component names below as candidate selections; verify the current component page, free/pro availability, exact variant, dependencies, props, and installation command before adding any component. Do not assume an API based on a component name.

| Candidate | Intended use | Constraint |
|---|---|---|
| **Particles** (ReactBits background) | Subtle hero particle field | One hero background only; low density and speed; disable or reduce under reduced-motion preferences |
| **Beams** (ReactBits background) | Alternative hero beam treatment | Choose this *or* Particles for the initial implementation, not both at full strength |
| **SpotlightCard** | Optional subtle pointer spotlight on one or two feature cards | Use only if the current free component and Tailwind variant are confirmed; disable pointer tracking on touch devices |
| **AnimatedContent** | Gentle entrance reveal for hero content or sections | Use sparingly; avoid replaying animation on every rerender |
| **ShinyText** | Brief accent on a small hero label or CTA | Never apply to body copy, specs, table cells, or status labels |

ReactBits official starting points:
- Components and installation overview: https://reactbits.dev/
- Background components: https://www.reactbits.dev/c/backgrounds
- Animated Content: https://reactbits.dev/animations/animated-content
- Component catalogue and variants: https://www.reactbits.dev/get-started/index

The official site currently documents `AnimatedContent` and `Particles`/`Beams` background options; the site provides component-specific installation instructions. Confirm exact component availability and commands at implementation time. Do not assume that a component named “Background Beams” or `SpotlightCard` is available in the exact chosen variant merely because similar names appear in examples or other libraries.

### Implementation approach

1. Create the React + Vite + Tailwind foundation only after the architecture conflict below is resolved.
2. Select one background effect first and verify it builds on the target Windows environment.
3. Add optional card/text effects only after core navigation, forms, tables, citations, and states work.
4. Use ReactBits components as owned source where the official install flow supports that; keep their dependencies explicit and reviewable.
5. Avoid a large animation dependency or WebGL effect if it threatens performance or implementation time.

## 10. Reusable component inventory

- **Button:** primary red action, secondary neutral action, and quiet/tertiary action. Includes disabled, loading, hover, focus, and active states.
- **Card:** consistent border, radius, spacing, and surface. Variants may include feature, product, recommendation, and status cards.
- **QuestionInput:** labelled input, submit action, examples, keyboard behavior, and validation.
- **SourceCard:** official source title, URL, optional page/section/excerpt, and source metadata. Never construct a source URL from an untrusted title.
- **ProductCard:** exact model, family, known sourced facts, data-quality status, and official source link.
- **SpecificationValue:** formats value and unit consistently; represents unknown values explicitly.
- **StatusIndicator:** label + icon + accessible text for provider, verification, loading, and error states. Color is supplementary.
- **Notification:** non-blocking success/error/info feedback. Important errors remain visible and are not conveyed only by a disappearing toast.
- **EmptyState:** clear explanation and next action for empty catalogue search, no comparison selection, no recommendations, and insufficient retrieval.
- **LoadingState:** concise status text plus restrained indicator; preserve layout to reduce visual jumps.

## 11. Interaction states and accessibility

All interactive elements must have:
- Default, hover, focus-visible, active, disabled, loading, empty, and error states where applicable.
- Keyboard-accessible navigation and controls with visible focus indicators.
- Semantic headings, buttons, links, form labels, table headers, and appropriate ARIA only where native semantics are insufficient.
- Sufficient contrast for text, borders, focus rings, and status labels.
- A logical tab order and no keyboard traps.
- Accessible names for icon-only controls.
- Screen-reader announcements for asynchronous loading and meaningful result/error updates.
- Reduced-motion support using `prefers-reduced-motion`; remove or substantially reduce particles, beam motion, parallax, and reveal effects when requested.
- No flashing, rapid pulses, or animation that interferes with reading.
- A functional layout at mobile widths and browser zoom.
- External source links that are keyboard accessible and clearly identified.

Animation must never be required to understand a control, status, source, or specification.

## 12. Provider and AMD verification status

- Display the **active runtime provider** and model reported by the actual provider instance, not merely a raw `.env` setting or hardcoded label.
- Distinguish configured provider from active provider if fallback occurs.
- Show states such as **Token Factory active**, **Local fallback active**, or **Provider unavailable** only when the runtime can establish those facts.
- Keep **AMD execution: NOT VERIFIED** until the project's real verification procedure succeeds with the required AMD-host evidence.
- A successful completion from an endpoint is not, by itself, proof that execution ran on approved AMD infrastructure.
- Never use an AMD-verified badge based only on configuration, a user-entered flag, a model name, or a previous stale verification record.
- Provide a link or expandable detail area for the verification record, without exposing API keys or other secrets.

## 13. Implementation guidance and architecture alignment

This design assumes the desired future frontend is **React + Vite + Tailwind CSS with ReactBits**, with **FastAPI as the backend**. That is a proposed direction, not the current architecture documented in the project files.

The existing `ARCHITECTURE.md` and `AGENTS.md` specify a Python 3.11 application with a **Streamlit UI** at `src/amd_hardware_advisor/ui/app.py`; the current PRD also lists Streamlit as the MVP UI. Therefore, the React frontend conflicts with the current documented stack and must not be introduced silently.

If React is approved:
- Update `PRD.md`, `ARCHITECTURE.md`, and `AGENTS.md` in a separate, explicit architecture-change task; this DESIGN.md task does not modify them.
- Define FastAPI routes and request/response schemas for Ask, Compare, Recommend, Catalogue, provider status, and AMD verification status before wiring the UI.
- Keep the current RAG index and structured catalogue as separate backend responsibilities. Q&A uses retrieved document chunks; comparison/recommendation specifications come from the validated catalogue.
- Preserve source metadata end to end so the frontend renders real citations and provenance rather than generating links itself.
- Keep provider selection, API credentials, retrieval, answer generation, and verification on the Python backend. Never place provider secrets in Vite client-side environment variables.
- Use typed API response shapes and loading/error states. Keep mock responses confined to isolated UI development and never present them as live results.
- Use Vite's development proxy for local API requests if useful; production routing/deployment remains a separate decision.
- Keep the React layer presentational and interaction-focused; avoid reimplementing RAG, catalogue validation, comparison, or recommendation logic in the browser.

If React is not approved for the MVP, implement this visual direction within the existing Streamlit app and defer the ReactBits plan. Do not build both frontends for the same MVP without an explicit decision.

## 14. Architecture decisions still requiring confirmation

1. **Frontend stack:** keep Streamlit for the hackathon MVP or formally migrate to React + Vite + Tailwind + ReactBits.
2. **API boundary:** if React is selected, confirm whether FastAPI will be added as a new service and define the endpoint schemas and local/production serving arrangement.
3. **Scope of product families:** confirm which of Instinct, EPYC, Ryzen AI, and Radeon Pro have real verified catalogue entries; filters and cards must reflect actual data.
4. **ReactBits selection:** confirm one hero background effect and verify its exact free component, Tailwind variant, dependencies, and installation command.
5. **Provider status contract:** confirm how the frontend obtains active provider/model, fallback reason, and verification record from the backend.
6. **Responsive/navigation structure:** choose top navigation versus a compact left rail after a quick browser-width prototype; both are compatible with the visual system.
7. **Deployment:** confirm how the frontend and backend will be hosted and how API URLs/secrets will be configured outside local development.

These decisions should be resolved before a React implementation starts. No existing project document or application code is changed by this design specification.
