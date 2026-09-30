/** The DevLens mark: a lens over a rising score line, on the brand gradient. Decorative; the name is always next to it. */
export function BrandMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" className={className}>
      <defs>
        <linearGradient id="devlens-mark" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1" />
          <stop offset="1" stopColor="#4338ca" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#devlens-mark)" />
      <circle cx="14.5" cy="14.5" r="6.2" fill="none" stroke="#fff" strokeWidth="2.2" />
      <path d="M19.2 19.2 24.5 24.5" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M11.4 16.4l2.2-2.4 1.8 1.5 2.4-3" fill="none" stroke="#a5b4fc" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
