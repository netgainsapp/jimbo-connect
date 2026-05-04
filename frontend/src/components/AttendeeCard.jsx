import { Bookmark, BookmarkCheck } from "lucide-react";
import Avatar from "./Avatar.jsx";

export default function AttendeeCard({ attendee, isSaved, onToggleSave, onOpen }) {
  const p = attendee.profile || {};
  return (
    <div
      className="card p-5 flex flex-col gap-3 hover:border-primary/50 transition cursor-pointer"
      onClick={() => onOpen?.(attendee)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={p.name} photoUrl={p.photo_url} size={48} />
          <div className="min-w-0">
            <div className="font-bold text-text-primary truncate">
              {p.name || attendee.email}
            </div>
            <div className="text-sm text-text-secondary truncate">
              {p.role}
              {p.role && p.company && " · "}
              {p.company}
            </div>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleSave?.(attendee);
          }}
          className={`p-2 rounded-full transition ${
            isSaved
              ? "bg-primary/10 text-primary"
              : "text-text-muted hover:bg-bg-secondary hover:text-primary"
          }`}
          aria-label={isSaved ? "Remove from saved" : "Save contact"}
        >
          {isSaved ? (
            <BookmarkCheck className="w-5 h-5" />
          ) : (
            <Bookmark className="w-5 h-5" />
          )}
        </button>
      </div>
      {p.industry && <span className="pill self-start">{p.industry}</span>}
      {p.bio && (
        <p className="text-sm text-text-secondary line-clamp-2">{p.bio}</p>
      )}
    </div>
  );
}
