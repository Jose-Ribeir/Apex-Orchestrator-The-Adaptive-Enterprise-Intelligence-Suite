/**
 * Theme-aware animated gradient panel for auth cards (sign-in, sign-up).
 * Works in both light and dark themes.
 */
export function AuthCardGradient() {
  return (
    <div className="relative hidden overflow-hidden md:block" aria-hidden>
      <div className="absolute inset-0 bg-muted" />
      {/* Light theme gradient */}
      <div
        className="absolute inset-0 dark:hidden"
        style={{
          background:
            "linear-gradient(135deg, rgb(212 212 212 / 0.4) 0%, transparent 40%, rgb(163 163 163 / 0.3) 70%, rgb(115 115 115 / 0.25) 100%)",
          backgroundSize: "200% 200%",
          animation: "gradient-shift 10s ease infinite",
        }}
      />
      {/* Dark theme gradient */}
      <div
        className="absolute inset-0 hidden dark:block"
        style={{
          background:
            "linear-gradient(135deg, rgb(82 82 82 / 0.5) 0%, transparent 40%, rgb(115 115 115 / 0.35) 70%, rgb(64 64 64 / 0.4) 100%)",
          backgroundSize: "200% 200%",
          animation: "gradient-shift 10s ease infinite",
        }}
      />
      {/* Second layer, opposite direction */}
      <div
        className="absolute inset-0 opacity-70 dark:hidden"
        style={{
          background:
            "linear-gradient(225deg, transparent 0%, rgb(163 163 163 / 0.2) 50%, transparent 100%)",
          backgroundSize: "200% 200%",
          animation: "gradient-shift 12s ease infinite reverse",
        }}
      />
      <div
        className="absolute inset-0 hidden opacity-60 dark:block"
        style={{
          background:
            "linear-gradient(225deg, transparent 0%, rgb(115 115 115 / 0.25) 50%, transparent 100%)",
          backgroundSize: "200% 200%",
          animation: "gradient-shift 12s ease infinite reverse",
        }}
      />
    </div>
  );
}
