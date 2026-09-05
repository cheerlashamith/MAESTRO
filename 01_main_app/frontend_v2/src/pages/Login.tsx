import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Wand2 } from 'lucide-react';
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
      navigate('/user/studio');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-icon-large">
            {/* Custom MAESTRO Orchestration SVG Icon */}
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Central Conductor Spark */}
              <path d="M18 4L20.2 13.8L30 16L20.2 18.2L18 28L15.8 18.2L6 16L15.8 13.8L18 4Z" fill="#FFFFFF" />
              {/* Orbital Agent Nodes */}
              <circle cx="6" cy="8" r="2.5" fill="#93C5FD" />
              <circle cx="30" cy="8" r="2.5" fill="#C4B5FD" />
              <circle cx="6" cy="28" r="2" fill="#93C5FD" />
              <circle cx="30" cy="28" r="2" fill="#C4B5FD" />
              <path d="M8.5 9.5C12 13 15 14.5 18 15" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" strokeDasharray="2 2" />
              <path d="M27.5 9.5C24 13 21 14.5 18 15" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" strokeDasharray="2 2" />
            </svg>
          </div>
          <h1 className="login-title-maestro">MAESTRO</h1>
          <p className="login-subtitle-maestro">
            Multi-Agent Autonomous Engine for Scalable Transmedia Production &amp; Orchestration
          </p>
          <div className="login-portal-badge">
            SELECT ACCESS PORTAL
          </div>
        </div>

        <div className="login-options">
          <button className="login-btn user-btn" onClick={() => handleLogin('shamith')}>
            <div className="btn-icon">
              <Wand2 size={24} />
            </div>
            <div className="btn-text">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3>Shamith (Creator Portal)</h3>
                <span className="account-tag creator">CREATOR</span>
              </div>
              <p>Visual AI Studio, Video Generation & YouTube Publisher</p>
            </div>
          </button>

          <button className="login-btn admin-btn" onClick={() => handleLogin('shamith_admin')}>
            <div className="btn-icon">
              <ShieldCheck size={24} />
            </div>
            <div className="btn-text">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3>Shamith Admin (Admin Portal)</h3>
                <span className="account-tag admin">SUPER ADMIN</span>
              </div>
              <p>Dynamic IAM Permission Matrix, Providers & Workflow Architect</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
