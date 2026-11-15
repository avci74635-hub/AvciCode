import { createSignal, ErrorBoundary, onCleanup, onMount, Show } from "solid-js"
import { Portal } from "solid-js/web"

// AvciCode ambient background layer. Rendered into <body> via a Portal so it
// can never affect the stacking / layout / clipping of vendor panels. Behind
// everything with z-index: -1 and pointer-events: none.
//
// The generic motion set (orbs, beam, grid) runs on every theme. The named
// kits add their own ornament on top. Static themes still get the base layer,
// because the base layer is what makes the app feel alive.
//
// If any decoration throws during paint, the ErrorBoundary catches it and
// renders nothing — the app keeps working.

function readTheme(): string {
  if (typeof document === "undefined") return ""
  return document.documentElement.getAttribute("data-theme") ?? ""
}

export function OlliecodeFxAmbient() {
  const [theme, setTheme] = createSignal<string>(readTheme())

  onMount(() => {
    const html = document.documentElement
    setTheme(html.getAttribute("data-theme") ?? "")
    const obs = new MutationObserver(() => {
      const t = html.getAttribute("data-theme") ?? ""
      if (t !== theme()) setTheme(t)
    })
    obs.observe(html, { attributes: true, attributeFilter: ["data-theme"] })
    onCleanup(() => obs.disconnect())
  })

  const kit = () => theme()

  return (
    <ErrorBoundary fallback={<></>}>
      <Portal mount={document.body}>
        <div class="olliE-ambient pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
          {/* Always-on motion layer. */}
          <div class="ac-orbs">
            <i />
            <i />
            <i />
            <i />
          </div>
          <div class="ac-beam" />
          <div class="ac-grid" />

          {/* Named-kit ornaments. */}
          <Show when={kit() === "frost"}>
            <div class="olliE-orb olliE-orb-a" />
            <div class="olliE-orb olliE-orb-b" />
            <div class="olliE-orb olliE-orb-c" />
          </Show>
          <Show when={kit() === "porcelain"}>
            <div class="olliE-blob olliE-blob-a" />
            <div class="olliE-blob olliE-blob-b" />
            <div class="olliE-blob olliE-blob-c" />
          </Show>
          <Show when={kit() === "prism"}>
            <div class="olliE-aura olliE-aura-a" />
            <div class="olliE-aura olliE-aura-b" />
          </Show>
          <Show when={kit() === "vapor"}>
            <div class="olliE-sky" />
          </Show>
          <Show when={kit() === "obsidian"}>
            <div class="olliE-grain" />
          </Show>
        </div>
      </Portal>
    </ErrorBoundary>
  )
}
