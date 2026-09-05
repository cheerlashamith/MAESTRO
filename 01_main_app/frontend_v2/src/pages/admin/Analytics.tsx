import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Users, Video, RefreshCw, CheckCircle2, Clock, XCircle, ShieldAlert } from 'lucide-react';

interface DayData {
  label: string;
  count: number;
}

export default function Analytics() {
  const [totalVideos, setTotalVideos] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [inProgressCount, setInProgressCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [cancelledCount, setCancelledCount] = useState(0);
  const [successRate, setSuccessRate] = useState(0);
  const [activeUsersCount, setActiveUsersCount] = useState(0);
  const [dailyData, setDailyData] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    try {
      // 1. Fetch real jobs
      const jobsRes = await fetch('/api/jobs');
      const jobsData = await jobsRes.json();
      const arr = Object.values(jobsData) as any[];

      setTotalVideos(arr.length);
      const completed = arr.filter(j => j.status === 'completed').length;
      const failed = arr.filter(j => j.status === 'failed').length;
      const cancelled = arr.filter(j => j.status === 'cancelled').length;
      const inProgress = arr.filter(j => ['queued', 'planning', 'rendering', 'assembling', 'awaiting_approval'].includes(j.status)).length;

      setCompletedCount(completed);
      setFailedCount(failed);
      setCancelledCount(cancelled);
      setInProgressCount(inProgress);

      const resolved = completed + failed + cancelled;
      setSuccessRate(resolved > 0 ? Math.round((completed / resolved) * 1000) / 10 : 0);

      // 2. Real Calendar 7-Day Timeline
      const days: DayData[] = [];
      const now = new Date();
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const dayLabel = i === 0 ? 'Today' : i === 1 ? 'Yesterday' : d.toLocaleDateString(undefined, { weekday: 'short', month: 'numeric', day: 'numeric' });
        
        const count = arr.filter(j => {
          if (!j.created_at) return false;
          const jobDate = new Date(j.created_at);
          return (
            jobDate.getFullYear() === d.getFullYear() &&
            jobDate.getMonth() === d.getMonth() &&
            jobDate.getDate() === d.getDate()
          );
        }).length;

        days.push({ label: dayLabel, count });
      }
      setDailyData(days);

      // 3. Fetch real IAM users count
      try {
        const usersRes = await fetch('/api/iam/users');
        const usersData = await usersRes.json();
        if (usersData?.users && Array.isArray(usersData.users)) {
          setActiveUsersCount(usersData.users.length);
        } else {
          setActiveUsersCount(1);
        }
      } catch {
        setActiveUsersCount(1);
      }

    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(interval);
  }, []);

  const maxCount = Math.max(...dailyData.map(d => d.count), 5);

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div className="badge badge-blue" style={{ marginBottom: '0.4rem' }}>
            REAL-TIME TELEMETRY
          </div>
          <h1 style={{ fontFamily: "'Libre Baskerville', Georgia, serif", fontSize: '1.75rem', fontWeight: 700 }}>
            System Analytics
          </h1>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Live usage statistics, worker throughput, and real pipeline metrics over time.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchAnalytics} disabled={loading}>
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>
      
      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
        <div className="card glass-panel" style={{ padding: '1.25rem 1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748B', fontSize: '0.825rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Video size={16} color="#1D4ED8" /> Total Tasks
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0F172A' }}>{totalVideos}</div>
          <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.25rem' }}>
            {completedCount} completed · {inProgressCount} in-flight
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '1.25rem 1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748B', fontSize: '0.825rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Users size={16} color="#7E22CE" /> Active IAM Users
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0F172A' }}>{activeUsersCount}</div>
          <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.25rem' }}>
            Registered RBAC accounts
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '1.25rem 1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748B', fontSize: '0.825rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <TrendingUp size={16} color="#15803D" /> Pipeline Success Rate
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: successRate >= 70 ? '#15803D' : successRate >= 40 ? '#D97706' : '#DC2626' }}>
            {successRate}%
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.25rem' }}>
            {completedCount} successful of {completedCount + failedCount + cancelledCount} resolved
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '1.25rem 1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748B', fontSize: '0.825rem', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Clock size={16} color="#0284C7" /> Active Workflows
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0F172A' }}>{inProgressCount}</div>
          <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.25rem' }}>
            {inProgressCount > 0 ? "Executing pipeline steps" : "Worker queue idle"}
          </div>
        </div>
      </div>

      {/* 7-Day Volume Chart with Real Calendar Dates */}
      <div className="card glass-panel" style={{ padding: '1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0, fontSize: '1.15rem' }}>
            <BarChart3 size={18} color="#1D4ED8" /> Generation Volume (Last 7 Days)
          </h2>
          <span className="badge badge-blue">Dynamic Timeline</span>
        </div>

        <div style={{ height: '260px', display: 'flex', alignItems: 'flex-end', gap: '1.25rem', padding: '1.5rem 0.5rem 0.5rem', borderBottom: '1px solid #E2E8F0' }}>
          {dailyData.map((d, i) => {
            const heightPercent = Math.max(6, (d.count / maxCount) * 100);
            return (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem', height: '100%', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: d.count > 0 ? '#1D4ED8' : '#94A3B8' }}>
                  {d.count}
                </span>
                <div 
                  style={{ 
                    width: '100%', 
                    maxWidth: '48px',
                    height: `${heightPercent}%`, 
                    background: d.count > 0 ? 'linear-gradient(180deg, #2563EB 0%, #1D4ED8 100%)' : '#E2E8F0', 
                    borderRadius: '6px 6px 0 0', 
                    transition: 'height 0.4s ease' 
                  }}
                  title={`${d.label}: ${d.count} tasks generated`}
                />
                <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600, textAlign: 'center', whiteSpace: 'nowrap' }}>
                  {d.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline Status Breakdown */}
      <div className="card glass-panel" style={{ padding: '1.5rem', background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '12px' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem', color: '#0F172A' }}>
          Pipeline Task Status Distribution
        </h2>

        <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: '#E2E8F0', marginBottom: '1.25rem' }}>
          {totalVideos > 0 ? (
            <>
              <div style={{ width: `${(completedCount / totalVideos) * 100}%`, background: '#16A34A' }} title={`Completed: ${completedCount}`} />
              <div style={{ width: `${(inProgressCount / totalVideos) * 100}%`, background: '#2563EB' }} title={`In-Progress: ${inProgressCount}`} />
              <div style={{ width: `${(failedCount / totalVideos) * 100}%`, background: '#DC2626' }} title={`Failed: ${failedCount}`} />
              <div style={{ width: `${(cancelledCount / totalVideos) * 100}%`, background: '#94A3B8' }} title={`Cancelled: ${cancelledCount}`} />
            </>
          ) : (
            <div style={{ width: '100%', background: '#CBD5E1' }} />
          )}
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <CheckCircle2 size={15} color="#16A34A" />
            <span style={{ fontWeight: 600, color: '#0F172A' }}>Completed:</span>
            <span style={{ color: '#64748B' }}>{completedCount}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <Clock size={15} color="#2563EB" />
            <span style={{ fontWeight: 600, color: '#0F172A' }}>In Progress:</span>
            <span style={{ color: '#64748B' }}>{inProgressCount}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <XCircle size={15} color="#DC2626" />
            <span style={{ fontWeight: 600, color: '#0F172A' }}>Failed:</span>
            <span style={{ color: '#64748B' }}>{failedCount}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <ShieldAlert size={15} color="#94A3B8" />
            <span style={{ fontWeight: 600, color: '#0F172A' }}>Cancelled:</span>
            <span style={{ color: '#64748B' }}>{cancelledCount}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
