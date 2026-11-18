import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  ClipboardList,
  Eye,
  EyeOff,
  Flag,
  ShieldAlert,
  Users,
  XCircle,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type {
  AdminUserItem,
  ModerationLogItem,
  ReportItem,
  UserRole,
  VideoCardItem,
} from '../types';
import { formatRelativeTime } from '../utils/format';

export const ModerationPage: React.FC = () => {
  const { isStaff, isAdmin, user } = useAuth();
  const [tab, setTab] = useState<'reports' | 'hidden' | 'logs' | 'users'>('reports');
  const [statusFilter, setStatusFilter] = useState<'open' | 'resolved_hidden' | 'dismissed' | 'all'>('open');
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [hiddenVideos, setHiddenVideos] = useState<VideoCardItem[]>([]);
  const [logs, setLogs] = useState<ModerationLogItem[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!isStaff) return;
    setLoading(true);
    try {
      const [reps, hid, lgs] = await Promise.all([
        api.listReports(statusFilter),
        api.listHiddenVideos(),
        api.listModerationLogs(),
      ]);
      setReports(reps);
      setHiddenVideos(hid);
      setLogs(lgs);
      if (isAdmin) {
        const us = await api.listAdminUsers();
        setAdminUsers(us);
      }
    } finally {
      setLoading(false);
    }
  }, [isStaff, isAdmin, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (!isStaff) {
    return (
      <div className="max-w-lg mx-auto py-20 text-center bg-[#181818] border border-zinc-800 rounded-2xl p-8">
        <ShieldAlert className="w-12 h-12 mx-auto text-red-500 mb-3" />
        <h2 className="text-xl font-bold">Restricted Access</h2>
        <p className="text-sm text-zinc-400 mt-2">
          Moderation tools are accessible only to accounts with Moderator or Administrator roles.
        </p>
        <Link
          to="/login"
          className="inline-block mt-5 px-5 py-2 rounded-full bg-[#3ea6ff] text-black font-semibold text-sm"
        >
          Sign in as Moderator / Admin
        </Link>
      </div>
    );
  }

  const handleResolve = async (reportId: string, action: 'hide_video' | 'dismiss') => {
    const note =
      window.prompt(
        action === 'hide_video' ? 'Moderation reason for hiding video:' : 'Optional dismissal note:',
        action === 'hide_video' ? 'Violates community guidelines' : 'Reviewed — no violation',
      ) ?? '';
    await api.resolveReport(reportId, action, note);
    setBanner(
      action === 'hide_video'
        ? 'Video hidden and open reports resolved.'
        : 'Report dismissed.',
    );
    loadData();
  };

  const handleUnhide = async (videoId: string) => {
    await api.unhideVideo(videoId, 'Restored by moderator');
    setBanner('Video restored to active status.');
    loadData();
  };

  const handleRoleChange = async (userId: string, role: UserRole) => {
    await api.updateUserRole(userId, role);
    setBanner('User role updated.');
    loadData();
  };

  const handleToggleActive = async (userId: string, active: boolean) => {
    await api.toggleUserActive(userId, active);
    setBanner(`User account ${active ? 'activated' : 'suspended'}.`);
    loadData();
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Moderation & Trust Dashboard</h1>
            <p className="text-xs text-zinc-400">
              Review user reports, hide policy-violating videos, and audit staff actions
            </p>
          </div>
        </div>
      </div>

      {banner && (
        <div className="mb-5 p-3 rounded-xl bg-emerald-950/50 border border-emerald-700 text-emerald-200 text-sm">
          {banner}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 pb-3 mb-6">
        <button
          type="button"
          onClick={() => setTab('reports')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer ${
            tab === 'reports' ? 'bg-[#272727] text-white' : 'text-zinc-400 hover:bg-[#1a1a1a]'
          }`}
        >
          <Flag className="w-4 h-4" /> Reports Queue ({reports.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('hidden')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer ${
            tab === 'hidden' ? 'bg-[#272727] text-white' : 'text-zinc-400 hover:bg-[#1a1a1a]'
          }`}
        >
          <EyeOff className="w-4 h-4" /> Hidden Videos ({hiddenVideos.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('logs')}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer ${
            tab === 'logs' ? 'bg-[#272727] text-white' : 'text-zinc-400 hover:bg-[#1a1a1a]'
          }`}
        >
          <ClipboardList className="w-4 h-4" /> Audit Log
        </button>
        {isAdmin && (
          <button
            type="button"
            onClick={() => setTab('users')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer ${
              tab === 'users' ? 'bg-[#272727] text-white' : 'text-zinc-400 hover:bg-[#1a1a1a]'
            }`}
          >
            <Users className="w-4 h-4" /> Users & Roles ({adminUsers.length})
          </button>
        )}
      </div>

      {loading ? (
        <div className="h-48 rounded-2xl bg-zinc-900 animate-pulse" />
      ) : (
        <>
          {tab === 'reports' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {(['open', 'resolved_hidden', 'dismissed', 'all'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setStatusFilter(st)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium capitalize cursor-pointer ${
                      statusFilter === st
                        ? 'bg-white text-black'
                        : 'bg-[#272727] text-zinc-300 hover:bg-[#3f3f3f]'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
              </div>

              {reports.length === 0 ? (
                <div className="py-16 text-center bg-[#181818] border border-zinc-800 rounded-2xl text-zinc-400">
                  <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500 mb-2" />
                  <p>No reports matching filter "{statusFilter}".</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {reports.map((rep) => (
                    <div
                      key={rep.id}
                      className="p-4 rounded-xl bg-[#181818] border border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-red-600/20 border border-red-500/40 text-red-300 text-xs font-semibold uppercase">
                            {rep.reason}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 text-xs">
                            {rep.status}
                          </span>
                          <span className="text-xs text-zinc-500">
                            {formatRelativeTime(rep.created_at)}
                          </span>
                        </div>
                        <Link
                          to={`/watch/${rep.video_id}`}
                          className="block text-base font-semibold text-[#3ea6ff] hover:underline truncate"
                        >
                          {rep.video_title}
                        </Link>
                        <p className="text-xs text-zinc-400">
                          Owner: @{rep.video_owner_username} • Reported by: @{rep.reporter.username}
                        </p>
                        {rep.details && (
                          <p className="text-sm text-zinc-200 mt-1">{rep.details}</p>
                        )}
                        {rep.resolution_note && (
                          <p className="text-xs text-emerald-400 mt-1">
                            Resolution: {rep.resolution_note}
                          </p>
                        )}
                      </div>

                      {rep.status === 'open' && (
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleResolve(rep.id, 'hide_video')}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold cursor-pointer"
                          >
                            <EyeOff className="w-3.5 h-3.5" /> Hide Video
                          </button>
                          <button
                            type="button"
                            onClick={() => handleResolve(rep.id, 'dismiss')}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#272727] hover:bg-[#3f3f3f] text-zinc-200 text-xs font-medium cursor-pointer"
                          >
                            <XCircle className="w-3.5 h-3.5" /> Dismiss
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'hidden' && (
            <div className="space-y-3">
              {hiddenVideos.length === 0 ? (
                <div className="py-16 text-center bg-[#181818] border border-zinc-800 rounded-2xl text-zinc-400">
                  No currently hidden videos.
                </div>
              ) : (
                hiddenVideos.map((v) => (
                  <div
                    key={v.id}
                    className="p-4 rounded-xl bg-[#181818] border border-zinc-800 flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
                      <Link
                        to={`/watch/${v.id}`}
                        className="font-semibold text-sm text-[#3ea6ff] hover:underline truncate block"
                      >
                        {v.title}
                      </Link>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        Channel: @{v.owner.username} • Uploaded {formatRelativeTime(v.created_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleUnhide(v.id)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shrink-0 cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" /> Restore Video
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'logs' && (
            <div className="overflow-x-auto bg-[#181818] border border-zinc-800 rounded-2xl">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-800 text-xs text-zinc-400 uppercase">
                  <tr>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Actor</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Target</th>
                    <th className="px-4 py-3">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/70 text-xs">
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                        No moderation events recorded yet.
                      </td>
                    </tr>
                  ) : (
                    logs.map((lg) => (
                      <tr key={lg.id} className="hover:bg-zinc-800/30">
                        <td className="px-4 py-3 text-zinc-400 whitespace-nowrap">
                          {formatRelativeTime(lg.created_at)}
                        </td>
                        <td className="px-4 py-3 font-medium">@{lg.actor_username || 'system'}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded bg-zinc-800 text-amber-300 font-mono">
                            {lg.action}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-zinc-400 font-mono">
                          {lg.target_type}:{lg.target_id.slice(0, 8)}
                        </td>
                        <td className="px-4 py-3 text-zinc-200">{lg.reason}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'users' && isAdmin && (
            <div className="overflow-x-auto bg-[#181818] border border-zinc-800 rounded-2xl">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-800 text-xs text-zinc-400 uppercase">
                  <tr>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Videos</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/70 text-xs">
                  {adminUsers.map((u) => {
                    const isSelf = u.id === user?.id;
                    return (
                      <tr key={u.id} className="hover:bg-zinc-800/30">
                        <td className="px-4 py-3 font-semibold">
                          {u.channel_name}{' '}
                          <span className="text-zinc-400 font-normal">@{u.username}</span>
                        </td>
                        <td className="px-4 py-3 text-zinc-400">{u.email}</td>
                        <td className="px-4 py-3">{u.videos_count}</td>
                        <td className="px-4 py-3">
                          <select
                            disabled={isSelf}
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                            className="bg-[#121212] border border-zinc-700 rounded px-2 py-1 text-xs disabled:opacity-50"
                          >
                            <option value="user">user</option>
                            <option value="moderator">moderator</option>
                            <option value="admin">admin</option>
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            disabled={isSelf}
                            onClick={() => handleToggleActive(u.id, !u.is_active)}
                            className={`px-2.5 py-1 rounded text-xs font-medium disabled:opacity-50 cursor-pointer ${
                              u.is_active
                                ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700'
                                : 'bg-red-900/50 text-red-300 border border-red-700'
                            }`}
                          >
                            {u.is_active ? 'Active' : 'Suspended'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
};
