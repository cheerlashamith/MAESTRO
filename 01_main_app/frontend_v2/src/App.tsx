import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Login from './pages/Login';

// User Portal Pages
import CreateVideo from './pages/user/CreateVideo';
import GenerationProgress from './pages/user/GenerationProgress';
import MyVideos from './pages/user/MyVideos';
import YouTubePublisher from './pages/user/YouTubePublisher';
import History from './pages/user/History';
import Settings from './pages/user/Settings';

// Admin Portal Pages
import IAMPage from './pages/admin/IAMPage';
import WorkflowArchitectPage from './pages/admin/WorkflowArchitectPage';
import SystemDashboard from './pages/admin/SystemDashboard';
import Configuration from './pages/admin/Configuration';
import BrainManager from './pages/admin/BrainManager';
import PluginManager from './pages/admin/PluginManager';
import JobManager from './pages/admin/JobManager';
import CacheManager from './pages/admin/CacheManager';
import Analytics from './pages/admin/Analytics';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        
        {/* User Portal Routes */}
        <Route path="/user" element={<AppLayout />}>
          <Route index element={<Navigate to="/user/create" replace />} />
          <Route path="create" element={<CreateVideo />} />
          <Route path="progress" element={<GenerationProgress />} />
          <Route path="videos" element={<MyVideos />} />
          <Route path="publisher" element={<YouTubePublisher />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Settings />} />
          <Route path="studio" element={<Navigate to="/admin/studio" replace />} />
          <Route path="dashboard" element={<Navigate to="/user/create" replace />} />
        </Route>

        {/* Admin Portal Routes */}
        <Route path="/admin" element={<AppLayout />}>
          <Route index element={<Navigate to="/admin/iam" replace />} />
          <Route path="iam" element={<IAMPage />} />
          <Route path="studio" element={<WorkflowArchitectPage />} />
          <Route path="providers" element={<Configuration />} />
          <Route path="config" element={<Configuration />} />
          <Route path="system" element={<SystemDashboard />} />
          <Route path="jobs" element={<JobManager />} />
          <Route path="brain" element={<BrainManager />} />
          <Route path="plugins" element={<PluginManager />} />
          <Route path="cache" element={<CacheManager />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
