import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  FileCode2,
  FolderLock,
  Home,
  LogOut,
  Menu,
  PlaySquare,
  Search,
  ShieldAlert,
  Tv,
  Upload,
  UserCircle2,
  Video,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { ChannelSummary } from '../types';
import { Avatar } from './Avatar';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, isStaff, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [subscriptions, setSubscriptions] = useState<ChannelSummary[]>([]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get('q');
    if (location.pathname === '/search' && q !== null) {
      setSearchQuery(q);
    }
  }, [location]);

  useEffect(() => {
    if (!user) {
      setSubscriptions([]);
      return;
    }
    api.listMySubscriptions().then(setSubscriptions).catch(() => {});
  }, [user]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = searchQuery.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    } else {
      navigate('/');
    }
  };

  const navItems = [
    { to: '/', label: 'Home', icon: Home, show: true },
    { to: '/subscriptions', label: 'Subscriptions', icon: Tv, show: Boolean(user) },
    { to: '/shared', label: 'Shared with me', icon: FolderLock, show: Boolean(user) },
    { to: '/studio', label: 'My Videos', icon: PlaySquare, show: Boolean(user) },
    { to: '/upload', label: 'Upload Video', icon: Upload, show: Boolean(user) },
    { to: '/moderation', label: 'Moderation', icon: ShieldAlert, show: isStaff },
  ].filter((item) => item.show);

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-[#f1f1f1] flex flex-col">
      {/* Sticky Top Header */}
      <header className="sticky top-0 z-40 h-14 bg-[#0f0f0f]/90 backdrop-blur-md border-b border-zinc-800/70 px-3 sm:px-4 flex items-center justify-between gap-3">
        {/* Left: Menu + Brand */}
        <div className="flex items-center gap-2 sm:gap-4 shrink-0">
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            className="p-2 rounded-full hover:bg-[#272727] active:scale-90 transition-all duration-150 cursor-pointer"
            aria-label="Toggle sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
          <Link to="/" className="group flex items-center gap-1.5 select-none">
            <div className="w-8 h-6 rounded-md bg-[#ff0000] flex items-center justify-center shadow group-hover:scale-105 group-hover:shadow-red-600/40 transition-all duration-200">
              <div className="w-0 h-0 border-t-[5px] border-t-transparent border-b-[5px] border-b-transparent border-l-[9px] border-l-white ml-0.5" />
            </div>
            <span className="text-lg font-bold tracking-tight hidden sm:inline">
              Stream<span className="text-[#ff0000]">Tube</span>
            </span>
          </Link>
        </div>

        {/* Center: Search Bar */}
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl flex items-center">
          <div className="flex w-full items-center bg-[#121212] border border-[#303030] focus-within:border-[#3ea6ff] focus-within:shadow-[0_0_0_3px_rgba(62,166,255,0.12)] rounded-full overflow-hidden transition-all duration-200">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search videos, channels, tags..."
              className="w-full bg-transparent px-4 py-1.5 text-sm text-[#f1f1f1] placeholder-[#888888] focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="p-1.5 text-zinc-400 hover:text-white active:scale-90 transition-all cursor-pointer"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              type="submit"
              className="px-5 py-2 bg-[#222222] hover:bg-[#303030] active:bg-[#3a3a3a] border-l border-[#303030] text-zinc-200 transition-colors cursor-pointer"
              aria-label="Search"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </form>

        {/* Right: Create + User */}
        <div className="flex items-center gap-2 shrink-0">
          {user && (
            <Link
              to="/upload"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#272727] hover:bg-[#3f3f3f] active:scale-95 text-sm font-medium transition-all duration-150"
            >
              <Video className="w-4 h-4 text-[#ff0000]" />
              <span className="hidden md:inline">Create</span>
            </Link>
          )}

          {isStaff && (
            <Link
              to="/moderation"
              className="p-2 rounded-full hover:bg-[#272727] active:scale-90 text-amber-400 transition-all duration-150"
              title="Moderation Dashboard"
            >
              <ShieldAlert className="w-5 h-5" />
            </Link>
          )}

          {user ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 rounded-full p-0.5 hover:ring-2 hover:ring-zinc-600 active:scale-95 transition-all duration-150 cursor-pointer"
              >
                <Avatar name={user.channel_name} color={user.avatar_color} size="sm" />
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[#242424]/95 backdrop-blur-md border border-zinc-700/80 shadow-2xl z-50 py-2 animate-scale-pop origin-top-right">
                    <div className="px-4 py-2.5 border-b border-zinc-700/80 flex items-center gap-3">
                      <Avatar name={user.channel_name} color={user.avatar_color} size="md" />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold truncate">{user.channel_name}</p>
                        <p className="text-xs text-zinc-400 truncate">@{user.username}</p>
                        <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] uppercase tracking-wider rounded bg-zinc-700 text-zinc-200">
                          {user.role}
                        </span>
                      </div>
                    </div>
                    <Link
                      to={`/channel/${user.username}`}
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-3 px-4 py-2 text-sm hover:bg-zinc-700/70"
                    >
                      <UserCircle2 className="w-4 h-4" /> Your Channel
                    </Link>
                    <Link
                      to="/studio"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-3 px-4 py-2 text-sm hover:bg-zinc-700/70"
                    >
                      <PlaySquare className="w-4 h-4" /> My Videos
                    </Link>
                    <Link
                      to="/shared"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-3 px-4 py-2 text-sm hover:bg-zinc-700/70"
                    >
                      <FolderLock className="w-4 h-4" /> Shared Private Videos
                    </Link>
                    {isStaff && (
                      <Link
                        to="/moderation"
                        onClick={() => setMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2 text-sm text-amber-400 hover:bg-zinc-700/70"
                      >
                        <ShieldAlert className="w-4 h-4" /> Moderation Panel
                      </Link>
                    )}
                    <button
                      type="button"
                      onClick={async () => {
                        setMenuOpen(false);
                        await logout();
                        navigate('/');
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-zinc-700/70 cursor-pointer"
                    >
                      <LogOut className="w-4 h-4" /> Sign out
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#303030] hover:bg-[#263850] text-[#3ea6ff] text-sm font-medium transition-colors"
            >
              <UserCircle2 className="w-4 h-4" />
              <span>Sign in</span>
            </Link>
          )}
        </div>
      </header>

      {/* Body with Animated Collapsible Sidebar */}
      <div className="flex flex-1 min-h-0">
        <aside
          className={`shrink-0 hidden md:flex flex-col border-r border-zinc-800/60 bg-[#0f0f0f] overflow-hidden sticky top-14 h-[calc(100vh-3.5rem)] transition-all duration-300 ease-out ${
            sidebarOpen ? 'w-56 px-3 py-3 opacity-100' : 'w-0 px-0 py-3 opacity-0 border-r-0'
          }`}
        >
          <div className="w-50 flex flex-col flex-1 overflow-y-auto">
            <nav className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.to;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`flex items-center gap-4 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 active:scale-[0.98] ${
                      active
                        ? 'bg-[#272727] text-white shadow-sm'
                        : 'text-[#f1f1f1] hover:bg-[#1f1f1f] hover:translate-x-0.5'
                    }`}
                  >
                    <Icon className="w-5 h-5 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {user && subscriptions.length > 0 && (
              <div className="mt-5 pt-4 border-t border-zinc-800">
                <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Subscriptions
                </p>
                <div className="space-y-0.5">
                  {subscriptions.map((ch) => (
                    <Link
                      key={ch.id}
                      to={`/channel/${ch.username}`}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl text-sm hover:bg-[#1f1f1f] hover:translate-x-0.5 transition-all duration-150"
                    >
                      <Avatar name={ch.channel_name} color={ch.avatar_color} size="xs" />
                      <span className="truncate text-zinc-200">{ch.channel_name}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-auto pt-4 border-t border-zinc-800 space-y-1">
              <a
                href="/docs"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-zinc-400 hover:text-white hover:bg-[#1f1f1f] transition-colors"
              >
                <FileCode2 className="w-4 h-4" />
                <span>API Swagger (/docs)</span>
              </a>
              <p className="px-3 text-[11px] text-zinc-600">StreamTube • FastAPI + HLS</p>
            </div>
          </div>
        </aside>

        <main key={location.pathname} className="flex-1 min-w-0 px-4 sm:px-6 py-5 animate-fade-in">
          {children}
        </main>
      </div>
    </div>
  );
};
