import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { KeyRound, ShieldCheck, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AuthPageProps {
  mode: 'login' | 'register';
}

const DEMO_ACCOUNTS = [
  { label: 'Admin', username: 'admin', pass: 'AdminPass123!', desc: 'Full admin + moderation' },
  { label: 'Moderator', username: 'moderator', pass: 'ModPass123!', desc: 'Reports & hide videos' },
  { label: 'Creator (techdev)', username: 'techdev', pass: 'DemoPass123!', desc: 'Owns public + private video' },
  { label: 'Viewer (alice)', username: 'alice', pass: 'DemoPass123!', desc: 'Granted private video access' },
  { label: 'Viewer (bob)', username: 'bob', pass: 'DemoPass123!', desc: 'No private access (tests 403)' },
];

export const AuthPage: React.FC<AuthPageProps> = ({ mode }) => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [channelName, setChannelName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(identifier.trim(), password);
      } else {
        await register({
          username: username.trim(),
          email: email.trim(),
          password,
          channel_name: channelName.trim() || undefined,
        });
      }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-8 animate-fade-up">
      <div className="bg-[#181818] border border-zinc-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
        <div className="flex items-center gap-2.5 mb-6">
          <div className="w-9 h-7 rounded-md bg-[#ff0000] flex items-center justify-center">
            <div className="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-white ml-0.5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">
              {mode === 'login' ? 'Sign in to StreamTube' : 'Create your StreamTube channel'}
            </h1>
            <p className="text-xs text-zinc-400">
              {mode === 'login'
                ? 'Access uploads, subscriptions, private videos, and comments'
                : 'Upload videos, build playlists, and join the community'}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/60 border border-red-800 text-red-200 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'login' ? (
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Username or Email
              </label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. techdev or tech@streamtube.dev"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
              />
            </div>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Username</label>
                <input
                  type="text"
                  required
                  minLength={3}
                  maxLength={32}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="alex_dev"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@example.com"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                  Channel Display Name (optional)
                </label>
                <input
                  type="text"
                  maxLength={80}
                  value={channelName}
                  onChange={(e) => setChannelName(e.target.value)}
                  placeholder="Alex Dev Studio"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Password</label>
            <input
              type="password"
              required
              minLength={mode === 'register' ? 8 : 1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'register' ? 'Minimum 8 characters' : '••••••••'}
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#121212] border border-zinc-700 text-sm focus:outline-none focus:border-[#3ea6ff]"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-xl bg-[#ff0000] hover:bg-red-700 disabled:opacity-60 text-white font-semibold text-sm flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            {mode === 'login' ? <KeyRound className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
            <span>{submitting ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}</span>
          </button>
        </form>

        <div className="mt-5 text-center text-sm text-zinc-400">
          {mode === 'login' ? (
            <>
              New to StreamTube?{' '}
              <Link to="/register" className="text-[#3ea6ff] hover:underline font-medium">
                Create an account
              </Link>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <Link to="/login" className="text-[#3ea6ff] hover:underline font-medium">
                Sign in
              </Link>
            </>
          )}
        </div>

        {mode === 'login' && (
          <div className="mt-6 pt-5 border-t border-zinc-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-300 mb-2.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Demo Accounts (1-click fill)</span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  onClick={() => {
                    setIdentifier(acc.username);
                    setPassword(acc.pass);
                  }}
                  className="text-left px-3 py-2 rounded-lg bg-[#222222] hover:bg-[#2c2c2c] transition-colors flex items-center justify-between gap-2 cursor-pointer"
                >
                  <div>
                    <span className="text-xs font-semibold text-zinc-100">{acc.label}</span>
                    <span className="text-[11px] text-zinc-400 ml-2">{acc.desc}</span>
                  </div>
                  <code className="text-[11px] text-[#3ea6ff]">{acc.username}</code>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
