import { useState, useEffect } from 'react';
import { Activity, Play, ThumbsUp, MessageSquare, AlertCircle } from 'lucide-react';
import './AnalyticsDashboard.css';

interface AnalyticsItem {
  job_id: string;
  topic: string;
  video_id: string;
  views: number;
  likes: number;
  comments: number;
  uploaded_at: string;
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch('/api/admin/youtube-analytics')
      .then(res => res.json())
      .then(json => {
        if (json.error) {
          setError(json.error);
        } else {
          setData(json.analytics || []);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Analytics & Agent Strategy</h1>
          <p className="text-muted">Monitor YouTube performance and see how the Autonomous Agent adapts.</p>
        </div>
      </div>

      {error && (
        <div className="glass-panel" style={{ padding: '1rem', color: '#ff6b6b', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: '2rem', textAlign: 'center' }}>Loading analytics from YouTube...</div>
      ) : (
        <div className="dashboard-grid" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3>Agent Status</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', color: '#51cf66' }}>
              <Activity size={20} />
              <span>Monitoring active. Checking stats every hour to optimize engagement.</span>
            </div>
            <p className="text-muted" style={{ marginTop: '0.5rem' }}>If a video drops below the view threshold, the agent will automatically formulate a new strategy and enqueue a new generation.</p>
          </div>

          <h3>Uploaded Videos Performance</h3>
          {data.length === 0 ? (
            <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', opacity: 0.7 }}>
              No videos uploaded to YouTube yet.
            </div>
          ) : (
            <div className="table-responsive glass-panel">
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <th style={{ padding: '1rem' }}>Topic</th>
                    <th style={{ padding: '1rem' }}>Uploaded</th>
                    <th style={{ padding: '1rem' }}><div style={{display:'flex', alignItems:'center', gap:'0.2rem'}}><Play size={16}/> Views</div></th>
                    <th style={{ padding: '1rem' }}><div style={{display:'flex', alignItems:'center', gap:'0.2rem'}}><ThumbsUp size={16}/> Likes</div></th>
                    <th style={{ padding: '1rem' }}><div style={{display:'flex', alignItems:'center', gap:'0.2rem'}}><MessageSquare size={16}/> Comments</div></th>
                  </tr>
                </thead>
                <tbody>
                  {data.map(item => (
                    <tr key={item.video_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '1rem' }}>
                        <a href={`https://youtube.com/watch?v=${item.video_id}`} target="_blank" rel="noreferrer" style={{ color: 'var(--primary-color)' }}>
                          {item.topic}
                        </a>
                      </td>
                      <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{new Date(item.uploaded_at).toLocaleDateString()}</td>
                      <td style={{ padding: '1rem', fontWeight: 'bold', color: item.views < 50 ? '#ffc9c9' : 'inherit' }}>{item.views.toLocaleString()}</td>
                      <td style={{ padding: '1rem' }}>{item.likes.toLocaleString()}</td>
                      <td style={{ padding: '1rem' }}>{item.comments.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
