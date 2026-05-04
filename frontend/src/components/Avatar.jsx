import { initials } from "../lib/utils.js";

export default function Avatar({ name, photoUrl, size = 48, className = "" }) {
  const dim = `${size}px`;
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={name || ""}
        style={{ width: dim, height: dim }}
        className={`rounded-full object-cover border border-border-default ${className}`}
      />
    );
  }
  const fontSize = Math.max(12, Math.floor(size * 0.38));
  return (
    <div
      style={{ width: dim, height: dim, fontSize: `${fontSize}px` }}
      className={`rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center select-none ${className}`}
    >
      {initials(name)}
    </div>
  );
}
