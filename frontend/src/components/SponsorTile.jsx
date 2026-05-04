import { ExternalLink, RefreshCw, Trash2, EyeOff } from "lucide-react";

function gradientFor(seed) {
  const hues = [210, 200, 220, 190, 230, 250, 180];
  const hash = (seed || "")
    .split("")
    .reduce((a, c) => a + c.charCodeAt(0), 0);
  const h1 = hues[hash % hues.length];
  const h2 = hues[(hash + 3) % hues.length];
  return `linear-gradient(135deg, hsl(${h1} 70% 55%), hsl(${h2} 65% 40%))`;
}

function hostnameOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function SponsorTile({
  sponsor,
  isAdmin = false,
  onRefresh,
  onToggleActive,
  onDelete,
}) {
  const host = sponsor.site_name || hostnameOf(sponsor.url);
  const dim = !sponsor.active && isAdmin;
  return (
    <div
      className={`card overflow-hidden flex flex-col transition ${
        dim ? "opacity-60" : ""
      }`}
    >
      <a
        href={sponsor.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block aspect-[21/9] relative"
        style={
          sponsor.image_url
            ? {
                backgroundImage: `url(${sponsor.image_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : { background: gradientFor(host) }
        }
      >
        {!sponsor.image_url && (
          <div className="absolute inset-0 flex items-center justify-center text-white font-bold text-xl tracking-tight">
            {host}
          </div>
        )}
      </a>
      <div className="p-3 flex flex-col gap-1.5 flex-1">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="font-bold text-text-primary truncate text-sm">
              {sponsor.title || host}
              <span className="text-text-muted font-normal ml-1.5 text-xs uppercase tracking-wider">
                · Sponsor
              </span>
            </div>
          </div>
          <a
            href={sponsor.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            Visit <ExternalLink className="w-3 h-3" />
          </a>
        </div>
        {sponsor.description && (
          <p className="text-xs text-text-secondary line-clamp-2 leading-snug">
            {sponsor.description}
          </p>
        )}
        {isAdmin && (
          <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-border-default">
            <label
              className="flex items-center gap-1 text-xs text-text-secondary cursor-pointer"
              title="Show on directory"
            >
              <input
                type="checkbox"
                checked={sponsor.active}
                onChange={(e) => onToggleActive?.(sponsor, e.target.checked)}
                className="accent-primary"
              />
              {sponsor.active ? "Active" : (
                <span className="inline-flex items-center gap-1">
                  <EyeOff className="w-3 h-3" /> Hidden
                </span>
              )}
            </label>
            <div className="flex items-center gap-0.5">
              <button
                onClick={() => onRefresh?.(sponsor)}
                className="p-1 rounded-full hover:bg-bg-secondary text-text-secondary"
                title="Refresh from URL"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onDelete?.(sponsor)}
                className="p-1 rounded-full hover:bg-red-50 text-red-500"
                title="Remove"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
