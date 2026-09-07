import React, { useState, useEffect, useRef } from 'react';
import { 
  GitBranch, 
  Plus, 
  Trash2, 
  Save, 
  Check, 
  ArrowLeft, 
  Play, 
  Activity, 
  Pencil, 
  Link2, 
  X, 
  Bot, 
  Zap, 
  Database, 
  Mail, 
  Bell, 
  Code, 
  Wand2, 
  Mic, 
  Layers, 
  Share2, 
  Search, 
  UserCheck, 
  Sliders, 
  Sparkles,
  Download
} from 'lucide-react';
import HumanInTheLoopReview from '../../components/HumanInTheLoopReview';
import './WorkflowArchitectPage.css';

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

interface NodeDefinition {
  id: string;
  slug: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  color: string;
  default_config: Record<string, any>;
}

export default function WorkflowArchitectPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [nodeDefinitions, setNodeDefinitions] = useState<NodeDefinition[]>([]);
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);
  
  // View mode: 'directory' (Image 1) or 'canvas' (Image 2 & 3)
  const [viewMode, setViewMode] = useState<'directory' | 'canvas'>('directory');
  
  // Canvas Drawer & Modals
  const [showNodePalette, setShowNodePalette] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NodeConfig | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  
  // Filter & Search in Directory
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'draft' | 'published'>('all');
  
  // Live Execution State
  const [isExecuting, setIsExecuting] = useState(false);
  const [executingJobId, setExecutingJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [topicInput, setTopicInput] = useState('');
  const [autonomousMode, setAutonomousMode] = useState(true);
  const [showRunModal, setShowRunModal] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [wfRes, ntRes] = await Promise.all([
        fetch('/api/studio/workflows'),
        fetch('/api/studio/node-types')
      ]);
      const wfData = await wfRes.json();
      const ntData = await ntRes.json();
      setWorkflows(wfData.workflows || []);
      setNodeDefinitions(ntData.node_types || []);
      if (wfData.workflows?.length > 0 && !activeWorkflow) {
        setActiveWorkflow(wfData.workflows[0]);
      }
    } catch (err) {
      console.error('Failed to load studio data', err);
    }
  };

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // Switch to Canvas Editor for a workflow
  const handleEditWorkflow = (wf: Workflow) => {
    setActiveWorkflow(wf);
    setViewMode('canvas');
    setSelectedNode(null);
  };

  // Create new workflow
  const handleCreateNewWorkflow = async () => {
    const newWf: Workflow = {
      id: `wf-${Date.now().toString(36)}`,
      name: 'New Video Production Pipeline',
      description: 'Custom multi-engine automated video workflow with Human-in-the-Loop review.',
      category: 'Custom Automation',
      icon: 'GitBranch',
      status: 'published',
      version: '1.0.0',
      nodes: [
        {
          id: 'node-1',
          node_type_id: 'nt-input',
          label: 'Start Topic Trigger',
          position_x: 250,
          position_y: 40,
          config: { mode: 'manual_course', topic: 'Binary Search Trees' }
        },
        {
          id: 'node-2',
          node_type_id: 'nt-planner',
          label: 'AI Script Planner',
          position_x: 250,
          position_y: 150,
          config: { model: 'qwen2.5:7b', temperature: 0.7 }
        },
        {
          id: 'node-3',
          node_type_id: 'nt-approval',
          label: 'Human Review Gate',
          position_x: 250,
          position_y: 260,
          config: { reviewer_role: 'Video Creator' }
        },
        {
          id: 'node-4',
          node_type_id: 'nt-assembly',
          label: 'DirectSynthesizer Video Mux',
          position_x: 250,
          position_y: 380,
          config: { aspect: '16:9' }
        }
      ],
      edges: [
        { id: 'e1-2', source: 'node-1', target: 'node-2' },
        { id: 'e2-3', source: 'node-2', target: 'node-3' },
        { id: 'e3-4', source: 'node-3', target: 'node-4', label: 'approved' }
      ]
    };

    try {
      const res = await fetch('/api/studio/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newWf)
      });
      if (res.ok) {
        showToastMsg('Created new workflow pipeline!');
        await loadData();
        setActiveWorkflow(newWf);
        setViewMode('canvas');
      }
    } catch (err) {
      alert('Failed to create workflow: ' + err);
    }
  };

  const handleSaveWorkflow = async () => {
    if (!activeWorkflow) return;
    try {
      const res = await fetch('/api/studio/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeWorkflow)
      });
      if (res.ok) {
        showToastMsg('Workflow saved successfully!');
        loadData();
      } else {
        alert('Failed to save workflow');
      }
    } catch (err) {
      alert('Error saving workflow: ' + err);
    }
  };

  const handleDeleteWorkflow = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    try {
      const res = await fetch(`/api/studio/workflows/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showToastMsg('Workflow deleted');
        loadData();
        if (activeWorkflow?.id === id) {
          setViewMode('directory');
        }
      }
    } catch (err) {
      alert('Failed to delete workflow: ' + err);
    }
  };

  // Add node from Palette to active workflow
  const handleAddNodeFromPalette = (def: NodeDefinition) => {
    if (!activeWorkflow) return;
    const newNodeId = `node-${Date.now().toString(36)}`;
    const lastNode = activeWorkflow.nodes[activeWorkflow.nodes.length - 1];
    const newY = lastNode ? lastNode.position_y + 110 : 100;
    
    const newNode: NodeConfig = {
      id: newNodeId,
      node_type_id: def.id,
      label: def.name,
      position_x: 250,
      position_y: newY,
      config: { ...def.default_config }
    };

    const updatedNodes = [...activeWorkflow.nodes, newNode];
    const updatedEdges = [...activeWorkflow.edges];
    if (lastNode) {
      updatedEdges.push({
        id: `e-${lastNode.id}-${newNodeId}`,
        source: lastNode.id,
        target: newNodeId
      });
    }

    setActiveWorkflow({
      ...activeWorkflow,
      nodes: updatedNodes,
      edges: updatedEdges
    });

    showToastMsg(`Added ${def.name} to workflow`);
    setShowNodePalette(false);
  };

  // Update node parameters from NodeConfigModal
  const handleUpdateNodeConfig = (nodeId: string, updatedConfig: Record<string, any>, updatedLabel?: string) => {
    if (!activeWorkflow) return;
    const updatedNodes = activeWorkflow.nodes.map(n => {
      if (n.id === nodeId) {
        return {
          ...n,
          label: updatedLabel || n.label,
          config: { ...n.config, ...updatedConfig }
        };
      }
      return n;
    });

    setActiveWorkflow({
      ...activeWorkflow,
      nodes: updatedNodes
    });
    setSelectedNode(null);
    showToastMsg('Node configuration updated!');
  };

  // Run pipeline live
  const handleTriggerRun = (wf: Workflow) => {
    setActiveWorkflow(wf);
    const inputNode = wf.nodes.find(n => n.node_type_id === 'nt-input');
    setTopicInput(inputNode?.config.topic || 'Mastering Modern Distributed Systems & Microservices');
    setShowRunModal(true);
    setJobStatus(null);
    setIsExecuting(false);
  };

  const handleCloseRunModal = () => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
    setShowRunModal(false);
    if (isExecuting) {
      showToastMsg('Pipeline execution running in background. Track in Jobs & Workers.');
    }
  };

  const executePipelineRun = async () => {
    if (!activeWorkflow) return;
    setIsExecuting(true);
    setJobStatus(null);

    try {
      const res = await fetch(`/api/studio/workflows/${activeWorkflow.id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          topic: topicInput,
          autonomous: autonomousMode,
          require_approval: !autonomousMode
        })
      });
      const data = await res.json();
      if (data.job_id) {
        setExecutingJobId(data.job_id);
        listenToJob(data.job_id);
      } else {
        alert('Failed to start run: ' + (data.error || 'Unknown error'));
        setIsExecuting(false);
      }
    } catch (err) {
      alert('Error running workflow: ' + err);
      setIsExecuting(false);
    }
  };

  const listenToJob = (jobId: string) => {
    if (sseRef.current) {
      sseRef.current.close();
    }
    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    sseRef.current = es;
    es.onmessage = (event) => {
      try {
        const job = JSON.parse(event.data);
        setJobStatus(job);
        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
          setIsExecuting(false);
          es.close();
          sseRef.current = null;
        }
      } catch (e) {
        console.error('SSE error', e);
      }
    };
    es.onerror = () => {
      es.close();
      sseRef.current = null;
    };
  };

  // Helpers for node visuals
  const getNodeColor = (typeId: string) => {
    switch (typeId) {
      case 'nt-input': return { bg: '#ECFDF5', border: '#10B981', color: '#047857' };
      case 'nt-condition': return { bg: '#ECFDF5', border: '#10B981', color: '#047857' };
      case 'nt-approval': return { bg: '#FFFBEB', border: '#F59E0B', color: '#B45309' };
      case 'nt-planner': return { bg: '#EFF6FF', border: '#3B82F6', color: '#1D4ED8' };
      case 'nt-verification': return { bg: '#FDF2F8', border: '#EC4899', color: '#BE185D' };
      case 'nt-tts': return { bg: '#FEF3C7', border: '#F59E0B', color: '#D97706' };
      case 'nt-manim': return { bg: '#ECFDF5', border: '#10B981', color: '#059669' };
      case 'nt-comfyui': return { bg: '#FDF2F8', border: '#EC4899', color: '#DB2777' };
      case 'nt-assembly': return { bg: '#EEF2FF', border: '#6366F1', color: '#4F46E5' };
      case 'nt-publisher': return { bg: '#FEF2F2', border: '#EF4444', color: '#DC2626' };
      default: return { bg: '#FFF1F2', border: '#FB7185', color: '#E11D48' };
    }
  };

  const getNodeIconComponent = (typeId: string) => {
    switch (typeId) {
      case 'nt-input': return <Play size={15} />;
      case 'nt-condition': return <GitBranch size={15} />;
      case 'nt-approval': return <UserCheck size={15} />;
      case 'nt-planner': return <Bot size={15} />;
      case 'nt-verification': return <Sparkles size={15} />;
      case 'nt-api': return <Zap size={15} />;
      case 'nt-insert': return <Database size={15} />;
      case 'nt-lookup': return <Search size={15} />;
      case 'nt-email': return <Mail size={15} />;
      case 'nt-notify': return <Bell size={15} />;
      case 'nt-manim': return <Code size={15} />;
      case 'nt-comfyui': return <Wand2 size={15} />;
      case 'nt-tts': return <Mic size={15} />;
      case 'nt-assembly': return <Layers size={15} />;
      case 'nt-publisher': return <Share2 size={15} />;
      default: return <Sliders size={15} />;
    }
  };

  // Filter workflows in Directory View
  const filteredWorkflows = workflows.filter(wf => {
    const matchesSearch = wf.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          wf.description.toLowerCase().includes(searchQuery.toLowerCase());
    if (statusFilter === 'all') return matchesSearch;
    return matchesSearch && wf.status.toLowerCase() === statusFilter;
  });

  return (
    <div className="studio-architect-page">
      {/* Toast Notification */}
      {toast && (
        <div className="studio-floating-toast">
          <Check size={15} />
          <span>{toast}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 1: WORKFLOWS DIRECTORY VIEW (Exact match to Image 1)             */}
      {/* ========================================================================= */}
      {viewMode === 'directory' && (
        <div className="workflows-directory-view">
          {/* Header Row */}
          <div className="directory-header-row">
            <div>
              <h1 className="directory-heading">Workflows</h1>
              <span className="directory-count-sub">{workflows.length} workflows</span>
            </div>
            <button 
              className="btn btn-primary new-workflow-btn"
              onClick={handleCreateNewWorkflow}
            >
              <Plus size={15} />
              <span>New Workflow</span>
            </button>
          </div>

          {/* Search & Filter Pills Row */}
          <div className="directory-filter-bar">
            <div className="directory-search-box">
              <Search size={15} className="search-icon-muted" />
              <input 
                type="text" 
                placeholder="Search workflows..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="status-filter-pills">
              <button 
                className={`filter-pill ${statusFilter === 'all' ? 'active' : ''}`}
                onClick={() => setStatusFilter('all')}
              >
                All
              </button>
              <button 
                className={`filter-pill ${statusFilter === 'draft' ? 'active' : ''}`}
                onClick={() => setStatusFilter('draft')}
              >
                Draft
              </button>
              <button 
                className={`filter-pill ${statusFilter === 'published' ? 'active' : ''}`}
                onClick={() => setStatusFilter('published')}
              >
                Published
              </button>
            </div>
          </div>

          {/* 3-Column Responsive Workflow Cards Grid */}
          {filteredWorkflows.length === 0 ? (
            <div style={{
              background: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              padding: '3.5rem 1.5rem',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.75rem',
              color: '#64748B'
            }}>
              <GitBranch size={40} color="#94A3B8" />
              <h3 style={{ margin: 0, color: '#0F172A', fontSize: '1.15rem', fontWeight: 600 }}>
                No Workflows Found in '{statusFilter.toUpperCase()}' Status
              </h3>
              <p style={{ margin: 0, fontSize: '0.875rem' }}>
                All our current pipelines are active and published. Click below to view all workflows.
              </p>
              <button 
                className="btn btn-secondary" 
                onClick={() => { setStatusFilter('all'); setSearchQuery(''); }}
                style={{ marginTop: '0.5rem' }}
              >
                Show All Workflows
              </button>
            </div>
          ) : (
            <div className="workflows-cards-grid">
              {filteredWorkflows.map(wf => (
              <div 
                key={wf.id} 
                className="workflow-card-sasi"
                onClick={() => handleEditWorkflow(wf)}
              >
                <div className="card-top-content">
                  <div className="card-header-flex">
                    <div className="emerald-icon-badge">
                      <GitBranch size={16} />
                    </div>
                    <div className="card-title-meta">
                      <h3 className="card-title-text">{wf.name}</h3>
                      <span className="card-status-pill">{wf.status || 'Published'}</span>
                    </div>
                  </div>
                  <p className="card-description-text">
                    {wf.description || 'No description provided'}
                  </p>
                </div>

                {/* Footer Action Bar: Edit, Assign, Trigger, Submissions, Delete */}
                <div className="card-actions-footer">
                  <div className="footer-left-actions">
                    <button 
                      className="footer-action-btn edit-action"
                      onClick={(e) => { e.stopPropagation(); handleEditWorkflow(wf); }}
                      title="Edit Canvas Graph"
                    >
                      <Pencil size={11} />
                      <span>Edit</span>
                    </button>
                    <button 
                      className="footer-action-btn assign-action"
                      onClick={(e) => { e.stopPropagation(); showToastMsg(`Roles assigned to ${wf.name}`); }}
                      title="Assign Roles"
                    >
                      <Link2 size={11} />
                      <span>Assign</span>
                    </button>
                    <button 
                      className="footer-action-btn trigger-action"
                      onClick={(e) => { e.stopPropagation(); handleTriggerRun(wf); }}
                      title="Trigger Pipeline Execution"
                    >
                      <Play size={11} />
                      <span>Trigger</span>
                    </button>
                    <button 
                      className="footer-action-btn submissions-action"
                      onClick={(e) => { e.stopPropagation(); showToastMsg(`Showing execution history for ${wf.name}`); }}
                      title="View Submissions & Runs"
                    >
                      <Activity size={11} />
                      <span>Submissions</span>
                    </button>
                  </div>
                  <button 
                    className="footer-delete-btn"
                    onClick={(e) => handleDeleteWorkflow(wf.id, e)}
                    title="Delete Workflow"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW MODE 2: VISUAL WORKFLOW CANVAS & EDITOR (Exact match to Image 2 & 3)   */}
      {/* ========================================================================= */}
      {viewMode === 'canvas' && activeWorkflow && (
        <div className="canvas-editor-view">
          {/* Top Editor Toolbar (Image 2 & 3 header) */}
          <div className="canvas-editor-toolbar">
            <div className="toolbar-left-cluster">
              <button 
                className="toolbar-back-btn"
                onClick={() => setViewMode('directory')}
                title="Back to Workflows Directory"
              >
                <ArrowLeft size={16} />
              </button>
              <div className="toolbar-divider" />
              
              <input 
                type="text"
                className="toolbar-title-input"
                value={activeWorkflow.name}
                onChange={(e) => setActiveWorkflow({ ...activeWorkflow, name: e.target.value })}
              />

              <span className="badge-published-pill">{activeWorkflow.status || 'Published'}</span>
              <span className="badge-version-pill">v{activeWorkflow.version || '1'}</span>
            </div>

            <div className="toolbar-right-cluster">
              <button 
                className={`btn btn-secondary add-node-toggle-btn ${showNodePalette ? 'active-palette-open' : ''}`}
                onClick={() => setShowNodePalette(!showNodePalette)}
              >
                <Plus size={14} />
                <span>Add Node</span>
              </button>

              <button className="btn btn-secondary" onClick={() => showToastMsg('Version 1.0.0 (Latest)')}>
                Versions
              </button>

              <button className="btn btn-secondary" onClick={handleSaveWorkflow}>
                <Save size={14} />
                <span>Save</span>
              </button>

              <button 
                className="btn btn-success publish-workflow-btn"
                onClick={() => {
                  setActiveWorkflow({ ...activeWorkflow, status: 'published' });
                  handleSaveWorkflow();
                }}
              >
                Publish
              </button>

              <button 
                className="btn btn-primary run-pipeline-pill-btn"
                onClick={() => handleTriggerRun(activeWorkflow)}
              >
                <Play size={14} />
                <span>Run Pipeline</span>
              </button>
            </div>
          </div>

          {/* Canvas Workspace & Slide-out Palette */}
          <div className="canvas-main-workspace">
            {/* Center: Visual Branching DAG Flow (Image 2) */}
            <div className="vertical-graph-canvas">
              <div className="flow-nodes-column">
                {activeWorkflow.nodes.map((node, index) => {
                  const colors = getNodeColor(node.node_type_id);
                  const isCondition = node.node_type_id === 'nt-condition';
                  const isApproval = node.node_type_id === 'nt-approval';

                  return (
                    <React.Fragment key={node.id}>
                      {/* Node Box */}
                      <div 
                        className="custom-flow-node"
                        style={{ backgroundColor: colors.bg, borderColor: colors.border }}
                        onClick={() => setSelectedNode(node)}
                      >
                        {/* Top Handle */}
                        <div className="node-handle-top" />

                        <div className="node-inner-header">
                          <div className="node-category-icon-box" style={{ color: colors.color }}>
                            {getNodeIconComponent(node.node_type_id)}
                          </div>
                          <div className="node-text-meta">
                            <span className="node-label-title">{node.label}</span>
                            <span className="node-type-subtitle">{node.node_type_id.replace('nt-', '').toUpperCase()}</span>
                          </div>
                        </div>

                        {/* Node Properties Snippets */}
                        {node.config?.model && (
                          <span className="node-prop-tag">model: {node.config.model}</span>
                        )}
                        {node.config?.topic && (
                          <span className="node-prop-tag">topic: {node.config.topic}</span>
                        )}
                        {node.config?.expression && (
                          <span className="node-prop-tag font-mono text-emerald-600">expr: {node.config.expression}</span>
                        )}

                        {/* Branch Handles for Condition & Approval */}
                        {isCondition ? (
                          <div className="branch-handles-row">
                            <div className="branch-pill branch-true">
                              <div className="handle-dot dot-green" />
                              <span>True</span>
                            </div>
                            <div className="branch-pill branch-false">
                              <div className="handle-dot dot-red" />
                              <span>False</span>
                            </div>
                          </div>
                        ) : isApproval ? (
                          <div className="branch-handles-row">
                            <div className="branch-pill branch-approved">
                              <div className="handle-dot dot-green" />
                              <span>Approved</span>
                            </div>
                            <div className="branch-pill branch-rejected">
                              <div className="handle-dot dot-red" />
                              <span>Rejected</span>
                            </div>
                          </div>
                        ) : (
                          <div className="node-handle-bottom" />
                        )}
                      </div>

                      {/* Animated Flow Connector Arrow between nodes */}
                      {index < activeWorkflow.nodes.length - 1 && (
                        <div className="flow-connector-line">
                          <div className="connector-dashed-svg">
                            <svg width="28" height="46" viewBox="0 0 28 46" className={`workflow-arrow-svg ${isExecuting ? 'flow-executing' : ''}`}>
                              <defs>
                                <linearGradient id={`flowGrad-${index}`} x1="0%" y1="0%" x2="0%" y2="100%">
                                  <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.75" />
                                  <stop offset="100%" stopColor="#5227c7" stopOpacity="1" />
                                </linearGradient>
                                <filter id={`flowGlow-${index}`} x="-50%" y="-50%" width="200%" height="200%">
                                  <feGaussianBlur stdDeviation="1.5" result="blur" />
                                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                </filter>
                              </defs>

                              {/* Subtle track guide line */}
                              <line 
                                x1="14" y1="0" 
                                x2="14" y2="36" 
                                stroke="#CBD5E1" 
                                strokeWidth="1.5" 
                                strokeOpacity="0.45"
                              />

                              {/* Continuous downward moving dashed flow line */}
                              <line 
                                x1="14" y1="0" 
                                x2="14" y2="36" 
                                stroke={isExecuting ? '#ff6d34' : `url(#flowGrad-${index})`}
                                strokeWidth="2.5" 
                                strokeDasharray="4 4" 
                                strokeLinecap="round"
                                className="animated-flow-line" 
                              />

                              {/* Traveling pulse dot 1 */}
                              <circle 
                                cx="14" cy="0" 
                                r="2.5" 
                                fill={isExecuting ? '#ff6d34' : '#ff6d34'}
                                filter={`url(#flowGlow-${index})`}
                                className="animated-flow-dot dot-primary"
                              />

                              {/* Traveling pulse dot 2 (interleaved flow) */}
                              <circle 
                                cx="14" cy="0" 
                                r="2" 
                                fill={isExecuting ? '#ff6d34' : '#7c3aed'}
                                className="animated-flow-dot dot-secondary"
                              />

                              {/* Directional arrowhead */}
                              <polygon 
                                points="9,34 19,34 14,42" 
                                fill={isExecuting ? '#ff6d34' : '#5227c7'}
                                className="animated-arrow-head"
                              />
                            </svg>
                          </div>
                        </div>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Floating Canvas Controls on Bottom-Left */}
              <div className="floating-canvas-controls">
                <button className="canvas-control-btn" title="Zoom In">+</button>
                <button className="canvas-control-btn" title="Zoom Out">−</button>
                <button className="canvas-control-btn" title="Fit Screen">⊡</button>
              </div>
            </div>

            {/* Right: Slide-Over Node Palette (Exact replica of Image 3) */}
            {showNodePalette && (
              <div className="slide-over-node-palette">
                <div className="palette-header">
                  <span className="palette-title">Node Palette</span>
                  <button 
                    className="palette-close-btn"
                    onClick={() => setShowNodePalette(false)}
                    title="Close Palette"
                  >
                    <X size={15} />
                  </button>
                </div>

                {/* 2-Column Grid of Pastel Node Definition Cards (Image 3) */}
                <div className="palette-scroll-content">
                  <div className="palette-2col-grid">
                    {nodeDefinitions.map(def => (
                      <div 
                        key={def.id}
                        className="palette-node-card"
                        onClick={() => handleAddNodeFromPalette(def)}
                        title={def.description}
                      >
                        <div className="palette-card-icon-wrap">
                          {getNodeIconComponent(def.id)}
                        </div>
                        <span className="palette-card-name">{def.name}</span>
                        <span className="palette-card-desc">{def.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: NODE CONFIGURATION MODAL (Configurable from UI, never touch code!) */}
      {/* ========================================================================= */}
      {selectedNode && (
        <div className="node-config-modal-overlay">
          <div className="node-config-modal-card">
            <div className="modal-header-row">
              <div className="modal-title-wrap">
                <div className="modal-icon-badge">
                  {getNodeIconComponent(selectedNode.node_type_id)}
                </div>
                <div>
                  <h3 className="modal-title-text">{selectedNode.label}</h3>
                  <span className="modal-type-sub">{selectedNode.node_type_id}</span>
                </div>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedNode(null)}>
                <X size={16} />
              </button>
            </div>

            {/* Editable Configuration Fields */}
            <div className="modal-body-scroll">
              <div className="form-group-wrap">
                <label>Node Display Name</label>
                <input 
                  type="text" 
                  className="input-field"
                  defaultValue={selectedNode.label}
                  id="cfg-node-label"
                />
              </div>

              {/* LLM & AI Script Parameters */}
              {selectedNode.node_type_id === 'nt-planner' && (
                <>
                  <div className="form-group-wrap">
                    <label>AI Model Provider</label>
                    <select className="input-field" defaultValue={selectedNode.config.model || 'qwen2.5:7b'} id="cfg-model">
                      <option value="qwen2.5:7b">Qwen 2.5:7B (Ollama Local - 100% Free, Zero Trace)</option>
                      <option value="llama3:latest">Llama 3 (Ollama Local - 100% Free, Zero Trace)</option>
                      <option value="gpt-4o-mini">OpenAI GPT-4o-Mini (Ultra-low cost, fractions of a cent)</option>
                      <option value="gpt-4o">OpenAI GPT-4o (Frontier Model)</option>
                      <option value="gemini-2.0-flash">Google Gemini 2.0 Flash</option>
                    </select>
                  </div>
                  <div className="form-group-wrap">
                    <label>Temperature (Creativity)</label>
                    <input type="number" step="0.1" min="0" max="1" className="input-field" defaultValue={selectedNode.config.temperature || 0.7} id="cfg-temp" />
                  </div>
                  <div className="form-group-wrap">
                    <label>System Instructions Prompt</label>
                    <textarea 
                      className="input-field" 
                      rows={4}
                      defaultValue={selectedNode.config.system_prompt || 'You are an expert academic curriculum and video script designer.'}
                      id="cfg-prompt"
                    />
                  </div>
                </>
              )}

              {/* TTS Audio Parameters */}
              {selectedNode.node_type_id === 'nt-tts' && (
                <>
                  <div className="form-group-wrap">
                    <label>Neural Voice Character</label>
                    <select className="input-field" defaultValue={selectedNode.config.voice || 'en-US-AndrewMultilingualNeural'} id="cfg-voice">
                      <option value="en-US-AndrewMultilingualNeural">Andrew (Natural & Multilingual)</option>
                      <option value="en-US-GuyNeural">Guy (Energetic & Clear)</option>
                      <option value="en-US-AriaNeural">Aria (Expressive & Engaging)</option>
                      <option value="en-US-JennyNeural">Jenny (Story & Warm)</option>
                    </select>
                  </div>
                  <div className="form-group-wrap">
                    <label>Speaking Speed</label>
                    <input type="text" className="input-field" defaultValue={selectedNode.config.rate || '+0%'} id="cfg-rate" placeholder="+10% or -5%" />
                  </div>
                </>
              )}

              {/* Visual Renderer & Assembly */}
              {(selectedNode.node_type_id === 'nt-assembly' || selectedNode.node_type_id === 'nt-comfyui') && (
                <div className="form-group-wrap">
                  <label>Aspect Ratio & Resolution</label>
                  <select className="input-field" defaultValue={selectedNode.config.aspect || '16:9'} id="cfg-aspect">
                    <option value="16:9">16:9 Landscape (YouTube standard 1080p)</option>
                    <option value="9:16">9:16 Vertical (Shorts & Reels 1080x1920)</option>
                    <option value="1:1">1:1 Square (Feed)</option>
                  </select>
                </div>
              )}

              {/* Approval Gate Parameters */}
              {selectedNode.node_type_id === 'nt-approval' && (
                <>
                  <div className="form-group-wrap">
                    <label>Reviewer Role Required</label>
                    <select className="input-field" defaultValue={selectedNode.config.reviewer_role || 'Video Creator'} id="cfg-role">
                      <option value="System Administrator">System Administrator</option>
                      <option value="Video Creator">Video Creator</option>
                      <option value="Content Reviewer">Content Reviewer</option>
                    </select>
                  </div>
                  <div className="form-group-wrap">
                    <label>Approval Timeout (Seconds)</label>
                    <input type="number" className="input-field" defaultValue={selectedNode.config.timeout_seconds || 300} id="cfg-timeout" />
                  </div>
                </>
              )}

              {/* Generic Config Key-Values */}
              <div className="form-group-wrap">
                <label>Raw Parameter Config (JSON)</label>
                <textarea 
                  className="input-field font-mono"
                  rows={4}
                  defaultValue={JSON.stringify(selectedNode.config, null, 2)}
                  id="cfg-raw-json"
                />
              </div>
            </div>

            {/* Modal Actions */}
            <div className="modal-footer-row">
              <button 
                className="btn btn-danger"
                onClick={() => {
                  if (confirm('Delete this node from workflow?')) {
                    const filtered = activeWorkflow?.nodes.filter(n => n.id !== selectedNode.id) || [];
                    const filteredEdges = activeWorkflow?.edges.filter(e => e.source !== selectedNode.id && e.target !== selectedNode.id) || [];
                    if (activeWorkflow) {
                      setActiveWorkflow({ ...activeWorkflow, nodes: filtered, edges: filteredEdges });
                    }
                    setSelectedNode(null);
                  }
                }}
              >
                Delete Node
              </button>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-secondary" onClick={() => setSelectedNode(null)}>
                  Cancel
                </button>
                <button 
                  className="btn btn-primary"
                  onClick={() => {
                    const labelInput = (document.getElementById('cfg-node-label') as HTMLInputElement)?.value;
                    const rawJson = (document.getElementById('cfg-raw-json') as HTMLTextAreaElement)?.value;
                    let parsed: any = {};
                    try {
                      parsed = JSON.parse(rawJson);
                    } catch {
                      parsed = selectedNode.config;
                    }

                    // Also pull form specific inputs
                    const modelEl = document.getElementById('cfg-model') as HTMLSelectElement;
                    if (modelEl) parsed.model = modelEl.value;

                    const voiceEl = document.getElementById('cfg-voice') as HTMLSelectElement;
                    if (voiceEl) parsed.voice = voiceEl.value;

                    const aspectEl = document.getElementById('cfg-aspect') as HTMLSelectElement;
                    if (aspectEl) parsed.aspect = aspectEl.value;

                    handleUpdateNodeConfig(selectedNode.id, parsed, labelInput);
                  }}
                >
                  Save Node Configuration
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL: LIVE PIPELINE EXECUTION & HUMAN-IN-THE-LOOP APPROVAL               */}
      {/* ========================================================================= */}
      {/* ========================================================================= */}
      {/* MODAL: LIVE PIPELINE EXECUTION & HUMAN-IN-THE-LOOP APPROVAL               */}
      {/* ========================================================================= */}
      {showRunModal && activeWorkflow && (
        <div className="node-config-modal-overlay">
          <div className="node-config-modal-card" style={{ maxWidth: '820px', width: '95%', maxHeight: '90vh' }}>
            <div className="modal-header-row">
              <div className="modal-title-wrap">
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Play size={18} color="#DC2626" />
                </div>
                <div>
                  <h3 className="modal-title-text" style={{ fontSize: '1.2rem', color: '#0F172A' }}>Trigger Workflow Execution</h3>
                  <span className="modal-type-sub" style={{ color: '#64748B' }}>{activeWorkflow.name}</span>
                </div>
              </div>
              <button className="modal-close-btn" onClick={handleCloseRunModal} title="Close Modal">
                <X size={18} />
              </button>
            </div>

            <div className="modal-body-scroll" style={{ padding: '1.5rem', maxHeight: 'calc(90vh - 140px)', overflowY: 'auto' }}>
              {/* Topic Input */}
              <div className="form-group-wrap">
                <label style={{ fontSize: '0.875rem', fontWeight: 600, color: '#0F172A' }}>Video Topic / Prompt Target</label>
                <input 
                  type="text" 
                  className="input-field" 
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  placeholder="e.g. Mastering Modern Distributed Systems & Microservices"
                  disabled={isExecuting}
                  style={{ padding: '0.75rem 1rem', fontSize: '0.925rem', borderRadius: '8px', border: '1px solid #CBD5E1', background: '#F8FAFC', color: '#0F172A' }}
                />
              </div>

              {/* Autonomous Mode Toggle */}
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.75rem',
                padding: '0.85rem 1rem',
                background: autonomousMode ? '#FEF2F2' : '#F8FAFC',
                border: autonomousMode ? '1px solid #FECDD3' : '1px solid #E2E8F0',
                borderRadius: '8px',
                marginTop: '0.5rem',
                transition: 'all 0.2s'
              }}>
                <input 
                  type="checkbox" 
                  id="modal-autonomous-toggle"
                  checked={autonomousMode}
                  onChange={(e) => setAutonomousMode(e.target.checked)}
                  disabled={isExecuting}
                  style={{ width: '18px', height: '18px', marginTop: '2px', cursor: 'pointer', accentColor: '#DC2626' }}
                />
                <label htmlFor="modal-autonomous-toggle" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 700, color: autonomousMode ? '#991B1B' : '#0F172A' }}>
                    ⚡ Full Autonomous Autopilot (Recommended)
                  </span>
                  <span style={{ fontSize: '0.775rem', color: '#64748B', marginTop: '0.15rem' }}>
                    Chains all sub-steps automatically: AI Planning &rarr; Manim Animation &rarr; Edge-TTS Narration &rarr; MPT Audio Mux &rarr; YouTube Viral SEO &rarr; Direct Publishing & Analytics.
                  </span>
                </label>
              </div>

              {!isExecuting && !jobStatus && (
                <div style={{
                  background: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  padding: '1rem',
                  borderRadius: '8px',
                  color: '#1E40AF',
                  fontSize: '0.85rem',
                  lineHeight: 1.5,
                  marginTop: '0.5rem'
                }}>
                  Clicking <strong>Start Execution</strong> will compile this workflow graph, trigger background workers, and stream live progress.
                </div>
              )}

              {/* Live SSE Execution Monitor */}
              {jobStatus && (
                <div className="live-job-panel" style={{ marginTop: '0.75rem', border: '1px solid #E2E8F0', background: '#FFFFFF', borderRadius: '10px', padding: '1.25rem' }}>
                  <div className="job-status-banner-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="text-muted" style={{ fontSize: '0.85rem' }}>Status:</span>
                      <span className={`status-badge-pill ${jobStatus.status}`}>
                        {jobStatus.status.toUpperCase()}
                      </span>
                    </div>
                    <span style={{ fontWeight: 700, color: '#DC2626', fontSize: '0.95rem' }}>{jobStatus.progress_percentage || 0}%</span>
                  </div>

                  <div className="progress-bar-track" style={{ height: '8px', background: '#F1F5F9', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.75rem' }}>
                    <div 
                      style={{ 
                        width: `${jobStatus.progress_percentage || 0}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #DC2626, #EF4444)',
                        transition: 'width 0.3s ease'
                      }}
                    />
                  </div>

                  <p style={{ fontSize: '0.85rem', color: '#334155', margin: '0 0 1rem 0', fontWeight: 500 }}>
                    {jobStatus.message}
                  </p>

                  {/* Human-in-the-Loop Review Gate Component */}
                  {jobStatus.status === 'awaiting_approval' && executingJobId && (
                    <HumanInTheLoopReview 
                      jobId={executingJobId}
                      files={jobStatus.files || {}}
                      onApproved={() => {
                        showToastMsg('Approval registered! Resuming generation.');
                      }}
                      onCancelled={() => {
                        setIsExecuting(false);
                      }}
                    />
                  )}

                  {/* Output Video Ready */}
                  {jobStatus.files?.final_video && (
                    <div style={{
                      background: '#ECFDF5',
                      border: '1px solid #A7F3D0',
                      borderRadius: '8px',
                      padding: '1.25rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '1rem',
                      marginTop: '1rem'
                    }}>
                      <div>
                        <h4 style={{ margin: '0 0 0.25rem 0', color: '#065F46', fontSize: '1rem', fontWeight: 700 }}>Master Video Ready!</h4>
                        <p style={{ margin: 0, fontSize: '0.825rem', color: '#047857' }}>
                          Video rendering & assembly completed successfully.
                        </p>
                      </div>
                      <a 
                        href={`/api/download?path=${encodeURIComponent(jobStatus.files.final_video)}`}
                        className="btn btn-primary"
                        download
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.25rem' }}
                      >
                        <Download size={16} />
                        Download Final Video (.mp4)
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="modal-footer-row" style={{ padding: '1rem 1.5rem', background: '#F8FAFC', borderTop: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button 
                className="btn btn-secondary" 
                onClick={handleCloseRunModal}
                style={{ padding: '0.55rem 1.25rem', fontWeight: 600 }}
              >
                Close
              </button>

              {!isExecuting && !jobStatus && (
                <button 
                  className="btn btn-primary" 
                  onClick={executePipelineRun}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.55rem 1.25rem' }}
                >
                  <Play size={15} />
                  <span>Start Execution</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
