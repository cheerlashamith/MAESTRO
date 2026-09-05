import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { 
  Video, 
  Activity, 
  Film, 
  History, 
  Settings,
  Server,
  ListTodo,
  BarChart3,
  LogOut,
  Share2,
  Shield,
  HardDrive,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAdminPortal = location.pathname.startsWith('/admin');

  return (
    <aside className="sidebar-enterprise">
      <div className="sidebar-section-header">
        <span className="sidebar-portal-heading">
          {isAdminPortal ? 'ADMINISTRATIVE SUITE' : 'CONTENT PRODUCTION'}
        </span>
        <span className="sidebar-portal-sub">
          {isAdminPortal ? 'Engine & IAM Control' : 'Video Creator Tools'}
        </span>
      </div>

      <div className="sidebar-nav-container">
        {/* USER PORTAL NAVIGATION - AI Studio is hidden here per user request! */}
        {!isAdminPortal && (
          <nav className="nav-item-list">
            <NavLink to="/user/create" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Video size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Create Video</span>
                <span className="nav-item-sub">Course, Story & Shorts</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/user/progress" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Activity size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Live Progress</span>
                <span className="nav-item-sub">Execution & HITL Review</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/user/videos" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Film size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">My Videos</span>
                <span className="nav-item-sub">Rendered MP4 Gallery</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/user/publisher" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Share2 size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">YouTube Publisher</span>
                <span className="nav-item-sub">SEO & Channel Upload</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/user/history" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <History size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Task History</span>
                <span className="nav-item-sub">Completed Generations</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/user/settings" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Settings size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Preferences</span>
                <span className="nav-item-sub">Voices & Resolution</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>
          </nav>
        )}

        {/* ADMIN PORTAL NAVIGATION - AI Studio Workflow Architect is here! */}
        {isAdminPortal && (
          <nav className="nav-item-list">
            <NavLink to="/admin/studio" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Sparkles size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Workflow Architect</span>
                <span className="nav-item-sub">AI Studio Visual Canvas</span>
              </div>
              <span className="admin-pill-badge">STUDIO</span>
            </NavLink>

            <NavLink to="/admin/iam" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Shield size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">IAM & Permissions</span>
                <span className="nav-item-sub">Role Matrix & Policies</span>
              </div>
              <span className="admin-pill-badge">RBAC</span>
            </NavLink>

            <NavLink to="/admin/providers" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <HardDrive size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Engine & Providers</span>
                <span className="nav-item-sub">Ollama, ComfyUI, TTS</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/admin/jobs" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <ListTodo size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">Jobs & Workers</span>
                <span className="nav-item-sub">Monitor Background Tasks</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/admin/system" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <Server size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">System Metrics</span>
                <span className="nav-item-sub">GPU & RAM Health</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>

            <NavLink to="/admin/analytics" className={({isActive}) => isActive ? "nav-item-row active" : "nav-item-row"}>
              <div className="nav-item-icon-box">
                <BarChart3 size={17} />
              </div>
              <div className="nav-item-meta">
                <span className="nav-item-title">System Analytics</span>
                <span className="nav-item-sub">Throughput & Success</span>
              </div>
              <ChevronRight size={14} className="nav-item-chevron" />
            </NavLink>
          </nav>
        )}
      </div>

      {/* Footer Account Status */}
      <div className="sidebar-enterprise-footer">
        <div className="sidebar-user-pill">
          <div className="sidebar-avatar-circle">
            SM
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">Shamith</span>
            <span className="sidebar-user-role">{isAdminPortal ? 'System Administrator' : 'Video Creator'}</span>
          </div>
          <button 
            className="sidebar-logout-btn" 
            title="Sign Out"
            onClick={() => {
              localStorage.removeItem('role');
              navigate('/login');
            }}
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}

