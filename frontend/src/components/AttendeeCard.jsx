import { Bookmark, BookmarkCheck, StickyNote } from "lucide-react";
import Avatar from "./Avatar.jsx";

export default function AttendeeCard({
  attendee,
  isSaved,
  onToggleSave,
  onOpen,
  hideActions = false,
  meta = null,
  note = "",
}) {
  const p = attendee.profile || {};
  const hasFooter = note || meta;
  return (
    <div
      className="card p-4 flex flex-col gap-2 hover:border-primary/50 transition cursor-pointer"
      onClick={() => onOpen?.(attendee)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <Avatar name={p.name} photoUrl={p.photo_url} size={40} />
          <div className="min-w-0">
            <div className="font-bold text-text-primary truncate leading-tight">
              {p.name || attendee.email}
            </div>
            <div className="text-xs text-text-secondary truncate">
              {p.role}
              {p.role && p.company && " · "}
              {p.company}
              {(p.role || p.company) && p.industry && " · "}
              {p.industry}
            </div>
          </div>
        </div>
        {!hideActions && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleSave?.(attendee);
            }}
            className={`p-1.5 rounded-full transition shrink-0 ${
              isSaved
                ? "bg-primary/10 text-primary"
                : "text-text-muted hover:bg-bg-secondary hover:text-primary"
            }`}
            aria-label={isSaved ? "Remove from saved" : "Save contact"}
          >
            {isSaved ? (
              <BookmarkCheck className="w-4 h-4" />
            ) : (
              <Bookmark className="w-4 h-4" />
            )}
          </button>
        )}
      </div>
      {p.bio && (
        <p className="text-xs text-text-secondary line-clamp-2 leading-snug">
          {p.bio}
        </p>
      )}
      {hasFooter && (
        <div className="flex items-start justify-between gap-2 pt-2 border-t border-border-default">
          {note ? (
            <div className="flex items-start gap-1.5 text-xs flex-1 min-w-0">
              <StickyNote className="w-3 h-3 text-primary mt-0.5 shrink-0" />
              <p className="text-text-secondary line-clamp-2 italic">{note}</p>
            </div>
          ) : (
            <div />
          )}
          {meta && (
            <div className="text-xs text-text-muted shrink-0">{meta}</div>
          )}
        </div>
      )}
    </div>
  );
}
