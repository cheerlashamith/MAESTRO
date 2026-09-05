import { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Clock, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchCurrentUser } from '../../utils/userSession';
import './History.css';

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  message: string;
  files?: Record<string, any>;
  created_at?: string;
}

function formatDate(iso?: string): string {
  if (!iso) return "Unknown";
  try {
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    return d.toLocaleString();
  } catch {
    return "Unknown";
  }
}

export default function History() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCurrentUser()
      .then(user => fetch(`/api/jobs?user_id=${encodeURIComponent(user.username)}`))
      .then(res => res.json())
      .then(data => {
        const arr = Object.values(data) as JobSummary[];
        arr.sort((a, b) => {
          const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
          const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
          return tb - ta; // Newest first
        });
        setJobs(arr);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch jobs", err);
        setLoading(false);
      });
  }, []);

  const handleDownload = (path: string) => {
    window.open(`/api/download?path=${encodeURIComponent(path)}`, '_blank');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Generation History</h1>
          <p className="text-muted">A log of all your video generation tasks.</p>
        </div>
      </div>

      <div className="card glass-panel">
        <table className="history-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Video Title</th>
              <th>Generation Mode</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{textAlign: 'center', padding: '2rem'}}>Loading history...</td></tr>
            ) : jobs.length === 0 ? (
              <tr><td colSpan={6} style={{textAlign: 'center', padding: '2rem'}}>No jobs found. Generate your first video!</td></tr>
            ) : jobs.map(job => (
              <tr key={job.job_id} style={{cursor: 'pointer'}} onClick={() => navigate(`/user/progress?jobId=${job.job_id}`)}>
                <td className="job-id">{job.job_id.substring(0, 8)}...</td>
                <td className="job-title">{job.request?.topic || job.request?.youtube_url || "AutoCourse Generation"}</td>
                <td><span className="mode-badge">{job.request?.mode}</span></td>
                <td>
                  {job.status === 'completed' ? (
                    <span className="status-badge success">
                      <CheckCircle2 size={14} /> Completed
                    </span>
                  ) : job.status === 'failed' || job.status === 'cancelled' ? (
                    <span className="status-badge danger">
                      <XCircle size={14} /> {job.status}
                    </span>
                  ) : (
                    <span className="status-badge" style={{color: 'var(--primary-color)'}}>
                      <Clock size={14} /> {job.status}
                    </span>
                  )}
                </td>
                <td className="text-muted">{formatDate(job.created_at)}</td>
                <td onClick={e => e.stopPropagation()}>
                  {job.status === 'completed' && job.files?.final_video && (
                    <button className="btn btn-secondary btn-sm" onClick={() => handleDownload(job.files!.final_video)}>
                      <Download size={14} /> Download
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

