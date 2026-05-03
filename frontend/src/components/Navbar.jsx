import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, SignOut, Gear, House, BookmarkSimple, Users } from '@phosphor-icons/react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glassmorphism">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group" data-testid="nav-logo">
            <div className="w-10 h-10 bg-[#D4AF37] rounded-sm flex items-center justify-center">
              <span className="font-['Playfair_Display'] font-bold text-[#0A0D14] text-xl">J</span>
            </div>
            <span className="font-['Playfair_Display'] text-xl text-white group-hover:text-[#D4AF37] transition-colors">
              Jimbo Connect
            </span>
          </Link>

          <div className="flex items-center gap-6">
            {user ? (
              <>
                <Link
                  to="/events"
                  className="text-white/70 hover:text-white transition-colors text-sm font-medium flex items-center gap-2"
                  data-testid="nav-events"
                >
                  <House size={18} weight="duotone" />
                  Events
                </Link>
                <Link
                  to="/contacts"
                  className="text-white/70 hover:text-white transition-colors text-sm font-medium flex items-center gap-2"
                  data-testid="nav-contacts"
                >
                  <BookmarkSimple size={18} weight="duotone" />
                  Saved
                </Link>
                {user.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="text-white/70 hover:text-white transition-colors text-sm font-medium flex items-center gap-2"
                    data-testid="nav-admin"
                  >
                    <Gear size={18} weight="duotone" />
                    Admin
                  </Link>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-sm px-3 py-2 transition-all"
                      data-testid="user-menu-trigger"
                    >
                      <User size={18} weight="duotone" className="text-[#D4AF37]" />
                      <span className="text-white text-sm">{user.name}</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="bg-[#121621] border-white/10">
                    <DropdownMenuItem asChild>
                      <Link to="/profile" className="flex items-center gap-2 cursor-pointer" data-testid="menu-profile">
                        <User size={16} weight="duotone" />
                        Profile
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-white/10" />
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="flex items-center gap-2 text-red-400 focus:text-red-400 cursor-pointer"
                      data-testid="menu-logout"
                    >
                      <SignOut size={16} weight="duotone" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-white/70 hover:text-white transition-colors text-sm font-medium"
                  data-testid="nav-login"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="bg-[#D4AF37] text-[#0A0D14] font-medium px-4 py-2 rounded-sm hover:bg-[#F0C84B] transition-all text-sm"
                  data-testid="nav-register"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
