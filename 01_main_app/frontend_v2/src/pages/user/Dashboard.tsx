import { useState, useEffect } from 'react';
import { Video, Clock, CheckCircle2, AlertCircle, PlayCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchCurrentUser } from '../../utils/userSession';
import './Dashboard.css';

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  message: string;
  files?: Record<string, any>;
}

interface PluginHealth {
  plugin: string;
  healthy: boolean;
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [plugins, setPlugins] = useState<PluginHealth[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCurrentUser()
      .then(user => fetch(`/api/jobs?user_id=${encodeURIComponent(user.username)}`))
      .then(res => res.json())
      .then(data => {
        const arr = Object.values(data) as JobSummary[];
        arr.reverse();
        setJobs(arr);
      })
      .catch(console.error);

    fetch('/api/admin/plugins').then(res => res.json()).then(data => {
      setPlugins(data);
    }).catch(console.error);
  }, []);

  const totalVideos = jobs.length;
  const completed = jobs.filter(j => j.status === 'completed').length;
  const failed = jobs.filter(j => j.status === 'failed').length;
  const successRate = totalVideos > 0 ? Math.round((completed / totalVideos) * 100) : 0;
  // Fallback avg render time
  const avgTime = "2m";

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <h1>Welcome back, Admin</h1>
          <p className="text-muted">Here's what's happening with your video generation pipeline today.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/user/create')}>
          <Video size={18} />
          New Generation
        </button>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon bg-blue-100">
            <Video className="text-primary" size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{totalVideos}</span>
            <span className="stat-label">Videos Generated</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon bg-green-100">
            <CheckCircle2 className="text-success" size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{successRate}%</span>
            <span className="stat-label">Success Rate</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon bg-purple-100">
            <Clock className="text-purple" size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{avgTime}</span>
            <span className="stat-label">Avg. Render Time</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon bg-orange-100">
            <AlertCircle className="text-warning" size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{failed}</span>
            <span className="stat-label">Failed Jobs</span>
          </div>
        </div>
      </section>

      <div className="dashboard-content-grid">
        <div className="card recent-activity">
          <h2 className="card-title">Recent Activity</h2>
          <div className="activity-list">
            {jobs.length === 0 ? <p style={{padding: '1rem', color: 'var(--text-muted)'}}>No recent activity.</p> : jobs.slice(0, 5).map((job) => (
              <div key={job.job_id} className="activity-item">
                <div className={`activity-indicator ${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'active'}`}></div>
                <div className="activity-details">
                  <h4>{job.request?.topic || job.request?.youtube_url || "Generated Video"}</h4>
                  <span className="text-muted text-sm">{job.status} • {job.request?.mode} • {job.job_id.substring(0,8)}</span>
                </div>
                <button className="icon-btn" onClick={() => navigate(`/user/progress?jobId=${job.job_id}`)}>
                  <PlayCircle size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>
        
        <div className="card system-status">
          <h2 className="card-title">System Status</h2>
          <div className="status-list">
            <div className="status-item">
              <span>Backend API</span>
              <span className="status-badge active">Online</span>
            </div>
            {plugins.map(p => (
              <div key={p.plugin} className="status-item">
                <span>{p.plugin} Engine</span>
                <span className={`status-badge ${p.healthy ? 'active' : 'offline'}`}>{p.healthy ? 'Online' : 'Offline'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
