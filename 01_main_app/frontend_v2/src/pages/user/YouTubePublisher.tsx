import { useState, useEffect, useRef } from 'react';
import {
  Share2,
  Calendar,
  Clock,
  Sparkles,
  CheckCircle,
  ExternalLink,
  Copy,
  Trash2,
  RefreshCw,
  Eye,
  ThumbsUp,
  MessageSquare,
  UploadCloud,
  X,
  Play,
  AlertCircle,
  Sliders,
  Image as ImageIcon
} from 'lucide-react';
import { fetchCurrentUser } from '../../utils/userSession';
import './YouTubePublisher.css';

interface ChannelProfile {
  id: string;
  title: string;
  custom_url: string;
  description: string;
  avatar: string;
  subscriber_count: number;
  video_count: number;
  view_count: number;
}

interface ScheduledItem {
  schedule_id: string;
  job_id?: string;
  video_path: string;
  title: string;
  description: string;
  tags: string[];
  category_id: string;
  privacy_status: string;
  schedule_time?: string;
  schedule_mode: string;
  thumbnail_path?: string;
  status: 'scheduled' | 'uploading' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  message: string;
  created_at: string;
  youtube_video_id?: string;
  youtube_url?: string;
  uploaded_at?: string;
  error?: string;
}

interface PublishedVideo {
  job_id: string;
  video_id: string;
  title: string;
  topic: string;
  description: string;
  thumbnail_url: string;
  views: number;
  likes: number;
  comments: number;
  published_at: string;
  watch_url: string;
}

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  files: Record<string, any>;
  youtube_video_id?: string;
}

export default function YouTubePublisher() {
  const [channel, setChannel] = useState<ChannelProfile | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'queue' | 'published' | 'rules'>('queue');

  // Queue & Published data
  const [queue, setQueue] = useState<ScheduledItem[]>([]);
  const [published, setPublished] = useState<PublishedVideo[]>([]);
  const [completedJobs, setCompletedJobs] = useState<JobSummary[]>([]);

  // Publish / Schedule Modal State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [modalTitle, setModalTitle] = useState<string>('');
  const [titleChoices, setTitleChoices] = useState<string[]>([]);
  const [modalDescription, setModalDescription] = useState<string>('');
  const [modalTags, setModalTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState<string>('');
  const [modalCategory, setModalCategory] = useState<string>('27');
  const [modalPrivacy, setModalPrivacy] = useState<string>('private');
  const [modalScheduleDate, setModalScheduleDate] = useState<string>('');
  const [modalScheduleTime, setModalScheduleTime] = useState<string>('12:00');
  const [modalScheduleMode, setModalScheduleMode] = useState<string>('local');
  const [modalThumbnail, setModalThumbnail] = useState<string>('');
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Automation rules settings
  const [autoPublishEnabled, setAutoPublishEnabled] = useState<boolean>(false);
  const [defaultPrivacy, setDefaultPrivacy] = useState<string>('private');
  const [defaultScheduleMode, setDefaultScheduleMode] = useState<string>('local');
  const [defaultCategory, setDefaultCategory] = useState<string>('27');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check URL params for OAuth return
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('connected') === 'true') {
      alert('YouTube Channel connected successfully!');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get('error')) {
      alert('YouTube connection error: ' + urlParams.get('error'));
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const loadData = async () => {
    try {
      // 1. Channel Status
      const statusRes = await fetch('/api/youtube/status');
      const statusData = await statusRes.json();
      setConnected(statusData.connected || false);
      setChannel(statusData.channel || null);

      // 2. Queue
      const queueRes = await fetch('/api/youtube/queue');
      const queueData = await queueRes.json();
      setQueue(queueData.queue || []);

      // 3. Analytics / Published
      const analyticsRes = await fetch('/api/youtube/analytics');
      const analyticsData = await analyticsRes.json();
      setPublished(analyticsData.analytics || []);

      // 4. Completed Jobs for modal selector (scoped to current user)
      const user = await fetchCurrentUser();
      const jobsRes = await fetch(`/api/jobs?user_id=${encodeURIComponent(user.username)}`);
      const jobsData = await jobsRes.json();
      const arr = Object.values(jobsData) as JobSummary[];
      const ready = arr.filter(j => j.status === 'completed' && (j.files?.final_video || j.files?.videos?.[0]));
      ready.reverse();
      setCompletedJobs(ready);

      setLoading(false);
    } catch (err) {
      console.error('Failed to load YouTube data', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleConnect = async () => {
    try {
      const res = await fetch('/api/youtube/auth/url');
      const data = await res.json();
      if (data.auth_url) {
        window.location.href = data.auth_url;
      } else {
        alert('Could not generate OAuth URL: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Failed to initiate YouTube connection: ' + err);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your YouTube channel?')) return;
    try {
      await fetch('/api/youtube/auth/disconnect', { method: 'POST' });
      setConnected(false);
      setChannel(null);
      alert('Channel disconnected.');
      loadData();
    } catch (err) {
      alert('Error disconnecting: ' + err);
    }
  };

  const handleOpenPublishModal = (jobId?: string) => {
    setErrorMessage('');
    setTitleChoices([]);
    setUploadProgress(0);
    setIsPublishing(false);

    const targetJob = jobId 
      ? completedJobs.find(j => j.job_id === jobId) 
      : (completedJobs.length > 0 ? completedJobs[0] : null);

    if (targetJob) {
      setSelectedJobId(targetJob.job_id);
      setModalTitle(targetJob.request?.topic || 'AutoCourse Generated Video');
      setModalDescription(targetJob.request?.notes ? `Course Overview:\n${targetJob.request.notes}` : 'Generated by MAESTRO - Multi-Agent Autonomous Engine for Scalable Transmedia Production & Orchestration');
      setModalTags(['MAESTRO', 'Education', 'Tutorial', 'AI', 'Course']);
      setModalCategory(defaultCategory);
      setModalPrivacy(defaultPrivacy);
      setModalScheduleMode(defaultScheduleMode);
      
      const vPath = targetJob.files?.final_video || targetJob.files?.videos?.[0] || '';
      // Trigger AI Optimization immediately for convenience
      handleAIOptimize(targetJob.request?.topic || 'Course', vPath);
    } else {
      setSelectedJobId('');
      setModalTitle('');
      setModalDescription('');
      setModalTags(['AutoCourse', 'Education']);
    }

    setShowModal(true);
  };

  const handleAIOptimize = async (topicOverride?: string, videoPathOverride?: string) => {
    const job = completedJobs.find(j => j.job_id === selectedJobId);
    const topic = topicOverride || (job ? job.request?.topic : modalTitle);
    const videoPath = videoPathOverride || (job ? (job.files?.final_video || job.files?.videos?.[0]) : undefined);

    if (!topic) return;
    setIsOptimizing(true);

    try {
      const res = await fetch('/api/youtube/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          script: job?.request?.notes || '',
          visual_style: job?.request?.visual_style || 'manim_course',
          video_path: videoPath
        })
      });
      const data = await res.json();
      if (data.titles && data.titles.length > 0) {
        setTitleChoices(data.titles);
        setModalTitle(data.titles[0]);
      }
      if (data.description) {
        setModalDescription(data.description);
      }
      if (data.tags) {
        setModalTags(data.tags);
      }
      if (data.category_id) {
        setModalCategory(data.category_id);
      }
      if (data.suggested_thumbnail_path) {
        setModalThumbnail(data.suggested_thumbnail_path);
      }
    } catch (err) {
      console.error('Optimization error', err);
    }
    setIsOptimizing(false);
  };

  const handleAddTag = () => {
    if (!tagInput.trim()) return;
    if (!modalTags.includes(tagInput.trim())) {
      setModalTags([...modalTags, tagInput.trim()]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setModalTags(modalTags.filter(t => t !== tagToRemove));
  };

  const handleThumbnailUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/youtube/upload-thumbnail', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.thumbnail_path) {
        setModalThumbnail(data.thumbnail_path);
      }
    } catch (err) {
      alert('Failed to upload thumbnail: ' + err);
    }
  };

  const handleSubmitPublish = async () => {
    if (!modalTitle.trim()) {
      setErrorMessage('Video title is required.');
      return;
    }
    const job = completedJobs.find(j => j.job_id === selectedJobId);
    const videoPath = job ? (job.files?.final_video || job.files?.videos?.[0]) : '';

    if (!videoPath) {
      setErrorMessage('Please select a completed video.');
      return;
    }

    let scheduleTimeIso: string | undefined = undefined;
    if (modalPrivacy === 'scheduled') {
      if (!modalScheduleDate) {
        setErrorMessage('Please choose a schedule date.');
        return;
      }
      const combined = `${modalScheduleDate}T${modalScheduleTime || '12:00'}:00`;
      scheduleTimeIso = new Date(combined).toISOString();
    }

    setIsPublishing(true);
    setUploadProgress(15);

    try {
      const res = await fetch('/api/youtube/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: selectedJobId,
          video_path: videoPath,
          title: modalTitle,
          description: modalDescription,
          tags: modalTags,
          category_id: modalCategory,
          privacy_status: modalPrivacy,
          schedule_time: scheduleTimeIso,
          schedule_mode: modalScheduleMode,
          thumbnail_path: modalThumbnail || undefined
        })
      });

      const data = await res.json();
      if (res.ok) {
        setUploadProgress(100);
        setTimeout(() => {
          setIsPublishing(false);
          setShowModal(false);
          loadData();
        }, 800);
      } else {
        setIsPublishing(false);
        setErrorMessage(data.error || 'Publishing request failed.');
      }
    } catch (err: any) {
      setIsPublishing(false);
      setErrorMessage('Network error: ' + err.message);
    }
  };

  const handleCancelScheduled = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to cancel this scheduled upload?')) return;
    try {
      const res = await fetch(`/api/youtube/queue/${scheduleId}`, { method: 'DELETE' });
      if (res.ok) {
        loadData();
      } else {
        const d = await res.json();
        alert(d.detail || 'Could not cancel schedule.');
      }
    } catch (err) {
      alert('Error cancelling: ' + err);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied link to clipboard!');
  };

  return (
    <div className="yt-publisher-page">
      {/* Header Banner */}
      <div className="yt-header-banner">
        <div className="yt-channel-card">
          {channel?.avatar ? (
            <img src={channel.avatar} alt="Channel Avatar" className="yt-channel-avatar" />
          ) : (
            <div className="yt-channel-avatar-placeholder">
              <Share2 size={28} />
            </div>
          )}
          <div className="yt-channel-info">
            <h2>
              {connected && channel ? channel.title : 'YouTube Studio Hub'}
              {connected && <CheckCircle size={18} color="#22c55e" />}
            </h2>
            {connected && channel ? (
              <div className="yt-stats-row">
                <span className="yt-handle">{channel.custom_url || '@channel'}</span>
                <span className="yt-stat-pill">
                  <Eye size={14} /> {channel.subscriber_count.toLocaleString()} Subscribers
                </span>
                <span className="yt-stat-pill">
                  <Play size={14} /> {channel.video_count} Videos
                </span>
              </div>
            ) : (
              <p className="text-muted" style={{ margin: 0 }}>
                Connect your YouTube channel to enable 1-click AI optimization, automated publishing, and scheduled queues.
              </p>
            )}
          </div>
        </div>

        <div className="yt-header-actions">
          {connected ? (
            <>
              <button className="btn btn-primary" onClick={() => handleOpenPublishModal()}>
                <UploadCloud size={16} /> Publish / Schedule Video
              </button>
              <button className="btn btn-secondary" onClick={handleDisconnect}>
                Disconnect
              </button>
            </>
          ) : (
            <button className="btn btn-primary" onClick={handleConnect} style={{ background: '#ff0000', borderColor: '#ff0000' }}>
              <Share2 size={16} /> Connect YouTube Channel
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="yt-tabs">
        <button
          className={`yt-tab-btn ${activeTab === 'queue' ? 'active' : ''}`}
          onClick={() => setActiveTab('queue')}
        >
          <Calendar size={16} />
          Scheduled Queue
          <span className="yt-tab-count">{queue.filter(q => q.status === 'scheduled' || q.status === 'uploading').length}</span>
        </button>

        <button
          className={`yt-tab-btn ${activeTab === 'published' ? 'active' : ''}`}
          onClick={() => setActiveTab('published')}
        >
          <CheckCircle size={16} />
          Published & Analytics
          <span className="yt-tab-count">{published.length}</span>
        </button>

        <button
          className={`yt-tab-btn ${activeTab === 'rules' ? 'active' : ''}`}
          onClick={() => setActiveTab('rules')}
        >
          <Sliders size={16} />
          Automation Rules
        </button>
      </div>

      {/* Tab 1: Scheduled Queue */}
      {activeTab === 'queue' && (
        <div>
          {queue.length === 0 ? (
            <div className="card glass-panel" style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
              <Calendar size={48} style={{ opacity: 0.3, marginBottom: '1rem', color: '#ff4d4d' }} />
              <h3>No Videos in Publishing Queue</h3>
              <p className="text-muted" style={{ maxWidth: '460px', margin: '0 auto 1.5rem auto' }}>
                Schedule videos to publish automatically at specific dates and times, or enable automatic publishing in generation settings.
              </p>
              <button className="btn btn-primary" onClick={() => handleOpenPublishModal()}>
                <UploadCloud size={16} /> Schedule Video Now
              </button>
            </div>
          ) : (
            <div className="yt-queue-grid">
              {queue.map(item => (
                <div key={item.schedule_id} className="yt-queue-card">
                  <div className="yt-queue-thumb-wrapper">
                    {item.thumbnail_path ? (
                      <img src={`/api/download?path=${encodeURIComponent(item.thumbnail_path)}`} alt={item.title} className="yt-queue-thumb" />
                    ) : (
                      <div className="yt-thumb-placeholder">
                        <Play size={32} />
                        <span>Auto-Captured Thumbnail</span>
                      </div>
                    )}
                    <span className={`yt-status-badge yt-status-${item.status}`}>
                      {item.status}
                    </span>
                    <span className="yt-privacy-tag">
                      {item.privacy_status.toUpperCase()}
                    </span>
                  </div>

                  <div className="yt-card-body">
                    <h3 className="yt-card-title" title={item.title}>{item.title}</h3>
                    <div className="yt-card-meta">
                      <Clock size={14} />
                      {item.schedule_time 
                        ? `Scheduled for: ${new Date(item.schedule_time).toLocaleString()}` 
                        : 'Immediate Upload'}
                    </div>

                    {item.status === 'uploading' && (
                      <div className="yt-progress-container" style={{ margin: '0 0 1rem 0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                          <span>{item.message}</span>
                          <span>{item.progress}%</span>
                        </div>
                        <div className="yt-progress-bar-bg">
                          <div className="yt-progress-bar-fill" style={{ width: `${item.progress}%` }}></div>
                        </div>
                      </div>
                    )}

                    {item.error && (
                      <div style={{ color: '#ef4444', fontSize: '0.8rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <AlertCircle size={14} /> {item.error}
                      </div>
                    )}

                    <div className="yt-card-actions">
                      {item.status === 'completed' && item.youtube_url && (
                        <a href={item.youtube_url} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                          <ExternalLink size={14} /> Watch on YouTube
                        </a>
                      )}
                      {item.status === 'scheduled' && (
                        <button className="btn btn-secondary btn-sm" style={{ color: '#ef4444' }} onClick={() => handleCancelScheduled(item.schedule_id)}>
                          <Trash2 size={14} /> Cancel Schedule
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Published Videos & Live Analytics */}
      {activeTab === 'published' && (
        <div>
          {published.length === 0 ? (
            <div className="card glass-panel" style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
              <Share2 size={48} style={{ opacity: 0.3, marginBottom: '1rem', color: '#ff4d4d' }} />
              <h3>No Published Videos Found</h3>
              <p className="text-muted" style={{ maxWidth: '450px', margin: '0 auto 1.5rem auto' }}>
                Published videos and real-time performance analytics will automatically appear here once videos are uploaded.
              </p>
            </div>
          ) : (
            <div className="yt-queue-grid">
              {published.map(vid => (
                <div key={vid.video_id} className="yt-queue-card">
                  <div className="yt-queue-thumb-wrapper">
                    <img src={vid.thumbnail_url} alt={vid.title} className="yt-queue-thumb" />
                    <span className="yt-status-badge yt-status-completed">LIVE</span>
                  </div>

                  <div className="yt-card-body">
                    <h3 className="yt-card-title">{vid.title}</h3>
                    <p className="text-muted" style={{ fontSize: '0.825rem', marginBottom: '0.75rem' }}>
                      Published: {vid.published_at ? new Date(vid.published_at).toLocaleDateString() : 'Recent'}
                    </p>

                    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem' }}>
                      <span className="yt-stat-pill"><Eye size={14} /> {vid.views.toLocaleString()}</span>
                      <span className="yt-stat-pill"><ThumbsUp size={14} /> {vid.likes.toLocaleString()}</span>
                      <span className="yt-stat-pill"><MessageSquare size={14} /> {vid.comments.toLocaleString()}</span>
                    </div>

                    <div className="yt-card-actions">
                      <a href={vid.watch_url} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                        <ExternalLink size={14} /> Open on YouTube
                      </a>
                      <button className="btn btn-secondary btn-sm" title="Copy Link" onClick={() => copyToClipboard(vid.watch_url)}>
                        <Copy size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Automation Rules */}
      {activeTab === 'rules' && (
        <div className="yt-rules-panel">
          <div className="yt-rule-item">
            <div>
              <h3 style={{ margin: '0 0 0.25rem 0' }}>Auto-Publish on Generation Complete</h3>
              <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
                Automatically optimize metadata with AI and schedule or publish finished course videos immediately.
              </p>
            </div>
            <input 
              type="checkbox" 
              checked={autoPublishEnabled} 
              onChange={e => setAutoPublishEnabled(e.target.checked)} 
              style={{ width: '20px', height: '20px', cursor: 'pointer' }}
            />
          </div>

          <div className="yt-rule-item">
            <div>
              <h3 style={{ margin: '0 0 0.25rem 0' }}>Default Privacy Setting</h3>
              <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
                Choose the default visibility applied to automatically published videos.
              </p>
            </div>
            <select className="input-field" style={{ width: '180px' }} value={defaultPrivacy} onChange={e => setDefaultPrivacy(e.target.value)}>
              <option value="private">Private (Recommended)</option>
              <option value="unlisted">Unlisted</option>
              <option value="public">Public</option>
            </select>
          </div>

          <div className="yt-rule-item">
            <div>
              <h3 style={{ margin: '0 0 0.25rem 0' }}>Default Category</h3>
              <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
                Target category for YouTube indexing.
              </p>
            </div>
            <select className="input-field" style={{ width: '220px' }} value={defaultCategory} onChange={e => setDefaultCategory(e.target.value)}>
              <option value="27">Education (27)</option>
              <option value="28">Science & Technology (28)</option>
              <option value="22">People & Blogs (22)</option>
              <option value="24">Entertainment (24)</option>
            </select>
          </div>

          <div className="yt-rule-item">
            <div>
              <h3 style={{ margin: '0 0 0.25rem 0' }}>Scheduling Mode</h3>
              <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
                Local Queue uploads at target time; Native sets publishAt directly on YouTube API.
              </p>
            </div>
            <select className="input-field" style={{ width: '220px' }} value={defaultScheduleMode} onChange={e => setDefaultScheduleMode(e.target.value)}>
              <option value="local">AutoCourse Local Queue</option>
              <option value="native">Native YouTube Scheduling</option>
            </select>
          </div>
        </div>
      )}

      {/* Publish & Schedule Modal Dialog */}
      {showModal && (
        <div className="yt-modal-backdrop">
          <div className="yt-modal-dialog">
            <div className="yt-modal-header">
              <h2><UploadCloud size={20} color="#ff4d4d" /> Publish & Schedule to YouTube</h2>
              <button className="icon-btn" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>

            <div className="yt-modal-body">
              {errorMessage && (
                <div style={{ padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '8px', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                  <AlertCircle size={16} /> {errorMessage}
                </div>
              )}

              {/* Video Selection */}
              <div className="form-group">
                <label>Select Generated Course Video</label>
                <select 
                  className="input-field" 
                  value={selectedJobId} 
                  onChange={e => {
                    setSelectedJobId(e.target.value);
                    const j = completedJobs.find(x => x.job_id === e.target.value);
                    if (j) {
                      setModalTitle(j.request?.topic || 'AutoCourse Video');
                    }
                  }}
                >
                  {completedJobs.map(job => (
                    <option key={job.job_id} value={job.job_id}>
                      {job.request?.topic || 'AutoCourse Video'} ({job.job_id})
                    </option>
                  ))}
                </select>
              </div>

              {/* AI Optimizer Card */}
              <div className="yt-ai-optimize-banner">
                <div>
                  <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#c084fc' }}>
                    <Sparkles size={16} /> AI Viral SEO Optimizer
                  </div>
                  <span style={{ fontSize: '0.8rem', color: '#d8b4fe' }}>
                    Generate high-CTR title variations, SEO chapter description, and ranking tags.
                  </span>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={() => handleAIOptimize()} disabled={isOptimizing}>
                  {isOptimizing ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {isOptimizing ? 'Optimizing...' : 'Re-Generate with AI'}
                </button>
              </div>

              {/* AI Title Selection */}
              {titleChoices.length > 0 && (
                <div className="form-group">
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>AI Title Suggestions (Click to Apply)</label>
                  <div className="yt-title-choices">
                    {titleChoices.map((t, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className={`yt-title-chip ${modalTitle === t ? 'selected' : ''}`}
                        onClick={() => setModalTitle(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Title Field */}
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <label>Video Title</label>
                  <span style={{ fontSize: '0.75rem', color: modalTitle.length > 95 ? '#ef4444' : 'var(--text-muted)' }}>
                    {modalTitle.length}/100
                  </span>
                </div>
                <input 
                  type="text" 
                  className="input-field" 
                  value={modalTitle} 
                  onChange={e => setModalTitle(e.target.value)} 
                  maxLength={100}
                />
              </div>

              {/* Description */}
              <div className="form-group">
                <label>SEO Description & Chapters</label>
                <textarea 
                  className="input-field" 
                  rows={6} 
                  value={modalDescription} 
                  onChange={e => setModalDescription(e.target.value)}
                />
              </div>

              {/* Tags Manager */}
              <div className="form-group">
                <label>Search Tags</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input 
                    type="text" 
                    className="input-field" 
                    placeholder="Add tag (e.g. Data Structures)..." 
                    value={tagInput}
                    onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); } }}
                  />
                  <button type="button" className="btn btn-secondary" onClick={handleAddTag}>Add</button>
                </div>
                <div className="yt-tags-container">
                  {modalTags.map(tag => (
                    <span key={tag} className="yt-tag-pill">
                      #{tag}
                      <span className="yt-tag-remove" onClick={() => handleRemoveTag(tag)}>&times;</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Privacy & Scheduling Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label>Privacy Visibility</label>
                  <select className="input-field" value={modalPrivacy} onChange={e => setModalPrivacy(e.target.value)}>
                    <option value="private">Private (Default)</option>
                    <option value="unlisted">Unlisted</option>
                    <option value="public">Public</option>
                    <option value="scheduled">Schedule for Later</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>YouTube Category</label>
                  <select className="input-field" value={modalCategory} onChange={e => setModalCategory(e.target.value)}>
                    <option value="27">Education (27)</option>
                    <option value="28">Science & Technology (28)</option>
                    <option value="22">People & Blogs (22)</option>
                  </select>
                </div>
              </div>

              {/* Schedule Date & Time Picker */}
              {modalPrivacy === 'scheduled' && (
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label>Publication Date</label>
                      <input 
                        type="date" 
                        className="input-field" 
                        value={modalScheduleDate} 
                        onChange={e => setModalScheduleDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                      />
                    </div>
                    <div className="form-group">
                      <label>Publication Time</label>
                      <input 
                        type="time" 
                        className="input-field" 
                        value={modalScheduleTime} 
                        onChange={e => setModalScheduleTime(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Scheduling Mode</label>
                    <select className="input-field" value={modalScheduleMode} onChange={e => setModalScheduleMode(e.target.value)}>
                      <option value="local">AutoCourse Local Queue (Safe upload at time)</option>
                      <option value="native">Native YouTube Scheduled (Uploads now as scheduled private)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Custom Thumbnail Picker */}
              <div className="form-group">
                <label>Video Thumbnail</label>
                <div className="yt-thumbnail-picker">
                  {modalThumbnail ? (
                    <img src={`/api/download?path=${encodeURIComponent(modalThumbnail)}`} alt="Thumbnail" className="yt-thumb-preview" />
                  ) : (
                    <div className="yt-thumb-preview" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.05)' }}>
                      <ImageIcon size={24} style={{ opacity: 0.4 }} />
                    </div>
                  )}
                  <div>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      style={{ display: 'none' }} 
                      accept="image/*" 
                      onChange={handleThumbnailUpload} 
                    />
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => fileInputRef.current?.click()}>
                      <ImageIcon size={14} /> Upload Custom Thumbnail
                    </button>
                    <p className="text-muted" style={{ fontSize: '0.75rem', marginTop: '0.35rem' }}>
                      Recommended: 1280x720 JPG or PNG (under 2MB).
                    </p>
                  </div>
                </div>
              </div>

              {/* Upload Progress */}
              {isPublishing && (
                <div className="yt-progress-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Publishing to YouTube...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="yt-progress-bar-bg">
                    <div className="yt-progress-bar-fill" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                </div>
              )}
            </div>

            <div className="yt-modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)} disabled={isPublishing}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleSubmitPublish} disabled={isPublishing}>
                {isPublishing ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" /> Publishing...
                  </>
                ) : (
                  modalPrivacy === 'scheduled' ? 'Schedule Publication' : 'Publish to YouTube Now'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
