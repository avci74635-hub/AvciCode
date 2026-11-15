import { type ComponentProps } from "solid-js"

// AvciCode wordmark glyph set.
//
// Nine letters — o l l i E c o d e — on the same 234×42 viewBox opencode uses,
// so every component sized for the wordmark (new-session, lodger, pin-board,
// brick-breaker) still lays out correctly without geometry changes elsewhere.
//
// Letter grid, variable widths with 6px gaps:
//   o   at x=3..27    cx=15    width 24   "user" side (--icon-base)
//   l   at x=33..45   cx=39    width 12
//   l   at x=51..63   cx=57    width 12
//   i   at x=69..81   cx=75    width 12
//   E   at x=87..111  cx=99    width 24
//   c   at x=117..141 cx=129   width 24   "code" side  (--icon-strong-base)
//   o   at x=147..171 cx=159   width 24
//   d   at x=177..201 cx=189   width 24
//   e   at x=207..231 cx=219   width 24
//
// All strokes are on the 6px pixel grid, matching opencode's "chunky block"
// aesthetic. The weak paths render under the stems with --icon-weak-base so
// counters cast a shadow the same way the OPENCODE wordmark did.
//
// The lodger lives in the top counter of the final `e`, centred on (219, 15).

export const Mark = (props: { class?: string }) => {
  return (
    <svg
      data-component="logo-mark"
      classList={{ [props.class ?? ""]: !!props.class }}
      viewBox="0 0 16 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path data-slot="logo-logo-mark-shadow" d="M12 16H4V8H12V16Z" fill="var(--icon-weak-base)" />
      <path data-slot="logo-logo-mark-o" d="M12 4H4V16H12V4ZM16 20H0V0H16V20Z" fill="var(--icon-strong-base)" />
    </svg>
  )
}

export const Splash = (props: Pick<ComponentProps<"svg">, "ref" | "class">) => {
  return (
    <svg
      ref={props.ref}
      data-component="logo-splash"
      classList={{ [props.class ?? ""]: !!props.class }}
      viewBox="0 0 80 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M60 80H20V40H60V80Z" fill="var(--icon-base)" />
      <path d="M60 20H20V80H60V20ZM80 100H0V0H80V100Z" fill="var(--icon-strong-base)" />
    </svg>
  )
}

export const Logo = (props: { class?: string }) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 234 42"
      fill="none"
      classList={{ [props.class ?? ""]: !!props.class }}
    >
      <g>
        {/* o — "user" side */}
        <path d="M21 30H9V18H21V30Z" fill="var(--icon-weak-base)" />
        <path d="M21 12H9V30H21V12ZM27 36H3V6H27V36Z" fill="var(--icon-base)" />
        {/* l */}
        <path d="M45 30H39V24H45V30Z" fill="var(--icon-weak-base)" />
        <path d="M33 6H39V30H45V36H33V6Z" fill="var(--icon-base)" />
        {/* l */}
        <path d="M63 30H57V24H63V30Z" fill="var(--icon-weak-base)" />
        <path d="M51 6H57V30H63V36H51V6Z" fill="var(--icon-base)" />
        {/* i */}
        <path d="M72 6H78V12H72V6ZM72 15H78V36H72V15Z" fill="var(--icon-base)" />
        {/* E (uppercase, mid-brand accent) */}
        <path d="M111 24V30H93V24H111Z" fill="var(--icon-weak-base)" />
        <path d="M111 24H93V30H111V36H87V6H111V24ZM93 18H105V12H93V18Z" fill="var(--icon-base)" />
        {/* c — "code" side */}
        <path d="M141 30H123V18H141V30Z" fill="var(--icon-weak-base)" />
        <path d="M141 12H123V30H141V36H117V6H141V12Z" fill="var(--icon-strong-base)" />
        {/* o */}
        <path d="M165 30H153V18H165V30Z" fill="var(--icon-weak-base)" />
        <path d="M165 12H153V30H165V12ZM171 36H147V6H171V36Z" fill="var(--icon-strong-base)" />
        {/* d */}
        <path d="M195 30H183V18H195V30Z" fill="var(--icon-weak-base)" />
        <path d="M195 12H183V30H195V12ZM201 36H177V6H195V0H201V36Z" fill="var(--icon-strong-base)" />
        {/* e */}
        <path d="M231 24V30H213V24H231Z" fill="var(--icon-weak-base)" />
        <path d="M213 12V18H225V12H213ZM231 24H213V30H231V36H207V6H231V24Z" fill="var(--icon-strong-base)" />
      </g>
    </svg>
  )
}
