import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import {
  LogOut,
  Calendar,
  Bookmark,
  LayoutDashboard,
  Users,
  Mail,
  MessageCircle,
  Compass,
  Menu,
  X,
} from "lucide-react";
import Avatar from "./Avatar.jsx";
import { messagesApi } from "../lib/api.js";

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) {
      setUnread(0);
      return;
    }
    let cancelled = false;
    const fetch = () => {
      messagesApi
        .unreadCount()
        .then((r) => {
          if (!cancelled) setUnread(r.unread || 0);
        })
        .catch(() => {});
    };
    fetch();
    const t = setInterval(fetch, 15000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [user]);

  // Close mobile menu on route change
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItem =
    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill text-sm font-semibold text-text-secondary hover:bg-bg-secondary";
  const activeNavItem = "text-primary bg-primary/5";

  const adminLinks = (
    <>
      <NavLink
        to="/admin"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <LayoutDashboard className="w-4 h-4" /> Dashboard
      </NavLink>
      <NavLink
        to="/admin/events"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <Users className="w-4 h-4" /> Events
      </NavLink>
      <NavLink
        to="/admin/templates"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <Mail className="w-4 h-4" /> Templates
      </NavLink>
      <NavLink
        to="/messages"
        className={({ isActive }) =>
          `${navItem} relative ${isActive ? activeNavItem : ""}`
        }
      >
        <MessageCircle className="w-4 h-4" /> Messages
        {unread > 0 && (
          <span className="ml-0.5 bg-primary text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] px-1 inline-flex items-center justify-center">
            {unread}
          </span>
        )}
      </NavLink>
    </>
  );

  const attendeeLinks = (
    <>
      <NavLink
        to="/events"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <Calendar className="w-4 h-4" /> My Events
      </NavLink>
      <NavLink
        to="/discover"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <Compass className="w-4 h-4" /> Discover
      </NavLink>
      <NavLink
        to="/contacts"
        className={({ isActive }) => `${navItem} ${isActive ? activeNavItem : ""}`}
      >
        <Bookmark className="w-4 h-4" /> Saved
      </NavLink>
      <NavLink
        to="/messages"
        className={({ isActive }) =>
          `${navItem} relative ${isActive ? activeNavItem : ""}`
        }
      >
        <MessageCircle className="w-4 h-4" /> Messages
        {unread > 0 && (
          <span className="ml-0.5 bg-primary text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] px-1 inline-flex items-center justify-center">
            {unread}
          </span>
        )}
      </NavLink>
    </>
  );

  return (
    <nav className="fixed top-0 inset-x-0 z-40 bg-white border-b border-border-default">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-2">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <div className="w-8 h-8 rounded-card bg-primary text-white flex items-center justify-center font-bold">
            J
          </div>
          <span className="font-bold text-text-primary text-lg tracking-tight hidden sm:block">
            Jimbo Connect
          </span>
        </Link>

        {user && (
          <div className="hidden md:flex items-center gap-1">
            {user.is_admin ? adminLinks : attendeeLinks}
          </div>
        )}

        <div className="flex items-center gap-2 shrink-0">
          {user ? (
            <>
              <Link
                to="/profile"
                className="hidden sm:flex items-center gap-2 hover:bg-bg-secondary rounded-pill px-2 py-1"
              >
                <Avatar
                  name={user.profile?.name}
                  photoUrl={user.profile?.photo_url}
                  size={28}
                />
                <span className="text-sm font-semibold text-text-primary hidden lg:block">
                  {user.profile?.name || user.email}
                </span>
              </Link>
              <button
                onClick={handleLogout}
                className="btn-ghost hidden md:inline-flex"
                title="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
              {/* Mobile hamburger */}
              <div className="md:hidden flex items-center gap-1">
                {unread > 0 && (
                  <span className="bg-primary text-white text-xs font-bold rounded-full min-w-[20px] h-5 px-1.5 inline-flex items-center justify-center">
                    {unread}
                  </span>
                )}
                <button
                  onClick={() => setOpen((v) => !v)}
                  className="p-2 rounded-pill hover:bg-bg-secondary text-text-primary"
                  aria-label="Menu"
                >
                  {open ? (
                    <X className="w-5 h-5" />
                  ) : (
                    <Menu className="w-5 h-5" />
                  )}
                </button>
              </div>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost text-sm">
                Log in
              </Link>
              <Link to="/register" className="btn-primary text-sm">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Mobile dropdown */}
      {user && open && (
        <div className="md:hidden border-t border-border-default bg-white">
          <div className="px-4 py-3 flex flex-col gap-1">
            <Link
              to="/profile"
              className="flex items-center gap-3 px-2 py-2 rounded-card hover:bg-bg-secondary"
              onClick={() => setOpen(false)}
            >
              <Avatar
                name={user.profile?.name}
                photoUrl={user.profile?.photo_url}
                size={32}
              />
              <div>
                <div className="font-bold text-text-primary text-sm">
                  {user.profile?.name || user.email}
                </div>
                <div className="text-xs text-text-secondary">View profile</div>
              </div>
            </Link>
            <div className="border-t border-border-default my-1" />
            {user.is_admin ? adminLinks : attendeeLinks}
            <div className="border-t border-border-default my-1" />
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-2 rounded-card text-sm font-semibold text-text-secondary hover:bg-bg-secondary text-left"
            >
              <LogOut className="w-4 h-4" /> Log out
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
