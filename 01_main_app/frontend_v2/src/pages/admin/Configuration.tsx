import { useState, useEffect } from 'react';
import { 
  Save, 
  Key, 
  Video, 
  Server, 
  Cpu, 
  CheckCircle2, 
  RefreshCw,
  Play,
  HardDrive
} from 'lucide-react';
import './Configuration.css';

export default function Configuration() {
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [testResults, setTestResults] = useState<Record<string, any>>({});
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        setConfig(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch config", err);
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      if (res.ok) {
        setToast('Configuration persisted successfully!');
        setTimeout(() => setToast(null), 3000);
      } else {
        alert('Failed to save configuration');
      }
    } catch (err) {
      alert('Failed to save configuration: ' + err);
    }
    setSaving(false);
  };

  const handleChange = (section: string, key: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  const handleTestProvider = async (provider: string, urlOrKey?: string) => {
    setTestingKey(provider);
    try {
      const res = await fetch('/api/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          url: urlOrKey?.startsWith('http') ? urlOrKey : undefined,
          api_key: !urlOrKey?.startsWith('http') ? urlOrKey : undefined
        })
      });
      const data = await res.json();
      setTestResults(prev => ({ ...prev, [provider]: data }));
    } catch (err) {
      setTestResults(prev => ({ ...prev, [provider]: { ok: false, status: 'Error', error: String(err) } }));
    }
    setTestingKey(null);
  };

  if (loading) return <div style={{padding: '2rem'}}>Loading configuration...</div>;

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1>Provider Hub & System Configuration</h1>
          <p className="text-muted">Live test and configure MoneyPrinterTurbo, ComfyUI, Ollama, Cloud LLMs, and rendering engines.</p>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Save size={18} />
          {saving ? 'Saving...' : 'Save All Settings'}
        </button>
      </div>

      {toast && (
        <div className="glass-panel" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.5rem', background: 'rgba(34, 197, 94, 0.15)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#4ade80', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={16} />
          {toast}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        
        {/* MoneyPrinterTurbo Engine */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem' }}>
              <Server size={20} className="text-primary" />
              MoneyPrinterTurbo (Assembly Engine)
            </h2>
            <button 
              className="btn btn-sm btn-outline"
              onClick={() => handleTestProvider('mpt', config?.paths?.moneyprinter_api_url)}
              disabled={testingKey === 'mpt'}
            >
              {testingKey === 'mpt' ? <RefreshCw className="spin" size={14} /> : <Play size={14} />}
              Test Connection
            </button>
          </div>

          {testResults['mpt'] && (
            <div style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem', background: testResults['mpt'].ok ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: testResults['mpt'].ok ? '#4ade80' : '#f87171' }}>
              Status: {testResults['mpt'].status} {testResults['mpt'].latency_ms ? `(${testResults['mpt'].latency_ms}ms)` : ''}
            </div>
          )}

          <div className="form-group mb-3">
            <label>MPT API URL</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.paths?.moneyprinter_api_url || 'http://127.0.0.1:8080'}
              onChange={e => handleChange('paths', 'moneyprinter_api_url', e.target.value)}
            />
          </div>

          <div className="form-group mb-3">
            <label>MPT Root Directory</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.paths?.moneyprinter_root || ''}
              onChange={e => handleChange('paths', 'moneyprinter_root', e.target.value)}
              placeholder="C:/MoneyPrinterTurbo-Portable..."
            />
          </div>
        </div>

        {/* ComfyUI Diffusion Engine */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem' }}>
              <HardDrive size={20} className="text-pink" />
              ComfyUI (Story & Image Engine)
            </h2>
            <button 
              className="btn btn-sm btn-outline"
              onClick={() => handleTestProvider('comfyui', config?.paths?.comfyui_url)}
              disabled={testingKey === 'comfyui'}
            >
              {testingKey === 'comfyui' ? <RefreshCw className="spin" size={14} /> : <Play size={14} />}
              Test Connection
            </button>
          </div>

          {testResults['comfyui'] && (
            <div style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem', background: testResults['comfyui'].ok ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: testResults['comfyui'].ok ? '#4ade80' : '#f87171' }}>
              Status: {testResults['comfyui'].status} {testResults['comfyui'].vram_gb ? `(VRAM: ${testResults['comfyui'].vram_gb} GB)` : ''}
            </div>
          )}

          <div className="form-group mb-3">
            <label>ComfyUI Web URL</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.paths?.comfyui_url || 'http://127.0.0.1:8188'}
              onChange={e => handleChange('paths', 'comfyui_url', e.target.value)}
            />
          </div>

          <div className="form-group mb-3">
            <label>ComfyUI Root Directory</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.paths?.comfyui_root || ''}
              onChange={e => handleChange('paths', 'comfyui_root', e.target.value)}
              placeholder="C:/ComfyUI_windows_portable..."
            />
          </div>
        </div>

        {/* Ollama Local LLM */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem' }}>
              <Cpu size={20} className="text-purple" />
              Ollama (Local LLM Provider)
            </h2>
            <button 
              className="btn btn-sm btn-outline"
              onClick={() => handleTestProvider('ollama', config?.providers?.ollama_url)}
              disabled={testingKey === 'ollama'}
            >
              {testingKey === 'ollama' ? <RefreshCw className="spin" size={14} /> : <Play size={14} />}
              Test Models
            </button>
          </div>

          {testResults['ollama'] && (
            <div style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem', background: testResults['ollama'].ok ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: testResults['ollama'].ok ? '#4ade80' : '#f87171' }}>
              Status: {testResults['ollama'].status} · Available Models: {testResults['ollama'].models?.join(', ') || 'None found'}
            </div>
          )}

          <div className="form-group mb-3">
            <label>Ollama Endpoint URL</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.providers?.ollama_url || 'http://127.0.0.1:11434'}
              onChange={e => handleChange('providers', 'ollama_url', e.target.value)}
            />
          </div>

          <div className="form-group mb-3">
            <label>Curriculum Planner Model</label>
            <input 
              type="text" 
              className="form-control"
              value={config?.providers?.planner_model || 'qwen2.5:7b'}
              onChange={e => handleChange('providers', 'planner_model', e.target.value)}
            />
          </div>
        </div>

        {/* Cloud LLMs & B-Roll */}
        <div className="card glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem' }}>
              <Key size={20} className="text-amber" />
              External APIs (OpenAI & Pexels)
            </h2>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className="btn btn-sm btn-outline"
                onClick={() => handleTestProvider('openai', config?.providers?.openai_api_key)}
                disabled={testingKey === 'openai'}
              >
                Test OpenAI
              </button>
              <button 
                className="btn btn-sm btn-outline"
                onClick={() => handleTestProvider('pexels', config?.providers?.pexels_api_key)}
                disabled={testingKey === 'pexels'}
              >
                Test Pexels
              </button>
            </div>
          </div>

          {testResults['openai'] && (
            <div style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '0.5rem', fontSize: '0.85rem', background: testResults['openai'].ok ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: testResults['openai'].ok ? '#4ade80' : '#f87171' }}>
              OpenAI: {testResults['openai'].message || testResults['openai'].status}
            </div>
          )}

          {testResults['pexels'] && (
            <div style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.85rem', background: testResults['pexels'].ok ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', color: testResults['pexels'].ok ? '#4ade80' : '#f87171' }}>
              Pexels: {testResults['pexels'].message || testResults['pexels'].status}
            </div>
          )}

          <div className="form-group mb-3">
            <label>OpenAI API Key (Optional)</label>
            <input 
              type="password" 
              className="form-control"
              value={config?.providers?.openai_api_key || ''}
              onChange={e => handleChange('providers', 'openai_api_key', e.target.value)}
              placeholder="sk-proj-..."
            />
          </div>

          <div className="form-group mb-3">
            <label>Pexels B-Roll API Key</label>
            <input 
              type="password" 
              className="form-control"
              value={config?.providers?.pexels_api_key || ''}
              onChange={e => handleChange('providers', 'pexels_api_key', e.target.value)}
              placeholder="Enter Pexels API key..."
            />
          </div>
        </div>

        {/* Global Rendering Defaults */}
        <div className="card glass-panel" style={{ padding: '1.5rem', gridColumn: 'span 2' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.15rem', marginBottom: '1.25rem' }}>
            <Video size={20} className="text-emerald" />
            Global Video Rendering Defaults & Storage
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
            <div className="form-group">
              <label>Course Voice (EdgeTTS)</label>
              <select 
                className="form-control"
                value={config?.rendering?.course_voice || 'en-US-AndrewMultilingualNeural'}
                onChange={e => handleChange('rendering', 'course_voice', e.target.value)}
              >
                <option value="en-US-AndrewMultilingualNeural">en-US - Andrew (Multilingual Male)</option>
                <option value="en-US-JennyNeural">en-US - Jenny (Natural Female)</option>
                <option value="en-US-GuyNeural">en-US - Guy (Narrative Male)</option>
                <option value="en-US-AriaNeural">en-US - Aria (Expressive Female)</option>
                <option value="en-US-ChristopherNeural">en-US - Christopher (Authoritative Male)</option>
                <option value="en-US-EricNeural">en-US - Eric (Clear Male)</option>
                <option value="en-US-MichelleNeural">en-US - Michelle (Warm Female)</option>
                <option value="en-GB-RyanNeural">en-GB - Ryan (British Male)</option>
                <option value="en-GB-SoniaNeural">en-GB - Sonia (British Female)</option>
                <option value="en-GB-LibbyNeural">en-GB - Libby (Casual Female)</option>
                <option value="en-IN-PrabhatNeural">en-IN - Prabhat (Indian Male)</option>
                <option value="en-IN-NeerjaNeural">en-IN - Neerja (Indian Female)</option>
                <option value="en-AU-WilliamNeural">en-AU - William (Aussie Male)</option>
                <option value="en-AU-NatashaNeural">en-AU - Natasha (Aussie Female)</option>
                <option value="en-CA-LiamNeural">en-CA - Liam (Canadian Male)</option>
                <option value="en-CA-ClaraNeural">en-CA - Clara (Canadian Female)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Story Voice (EdgeTTS)</label>
              <select 
                className="form-control"
                value={config?.rendering?.story_voice || 'en-US-JennyNeural'}
                onChange={e => handleChange('rendering', 'story_voice', e.target.value)}
              >
                <option value="en-US-JennyNeural">en-US - Jenny (Natural Female)</option>
                <option value="en-US-AndrewMultilingualNeural">en-US - Andrew (Multilingual Male)</option>
                <option value="en-US-GuyNeural">en-US - Guy (Narrative Male)</option>
                <option value="en-US-AriaNeural">en-US - Aria (Expressive Female)</option>
                <option value="en-US-ChristopherNeural">en-US - Christopher (Authoritative Male)</option>
                <option value="en-US-EricNeural">en-US - Eric (Clear Male)</option>
                <option value="en-US-MichelleNeural">en-US - Michelle (Warm Female)</option>
                <option value="en-GB-RyanNeural">en-GB - Ryan (British Male)</option>
                <option value="en-GB-SoniaNeural">en-GB - Sonia (British Female)</option>
                <option value="en-IN-PrabhatNeural">en-IN - Prabhat (Indian Male)</option>
                <option value="en-IN-NeerjaNeural">en-IN - Neerja (Indian Female)</option>
                <option value="en-AU-WilliamNeural">en-AU - William (Aussie Male)</option>
                <option value="en-AU-NatashaNeural">en-AU - Natasha (Aussie Female)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Course Aspect Ratio</label>
              <select 
                className="form-control"
                value={config?.rendering?.course_aspect || '16:9'}
                onChange={e => handleChange('rendering', 'course_aspect', e.target.value)}
              >
                <option value="16:9">16:9 (Landscape)</option>
                <option value="9:16">9:16 (Vertical)</option>
                <option value="1:1">1:1 (Square)</option>
              </select>
            </div>

            <div className="form-group">
              <label>BGM Volume</label>
              <input 
                type="number" 
                step="0.01" 
                min="0" 
                max="1" 
                className="form-control"
                value={config?.rendering?.bgm_volume ?? 0.05}
                onChange={e => handleChange('rendering', 'bgm_volume', parseFloat(e.target.value))}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <div className="form-group">
              <label>Platform Brand Name</label>
              <input 
                type="text" 
                className="form-control"
                value={config?.project_name || 'MAESTRO'}
                onChange={e => setConfig((prev: any) => ({ ...prev, project_name: e.target.value }))}
                placeholder="MAESTRO"
              />
            </div>

            <div className="form-group">
              <label>Output Video Storage Location</label>
              <select 
                className="form-control"
                value={config?.paths?.outputs_dir || 'outputs'}
                onChange={e => handleChange('paths', 'outputs_dir', e.target.value)}
              >
                <option value="outputs">Standard Workspace (outputs/)</option>
                <option value="data/videos">Media Library (data/videos/)</option>
                <option value="data/storage">Enterprise Storage (data/storage/)</option>
              </select>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
