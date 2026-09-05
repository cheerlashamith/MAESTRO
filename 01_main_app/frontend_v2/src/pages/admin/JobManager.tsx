import { useState, useEffect } from 'react';
import { Play, Pause, Square, RefreshCcw, ListTodo, Trash2, AlertCircle, Users, Building2 } from 'lucide-react';

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  message: string;
  progress_percentage: number;
  user_id?: string;
  tenant_id?: string;
  created_at?: string;
}

interface IAMUser {
  id: string;
  username: string;
  display_name: string;
  role_slug: string;
}

export default function JobManager() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [usersList, setUsersList] = useState<IAMUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'running' | 'completed' | 'failed'>('all');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [selectedTenant, setSelectedTenant] = useState<string>('all');
  const [actionId, setActionId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchUsers = () => {
    fetch('/api/iam/users')
      .then(res => res.json())
      .then(data => {
        if (data.users) setUsersList(data.users);
      })
      .catch(err => console.warn("Failed to fetch IAM users", err));
  };

  const fetchJobs = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (selectedUser !== 'all') params.append('user_id', selectedUser);
    if (selectedTenant !== 'all') params.append('tenant_id', selectedTenant);
    const query = params.toString() ? `?${params.toString()}` : '';

    fetch(`/api/jobs${query}`)
      .then(res => res.json())
      .then(data => {
        const arr = Object.values(data) as JobSummary[];
        arr.reverse();
        setJobs(arr);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch jobs", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [selectedUser, selectedTenant]);

  const handleCancelJob = async (jobId: string) => {
    setActionId(jobId);
    try {
      const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
      const data = await res.json();
      showToast(data.message || `Job ${jobId} stopped.`);
      fetchJobs();
    } catch (err) {
      console.error(err);
      showToast("Failed to stop job.");
    } finally {
      setActionId(null);
    }
  };

  const handlePauseResume = async (job: JobSummary) => {
    setActionId(job.job_id);
    try {
      if (job.status === 'awaiting_approval') {
        const res = await fetch(`/api/jobs/${job.job_id}/resume`, { method: 'POST' });
        const data = await res.json();
        showToast(data.message || `Job ${job.job_id} resumed.`);
      } else {
        const res = await fetch(`/api/jobs/${job.job_id}/pause`, { method: 'POST' });
        const data = await res.json();
        showToast(data.message || `Job ${job.job_id} paused.`);
      }
      fetchJobs();
    } catch (err) {
      console.error(err);
      showToast("Failed to toggle pause/resume.");
    } finally {
      setActionId(null);
    }
  };

  const [showClearModal, setShowClearModal] = useState(false);
  const [deleteModalJobId, setDeleteModalJobId] = useState<string | null>(null);

  const handleDeleteJob = async (jobId: string) => {
    setActionId(jobId);
    setDeleteModalJobId(null);
    try {
      const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
      const data = await res.json();
      showToast(data.message || `Job ${jobId} deleted.`);
      fetchJobs();
    } catch (err) {
      console.error(err);
      showToast("Failed to delete job.");
    } finally {
      setActionId(null);
    }
  };

  const confirmClearAllJobs = async () => {
    setShowClearModal(false);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedUser !== 'all') params.append('user_id', selectedUser);
      if (selectedTenant !== 'all') params.append('tenant_id', selectedTenant);
      const query = params.toString() ? `?${params.toString()}` : '';

      const res = await fetch(`/api/jobs${query}`, { method: 'DELETE' });
      const data = await res.json();
      showToast(data.message || "Tasks successfully cleared and deleted.");
      setJobs([]);
      fetchJobs();
    } catch (err) {
      console.error(err);
      showToast("Failed to clear jobs.");
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = jobs.filter(job => {
    if (filter === 'all') return true;
    if (filter === 'completed') return job.status === 'completed';
    if (filter === 'failed') return job.status === 'failed' || job.status === 'cancelled';
    if (filter === 'running') return job.status !== 'completed' && job.status !== 'failed' && job.status !== 'cancelled';
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">COMPLETED</span>;
      case 'failed':
        return <span className="badge" style={{ background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECDD3' }}>FAILED</span>;
      case 'cancelled':
        return <span className="badge" style={{ background: '#F1F5F9', color: '#64748B', border: '1px solid #CBD5E1' }}>CANCELLED</span>;
      case 'awaiting_approval':
        return <span className="badge badge-warning">PAUSED / REVIEW</span>;
      default:
        return <span className="badge badge-blue">{status.toUpperCase()}</span>;
    }
  };

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {toastMessage && (
        <div style={{
          padding: '0.75rem 1.25rem',
          background: '#0F172A',
          color: '#FFFFFF',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={16} color="#38BDF8" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div className="badge badge-blue" style={{ marginBottom: '0.4rem' }}>
            <ListTodo size={12} /> BACKGROUND WORKERS
          </div>
          <h1 style={{ fontFamily: "'Libre Baskerville', Georgia, serif", fontSize: '1.75rem', fontWeight: 700 }}>
            Job Manager
          </h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Monitor, inspect, and control automated background pipeline tasks with strict user & tenant isolation.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button 
            id="clear-all-jobs-btn"
            className="btn" 
            onClick={() => setShowClearModal(true)}
            style={{
              background: '#DC2626',
              color: '#FFFFFF',
              border: '1px solid #DC2626',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontWeight: 600,
              padding: '0.55rem 1.1rem',
              borderRadius: '6px',
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(220, 38, 38, 0.2)',
              transition: 'all 0.15s ease'
            }}
            title="Permanently stop and delete jobs"
          >
            <Trash2 size={16} />
            <span>{selectedUser !== 'all' ? `Clear Tasks (${selectedUser})` : 'Clear All Tasks'}</span>
          </button>

          <button className="btn btn-secondary" onClick={fetchJobs} style={{ padding: '0.55rem 1rem' }}>
            <RefreshCcw size={16} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tenant & User Multi-Tenant Scoping Filter Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.25rem',
        flexWrap: 'wrap',
        background: '#FFFFFF',
        padding: '0.85rem 1.25rem',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Users size={16} color="#DC2626" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0F172A' }}>User Scoping:</span>
          <select 
            value={selectedUser} 
            onChange={e => setSelectedUser(e.target.value)}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid #CBD5E1',
              fontSize: '0.825rem',
              background: '#F8FAFC',
              fontWeight: 500,
              color: '#0F172A',
              cursor: 'pointer'
            }}
          >
            <option value="all">All Users (Admin View)</option>
            {usersList.length > 0 ? (
              usersList.map(u => (
                <option key={u.id} value={u.username}>{u.display_name} ({u.username})</option>
              ))
            ) : (
              <>
                <option value="shamith">Shamith (shamith)</option>
                <option value="shamith_admin">Shamith Admin (shamith_admin)</option>
              </>
            )}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Building2 size={16} color="#2563EB" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0F172A' }}>Tenant Scoping:</span>
          <select 
            value={selectedTenant} 
            onChange={e => setSelectedTenant(e.target.value)}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid #CBD5E1',
              fontSize: '0.825rem',
              background: '#F8FAFC',
              fontWeight: 500,
              color: '#0F172A',
              cursor: 'pointer'
            }}
          >
            <option value="all">All Tenants</option>
            <option value="default">default (Default Tenant)</option>
          </select>
        </div>

        {selectedUser !== 'all' && (
          <span className="badge" style={{ background: '#FEE2E2', color: '#DC2626', border: '1px solid #FECDD3', fontSize: '0.775rem', fontWeight: 600 }}>
            Filtered to User: {selectedUser}
          </span>
        )}
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
        {(['all', 'running', 'completed', 'failed'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '0.4rem 0.85rem',
              borderRadius: '6px',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: 'pointer',
              textTransform: 'capitalize',
              background: filter === f ? 'var(--brand-soft)' : 'transparent',
              color: filter === f ? 'var(--brand)' : 'var(--text-muted)',
              border: filter === f ? '1px solid var(--brand-border)' : '1px solid transparent'
            }}
          >
            {f === 'all' ? `All Tasks (${jobs.length})` : f}
          </button>
        ))}
      </div>

      <div className="card glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#F1F5F9', borderBottom: '1px solid var(--border-color)' }}>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Job ID</th>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Task Details</th>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Tenant & User</th>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Status</th>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Progress</th>
              <th style={{ padding: '0.85rem 1.25rem', fontSize: '0.78rem', color: '#334155', fontWeight: 700, textTransform: 'uppercase' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>Loading background tasks...</td></tr>
            ) : filteredJobs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem', color: '#64748B' }}>
                    <ListTodo size={36} color="#94A3B8" />
                    <div style={{ fontWeight: 600, fontSize: '1rem', color: '#1E293B' }}>No Background Tasks</div>
                    <p style={{ fontSize: '0.85rem', margin: 0 }}>
                      {selectedUser !== 'all' 
                        ? `No tasks found for user '${selectedUser}'.` 
                        : "All jobs have been cleared or none are matching the selected filter."}
                    </p>
                  </div>
                </td>
              </tr>
            ) : filteredJobs.map(job => {
              const isTerminated = job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled';
              const isPaused = job.status === 'awaiting_approval';
              const isBusy = actionId === job.job_id;

              return (
                <tr key={job.job_id} style={{ borderBottom: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '0.85rem 1.25rem', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8rem', color: 'var(--brand)' }}>
                    {job.job_id.substring(0, 8)}...
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-heading)' }}>
                      {job.request?.topic || job.request?.youtube_url || "AutoCourse Task"}
                    </div>
                    {job.message && (
                      <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.15rem' }}>
                        {job.message}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', alignItems: 'flex-start' }}>
                      <span className="badge" style={{ background: '#EFF6FF', color: '#1E40AF', border: '1px solid #BFDBFE', fontSize: '0.725rem' }}>
                        👤 {job.user_id || 'shamith'}
                      </span>
                      <span className="badge" style={{ background: '#F1F5F9', color: '#475569', border: '1px solid #E2E8F0', fontSize: '0.7rem' }}>
                        🏢 {job.tenant_id || 'default'}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem' }}>
                    {getStatusBadge(job.status)}
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', minWidth: '130px' }}>
                      <div style={{ flex: 1, height: '7px', background: '#E2E8F0', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${job.progress_percentage || 0}%`, height: '100%', background: 'linear-gradient(90deg, #DC2626, #EF4444)' }} />
                      </div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#DC2626' }}>{job.progress_percentage || 0}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '0.85rem 1.25rem' }}>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      {/* Play / Pause Toggle Button */}
                      {!isTerminated && (
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem' }}
                          disabled={isBusy}
                          onClick={() => handlePauseResume(job)}
                          title={isPaused ? "Resume Pipeline" : "Pause Pipeline"}
                        >
                          {isPaused ? <Play size={13} color="#16A34A" /> : <Pause size={13} color="#D97706" />}
                        </button>
                      )}

                      {/* Stop / Cancel Button */}
                      {!isTerminated && (
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem', color: 'var(--danger-color)' }}
                          disabled={isBusy}
                          onClick={() => handleCancelJob(job.job_id)}
                          title="Stop / Cancel Job"
                        >
                          <Square size={13} />
                        </button>
                      )}

                      {/* Delete Button */}
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '0.35rem 0.55rem', fontSize: '0.75rem', color: '#DC2626' }}
                        disabled={isBusy}
                        onClick={() => setDeleteModalJobId(job.job_id)}
                        title="Delete Task Record"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Clear All Tasks In-App Confirmation Modal */}
      {showClearModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '2rem',
            maxWidth: '480px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            border: '1px solid #E2E8F0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', color: '#DC2626' }}>
              <Trash2 size={24} />
              <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0F172A' }}>
                {selectedUser !== 'all' ? `Clear Tasks for ${selectedUser}?` : 'Clear All Background Tasks?'}
              </h3>
            </div>
            <p style={{ fontSize: '0.9rem', color: '#475569', lineHeight: 1.5, marginBottom: '1.5rem' }}>
              This will immediately cancel running workers, abort awaiting review gates, and <strong>permanently delete all task records {selectedUser !== 'all' ? `belonging to user '${selectedUser}'` : 'across all tenants'}</strong> from disk. This action cannot be undone.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowClearModal(false)}
                style={{ padding: '0.6rem 1.25rem' }}
              >
                Cancel
              </button>
              <button 
                id="confirm-purge-btn"
                className="btn" 
                onClick={confirmClearAllJobs}
                style={{
                  background: '#DC2626',
                  color: '#FFFFFF',
                  border: '1px solid #DC2626',
                  fontWeight: 600,
                  padding: '0.6rem 1.25rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  boxShadow: '0 2px 4px rgba(220, 38, 38, 0.25)'
                }}
              >
                Yes, Purge Tasks
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Single Task Confirmation Modal */}
      {deleteModalJobId && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '1.75rem',
            maxWidth: '440px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
            border: '1px solid #E2E8F0'
          }}>
            <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1.15rem', fontWeight: 700, color: '#0F172A' }}>
              Delete Task Record?
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.5, marginBottom: '1.25rem' }}>
              Permanently remove task <code>{deleteModalJobId}</code> and delete all generated files from disk?
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setDeleteModalJobId(null)}
              >
                Cancel
              </button>
              <button 
                className="btn" 
                onClick={() => handleDeleteJob(deleteModalJobId)}
                style={{
                  background: '#DC2626',
                  color: '#FFFFFF',
                  border: '1px solid #DC2626',
                  fontWeight: 600,
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Delete Task
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
