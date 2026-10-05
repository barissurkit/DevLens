/**
 * The DevLens mark: a magnifying lens with three rising score bars inside, on a deep teal tile.
 * Decorative: the name always sits next to it. The same drawing is used for the favicon (`app/icon.svg`).
 */
export function BrandMark({ className = "h-8 w-8", idPrefix = "brand" }: { className?: string; idPrefix?: string }) {
  // Gradient ids must be unique per page, and the mark appears in the header, the footer and the printed cover.
  const tile = `${idPrefix}-tile`;
  const sheen = `${idPrefix}-sheen`;
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className={className}>
      <defs>
        <linearGradient id={tile} x1="6" y1="2" x2="42" y2="46" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2bb5a5" />
          <stop offset="0.55" stopColor="#0f766e" />
          <stop offset="1" stopColor="#134e4a" />
        </linearGradient>
        <linearGradient id={sheen} x1="24" y1="0" x2="24" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffffff" stopOpacity="0.28" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill={`url(#${tile})`} />
      <rect width="48" height="26" rx="12" fill={`url(#${sheen})`} />
      <circle cx="21.5" cy="21.5" r="11.2" fill="#ffffff" fillOpacity="0.1" stroke="#ffffff" strokeWidth="3.4" />
      <path d="M29.8 29.8 38 38" stroke="#ffffff" strokeWidth="4.6" strokeLinecap="round" />
      <rect x="15.2" y="22.6" width="3.4" height="4.4" rx="1.1" fill="#99f6e4" />
      <rect x="19.8" y="18.6" width="3.4" height="8.4" rx="1.1" fill="#ccfbf1" />
      <rect x="24.4" y="14.4" width="3.4" height="12.6" rx="1.1" fill="#ffffff" />
    </svg>
  );
}

/** "DevLens" set as a wordmark: the product name in strong ink, the lens half in the brand color. */
export function BrandWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-semibold tracking-tight text-slate-950 ${className}`}>
      Dev<span className="text-brand-700">Lens</span>
    </span>
  );
}
