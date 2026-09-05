import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Play, 
  Download, 
  Search, 
  Share2, 
  RefreshCw, 
  X, 
  Film, 
  CheckCircle2, 
  Calendar, 
  ExternalLink, 
  Plus,
  Tv
} from 'lucide-react';
import { fetchCurrentUser } from '../../utils/userSession';
import './MyVideos.css';

interface JobSummary {
  job_id: string;
  status: string;
  request: any;
  files: Record<string, any>;
  created_at?: string;
  youtube_video_id?: string;
  youtube_url?: string;
}

export default function MyVideos() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState<'all' | '16:9' | '9:16' | 'youtube'>('all');
  const [previewVideoJob, setPreviewVideoJob] = useState<JobSummary | null>(null);
  const [feedbackJobId, setFeedbackJobId] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [brokenThumbs, setBrokenThumbs] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchCurrentUser()
      .then(user => fetch(`/api/jobs?user_id=${encodeURIComponent(user.username)}`))
      .then(res => res.json())
      .then(data => {
        const arr = Object.values(data) as JobSummary[];
        // Filter jobs that completed and have a video file
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

  const handleDownload = (video: JobSummary) => {
    const rawTopic = video.request?.topic || video.request?.syllabus_subject || 'course_video';
    const cleanTopic = rawTopic.replace(/[^a-zA-Z0-9_\-\s]/g, '').trim().replace(/\s+/g, '_') || 'course_video';
    const filename = `${cleanTopic}.mp4`;
    const downloadUrl = `/api/jobs/${video.job_id}/download/${encodeURIComponent(filename)}`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
      alert('Job queued for regeneration with Maestro planner!');
      setFeedbackJobId(null);
      setFeedbackText("");
    } catch (err) {
      alert('Failed to regenerate: ' + err);
    }
    setActionLoading(null);
  };

  const handlePublishRedirect = (jobId: string) => {
    navigate(`/user/publisher?jobId=${jobId}`);
  };

  // Filter and search logic
  const filteredJobs = useMemo(() => {
    return jobs.filter(job => {
      const topic = (job.request?.topic || job.request?.syllabus_subject || '').toLowerCase();
      const mode = (job.request?.mode || '').toLowerCase();
      const jobId = job.job_id.toLowerCase();
      const q = searchQuery.toLowerCase().trim();

      if (q && !topic.includes(q) && !mode.includes(q) && !jobId.includes(q)) {
        return false;
      }

      const aspect = job.request?.aspect || '16:9';
      if (filterMode === '16:9' && aspect !== '16:9') return false;
      if (filterMode === '9:16' && aspect !== '9:16') return false;
      if (filterMode === 'youtube' && !job.youtube_video_id) return false;

      return true;
    });
  }, [jobs, searchQuery, filterMode]);

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return 'Recently';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return 'Recently';
    }
  };

  const getFormatLabel = (job: JobSummary) => {
    const aspect = job.request?.aspect;
    if (aspect === '9:16') return '9:16 Shorts';
    return '16:9 HD Course';
  };

  const getModeLabel = (job: JobSummary) => {
    const m = job.request?.mode || 'course';
    const style = job.request?.visual_style || '';
    if (m === 'manual_course') return 'Manim Course';
    if (m === 'autonomous') return style === 'pexels' ? 'Pexels B-Roll' : 'Autonomous';
    if (m === 'story') return 'AI Story';
    return 'Orchestrated';
  };

  return (
    <div className="videos-page-wrapper">
      {/* Top Header Section */}
      <div className="videos-header-area">
        <div className="videos-title-block">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 className="videos-main-title">My Videos</h1>
            <span className="videos-counter-tag">{jobs.length} Generated</span>
          </div>
          <p className="videos-sub-desc">
            Manage, stream, export, and publish your AI-orchestrated courses and productions.
          </p>
        </div>

        <button className="create-video-hero-btn" onClick={() => navigate('/user/create')}>
          <Plus size={18} />
          Create New Video
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="videos-toolbar-ribbon">
        <div className="videos-search-container">
          <Search size={17} className="search-icon-field" />
          <input 
            type="text" 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search videos by topic, concept, or mode..." 
            className="videos-search-input"
          />
          {searchQuery && (
            <button className="search-clear-btn" onClick={() => setSearchQuery('')}>
              <X size={15} />
            </button>
          )}
        </div>

        <div className="videos-filter-chips">
          <button 
            className={`filter-chip ${filterMode === 'all' ? 'active' : ''}`}
            onClick={() => setFilterMode('all')}
          >
            All Videos ({jobs.length})
          </button>
          <button 
            className={`filter-chip ${filterMode === '16:9' ? 'active' : ''}`}
            onClick={() => setFilterMode('16:9')}
          >
            16:9 Landscape
          </button>
          <button 
            className={`filter-chip ${filterMode === '9:16' ? 'active' : ''}`}
            onClick={() => setFilterMode('9:16')}
          >
            9:16 Shorts
          </button>
          <button 
            className={`filter-chip ${filterMode === 'youtube' ? 'active' : ''}`}
            onClick={() => setFilterMode('youtube')}
          >
            <Share2 size={13} style={{ marginRight: 4 }} />
            On YouTube
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="videos-state-panel">
          <div className="loader-spinner" />
          <p>Loading your generated library from Maestro store...</p>
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="videos-state-panel empty-state">
          <div className="empty-state-icon">
            <Film size={44} strokeWidth={1.5} />
          </div>
          <h3>{searchQuery ? 'No matching videos found' : 'No generated videos yet'}</h3>
          <p>
            {searchQuery 
              ? `We couldn't find any courses matching "${searchQuery}". Try a different keyword.` 
              : 'Assemble your first AI-orchestrated course using Manim or Pexels footage.'}
          </p>
          {searchQuery ? (
            <button className="btn btn-secondary" onClick={() => setSearchQuery('')}>
              Clear Search Filter
            </button>
          ) : (
            <button className="create-video-hero-btn" onClick={() => navigate('/user/create')}>
              <Plus size={16} />
              Assemble Your First Course
            </button>
          )}
        </div>
      ) : (
        <div className="videos-gallery-grid">
          {filteredJobs.map(video => {
            const hasError = brokenThumbs[video.job_id];
            const topic = video.request?.topic || video.request?.syllabus_subject || "AutoCourse Masterclass";
            const isShort = video.request?.aspect === '9:16';

            return (
              <div key={video.job_id} className="video-card-enterprise">
                {/* Thumbnail Container */}
                <div 
                  className={`video-thumb-container ${isShort ? 'aspect-short' : 'aspect-landscape'}`}
                  onClick={() => setPreviewVideoJob(video)}
                >
                  {!hasError ? (
                    <img 
                      src={`/api/jobs/${video.job_id}/thumbnail`}
                      alt={topic}
                      className="video-thumb-image"
                      onError={() => setBrokenThumbs(prev => ({ ...prev, [video.job_id]: true }))}
                    />
                  ) : (
                    <div className="video-thumb-fallback">
                      <Tv size={36} className="fallback-icon" />
                      <span className="fallback-topic">{topic}</span>
                    </div>
                  )}

                  {/* Badges on Thumbnail */}
                  <div className="thumb-badge-top-left">
                    {video.youtube_video_id ? (
                      <span className="thumb-badge badge-youtube">
                        <Share2 size={11} /> ON YOUTUBE
                      </span>
                    ) : (
                      <span className="thumb-badge badge-mode">
                        {getModeLabel(video)}
                      </span>
                    )}
                  </div>

                  <div className="thumb-badge-top-right">
                    <span className="thumb-badge badge-aspect">
                      {getFormatLabel(video)}
                    </span>
                  </div>

                  <div className="thumb-badge-bottom-right">
                    <span className="thumb-badge badge-ready">
                      <CheckCircle2 size={11} /> Ready
                    </span>
                  </div>

                  {/* Hover Play Button Overlay */}
                  <div className="video-hover-overlay">
                    <button 
                      className="hover-play-trigger"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewVideoJob(video);
                      }}
                      title="Watch Preview"
                    >
                      <Play size={24} fill="#FFFFFF" color="#FFFFFF" />
                    </button>
                    <span className="hover-play-label">Watch Preview</span>
                  </div>
                </div>

                {/* Card Information Body */}
                <div className="video-card-body">
                  <div className="video-card-title-row">
                    <h3 className="video-card-title" title={topic}>
                      {topic}
                    </h3>
                  </div>

                  <div className="video-card-meta-chips">
                    <span className="meta-chip">
                      <Calendar size={12} />
                      {formatDate(video.created_at)}
                    </span>
                    <span className="meta-chip-mode">
                      {video.request?.visual_style || 'manim_course'}
                    </span>
                  </div>

                  {/* Primary & Secondary Action Buttons */}
                  <div className="video-card-actions">
                    {/* Primary Button: Watch Preview */}
                    <button 
                      className="action-btn-primary"
                      onClick={() => setPreviewVideoJob(video)}
                    >
                      <Play size={15} fill="currentColor" />
                      Watch Preview
                    </button>

                    {/* Secondary Row: Download + Publish */}
                    <div className="action-row-split">
                      <button 
                        className="action-btn-secondary"
                        onClick={() => handleDownload(video)}
                        title="Download rendered MP4 video"
                      >
                        <Download size={14} />
                        Export MP4
                      </button>

                      {video.youtube_video_id ? (
                        <a 
                          href={video.youtube_url || `https://www.youtube.com/watch?v=${video.youtube_video_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="action-btn-youtube"
                          title="Watch on YouTube"
                        >
                          <ExternalLink size={13} />
                          YouTube
                        </a>
                      ) : (
                        <button 
                          className="action-btn-secondary"
                          onClick={() => handlePublishRedirect(video.job_id)}
                          title="Publish or schedule video to YouTube Studio"
                        >
                          <Share2 size={13} />
                          Publish
                        </button>
                      )}
                    </div>

                    {/* Tertiary Button: Regenerate / Fix */}
                    <button 
                      className="action-btn-tertiary"
                      onClick={() => setFeedbackJobId(video.job_id)}
                    >
                      <RefreshCw size={13} />
                      Regenerate / Fix
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* In-Browser Video Theater Player Modal */}
      {previewVideoJob && (
        <div className="theater-modal-backdrop" onClick={() => setPreviewVideoJob(null)}>
          <div className="theater-modal-window" onClick={e => e.stopPropagation()}>
            <div className="theater-modal-header">
              <div className="theater-header-info">
                <span className="theater-badge-tag">MAESTRO PLAYER</span>
                <h2 className="theater-video-title">
                  {previewVideoJob.request?.topic || "Generated Video Preview"}
                </h2>
              </div>
              <button 
                className="theater-close-btn"
                onClick={() => setPreviewVideoJob(null)}
                title="Close Player"
              >
                <X size={20} />
              </button>
            </div>

            <div className="theater-video-frame">
              <video 
                src={`/api/jobs/${previewVideoJob.job_id}/video`}
                controls
                autoPlay
                className="theater-video-element"
              />
            </div>

            <div className="theater-modal-footer">
              <div className="theater-footer-meta">
                <span><strong>Job ID:</strong> {previewVideoJob.job_id}</span>
                <span><strong>Mode:</strong> {previewVideoJob.request?.mode || 'autonomous'}</span>
                <span><strong>Aspect:</strong> {previewVideoJob.request?.aspect || '16:9'}</span>
              </div>

              <div className="theater-footer-actions">
                <button 
                  className="btn btn-secondary"
                  onClick={() => handleDownload(previewVideoJob)}
                >
                  <Download size={15} />
                  Download MP4
                </button>
                <button 
                  className="btn btn-primary"
                  onClick={() => {
                    const id = previewVideoJob.job_id;
                    setPreviewVideoJob(null);
                    handlePublishRedirect(id);
                  }}
                >
                  <Share2 size={15} />
                  YouTube Studio
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Regeneration Modal */}
      {feedbackJobId && (
        <div className="modal-backdrop-custom" onClick={() => setFeedbackJobId(null)}>
          <div className="feedback-modal-card" onClick={e => e.stopPropagation()}>
            <div className="feedback-modal-header">
              <div>
                <h2>Regenerate Video</h2>
                <p>Submit instructor feedback to have Maestro agents refine script & scenes.</p>
              </div>
              <button className="theater-close-btn" onClick={() => setFeedbackJobId(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="feedback-modal-body">
              <label>What adjustments should the agents make?</label>
              <textarea 
                value={feedbackText} 
                onChange={e => setFeedbackText(e.target.value)}
                placeholder="e.g. Simplify slide 2 diagrams, make narration more energetic, remove the summary scene..."
                rows={4}
                className="feedback-textarea"
              />

              <div className="feedback-quick-pills">
                <span onClick={() => setFeedbackText("Make the technical explanation simpler and slower paced.")}>
                  Simpler pace
                </span>
                <span onClick={() => setFeedbackText("Change visual color theme to vibrant dark mode.")}>
                  Vibrant theme
                </span>
                <span onClick={() => setFeedbackText("Add more concrete code walkthrough examples.")}>
                  More examples
                </span>
              </div>
            </div>

            <div className="feedback-modal-footer">
              <button 
                className="btn btn-secondary"
                onClick={() => setFeedbackJobId(null)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={() => handleRegenerate(feedbackJobId)}
                disabled={actionLoading === feedbackJobId || !feedbackText.trim()}
              >
                {actionLoading === feedbackJobId ? (
                  <>
                    <RefreshCw size={15} className="spin-icon" />
                    Queueing Agents...
                  </>
                ) : (
                  <>
                    <RefreshCw size={15} />
                    Regenerate with Maestro
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
