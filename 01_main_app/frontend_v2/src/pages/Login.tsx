import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Wand2, ArrowLeft } from 'lucide-react';
import MaestroLogo from '../components/MaestroLogo';
import './Login.css';

export default function Login() {
  const navigate = useNavigate();

  const handleLogin = async (username: 'shamith' | 'shamith_admin') => {
    try {
      await fetch('/api/iam/switch-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
    } catch (e) {
      console.error('Failed to sync session', e);
    }

    if (username === 'shamith_admin') {
      localStorage.setItem('role', 'admin');
      navigate('/admin/iam');
    } else {
      localStorage.setItem('role', 'user');
      navigate('/user/create');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        {/* Back to Home Link */}
        <div style={{ width: '100%', display: 'flex', justifyContent: 'flex-start' }}>
          <button 
            onClick={() => navigate('/')}
            className="login-back-btn"
            title="Return to Landing Page"
          >
            <ArrowLeft size={14} />
            <span>Back to Home</span>
          </button>
        </div>

        <div className="login-header">
          <MaestroLogo size="lg" showText={false} />
          <h1 className="login-title-maestro">MAESTRO</h1>
          <p className="login-subtitle-maestro">
            Multi-Agent Autonomous Engine for Scalable Transmedia Production &amp; Orchestration
          </p>
          <div className="login-portal-badge">
            SELECT ACCESS PORTAL
          </div>
        </div>

        <div className="login-options">
          {/* Creator Portal Button with Orange Hover & Badge */}
          <button className="login-btn user-btn" onClick={() => handleLogin('shamith')}>
            <div className="btn-icon user-icon">
              <Wand2 size={24} />
            </div>
            <div className="btn-text">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3>Shamith (Creator Portal)</h3>
                <span className="account-tag creator">CREATOR</span>
              </div>
              <p>Visual AI Studio, 4K Video Generation & YouTube Publisher Hub</p>
            </div>
          </button>

          {/* Admin Portal Button with Violet Theme */}
          <button className="login-btn admin-btn" onClick={() => handleLogin('shamith_admin')}>
            <div className="btn-icon admin-icon">
              <ShieldCheck size={24} />
            </div>
            <div className="btn-text">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3>Shamith Admin (Admin Portal)</h3>
                <span className="account-tag admin">SUPER ADMIN</span>
              </div>
              <p>Dynamic IAM Permissions, AI Providers, Workflow Architect & Analytics</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
