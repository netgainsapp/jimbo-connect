import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
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
} from "lucide-react";
import Avatar from "./Avatar.jsx";
import { messagesApi } from "../lib/api.js";

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

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

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItem =
    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill text-sm font-semibold text-text-secondary hover:bg-bg-secondary";
  const activeNavItem = "text-primary bg-primary/5";

  return (
    <nav className="fixed top-0 inset-x-0 z-40 bg-white border-b border-border-default">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-card bg-primary text-white flex items-center justify-center font-bold">
            J
          </div>
          <span className="font-bold text-text-primary text-lg tracking-tight">
            Jimbo Connect
          </span>
        </Link>

        {user && (
          <div className="flex items-center gap-1">
            {user.is_admin ? (
              <>
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
                >
                  <LayoutDashboard className="w-4 h-4" /> Dashboard
                </NavLink>
                <NavLink
                  to="/admin/events"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
                >
                  <Users className="w-4 h-4" /> Events
                </NavLink>
                <NavLink
                  to="/admin/templates"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
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
            ) : (
              <>
                <NavLink
                  to="/events"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
                >
                  <Calendar className="w-4 h-4" /> My Events
                </NavLink>
                <NavLink
                  to="/discover"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
                >
                  <Compass className="w-4 h-4" /> Discover
                </NavLink>
                <NavLink
                  to="/contacts"
                  className={({ isActive }) =>
                    `${navItem} ${isActive ? activeNavItem : ""}`
                  }
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
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-2 hover:bg-bg-secondary rounded-pill px-2 py-1"
              >
                <Avatar
                  name={user.profile?.name}
                  photoUrl={user.profile?.photo_url}
                  size={32}
                />
                <span className="text-sm font-semibold text-text-primary hidden sm:block">
                  {user.profile?.name || user.email}
                </span>
              </Link>
              <button onClick={handleLogout} className="btn-ghost" title="Log out">
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">
                Log in
              </Link>
              <Link to="/register" className="btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
