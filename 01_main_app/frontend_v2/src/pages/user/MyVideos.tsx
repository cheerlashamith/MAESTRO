import { useState, useEffect } from 'react';
import { Play, Download, MoreVertical, Search, Filter } from 'lucide-react';
import './MyVideos.css';

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  files: Record<string, any>;
  youtube_video_id?: string;
  youtube_url?: string;
}

export default function MyVideos() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedbackJobId, setFeedbackJobId] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/jobs')
      .then(res => res.json())
      .then(data => {
        const arr = Object.values(data) as JobSummary[];
        // Accept jobs with either final_video or videos[0]
        const completed = arr
          .filter(j => j.status === 'completed' && (j.files?.final_video || j.files?.videos?.[0]));
        completed.reverse();
        setJobs(completed);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch jobs", err);
        setLoading(false);
      });
  }, []);

  const getVideoPath = (job: JobSummary): string => {
    return job.files?.final_video || job.files?.videos?.[0] || '';
  };

  const handleDownload = (path: string) => {
    window.open(`/api/download?path=${encodeURIComponent(path)}`, '_blank');
  };

  const handleRegenerate = async (jobId: string) => {
    if (!feedbackText.trim()) return;
    setActionLoading(jobId);
    try {
      await fetch(`/api/jobs/${jobId}/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedbackText }),
      });
      alert('Job queued for regeneration!');
      setFeedbackJobId(null);
      setFeedbackText("");
    } catch (err) {
      alert('Failed to regenerate: ' + err);
    }
    setActionLoading(null);
  };

  const handlePublishRedirect = (jobId: string) => {
    window.location.href = `/user/publisher?jobId=${jobId}`;
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>My Videos</h1>
          <p className="text-muted">Manage, view, and export your generated courses.</p>
        </div>
        <div className="header-actions">
          <div className="search-bar">
            <Search size={18} />
            <input type="text" placeholder="Search videos..." />
          </div>
          <button className="btn btn-secondary">
            <Filter size={18} />
            Filter
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{padding: '2rem', textAlign: 'center'}}>Loading videos...</div>
      ) : jobs.length === 0 ? (
        <div style={{padding: '2rem', textAlign: 'center'}}>No completed videos yet.</div>
      ) : (
        <div className="video-grid">
          {jobs.map(video => (
            <div key={video.job_id} className="video-card glass-panel">
              <div className="video-thumbnail" style={{ backgroundColor: 'var(--card-bg)', position: 'relative' }}>
                <span className="video-duration">Ready</span>
                {video.youtube_video_id && (
                  <span style={{ position: 'absolute', top: 8, left: 8, padding: '0.2rem 0.5rem', background: '#ff0000', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>
                    ON YOUTUBE
                  </span>
                )}
                <div className="video-play-overlay">
                  <button className="play-btn" onClick={() => handleDownload(getVideoPath(video))}>
                    <Play size={24} fill="currentColor" />
                  </button>
                </div>
              </div>
              <div className="video-details">
                <div className="video-title-row">
                  <h3 className="video-title">{video.request?.topic || video.request?.youtube_url || "AutoCourse Generation"}</h3>
                  <button className="icon-btn">
                    <MoreVertical size={16} />
                  </button>
                </div>
                <p className="video-meta">Mode: {video.request?.mode || 'auto'}</p>
                <div className="video-actions" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <button className="btn btn-primary btn-sm btn-block" onClick={() => handleDownload(getVideoPath(video))}>
                    <Download size={14} />
                    Export Video
                  </button>
                  <button className="btn btn-secondary btn-sm btn-block" onClick={() => setFeedbackJobId(video.job_id)}>
                    Regenerate / Fix
                  </button>
                  {video.youtube_video_id ? (
                    <a 
                      href={video.youtube_url || `https://www.youtube.com/watch?v=${video.youtube_video_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-sm btn-block"
                      style={{ color: '#ff4d4d', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem' }}
                    >
                      Watch on YouTube
                    </a>
                  ) : (
                    <button className="btn btn-secondary btn-sm btn-block" onClick={() => handlePublishRedirect(video.job_id)}>
                      Publish to YouTube Studio
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {feedbackJobId && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <div className="modal-content glass-panel" style={{ padding: '2rem', width: '400px', maxWidth: '90%' }}>
            <h2>Regenerate Video</h2>
            <p>What didn't you like? What should we change?</p>
            <textarea 
              value={feedbackText} 
              onChange={e => setFeedbackText(e.target.value)}
              placeholder="e.g. Change the color theme to blue, remove the summary scene..."
              style={{ width: '100%', height: '100px', marginTop: '1rem', padding: '0.5rem', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid rgba(255,255,255,0.1)' }}
            />
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button className="btn btn-primary" onClick={() => handleRegenerate(feedbackJobId)} disabled={actionLoading === feedbackJobId}>
                {actionLoading === feedbackJobId ? "Sending..." : "Regenerate"}
              </button>
              <button className="btn btn-secondary" onClick={() => setFeedbackJobId(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
