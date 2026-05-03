import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { User, SignOut, Gear, House, BookmarkSimple, Sun, Moon } from '@phosphor-icons/react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Button } from './ui/button';

const Navbar = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
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
            <div className="w-10 h-10 bg-primary rounded-md flex items-center justify-center">
              <span className="font-semibold text-primary-foreground text-lg">J</span>
            </div>
            <span className="text-xl font-semibold text-foreground group-hover:text-primary transition-colors">
              Jimbo Connect
            </span>
          </Link>

          <div className="flex items-center gap-4">
            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="text-muted-foreground hover:text-foreground"
              data-testid="theme-toggle"
            >
              {theme === 'dark' ? <Sun size={20} weight="duotone" /> : <Moon size={20} weight="duotone" />}
            </Button>

            {user ? (
              <>
                <Link
                  to="/events"
                  className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium flex items-center gap-2"
                  data-testid="nav-events"
                >
                  <House size={18} weight="duotone" />
                  Events
                </Link>
                <Link
                  to="/contacts"
                  className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium flex items-center gap-2"
                  data-testid="nav-contacts"
                >
                  <BookmarkSimple size={18} weight="duotone" />
                  Saved
                </Link>
                {user.role === 'admin' && (
                  <Link
                    to="/admin"
                    className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium flex items-center gap-2"
                    data-testid="nav-admin"
                  >
                    <Gear size={18} weight="duotone" />
                    Admin
                  </Link>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="flex items-center gap-2 bg-muted hover:bg-muted/80 border border-border rounded-md px-3 py-2 transition-all"
                      data-testid="user-menu-trigger"
                    >
                      <User size={18} weight="duotone" className="text-primary" />
                      <span className="text-foreground text-sm">{user.name}</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="bg-popover border-border">
                    <DropdownMenuItem asChild>
                      <Link to="/profile" className="flex items-center gap-2 cursor-pointer" data-testid="menu-profile">
                        <User size={16} weight="duotone" />
                        Profile
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-border" />
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="flex items-center gap-2 text-destructive focus:text-destructive cursor-pointer"
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
                  className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium"
                  data-testid="nav-login"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="bg-primary text-primary-foreground font-medium px-4 py-2 rounded-md hover:bg-primary/90 transition-all text-sm"
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
