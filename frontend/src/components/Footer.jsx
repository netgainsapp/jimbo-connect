export default function Footer() {
  return (
    <footer className="border-t border-border-default mt-16 py-6">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-text-muted">
        <a
          href="https://frontrangedev.co"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 hover:opacity-80 transition group"
        >
          {/* Drop a PNG at frontend/public/frontrange-logo.png to use
              the real wordmark; this CSS recreation renders by default. */}
          <FrontRangeWordmark />
          <span className="text-text-secondary text-xs hidden sm:inline">
            Created by Front Range Dev Co.
          </span>
        </a>
        <div className="text-xs">
          Built in Colorado. Deployed Anywhere.
        </div>
      </div>
    </footer>
  );
}

function FrontRangeWordmark() {
  return (
    <div className="flex flex-col items-center text-text-primary leading-none select-none">
      <div className="text-[13px] font-black tracking-[0.18em]">
        FRONT RANGE
      </div>
      <div className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.25em] mt-0.5">
        <span className="h-px bg-current w-3" />
        DEV CO.
        <span className="h-px bg-current w-3" />
      </div>
    </div>
  );
}
