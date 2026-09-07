import { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Video, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  ShieldAlert,
  Share2,
  ExternalLink
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DayData {
  label: string;
  count: number;
}

export default function Analytics() {
  const navigate = useNavigate();
  const [totalVideos, setTotalVideos] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [inProgressCount, setInProgressCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [cancelledCount, setCancelledCount] = useState(0);
  const [successRate, setSuccessRate] = useState(0);
  const [activeUsersCount, setActiveUsersCount] = useState(0);
  const [dailyData, setDailyData] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);

  // YouTube Analytics
  const [ytTotalViews, setYtTotalViews] = useState(0);
  const [ytUploadedCount, setYtUploadedCount] = useState(0);

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
      const ytCount = arr.filter(j => j.youtube_video_id || j.youtube_url).length;

      setCompletedCount(completed);
      setFailedCount(failed);
      setCancelledCount(cancelled);
      setInProgressCount(inProgress);
      if (ytCount > 0) setYtUploadedCount(ytCount);

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

      // 4. Fetch YouTube Analytics
      try {
        const ytRes = await fetch('/api/youtube/analytics');
        const ytData = await ytRes.json();
        if (ytData?.analytics && Array.isArray(ytData.analytics) && ytData.analytics.length > 0) {
          const views = ytData.analytics.reduce((acc: number, item: any) => acc + (item.views || 0), 0);
          setYtTotalViews(views);
          setYtUploadedCount(ytData.analytics.length);
        }
      } catch {}

    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 6000);
    return () => clearInterval(interval);
  }, []);

  const maxCount = Math.max(...dailyData.map(d => d.count), 5);

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div className="badge badge-purple" style={{ marginBottom: '0.4rem' }}>
            REAL-TIME TELEMETRY
          </div>
          <h1 style={{ fontFamily: "'Libre Baskerville', Georgia, serif", fontSize: '1.85rem', fontWeight: 700, color: 'var(--text-heading)' }}>
            System Analytics &amp; Telemetry
          </h1>
          <p className="text-muted" style={{ fontSize: '0.88rem' }}>
            Live orchestration statistics, multi-agent throughput, and YouTube distribution metrics.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchAnalytics} disabled={loading}>
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>
      
      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1.25rem' }}>
        {/* Total Tasks */}
        <div className="card glass-panel" style={{ padding: '1.35rem 1.5rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Video size={16} color="#5227c7" /> Total Tasks
          </div>
          <div style={{ fontSize: '2.1rem', fontWeight: 700, color: 'var(--text-heading)' }}>{totalVideos}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {completedCount} completed · {inProgressCount} in-flight
          </div>
        </div>

        {/* Success Rate */}
        <div className="card glass-panel" style={{ padding: '1.35rem 1.5rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <TrendingUp size={16} color="#ff6d34" /> Pipeline Success Rate
          </div>
          <div style={{ fontSize: '2.1rem', fontWeight: 700, color: successRate >= 70 ? '#059669' : successRate >= 40 ? '#ff6d34' : '#DC2626' }}>
            {successRate}%
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {completedCount} successful of {completedCount + failedCount + cancelledCount} resolved
          </div>
        </div>

        {/* YouTube Distribution */}
        <div className="card glass-panel" style={{ padding: '1.35rem 1.5rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Share2 size={16} color="#ff6d34" /> YouTube Reach
          </div>
          <div style={{ fontSize: '2.1rem', fontWeight: 700, color: 'var(--accent-orange)' }}>
            {ytTotalViews.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {ytUploadedCount} videos indexed on YouTube
          </div>
        </div>

        {/* Active Workflows */}
        <div className="card glass-panel" style={{ padding: '1.35rem 1.5rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Clock size={16} color="#5227c7" /> Active Workflows
          </div>
          <div style={{ fontSize: '2.1rem', fontWeight: 700, color: 'var(--brand)' }}>{inProgressCount}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {inProgressCount > 0 ? "Executing pipeline steps" : "Worker queue idle"}
          </div>
        </div>

        {/* IAM Creators */}
        <div className="card glass-panel" style={{ padding: '1.35rem 1.5rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            <Users size={16} color="#7040f7" /> IAM Accounts
          </div>
          <div style={{ fontSize: '2.1rem', fontWeight: 700, color: 'var(--text-heading)' }}>{activeUsersCount}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Registered multi-tenant operators
          </div>
        </div>
      </div>

      {/* 7-Day Volume Chart with Purple & Orange Gradient */}
      <div className="card glass-panel" style={{ padding: '1.75rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: 0, fontSize: '1.18rem', color: 'var(--text-heading)' }}>
            <BarChart3 size={20} color="#5227c7" /> Generation Volume (Last 7 Days)
          </h2>
          <span className="badge badge-purple">Dynamic Timeline</span>
        </div>

        <div style={{ height: '260px', display: 'flex', alignItems: 'flex-end', gap: '1.25rem', padding: '1.5rem 0.5rem 0.5rem', borderBottom: '1px solid var(--border-color)' }}>
          {dailyData.map((d, i) => {
            const heightPercent = Math.max(8, (d.count / maxCount) * 100);
            return (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.6rem', height: '100%', justifyContent: 'flex-end' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: d.count > 0 ? '#ff6d34' : 'var(--text-light)' }}>
                  {d.count}
                </span>
                <div 
                  style={{ 
                    width: '100%', 
                    maxWidth: '48px',
                    height: `${heightPercent}%`, 
                    background: d.count > 0 ? 'linear-gradient(180deg, #ff6d34 0%, #5227c7 100%)' : 'var(--border-light)', 
                    borderRadius: '8px 8px 0 0', 
                    transition: 'height 0.4s ease',
                    boxShadow: d.count > 0 ? '0 4px 12px rgba(82, 39, 199, 0.25)' : 'none'
                  }}
                  title={`${d.label}: ${d.count} tasks generated`}
                />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textAlign: 'center', whiteSpace: 'nowrap' }}>
                  {d.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline Status Breakdown & Quick Links */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        <div className="card glass-panel" style={{ padding: '1.75rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1.2rem', color: 'var(--text-heading)' }}>
            Pipeline Task Status Distribution
          </h2>

          <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'var(--border-light)', marginBottom: '1.5rem' }}>
            {totalVideos > 0 ? (
              <>
                <div style={{ width: `${(completedCount / totalVideos) * 100}%`, background: '#059669' }} title={`Completed: ${completedCount}`} />
                <div style={{ width: `${(inProgressCount / totalVideos) * 100}%`, background: '#5227c7' }} title={`In-Progress: ${inProgressCount}`} />
                <div style={{ width: `${(failedCount / totalVideos) * 100}%`, background: '#DC2626' }} title={`Failed: ${failedCount}`} />
                <div style={{ width: `${(cancelledCount / totalVideos) * 100}%`, background: '#94A3B8' }} title={`Cancelled: ${cancelledCount}`} />
              </>
            ) : (
              <div style={{ width: '100%', background: 'var(--border-color)' }} />
            )}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <CheckCircle2 size={16} color="#059669" />
              <span style={{ fontWeight: 600, color: 'var(--text-heading)' }}>Completed:</span>
              <span style={{ color: 'var(--text-muted)' }}>{completedCount}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <Clock size={16} color="#5227c7" />
              <span style={{ fontWeight: 600, color: 'var(--text-heading)' }}>In Progress:</span>
              <span style={{ color: 'var(--text-muted)' }}>{inProgressCount}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <XCircle size={16} color="#DC2626" />
              <span style={{ fontWeight: 600, color: 'var(--text-heading)' }}>Failed:</span>
              <span style={{ color: 'var(--text-muted)' }}>{failedCount}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <ShieldAlert size={16} color="#94A3B8" />
              <span style={{ fontWeight: 600, color: 'var(--text-heading)' }}>Cancelled:</span>
              <span style={{ color: 'var(--text-muted)' }}>{cancelledCount}</span>
            </div>
          </div>
        </div>

        {/* YouTube Channel Quick Link Card */}
        <div className="card glass-panel" style={{ padding: '1.75rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span className="badge badge-orange">CHANNEL SYNC</span>
              <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 700 }}>● ONLINE</span>
            </div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.4rem', color: 'var(--text-heading)' }}>
              YouTube Studio Telemetry
            </h2>
            <p className="text-muted" style={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
              Channel synchronization is active with automated AI title optimization, keyword tagging, and scheduled upload workers.
            </p>
          </div>

          <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem' }}>
            <button 
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/user/publisher')}
              style={{ flex: 1 }}
            >
              <Share2 size={14} /> Open YouTube Hub
            </button>
            <a 
              href="https://www.youtube.com" 
              target="_blank" 
              rel="noreferrer" 
              className="btn btn-secondary btn-sm"
            >
              <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
