import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Sparkles, 
  CheckCircle2, 
  Download, 
  Share2, 
  Layers, 
  Brain, 
  Code2, 
  Wand2, 
  Film, 
  Mic, 
  ArrowRight,
  RefreshCw,
  Sliders,
  ChevronRight
} from 'lucide-react';
import HumanInTheLoopReview from '../../components/HumanInTheLoopReview';
import './StudioWorkflowPage.css';

interface NodeConfig {
  id: string;
  node_type_id: string;
  label: string;
  position_x: number;
  position_y: number;
  config: Record<string, any>;
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  status: string;
  version: string;
  nodes: NodeConfig[];
  edges: WorkflowEdge[];
}

export default function StudioWorkflowPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeConfig | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [topicInput, setTopicInput] = useState('');
  const [autoPublish, setAutoPublish] = useState(false);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      const res = await fetch('/api/studio/workflows');
      const data = await res.json();
      if (data.workflows && data.workflows.length > 0) {
        setWorkflows(data.workflows);
        setActiveWorkflow(data.workflows[0]);
        // Default topic from first workflow's input node
        const inputNode = data.workflows[0].nodes.find((n: NodeConfig) => n.node_type_id === 'nt-input');
        if (inputNode && inputNode.config.topic) {
          setTopicInput(inputNode.config.topic);
        }
      }
      setLoading(false);
    } catch (err) {
      console.error('Failed to load workflows', err);
      setLoading(false);
    }
  };

  const handleSelectWorkflow = (wf: Workflow) => {
    setActiveWorkflow(wf);
    setSelectedNode(null);
    const inputNode = wf.nodes.find(n => n.node_type_id === 'nt-input');
    if (inputNode && inputNode.config.topic) {
      setTopicInput(inputNode.config.topic);
    }
  };

  const handleRunWorkflow = async () => {
    if (!activeWorkflow) return;
    setIsRunning(true);
    setJobStatus(null);
    setActiveStepIndex(0);

    try {
      const res = await fetch(`/api/studio/workflows/${activeWorkflow.id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topicInput,
          auto_publish: autoPublish,
        })
      });
      const data = await res.json();
      if (data.job_id) {
        setActiveJobId(data.job_id);
        listenToJobStream(data.job_id);
      } else {
        alert('Failed to start workflow run: ' + (data.error || 'Unknown error'));
        setIsRunning(false);
      }
    } catch (err) {
      alert('Error running workflow: ' + err);
      setIsRunning(false);
    }
  };

  const listenToJobStream = (jobId: string) => {
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const job = JSON.parse(event.data);
        setJobStatus(job);

        // Update active step index based on backend task
        if (job.status === 'planning') {
          setActiveStepIndex(1);
        } else if (job.status === 'rendering') {
          setActiveStepIndex(2);
        } else if (job.status === 'assembling') {
          setActiveStepIndex(4);
        } else if (job.status === 'completed') {
          setActiveStepIndex(6);
          setIsRunning(false);
          eventSource.close();
        } else if (job.status === 'failed' || job.status === 'cancelled') {
          setIsRunning(false);
          eventSource.close();
        }
      } catch (e) {
        console.error('Error parsing SSE job update', e);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };
  };

  const getNodeIcon = (typeId: string) => {
    switch (typeId) {
      case 'nt-input': return <Play size={18} className="node-icon-svg text-blue" />;
      case 'nt-planner': return <Brain size={18} className="node-icon-svg text-purple" />;
      case 'nt-manim': return <Code2 size={18} className="node-icon-svg text-emerald" />;
      case 'nt-comfyui': return <Wand2 size={18} className="node-icon-svg text-pink" />;
      case 'nt-pexels': return <Film size={18} className="node-icon-svg text-cyan" />;
      case 'nt-tts': return <Mic size={18} className="node-icon-svg text-amber" />;
      case 'nt-assembly': return <Layers size={18} className="node-icon-svg text-indigo" />;
      case 'nt-seo': return <Sparkles size={18} className="node-icon-svg text-yellow" />;
      case 'nt-publisher': return <Share2 size={18} className="node-icon-svg text-rose" />;
      default: return <Sliders size={18} />;
    }
  };

  if (loading) {
    return <div className="studio-loading"><RefreshCw className="spin" size={24} /> Loading AI Studio Canvas...</div>;
  }

  return (
    <div className="studio-container">
      {/* Studio Top Control Bar */}
      <div className="studio-topbar glass-panel">
        <div className="studio-title-block">
          <div className="studio-badge"><Sparkles size={14} /> AI STUDIO</div>
          <h2>{activeWorkflow?.name || 'Workflow Runner'}</h2>
          <span className="workflow-version-badge">v{activeWorkflow?.version || '1.0.0'}</span>
          <span className="workflow-status-pill">{activeWorkflow?.status || 'Active'}</span>
        </div>

        {/* Workflow Switcher Dropdown */}
        <div className="workflow-picker">
          <label>Template Pipeline:</label>
          <select 
            value={activeWorkflow?.id} 
            onChange={(e) => {
              const wf = workflows.find(w => w.id === e.target.value);
              if (wf) handleSelectWorkflow(wf);
            }}
            className="workflow-select"
          >
            {workflows.map(wf => (
              <option key={wf.id} value={wf.id}>{wf.name} ({wf.category})</option>
            ))}
          </select>
        </div>

        {/* Action Controls */}
        <div className="studio-actions">
          <button 
            className="btn btn-primary run-workflow-btn"
            onClick={handleRunWorkflow}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <RefreshCw className="spin" size={16} />
                <span>Executing Pipeline...</span>
              </>
            ) : (
              <>
                <Play size={16} fill="white" />
                <span>Run Entire Workflow</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Work Area */}
      <div className="studio-workspace">
        
        {/* Left / Center: Interactive Visual Workflow Canvas */}
        <div className="canvas-wrapper glass-panel">
          <div className="canvas-header">
            <span className="canvas-legend">
              <span className="dot dot-active"></span> Node Graph Active
              <span className="dot dot-trigger ml-3"></span> Automatic Flow
            </span>
            <span className="text-muted" style={{ fontSize: '0.8rem' }}>Click any node to inspect parameters & outputs</span>
          </div>

          <div className="workflow-canvas-grid">
            {/* Visual Node Sequence */}
            <div className="nodes-flow-container">
              {activeWorkflow?.nodes.map((node, index) => {
                const isCurrentActive = activeStepIndex === index && isRunning;
                const isCompleted = activeStepIndex > index;
                const isSelected = selectedNode?.id === node.id;

                return (
                  <React.Fragment key={node.id}>
                    <div 
                      className={`canvas-node ${isSelected ? 'selected' : ''} ${isCurrentActive ? 'running-pulse' : ''} ${isCompleted ? 'completed-node' : ''}`}
                      onClick={() => setSelectedNode(node)}
                    >
                      <div className="node-top">
                        <div className="node-icon-badge">{getNodeIcon(node.node_type_id)}</div>
                        <span className="node-category">{node.node_type_id.replace('nt-', '').toUpperCase()}</span>
                        {isCompleted && <CheckCircle2 size={14} className="status-icon-check" />}
                        {isCurrentActive && <RefreshCw size={14} className="status-icon-spin spin" />}
                      </div>

                      <div className="node-body">
                        <h4 className="node-label">{node.label}</h4>
                        <div className="node-meta">
                          {node.config.model && <span className="meta-tag">{node.config.model}</span>}
                          {node.config.aspect && <span className="meta-tag">{node.config.aspect}</span>}
                          {node.config.voice && <span className="meta-tag">Voice: {node.config.voice.split('-')[2] || 'Default'}</span>}
                          {node.config.resolution && <span className="meta-tag">{node.config.resolution}</span>}
                        </div>
                      </div>

                      <div className="node-footer">
                        <span className="node-id">Step #{index + 1}</span>
                        <ChevronRight size={14} className="node-arrow" />
                      </div>
                    </div>

                    {index < (activeWorkflow.nodes.length - 1) && (
                      <div className={`edge-connector ${isCompleted ? 'edge-active' : ''}`}>
                        <div className="edge-line"></div>
                        <ArrowRight size={14} className="edge-arrow" />
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Quick Trigger Bar at bottom of canvas */}
          <div className="canvas-bottom-trigger">
            <div className="quick-input-group">
              <label>Topic / Prompt Target:</label>
              <input 
                type="text" 
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder="Enter topic (e.g. Graph Algorithms, A Space Adventure, or YouTube URL)"
                className="canvas-topic-input"
              />
            </div>
            <div className="publish-toggle-group">
              <label className="checkbox-label">
                <input 
                  type="checkbox" 
                  checked={autoPublish} 
                  onChange={(e) => setAutoPublish(e.target.checked)} 
                />
                <span>Auto-Publish to YouTube after completion</span>
              </label>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Node Parameter Inspector & Live Execution Console */}
        <div className="studio-inspector glass-panel">
          {selectedNode ? (
            <div className="inspector-content">
              <div className="inspector-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {getNodeIcon(selectedNode.node_type_id)}
                  <h3>{selectedNode.label}</h3>
                </div>
                <button className="btn-close" onClick={() => setSelectedNode(null)}>×</button>
              </div>

              <div className="inspector-section">
                <h4>Node Configuration</h4>
                <div className="config-key-value">
                  {Object.entries(selectedNode.config).map(([k, v]) => (
                    <div key={k} className="config-row">
                      <span className="config-key">{k}</span>
                      <span className="config-val">{typeof v === 'boolean' ? (v ? 'Enabled' : 'Disabled') : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="inspector-section">
                <h4>Engine Status</h4>
                <div className="engine-status-box">
                  <span className="dot dot-active"></span>
                  <span>Engine Ready for Execution</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="inspector-content">
              <div className="inspector-header">
                <h3>Live Execution Monitor</h3>
                {activeJobId && <span className="text-muted" style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>#{activeJobId.slice(0, 8)}</span>}
              </div>

              {jobStatus ? (
                <div className="job-live-monitor">
                  <div className="job-status-banner">
                    <span className="status-title">Status:</span>
                    <span className={`status-badge status-${jobStatus.status}`}>{jobStatus.status.toUpperCase()}</span>
                  </div>

                  <div className="progress-bar-container">
                    <div className="progress-bar-fill" style={{ width: `${jobStatus.progress_percentage || 0}%` }}></div>
                  </div>
                  <div className="progress-percent">{jobStatus.progress_percentage || 0}% Completed</div>

                  <div className="job-meta-list">
                    <div className="meta-item">
                      <span className="text-muted">Task:</span>
                      <strong>{jobStatus.current_task || 'Processing'}</strong>
                    </div>
                    {jobStatus.current_model && (
                      <div className="meta-item">
                        <span className="text-muted">Model:</span>
                        <span className="model-chip">{jobStatus.current_model}</span>
                      </div>
                    )}
                    <div className="meta-item">
                      <span className="text-muted">Message:</span>
                      <p className="job-message">{jobStatus.message}</p>
                    </div>
                  </div>

                  {jobStatus.status === 'awaiting_approval' && activeJobId && (
                    <HumanInTheLoopReview 
                      jobId={activeJobId} 
                      files={jobStatus.files || {}} 
                      onApproved={() => {
                        console.log("Human approval registered from Studio");
                      }}
                      onCancelled={() => {
                        setIsRunning(false);
                      }}
                    />
                  )}

                  {jobStatus.files?.final_video && (
                    <div className="output-video-ready card">
                      <h4>Output Video Ready!</h4>
                      <a 
                        href={`/api/download?path=${encodeURIComponent(jobStatus.files.final_video)}`}
                        className="btn btn-primary"
                        download
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center', marginTop: '0.5rem' }}
                      >
                        <Download size={16} /> Download Master MP4
                      </a>
                    </div>
                  )}
                </div>
              ) : (
                <div className="empty-inspector text-center">
                  <Sliders size={32} className="text-muted mb-2" />
                  <p className="text-muted">Click any node on the graph to inspect its parameters, or click <strong>Run Entire Workflow</strong> to start live execution.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
