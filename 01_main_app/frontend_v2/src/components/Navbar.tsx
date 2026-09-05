import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Search, 
  ArrowLeftRight, 
  Video, 
  Shield, 
  LogOut, 
  ChevronDown
} from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = location.pathname.startsWith('/admin');
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const [projectName, setProjectName] = useState('MAESTRO');
  const [projectFullName, setProjectFullName] = useState('Multi-Agent Autonomous Engine for Scalable Transmedia Production & Orchestration');

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        if (data.project) setProjectName(data.project);
        if (data.full_name) setProjectFullName(data.full_name);
      })
      .catch(() => {});
  }, []);

  const togglePortal = () => {
    if (isAdmin) {
      navigate('/user/create');
    } else {
      navigate('/admin/studio');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('role');
    navigate('/login');
  };

  return (
    <header className="navbar-enterprise">
      {/* Left: Brand Identity */}
      <div className="navbar-brand-section">
        <div className="brand-logo-badge" onClick={() => navigate(isAdmin ? '/admin/studio' : '/user/create')} title={projectFullName}>
          <div className="logo-spark-icon">
            <Video size={18} className="logo-icon-svg" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span className="brand-title">{projectName}</span>
            <span className="brand-sub-badge">ENGINE</span>
          </div>
        </div>

        <div className="navbar-divider-v" />

        <span className={`portal-tag-pill ${isAdmin ? 'portal-tag-admin' : 'portal-tag-user'}`}>
          {isAdmin ? 'ADMIN CONSOLE' : 'CREATOR STUDIO'}
        </span>
      </div>

      {/* Middle: Universal Search Bar */}
      <div className="navbar-search-section">
        <div className="search-bar-enterprise">
          <Search size={16} className="search-icon-enterprise" />
          <input 
            type="text" 
            placeholder={isAdmin ? "Search workflows, nodes, engine configs... (Cmd+K)" : "Search courses, videos, topics... (Cmd+K)"} 
          />
        </div>
      </div>

      {/* Right: Actions, Portal Switcher & Profile */}
      <div className="navbar-actions-section">
        {/* Portal Switcher Button */}
        <button 
          onClick={togglePortal}
          className="portal-switch-pill"
          title={isAdmin ? "Switch to Creator Portal" : "Switch to Admin Console"}
        >
          <ArrowLeftRight size={14} />
          <span>{isAdmin ? 'Creator Studio' : 'Admin Console'}</span>
        </button>

        <div className="navbar-divider-v" />

        {/* User Greeting */}
        <div className="user-greeting-block">
          <span className="user-greeting-name">Welcome back, Shamith</span>
          <span className="user-greeting-role">{isAdmin ? 'System Administrator' : 'Video Creator'}</span>
        </div>

        {/* Profile Avatar & Menu */}
        <div className="profile-menu-container" ref={profileRef}>
          <button 
            className="avatar-btn"
            onClick={() => setProfileOpen(!profileOpen)}
            title="Account Menu"
          >
            <span className="avatar-initials">SM</span>
            <ChevronDown size={13} className="avatar-chevron" />
          </button>

          {profileOpen && (
            <div className="profile-dropdown-card">
              <div className="dropdown-user-header">
                <div className="dropdown-avatar">SM</div>
                <div className="dropdown-user-meta">
                  <span className="dropdown-name">Shamith</span>
                  <span className="dropdown-email">shamith@autocourse.ai</span>
                  <span className="dropdown-badge">{isAdmin ? 'Admin' : 'Creator'}</span>
                </div>
              </div>

              <div className="dropdown-divider" />

              <button className="dropdown-item" onClick={togglePortal}>
                <ArrowLeftRight size={15} />
                <span>Switch to {isAdmin ? 'Creator Portal' : 'Admin Console'}</span>
              </button>

              <button className="dropdown-item" onClick={() => navigate(isAdmin ? '/admin/iam' : '/user/settings')}>
                <Shield size={15} />
                <span>{isAdmin ? 'Permissions & Policies' : 'Preferences'}</span>
              </button>

              <div className="dropdown-divider" />

              <button className="dropdown-item dropdown-logout" onClick={handleLogout}>
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

