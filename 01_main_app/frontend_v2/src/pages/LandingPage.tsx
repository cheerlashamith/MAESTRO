import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, 
  Share2, 
  Cpu, 
  Play, 
  CheckCircle2, 
  Layers, 
  Compass, 
  FileVideo,
  Code2,
  Terminal,
  Zap,
  Mic2,
  Bot,
  Activity
} from 'lucide-react';
import MaestroLogo from '../components/MaestroLogo';
import './LandingPage.css';

interface DemoTopic {
  title: string;
  icon: string;
  category: string;
  scenes: number;
  duration: string;
  codeSnippet: string;
  voice: string;
  tags: string[];
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState<number>(0);
  const [selectedTopicIdx, setSelectedTopicIdx] = useState<number>(0);

  const demoTopics: DemoTopic[] = [
    {
      title: "Distributed Consensus & Raft Protocol",
      icon: "⚡",
      category: "Systems Engineering",
      scenes: 4,
      duration: "4m 12s",
      voice: "Edge TTS - Andrew (US Multilingual)",
      tags: ["Distributed Systems", "Raft Protocol", "Leader Election", "Fault Tolerance"],
      codeSnippet: `from manim import *

class RaftConsensusScene(Scene):
    def construct(self):
        title = Title("Raft Protocol: Leader Election")
        nodes = VGroup(*[Circle(radius=0.6, color=BLUE) for _ in range(5)])
        nodes.arrange(RIGHT, buff=1.0)
        
        # Animate Candidate node broadcasting RequestVote RPCs
        candidate = nodes[2].set_color(ORANGE)
        self.play(Write(title), Create(nodes))
        self.play(candidate.animate.scale(1.25), run_time=1.2)
        
        # Broadcast heartbeats
        heartbeats = [Arrow(candidate.get_center(), n.get_center()) for n in nodes if n != candidate]
        self.play(*[GrowArrow(a) for a in heartbeats])
        self.wait(2)`
    },
    {
      title: "Dijkstra's Shortest Path Algorithm",
      icon: "📐",
      category: "Data Structures & Algorithms",
      scenes: 5,
      duration: "5m 30s",
      voice: "Edge TTS - Jenny (US Natural)",
      tags: ["Graph Algorithms", "Dijkstra", "Shortest Path", "Greedy Algorithm"],
      codeSnippet: `from manim import *

class DijkstraGraphScene(Scene):
    def construct(self):
        graph = Graph(
            vertices=[1, 2, 3, 4, 5],
            edges=[(1, 2), (2, 3), (3, 4), (4, 5), (1, 5), (2, 4)],
            layout="circular"
        )
        self.play(Create(graph))
        
        # Highlight relaxing edges with minimum priority queue
        edge_1_2 = graph.edges[(1, 2)]
        self.play(edge_1_2.animate.set_color(YELLOW).set_stroke_width(6))
        self.play(graph.vertices[2].animate.set_color(GREEN))
        self.wait(2)`
    },
    {
      title: "Gravitational Lensing & General Relativity",
      icon: "🌌",
      category: "Astrophysics",
      scenes: 4,
      duration: "3m 48s",
      voice: "Edge TTS - Christopher (US Authoritative)",
      tags: ["Astrophysics", "General Relativity", "Einstein Rings", "Space-Time"],
      codeSnippet: `from manim import *

class GravitationalLensingScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        massive_body = Sphere(radius=0.8, color=PURPLE).shift(IN)
        self.set_camera_orientation(phi=65 * DEGREES, theta=30 * DEGREES)
        
        # Deform space-time grid
        grid = Surface(lambda u, v: np.array([u, v, -0.5 / (u**2 + v**2 + 0.2)]))
        self.play(Create(axes), FadeIn(massive_body))
        self.play(Create(grid), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(3)`
    },
    {
      title: "Neural Transformers & Multi-Head Attention",
      icon: "🧬",
      category: "Machine Learning",
      scenes: 6,
      duration: "6m 15s",
      voice: "Edge TTS - Andrew (US Multilingual)",
      tags: ["Transformers", "Attention Mechanism", "Deep Learning", "LLMs"],
      codeSnippet: `from manim import *

class AttentionMatrixScene(Scene):
    def construct(self):
        q_matrix = Matrix([[0.8, 0.2], [0.1, 0.9]])
        k_matrix = Matrix([[0.7, 0.3], [0.4, 0.6]])
        
        # Softmax scaled dot product: Q * K^T / sqrt(d_k)
        formula = MathTex(r"\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V")
        self.play(Write(formula.to_edge(UP)))
        self.play(Create(q_matrix.shift(LEFT*2)), Create(k_matrix.shift(RIGHT*2)))
        self.wait(2)`
    }
  ];

  const currentTopic = demoTopics[selectedTopicIdx];

  const pipelineSteps = [
    {
      num: '01',
      title: 'Course & Script Ingestion',
      desc: 'Feed syllabus outlines, technical research topics, or YouTube URLs directly into the autonomous pipeline.',
      icon: <Compass size={22} />,
      tag: 'LLM Multi-Agent'
    },
    {
      num: '02',
      title: 'Visual Scene Orchestration',
      desc: 'Maestro synthesizes dynamic Python Manim mathematical scripts and ComfyUI visual storyboards.',
      icon: <Layers size={22} />,
      tag: 'Manim & ComfyUI'
    },
    {
      num: '03',
      title: 'Neural Speech & 4K Render',
      desc: 'Multi-lingual neural voices render in perfect sync with audio waveforms and auto-generated subtitles.',
      icon: <Cpu size={22} />,
      tag: 'EdgeTTS & FFmpeg'
    },
    {
      num: '04',
      title: '1-Click YouTube Publishing',
      desc: 'AI SEO title generation, description formatting, custom thumbnail extraction, and direct scheduling.',
      icon: <Share2 size={22} />,
      tag: 'YouTube Studio API'
    }
  ];

  const handleLaunchTopic = (topic: string) => {
    localStorage.setItem('role', 'user');
    navigate(`/user/create?topic=${encodeURIComponent(topic)}`);
  };

  return (
    <div className="landing-container">
      <div className="landing-ambient-bg" />

      {/* Top Navigation */}
      <header className="landing-header">
        <div className="landing-nav-content">
          <MaestroLogo size="md" onClick={() => navigate('/')} />

          <nav className="landing-nav-links">
            <a href="#pipeline" className="landing-nav-link">Pipeline</a>
            <a href="#playground" className="landing-nav-link">Playground</a>
            <a href="#architecture" className="landing-nav-link">Architecture</a>
            <a href="#comparison" className="landing-nav-link">Comparison</a>
            <button 
              onClick={() => navigate('/user/publisher')} 
              className="landing-nav-link"
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            >
              YouTube Hub
            </button>
          </nav>

          <div className="landing-header-actions">
            <button 
              onClick={() => navigate('/login')}
              className="btn btn-secondary"
              style={{ padding: '0.45rem 1rem' }}
            >
              Sign In
            </button>
            <button 
              onClick={() => {
                localStorage.setItem('role', 'user');
                navigate('/user/create');
              }}
              className="btn btn-primary"
              style={{ padding: '0.45rem 1.15rem' }}
            >
              <Sparkles size={15} />
              Launch Studio
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="hero-pill-badge">
          <Sparkles size={14} className="hero-pill-icon" />
          <span>MAESTRO • MULTI-AGENT AUTONOMOUS ENGINE FOR SCALABLE TRANSMEDIA RENDERING &amp; ORCHESTRATION</span>
        </div>

        <h1 className="hero-title">
          Scale Video Creation with <br />
          <span className="hero-title-highlight">Autonomous AI Orchestration</span>
        </h1>

        <p className="hero-subtitle">
          Maestro unifies large language model planners, mathematical Manim 4K animation engines, 
          ComfyUI visual narratives, and automated YouTube distribution into one seamless production platform.
        </p>

        {/* Dual Primary Call-To-Action */}
        <div className="hero-cta-group">
          <button 
            onClick={() => {
              localStorage.setItem('role', 'user');
              navigate('/user/create');
            }}
            className="btn-cta-orange"
          >
            <Play size={18} fill="#FFFFFF" />
            Launch Creator Studio
          </button>

          <button 
            onClick={() => {
              localStorage.setItem('role', 'admin');
              navigate('/admin/studio');
            }}
            className="btn-cta-violet"
          >
            <Layers size={18} />
            Workflow Architect
          </button>

          <button 
            onClick={() => navigate('/user/videos')}
            className="btn btn-secondary"
            style={{ padding: '0.85rem 1.4rem', borderRadius: '12px' }}
          >
            <FileVideo size={17} />
            View My Videos
          </button>
        </div>

        {/* MAESTRO Full Form Breakdown Matrix */}
        <div className="maestro-acronym-banner">
          <div className="acronym-title-row">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="acronym-tag">OFFICIAL ACRONYM SPECIFICATION</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Enterprise Architecture v2.0</span>
            </div>
            <div className="acronym-full-name">
              <strong>M.A.E.S.T.R.O.</strong> — Multi-Agent Autonomous Engine for Scalable Transmedia Rendering &amp; Orchestration
            </div>
          </div>
          <div className="acronym-letters-row">
            <div className="acronym-letter-chip">
              <span className="chip-letter">M</span>
              <div>
                <span className="chip-word">Multi-Agent</span>
                <span className="chip-sub">Swarm Planning</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">A</span>
              <div>
                <span className="chip-word">Autonomous</span>
                <span className="chip-sub">Zero Bottlenecks</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">E</span>
              <div>
                <span className="chip-word">Engine for</span>
                <span className="chip-sub">Direct Neural Flow</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">S</span>
              <div>
                <span className="chip-word">Scalable</span>
                <span className="chip-sub">19+ Topic Batches</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">T</span>
              <div>
                <span className="chip-word">Transmedia</span>
                <span className="chip-sub">16:9 &amp; 9:16 Shorts</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">R</span>
              <div>
                <span className="chip-word">Rendering</span>
                <span className="chip-sub">4K Manim &amp; ComfyUI</span>
              </div>
            </div>
            <div className="acronym-letter-chip">
              <span className="chip-letter">O</span>
              <div>
                <span className="chip-word">Orchestration</span>
                <span className="chip-sub">YouTube Autopilot</span>
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Pipeline Showcase Card */}
        <div className="pipeline-visualizer-card" id="pipeline">
          <div className="pipeline-header">
            <div className="pipeline-title-group">
              <span className="pipeline-badge-live">
                <span className="live-dot" /> LIVE ENGINE
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
                Autonomous Production Pipeline
              </h3>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Interactive Workflow Execution
            </span>
          </div>

          <div className="pipeline-steps-grid">
            {pipelineSteps.map((step, idx) => (
              <div 
                key={step.num}
                className={`pipeline-step-card ${activeStep === idx ? 'step-card-active' : ''}`}
                onClick={() => setActiveStep(idx)}
                style={{ cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="step-number-tag">STEP {step.num}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                    {step.tag}
                  </span>
                </div>
                <div className="step-icon-box">
                  {step.icon}
                </div>
                <h4 className="step-card-title">{step.title}</h4>
                <p className="step-card-desc">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Studio Playground Section */}
      <section className="landing-section" id="playground">
        <div className="section-header">
          <div className="section-badge">INTERACTIVE ENGINE SANDBOX</div>
          <h2 className="section-title">Test Drive Autonomous Synthesis</h2>
          <p className="section-subtitle">
            Select an engineering domain below to inspect how Maestro's multi-agent planners dynamically
            synthesize mathematical code, neural audio tracks, and YouTube distribution tags.
          </p>
        </div>

        <div className="playground-wrapper">
          {/* Topic Select Chips */}
          <div className="topic-chips-container">
            {demoTopics.map((item, idx) => (
              <button
                key={item.title}
                className={`topic-chip-btn ${selectedTopicIdx === idx ? 'active' : ''}`}
                onClick={() => setSelectedTopicIdx(idx)}
              >
                <span>{item.icon}</span>
                <span>{item.title}</span>
              </button>
            ))}
          </div>

          {/* Split View: Terminal Code & Agent Breakdown */}
          <div className="playground-split-grid">
            {/* Left: Code Terminal */}
            <div className="playground-terminal-card">
              <div className="terminal-header-bar">
                <div className="terminal-dots">
                  <span className="terminal-dot dot-red" />
                  <span className="terminal-dot dot-yellow" />
                  <span className="terminal-dot dot-green" />
                </div>
                <span className="terminal-title">
                  manim_scene_generated.py • 4K 60FPS
                </span>
                <span style={{ fontSize: '0.7rem', color: '#50fa7b', fontWeight: 600 }}>
                  VALIDATED
                </span>
              </div>

              <div className="code-preview-block">
                <pre style={{ margin: 0 }}>
                  <code>{currentTopic.codeSnippet}</code>
                </pre>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.75rem', borderTop: '1px solid rgba(255, 255, 255, 0.1)', fontSize: '0.75rem', color: '#9ca3af' }}>
                <span>Duration: {currentTopic.duration}</span>
                <span>Render: Manim Community v0.19</span>
              </div>
            </div>

            {/* Right: Agent Specs & 1-Click Launch */}
            <div className="playground-details-panel">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div className="agent-spec-item">
                  <div className="agent-spec-icon icon-purple">
                    <Bot size={18} />
                  </div>
                  <div>
                    <div className="agent-spec-title">Cognitive Planner (Qwen 14B)</div>
                    <div className="agent-spec-sub">
                      Generated {currentTopic.scenes} structured pedagogy scenes with audio pacing constraints.
                    </div>
                  </div>
                </div>

                <div className="agent-spec-item">
                  <div className="agent-spec-icon icon-orange">
                    <Code2 size={18} />
                  </div>
                  <div>
                    <div className="agent-spec-title">Mathematical Code Synthesizer</div>
                    <div className="agent-spec-sub">
                      Pure vector mathematical geometry with zero pixelation and 60FPS motion smoothing.
                    </div>
                  </div>
                </div>

                <div className="agent-spec-item">
                  <div className="agent-spec-icon icon-purple">
                    <Mic2 size={18} />
                  </div>
                  <div>
                    <div className="agent-spec-title">Neural Speech Vocoder</div>
                    <div className="agent-spec-sub">
                      Configured: {currentTopic.voice} with auto-timestamped subtitle alignment.
                    </div>
                  </div>
                </div>

                <div className="agent-spec-item">
                  <div className="agent-spec-icon icon-orange">
                    <Share2 size={18} />
                  </div>
                  <div>
                    <div className="agent-spec-title">Automated YouTube SEO Tags</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.3rem' }}>
                      {currentTopic.tags.map(t => (
                        <span key={t} style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem', background: '#FFFFFF', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--brand)', fontWeight: 600 }}>
                          #{t.replace(/\s+/g, '')}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Direct Launch CTA */}
              <button 
                className="btn btn-primary"
                onClick={() => handleLaunchTopic(currentTopic.title)}
                style={{ padding: '0.9rem 1.5rem', fontSize: '0.95rem', borderRadius: '12px' }}
              >
                <Zap size={18} />
                Generate This Full 4K Video in Studio
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Production Reality Architecture Section */}
      <section className="landing-section" id="architecture">
        <div className="section-header">
          <div className="section-badge">SYSTEM TOPOLOGY &amp; ARCHITECTURE</div>
          <h2 className="section-title">Architected for Industrial Scale</h2>
          <p className="section-subtitle">
            Maestro decouples orchestration from rendering, combining local Ollama LLMs, 
            sandboxed Python runtime execution, and asynchronous background daemons.
          </p>
        </div>

        <div className="arch-grid-6">
          {/* Node 1 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">OLLAMA 14B</span>
              <Bot size={20} color="#5227c7" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              Dual Cognitive Brain
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Autonomous Planner and Coding Agents analyze syllabi, construct time-synchronized script segments, and generate clean Manim code.
            </p>
          </div>

          {/* Node 2 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">PYTHON 3.12</span>
              <Terminal size={20} color="#ff6d34" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              Manim 4K Math Engine
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Compiles LaTeX typography, geometric coordinate matrices, and continuous calculus transformations into lossless 60FPS video layers.
            </p>
          </div>

          {/* Node 3 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">DIFFUSION</span>
              <Sparkles size={20} color="#5227c7" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              ComfyUI Visual Narratives
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Generates high-aesthetic cinematic frames, custom character consistency, and vertical 9:16 storyboards for social distribution.
            </p>
          </div>

          {/* Node 4 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">NEURAL VOCAL</span>
              <Mic2 size={20} color="#ff6d34" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              EdgeTTS Synthesis Engine
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Over 40 multilingual expressive voices with precise syllable boundary metadata for automatic audio-visual timing synchronization.
            </p>
          </div>

          {/* Node 5 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">HARDWARE ACCEL</span>
              <Cpu size={20} color="#5227c7" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              FFmpeg Assembly Core
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Multi-track audio ducking, subtitle burn-in, cross-fade transitions, and GPU-accelerated NVENC video rendering into web-ready MP4s.
            </p>
          </div>

          {/* Node 6 */}
          <div className="arch-node-card">
            <div className="arch-node-header">
              <span className="arch-badge-tech">YOUTUBE API V3</span>
              <Share2 size={20} color="#ff6d34" />
            </div>
            <h3 style={{ fontSize: '1.12rem', fontWeight: 700, margin: 0 }}>
              YouTube Studio Autopilot
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Direct OAuth 2.0 channel upload, tag optimization, automatic thumbnail frame extraction, and background schedule daemon.
            </p>
          </div>
        </div>
      </section>

      {/* Production Reality Comparison Section */}
      <section className="landing-section" id="comparison">
        <div className="section-header">
          <div className="section-badge">PRODUCTION REALITY</div>
          <h2 className="section-title">Manual Creation vs. Maestro Engine</h2>
          <p className="section-subtitle">
            See how autonomous multi-agent orchestration eliminates production bottlenecks 
            while drastically improving technical accuracy and output volume.
          </p>
        </div>

        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th style={{ width: '25%' }}>Workflow Dimension</th>
                <th style={{ width: '37.5%' }}>Traditional Manual Production</th>
                <th style={{ width: '37.5%' }} className="col-maestro">Maestro Autonomous Orchestrator</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Script &amp; Pedagogy</strong></td>
                <td><span className="badge-manual">3-5 Hours</span> Manual syllabus research &amp; script drafting</td>
                <td className="col-maestro"><span className="badge-winner"><CheckCircle2 size={13} /> Instant (15s)</span> Multi-agent syllabus-aware scene synthesis</td>
              </tr>
              <tr>
                <td><strong>Mathematical Animations</strong></td>
                <td><span className="badge-manual">6-10 Hours</span> Manual keyframing or writing Manim code line-by-line</td>
                <td className="col-maestro"><span className="badge-winner"><CheckCircle2 size={13} /> Autonomous</span> Self-healing Manim Python generation with syntax validation</td>
              </tr>
              <tr>
                <td><strong>Voiceover &amp; Timing</strong></td>
                <td><span className="badge-manual">$250 - $500</span> Studio equipment or voice actor hiring + retakes</td>
                <td className="col-maestro"><span className="badge-winner"><CheckCircle2 size={13} /> Included</span> 40+ neural voices with millisecond syllable alignment</td>
              </tr>
              <tr>
                <td><strong>Assembly &amp; Subtitling</strong></td>
                <td><span className="badge-manual">2-3 Hours</span> NLE video editing, audio ducking &amp; subtitle typing</td>
                <td className="col-maestro"><span className="badge-winner"><CheckCircle2 size={13} /> 1-Click</span> Hardware-accelerated FFmpeg 4K multiplexing</td>
              </tr>
              <tr>
                <td><strong>YouTube Distribution</strong></td>
                <td><span className="badge-manual">Manual Upload</span> Writing descriptions, keyword research &amp; manual upload</td>
                <td className="col-maestro"><span className="badge-winner"><CheckCircle2 size={13} /> Direct OAuth</span> AI SEO tags, thumbnail generation, &amp; scheduled queues</td>
              </tr>
              <tr>
                <td><strong>Total Production Cycle</strong></td>
                <td><span className="badge-manual">12 - 18 Hours / Video</span></td>
                <td className="col-maestro"><span className="badge-winner" style={{ background: '#FFF2EC', color: '#ff6d34', borderColor: '#FFD4C2' }}><Zap size={13} /> ~3 Minutes Total</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* High-Impact CTA Banner */}
      <section className="landing-section" style={{ paddingBottom: '2rem' }}>
        <div className="landing-cta-banner">
          <h2 className="cta-banner-title" style={{ color: '#FFFFFF' }}>
            Ready to Orchestrate Studio-Grade Videos?
          </h2>
          <p className="cta-banner-subtitle" style={{ color: '#FFFFFF' }}>
            Transform any syllabus, technical concept, or research paper into 4K mathematical courses 
            and publish directly to your YouTube channel.
          </p>

          <div className="cta-banner-buttons">
            <button 
              onClick={() => {
                localStorage.setItem('role', 'user');
                navigate('/user/create');
              }}
              className="btn-cta-orange"
              style={{ fontSize: '1.05rem', padding: '0.95rem 2.2rem' }}
            >
              <Play size={18} fill="#FFFFFF" />
              Launch Creator Studio Now
            </button>

            <button 
              onClick={() => {
                localStorage.setItem('role', 'admin');
                navigate('/admin/studio');
              }}
              className="btn-cta-violet"
              style={{ fontSize: '1.05rem', padding: '0.95rem 2rem' }}
            >
              <Layers size={18} />
              Explore Workflow Architect
            </button>
          </div>
        </div>
      </section>

      {/* Enterprise Multi-Column Footer */}
      <footer className="landing-footer-enterprise">
        <div className="footer-enterprise-content">
          {/* Col 1: Brand Info */}
          <div className="footer-brand-col">
            <MaestroLogo size="md" />
            <p className="footer-brand-desc">
              Multi-Agent Autonomous Engine for Scalable Transmedia Rendering &amp; Orchestration. 
              Built for high-precision technical courses, creative narratives, and automated channel syndication.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button 
                onClick={() => navigate('/user/publisher')} 
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.78rem' }}
              >
                <Share2 size={13} /> YouTube Hub
              </button>
              <button 
                onClick={() => navigate('/admin/analytics')} 
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.78rem' }}
              >
                <Activity size={13} /> Telemetry
              </button>
            </div>
          </div>

          {/* Col 2: Creator Tools */}
          <div className="footer-links-col">
            <h4>Creator Studio</h4>
            <button onClick={() => { localStorage.setItem('role', 'user'); navigate('/user/create'); }}>
              Create Video (4 Modes)
            </button>
            <button onClick={() => { localStorage.setItem('role', 'user'); navigate('/user/videos'); }}>
              Rendered MP4 Gallery
            </button>
            <button onClick={() => { localStorage.setItem('role', 'user'); navigate('/user/publisher'); }}>
              YouTube Scheduled Queue
            </button>
            <button onClick={() => { localStorage.setItem('role', 'user'); navigate('/user/history'); }}>
              Task Execution History
            </button>
            <button onClick={() => { localStorage.setItem('role', 'user'); navigate('/user/settings'); }}>
              Preferences &amp; Voices
            </button>
          </div>

          {/* Col 3: Admin Console */}
          <div className="footer-links-col">
            <h4>Administration</h4>
            <button onClick={() => { localStorage.setItem('role', 'admin'); navigate('/admin/studio'); }}>
              Visual Workflow Architect
            </button>
            <button onClick={() => { localStorage.setItem('role', 'admin'); navigate('/admin/iam'); }}>
              IAM &amp; Permission Matrix
            </button>
            <button onClick={() => { localStorage.setItem('role', 'admin'); navigate('/admin/providers'); }}>
              Engine Providers (Ollama/ComfyUI)
            </button>
            <button onClick={() => { localStorage.setItem('role', 'admin'); navigate('/admin/jobs'); }}>
              Background Job Manager
            </button>
            <button onClick={() => { localStorage.setItem('role', 'admin'); navigate('/admin/analytics'); }}>
              System Analytics
            </button>
          </div>

          {/* Col 4: Architecture */}
          <div className="footer-links-col">
            <h4>Architecture &amp; Specs</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              <div><strong>Core:</strong> Python 3.12 + FastAPI</div>
              <div><strong>LLMs:</strong> Qwen 14B / Gemma 4B</div>
              <div><strong>Rendering:</strong> Manim v0.19 (4K)</div>
              <div><strong>Visuals:</strong> ComfyUI Diffusion</div>
              <div><strong>Speech:</strong> Microsoft Edge TTS</div>
              <div><strong>Database:</strong> SQLite WAL Mode</div>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom-bar">
          <div className="footer-copyright">
            © {new Date().getFullYear()} MAESTRO Autonomous Video Engine. All rights reserved.
          </div>
          <div className="system-status-indicator">
            <span className="live-dot" />
            <span>Multi-Agent Services Active &amp; Operational</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
