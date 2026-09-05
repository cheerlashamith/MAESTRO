import { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  RotateCcw, 
  XCircle, 
  Edit3, 
  Mic, 
  Sparkles, 
  Clock, 
  Layers,
  Send
} from 'lucide-react';
import './HumanInTheLoopReview.css';

interface Scene {
  title: string;
  narration?: string;
  bullets?: string[];
  diagram_type?: string;
}

interface HumanInTheLoopReviewProps {
  jobId: string;
  files: Record<string, any>;
  onApproved?: () => void;
  onCancelled?: () => void;
}

export default function HumanInTheLoopReview({
  jobId,
  files,
  onApproved,
  onCancelled
}: HumanInTheLoopReviewProps) {
  const initialScript = files?.script_preview || files?.moneyprinter_script || '';
  const scenes: Scene[] = files?.scenes_preview || files?.scenes || [];
  const subject = files?.subject_preview || files?.subject || 'Course Topic';

  const [script, setScript] = useState<string>(initialScript);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRevisionBox, setShowRevisionBox] = useState(false);
  const [revisionFeedback, setRevisionFeedback] = useState('');
  const [activeTab, setActiveTab] = useState<'script' | 'scenes'>('script');

  useEffect(() => {
    if (initialScript && !script) {
      setScript(initialScript);
    }
  }, [initialScript]);

  // Calculate word count & estimated voiceover runtime
  const words = script.trim() ? script.trim().split(/\s+/).length : 0;
  const estimatedSeconds = Math.round((words / 140) * 60);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'approve',
          script_override: script
        })
      });
      const data = await res.json();
      if (data.ok) {
        if (onApproved) onApproved();
      } else {
        alert('Could not submit approval: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      alert('Network error while approving: ' + err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestRevision = async () => {
    if (!revisionFeedback.trim()) {
      alert('Please enter revision feedback or instructions for the AI.');
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'revise',
          feedback: revisionFeedback
        })
      });
      const data = await res.json();
      if (data.ok) {
        setShowRevisionBox(false);
        setRevisionFeedback('');
      } else {
        alert('Could not request revision: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      alert('Network error: ' + err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!window.confirm('Are you sure you want to cancel this video generation?')) return;
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reject' })
      });
      const data = await res.json();
      if (data.ok && onCancelled) onCancelled();
    } catch (err) {
      alert('Network error: ' + err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="hitl-container glass-panel animate-fade-in">
      <div className="hitl-header">
        <div className="hitl-badge">
          <span className="pulse-dot"></span>
          <span>HUMAN-IN-THE-LOOP INTERVENTION GATE</span>
        </div>
        <h2 className="hitl-title">Review & Approve Video Blueprint</h2>
        <p className="hitl-subtitle">
          The AI planner has constructed the video script and visual scenes for <strong>"{subject}"</strong>.
          Inspect the voiceover or make direct live edits below before video rendering starts.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="hitl-tabs">
        <button 
          className={`hitl-tab-btn ${activeTab === 'script' ? 'active' : ''}`}
          onClick={() => setActiveTab('script')}
        >
          <Edit3 size={16} />
          <span>Voiceover Narration Script</span>
          <span className="tab-pill">{words} words</span>
        </button>
        <button 
          className={`hitl-tab-btn ${activeTab === 'scenes' ? 'active' : ''}`}
          onClick={() => setActiveTab('scenes')}
        >
          <Layers size={16} />
          <span>Visual Scenes & Cues</span>
          <span className="tab-pill">{scenes.length} scenes</span>
        </button>
      </div>

      {/* Tab 1: Editable Script */}
      {activeTab === 'script' && (
        <div className="hitl-tab-content">
          <div className="script-meta-bar">
            <span className="meta-info">
              <Clock size={15} />
              Estimated Duration: <strong>~{estimatedSeconds}s</strong> ({Math.round(estimatedSeconds / 60 * 10) / 10} min)
            </span>
            <span className="meta-info">
              <Mic size={15} />
              Engine: <strong>Edge-TTS Neural Synthesizer</strong>
            </span>
            <span className="meta-hint">
              <Sparkles size={14} /> Feel free to edit words, tweak phrasing, or add pauses directly.
            </span>
          </div>

          <div className="script-editor-wrapper">
            <textarea
              className="hitl-textarea"
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder="Script preview is loading..."
              rows={9}
              disabled={isSubmitting}
            />
          </div>
        </div>
      )}

      {/* Tab 2: Scene Outline */}
      {activeTab === 'scenes' && (
        <div className="hitl-tab-content scenes-grid">
          {scenes.map((sc, i) => (
            <div key={i} className="scene-card">
              <div className="scene-card-header">
                <span className="scene-number">SCENE #{i + 1}</span>
                <span className="diagram-tag">
                  {sc.diagram_type ? sc.diagram_type.toUpperCase() : 'VISUAL CUE'}
                </span>
              </div>
              <h4 className="scene-card-title">{sc.title || `Scene ${i + 1}`}</h4>
              {sc.bullets && sc.bullets.length > 0 && (
                <ul className="scene-bullets">
                  {sc.bullets.map((b, bIdx) => (
                    <li key={bIdx}>{b}</li>
                  ))}
                </ul>
              )}
              {sc.narration && (
                <p className="scene-narration-snippet">
                  <em>"{sc.narration}"</em>
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Revision Drawer */}
      {showRevisionBox && (
        <div className="revision-drawer">
          <div className="revision-header">
            <Sparkles size={16} className="text-primary" />
            <h4>Prompt AI Revision</h4>
          </div>
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>
            Instruct the AI to rewrite or re-angle the script (e.g. "make the introduction shorter", "explain with a banking analogy").
          </p>
          <textarea
            className="hitl-textarea revision-textarea"
            placeholder="Enter revision instructions for the AI..."
            value={revisionFeedback}
            onChange={(e) => setRevisionFeedback(e.target.value)}
            rows={3}
          />
          <div className="revision-actions">
            <button 
              className="btn btn-outline"
              onClick={() => setShowRevisionBox(false)}
            >
              Cancel
            </button>
            <button 
              className="btn btn-primary"
              onClick={handleRequestRevision}
              disabled={isSubmitting}
            >
              <Send size={15} />
              {isSubmitting ? 'Regenerating...' : 'Submit Revision Prompt'}
            </button>
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="hitl-footer">
        <div className="footer-left">
          <button 
            className="btn btn-outline hitl-btn-cancel"
            onClick={handleReject}
            disabled={isSubmitting}
          >
            <XCircle size={17} />
            <span>Cancel Job</span>
          </button>
          {!showRevisionBox && (
            <button 
              className="btn btn-outline hitl-btn-revise"
              onClick={() => setShowRevisionBox(true)}
              disabled={isSubmitting}
            >
              <RotateCcw size={17} />
              <span>Request AI Revision</span>
            </button>
          )}
        </div>

        <div className="footer-right">
          <button 
            className="btn btn-primary hitl-btn-approve"
            onClick={handleApprove}
            disabled={isSubmitting}
          >
            <CheckCircle2 size={18} />
            <span>{isSubmitting ? 'Processing Approval...' : 'Approve & Proceed to Video Render'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
