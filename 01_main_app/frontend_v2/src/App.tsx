import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Login from './pages/Login';
import Dashboard from './pages/user/Dashboard';
import CreateVideo from './pages/user/CreateVideo';
import GenerationProgress from './pages/user/GenerationProgress';
import MyVideos from './pages/user/MyVideos';
import YouTubePublisher from './pages/user/YouTubePublisher';
import History from './pages/user/History';
import Settings from './pages/user/Settings';
import SystemDashboard from './pages/admin/SystemDashboard';
import BrainManager from './pages/admin/BrainManager';
import PluginManager from './pages/admin/PluginManager';
import JobManager from './pages/admin/JobManager';
import CacheManager from './pages/admin/CacheManager';
import Analytics from './pages/admin/Analytics';
import AnalyticsDashboard from './pages/admin/AnalyticsDashboard';
import Configuration from './pages/admin/Configuration';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        
        {/* User Routes */}
        <Route path="/user" element={<AppLayout />}>
          <Route index element={<Navigate to="/user/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="create" element={<CreateVideo />} />
          <Route path="progress" element={<GenerationProgress />} />
          <Route path="videos" element={<MyVideos />} />
          <Route path="publisher" element={<YouTubePublisher />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Admin Routes */}
        <Route path="/admin" element={<AppLayout />}>
          <Route index element={<Navigate to="/admin/system" replace />} />
          <Route path="system" element={<SystemDashboard />} />
          <Route path="brain" element={<BrainManager />} />
          <Route path="plugins" element={<PluginManager />} />
          <Route path="jobs" element={<JobManager />} />
          <Route path="cache" element={<CacheManager />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="analytics-dashboard" element={<AnalyticsDashboard />} />
          <Route path="config" element={<Configuration />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
