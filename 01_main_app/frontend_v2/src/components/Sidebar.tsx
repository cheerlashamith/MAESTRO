import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Video, 
  Activity, 
  Film, 
  History, 
  Settings,
  Server,
  Brain,
  Plug,
  ListTodo,
  Database,
  BarChart3,
  Wrench,
  LogOut,
  Share2
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar() {
  const role = localStorage.getItem('role') || 'user';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon"></div>
          <h2>AutoCourse</h2>
        </div>
      </div>
      
      <div className="sidebar-content">
        {role === 'user' && (
          <div className="nav-section">
            <span className="section-title">USER</span>
            <nav>
              <NavLink to="/user/dashboard" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <LayoutDashboard size={18} />
                <span>Dashboard</span>
              </NavLink>
              <NavLink to="/user/create" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Video size={18} />
                <span>Create Video</span>
              </NavLink>
              <NavLink to="/user/progress" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Activity size={18} />
                <span>Progress</span>
              </NavLink>
              <NavLink to="/user/videos" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Film size={18} />
                <span>My Videos</span>
              </NavLink>
              <NavLink to="/user/publisher" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Share2 size={18} />
                <span>YouTube Publisher</span>
              </NavLink>
              <NavLink to="/user/history" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <History size={18} />
                <span>History</span>
              </NavLink>
              <NavLink to="/user/settings" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Settings size={18} />
                <span>Settings</span>
              </NavLink>
            </nav>
          </div>
        )}

        {role === 'admin' && (
          <div className="nav-section">
            <span className="section-title">ADMIN</span>
            <nav>
              <NavLink to="/admin/system" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Server size={18} />
                <span>System</span>
              </NavLink>
              <NavLink to="/admin/brain" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Brain size={18} />
                <span>Brain Manager</span>
              </NavLink>
              <NavLink to="/admin/plugins" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Plug size={18} />
                <span>Plugins</span>
              </NavLink>
              <NavLink to="/admin/jobs" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <ListTodo size={18} />
                <span>Jobs</span>
              </NavLink>
              <NavLink to="/admin/cache" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Database size={18} />
                <span>Cache</span>
              </NavLink>
              <NavLink to="/admin/analytics" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <BarChart3 size={18} />
                <span>System Analytics</span>
              </NavLink>
              <NavLink to="/admin/analytics-dashboard" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Activity size={18} />
                <span>Agent Analytics</span>
              </NavLink>
              <NavLink to="/admin/config" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
                <Wrench size={18} />
                <span>Configuration</span>
              </NavLink>
            </nav>
          </div>
        )}
      </div>
      
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="avatar">{role === 'admin' ? 'AD' : 'US'}</div>
          <div className="user-info">
            <span className="user-name">{role === 'admin' ? 'Demo Admin' : 'Demo User'}</span>
            <span className="user-role">{role === 'admin' ? 'System Administrator' : 'Video Creator'}</span>
          </div>
          <button 
            className="icon-btn logout-btn" 
            title="Log Out"
            onClick={() => {
              localStorage.removeItem('role');
              window.location.href = '/login';
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}
