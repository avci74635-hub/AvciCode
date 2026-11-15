import { createUniqueId, type ComponentProps } from "solid-js"

// AvciCode splash + hero wordmark.
//
// Nine letters — o l l i E c o d e — on the same 234×42 viewBox the small
// Logo uses (overlay/packages/ui/src/components/logo.tsx). Downstream the
// splash renders this with `w-4/5` + `h-auto`, so the aspect ratio of the
// viewBox is all that matters — the browser scales it to whatever pixel size
// the layout allocates. The parent used to pass a 720×129 opencode glyph set
// here; swapping that for the AvciCode geometry replaces the loading-screen
// wordmark without touching the splash layout code.
//
// Letter grid (6px pixel grid, variable widths with 6px gaps):
//   o   x=3..27    cx=15    width 24   "user" side (--icon-base)
//   l   x=33..45   cx=39    width 12
//   l   x=51..63   cx=57    width 12
//   i   x=69..81   cx=75    width 12
//   E   x=87..111  cx=99    width 24
//   c   x=117..141 cx=129   width 24   "code" side  (--icon-strong-base)
//   o   x=147..171 cx=159   width 24
//   d   x=177..201 cx=189   width 24
//   e   x=207..231 cx=219   width 24
export function Wordmark(
  props: Pick<ComponentProps<"svg">, "class"> & { fade?: boolean; muted?: boolean; outline?: boolean },
) {
  const mask = createUniqueId()
  const maskGradient = createUniqueId()
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 234 42"
      fill="none"
      classList={{
        [props.class ?? ""]: !!props.class,
        "overflow-visible [&_path]:[vector-effect:non-scaling-stroke]": props.outline,
      }}
    >
      <g opacity={props.muted === false ? 1 : 0.6} class="[[data-color-scheme=dark]_&]:opacity-100">
        <g mask={props.fade === false ? undefined : `url(#${mask})`}>
          <g
            opacity={props.muted === false ? 1 : 0.16 * 0.7}
            fill={props.outline ? "none" : "currentColor"}
            stroke={props.outline ? "currentColor" : undefined}
            stroke-width={props.outline ? 1 : undefined}
          >
            {/* o — "user" side */}
            <path pathLength={props.outline ? 1 : undefined} d="M21 12H9V30H21V12ZM27 36H3V6H27V36Z" />
            {/* l */}
            <path pathLength={props.outline ? 1 : undefined} d="M33 6H39V30H45V36H33V6Z" />
            {/* l */}
            <path pathLength={props.outline ? 1 : undefined} d="M51 6H57V30H63V36H51V6Z" />
            {/* i */}
            <path pathLength={props.outline ? 1 : undefined} d="M72 6H78V12H72V6ZM72 15H78V36H72V15Z" />
            {/* E (uppercase, mid-brand accent) */}
            <path pathLength={props.outline ? 1 : undefined} d="M111 24H93V30H111V36H87V6H111V24ZM93 18H105V12H93V18Z" />
            {/* c — "code" side */}
            <path pathLength={props.outline ? 1 : undefined} d="M141 12H123V30H141V36H117V6H141V12Z" />
            {/* o */}
            <path pathLength={props.outline ? 1 : undefined} d="M165 12H153V30H165V12ZM171 36H147V6H171V36Z" />
            {/* d */}
            <path pathLength={props.outline ? 1 : undefined} d="M195 12H183V30H195V12ZM201 36H177V6H195V0H201V36Z" />
            {/* e */}
            <path pathLength={props.outline ? 1 : undefined} d="M213 12V18H225V12H213ZM231 24H213V30H231V36H207V6H231V24Z" />
          </g>
        </g>
      </g>
      <defs>
        <mask id={mask} style="mask-type:alpha" maskUnits="userSpaceOnUse" x="0" y="0" width="234" height="42">
          <rect width="234" height="42" fill={`url(#${maskGradient})`} />
        </mask>
        <linearGradient id={maskGradient} x1="117" y1="22" x2="117" y2="42" gradientUnits="userSpaceOnUse">
          <stop stop-color="white" stop-opacity="0.7" />
          <stop offset="1" stop-color="white" stop-opacity="0" />
        </linearGradient>
      </defs>
    </svg>
  )
}
