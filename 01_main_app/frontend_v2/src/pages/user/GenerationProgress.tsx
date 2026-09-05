import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, XCircle, FileVideo, Terminal } from 'lucide-react';
import HumanInTheLoopReview from '../../components/HumanInTheLoopReview';
import './GenerationProgress.css';

interface JobData {
  job_id: string;
  status: string;
  message: string;
  progress_percentage: number;
  current_task: string;
  current_model: string;
  files: Record<string, any>;
  request: any;
}

export default function GenerationProgress() {
  const [searchParams] = useSearchParams();
  const urlJobId = searchParams.get('jobId');
  const jobId = urlJobId || localStorage.getItem('lastAutoCourseJobId');

  const [job, setJob] = useState<JobData | null>(null);
  const [logs, setLogs] = useState<{time: string, msg: string}[]>([]);

  useEffect(() => {
    if (urlJobId) {
      localStorage.setItem('lastAutoCourseJobId', urlJobId);
    }
  }, [urlJobId]);

  useEffect(() => {
    if (!jobId) return;

    setLogs([{ time: new Date().toLocaleTimeString(), msg: `Connecting to job stream for ${jobId}...` }]);

    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    eventSource.onmessage = (e) => {
      try {
        const data: JobData = JSON.parse(e.data);
        setJob(prev => {
          if (!prev || prev.message !== data.message) {
            if (data.message) {
              setLogs(l => [...l, { time: new Date().toLocaleTimeString(), msg: data.message }]);
            }
          }
          return data;
        });

        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          eventSource.close();
          if (data.status === 'completed') {
            setLogs(l => [...l, { time: new Date().toLocaleTimeString(), msg: "Generation completed successfully." }]);
          }
        }
      } catch (err) {
        console.error("Failed to parse SSE data", err);
      }
    };

    eventSource.onerror = (e) => {
      console.error("EventSource failed", e);
      setLogs(l => [...l, { time: new Date().toLocaleTimeString(), msg: "Lost connection to server stream." }]);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  const handleDownload = () => {
    if (!job) return;
    const path = job.files?.final_video || job.files?.videos?.[0];
    if (path) {
      const rawTopic = job.request?.topic || job.request?.syllabus_subject || 'course_video';
      const cleanTopic = rawTopic.replace(/[^a-zA-Z0-9_\-\s]/g, '').trim().replace(/\s+/g, '_') || 'course_video';
      const filename = `${cleanTopic}.mp4`;
      const downloadUrl = `/api/jobs/${job.job_id}/download/${encodeURIComponent(filename)}`;

      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      alert("No final video file path found in job output. The video may still be processing.");
    }
  };

  const cancelJob = async () => {
    if (!jobId) return;
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    } catch (e) {
      alert("Failed to cancel job.");
    }
  };

  if (!jobId) {
    return (
      <div className="progress-page">
        <div className="progress-header">
          <h1>No Job Specified</h1>
          <p className="text-muted">Please start a new generation from the Create Video page.</p>
        </div>
      </div>
    );
  }

  const status = job?.status || 'queued';
  const progress = job?.progress_percentage || 0;
  const requestTopic = job?.request?.topic;
  let displayTopic = requestTopic || "Batch Generation (Full Course)";
  if (displayTopic.toLowerCase().startsWith("batch:")) {
    displayTopic = "Batch Mode: " + displayTopic.substring(6);
  }
  
  return (
    <div className="progress-page">
      <div className="progress-header">
        <h1>Generation Progress</h1>
        <p className="text-muted">Live pipeline tracking for "{displayTopic}"</p>
      </div>

      <div className="progress-container card glass-panel">
        <div className="progress-circle-container">
          <div className={`progress-circle ${status}`}>
            {status === 'completed' ? <CheckCircle2 size={48} /> : 
             (status === 'failed' || status === 'cancelled') ? <XCircle size={48} /> : 
             <span className="progress-percentage">{progress}%</span>}
          </div>
          <h2>{status.charAt(0).toUpperCase() + status.slice(1)}</h2>
          <p className="text-muted">
            {status === 'completed' ? 'Video is ready to download.' : 
             (status === 'failed' || status === 'cancelled') ? 'Job stopped.' :
             job?.current_task ? `Current Task: ${job.current_task}` : 'Please wait while AI generates your video.'}
          </p>
        </div>

        <div className="pipeline-steps">
          <div className={`step ${progress > 0 || status !== 'queued' ? 'active' : ''}`}>
            <div className="step-indicator">1</div>
            <div className="step-content">
              <h4>Planning</h4>
              <p>{job?.current_model || 'LLM Planner'}</p>
            </div>
          </div>
          <div className={`step-connector ${progress >= 30 || status === 'awaiting_approval' ? 'active' : ''}`}></div>
          <div className={`step ${status === 'awaiting_approval' ? 'active pulse-amber' : (progress >= 35 ? 'active' : '')}`}>
            <div className="step-indicator">2</div>
            <div className="step-content">
              <h4>HITL Review</h4>
              <p>{status === 'awaiting_approval' ? 'Action Required' : 'Approved'}</p>
            </div>
          </div>
          <div className={`step-connector ${progress >= 50 ? 'active' : ''}`}></div>
          <div className={`step ${progress >= 50 ? 'active' : ''}`}>
            <div className="step-indicator">3</div>
            <div className="step-content">
              <h4>Rendering</h4>
              <p>Visual Engine</p>
            </div>
          </div>
          <div className={`step-connector ${progress >= 75 ? 'active' : ''}`}></div>
          <div className={`step ${progress >= 75 ? 'active' : ''}`}>
            <div className="step-indicator">4</div>
            <div className="step-content">
              <h4>Assembling</h4>
              <p>MPT / Direct Mux</p>
            </div>
          </div>
        </div>

        {/* Human-in-the-Loop Approval & Review Gate */}
        {status === 'awaiting_approval' && job && (
          <HumanInTheLoopReview 
            jobId={jobId}
            files={job.files || {}}
            onApproved={() => {
              setLogs(l => [...l, { time: new Date().toLocaleTimeString(), msg: "Human approval registered. Starting video rendering & assembly..." }]);
            }}
            onCancelled={() => {
              setLogs(l => [...l, { time: new Date().toLocaleTimeString(), msg: "Job cancelled by reviewer." }]);
            }}
          />
        )}

        <div className="progress-actions">
          {status === 'completed' ? (
            <button className="btn btn-primary btn-lg" onClick={handleDownload} disabled={!job?.files?.final_video && !job?.files?.videos?.[0]}>
              <FileVideo size={20} />
              Download Final MP4
            </button>
          ) : (status !== 'failed' && status !== 'cancelled' && status !== 'awaiting_approval') ? (
            <button className="btn btn-outline btn-lg text-danger" onClick={cancelJob}>
              Cancel Job
            </button>
          ) : null}
        </div>
      </div>

      <div className="logs-container card">
        <div className="logs-header">
          <Terminal size={18} />
          <h3>Live Logs</h3>
        </div>
        <div className="logs-content">
          {logs.map((log, i) => (
            <div key={i} className="log-line">
              <span className="log-time">{log.time}</span>
              <span className="log-msg">{log.msg}</span>
            </div>
          ))}
          {status !== 'completed' && status !== 'failed' && status !== 'cancelled' && (
             <div className="log-line animate-pulse">
               <span className="log-msg text-primary">_</span>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
