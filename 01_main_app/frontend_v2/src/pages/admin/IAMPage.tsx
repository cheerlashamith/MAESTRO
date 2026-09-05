import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Users, 
  Save, 
  Plus, 
  CheckCircle2, 
  Lock, 
  UserCheck, 
  SlidersHorizontal
} from 'lucide-react';
import './IAMPage.css';

interface Permission {
  id: string;
  codename: string;
  name: string;
  module: string;
}

interface Role {
  id: string;
  name: string;
  slug: string;
  description: string;
  permissions: string[];
  scopes: Record<string, { scope: string; enabled: boolean }>;
  is_system: boolean;
}

interface UserProfile {
  id: string;
  username: string;
  display_name: string;
  email: string;
  avatar: string;
  role_slug: string;
  department: string;
  portal_access: string[];
}

export default function IAMPage() {
  const [activeTab, setActiveTab] = useState<'matrix' | 'roles' | 'users'>('matrix');
  const [modules, setModules] = useState<Record<string, Permission[]>>({});
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleSlug, setSelectedRoleSlug] = useState<string>('creator');
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  // Local changes to matrix
  const [activePermissions, setActivePermissions] = useState<Set<string>>(new Set());
  const [scopeMap, setScopeMap] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New role modal state
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleSlug, setNewRoleSlug] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [matrixRes, usersRes, curRes] = await Promise.all([
        fetch('/api/iam/matrix'),
        fetch('/api/iam/users'),
        fetch('/api/iam/current-user')
      ]);

      const matrixData = await matrixRes.json();
      const usersData = await usersRes.json();
      const curData = await curRes.json();

      setModules(matrixData.modules || {});
      setRoles(matrixData.roles || []);
      setUsers(usersData.users || []);
      setCurrentUser(curData);

      // Initialize selected role
      const initialRole = (matrixData.roles || []).find((r: Role) => r.slug === selectedRoleSlug) || matrixData.roles[0];
      if (initialRole) {
        setSelectedRoleSlug(initialRole.slug);
        syncRoleState(initialRole);
      }
    } catch (err) {
      console.error('Error loading IAM data', err);
    }
  };

  const syncRoleState = (role: Role) => {
    setActivePermissions(new Set(role.permissions || []));
    const scopes: Record<string, string> = {};
    if (role.scopes) {
      Object.entries(role.scopes).forEach(([k, v]) => {
        scopes[k] = v.scope || '*';
      });
    }
    setScopeMap(scopes);
    setHasChanges(false);
  };

  const handleSelectRole = (slug: string) => {
    setSelectedRoleSlug(slug);
    const r = roles.find(role => role.slug === slug);
    if (r) {
      syncRoleState(r);
    }
  };

  const togglePermission = (codename: string) => {
    const next = new Set(activePermissions);
    if (next.has(codename)) {
      next.delete(codename);
    } else {
      next.add(codename);
      if (!scopeMap[codename]) {
        setScopeMap(prev => ({ ...prev, [codename]: '*' }));
      }
    }
    setActivePermissions(next);
    setHasChanges(true);
  };

  const handleScopeChange = (codename: string, scopeVal: string) => {
    setScopeMap(prev => ({ ...prev, [codename]: scopeVal }));
    setHasChanges(true);
  };

  const handleSaveMatrix = async () => {
    setSaving(true);
    try {
      const scopesFormatted: Record<string, any> = {};
      activePermissions.forEach(p => {
        scopesFormatted[p] = {
          scope: scopeMap[p] || '*',
          enabled: true
        };
      });

      const res = await fetch('/api/iam/matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role_slug: selectedRoleSlug,
          permissions: Array.from(activePermissions),
          scopes: scopesFormatted
        })
      });

      if (res.ok) {
        setToastMessage('Permissions Matrix saved successfully!');
        setHasChanges(false);
        loadData();
      } else {
        alert('Failed to save permissions');
      }
    } catch (err) {
      alert('Error saving matrix: ' + err);
    }
    setSaving(false);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSwitchUser = async (username: string) => {
    try {
      const res = await fetch('/api/iam/switch-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
      const data = await res.json();
      setCurrentUser(data);
      localStorage.setItem('role', data.role_slug === 'admin' ? 'admin' : 'user');
      setToastMessage(`Switched active session to ${data.display_name} (${data.role_slug})`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      alert('Failed to switch user account: ' + err);
    }
  };

  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/iam/roles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newRoleName,
          slug: newRoleSlug,
          description: newRoleDesc,
          permissions: Array.from(activePermissions),
          scopes: {}
        })
      });
      if (res.ok) {
        setShowRoleModal(false);
        setNewRoleName('');
        setNewRoleSlug('');
        setNewRoleDesc('');
        loadData();
        setToastMessage('Role created successfully!');
      } else {
        const err = await res.json();
        alert('Error: ' + (err.detail || 'Could not create role'));
      }
    } catch (err) {
      alert('Failed to create role: ' + err);
    }
  };

  return (
    <div className="iam-container">
      {/* Top Header */}
      <div className="iam-header glass-panel">
        <div>
          <div className="iam-badge"><Shield size={14} /> SECURITY & ACCESS CONTROL</div>
          <h1>Identity & Access Management (IAM)</h1>
          <p className="text-muted">Directly manage dynamic RBAC policies, resource scopes, and user account assignments.</p>
        </div>

        {/* Current Active Account Card */}
        {currentUser && (
          <div className="active-account-card">
            <div className="account-avatar">{currentUser.avatar || 'US'}</div>
            <div className="account-details">
              <span className="account-name">{currentUser.display_name}</span>
              <span className="account-role-tag">{currentUser.role_details?.name || currentUser.role_slug}</span>
            </div>
            <div className="account-status-dot" title="Active Session"></div>
          </div>
        )}
      </div>

      {toastMessage && (
        <div className="iam-toast">
          <CheckCircle2 size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="iam-tabs">
        <button 
          className={`iam-tab-btn ${activeTab === 'matrix' ? 'active' : ''}`}
          onClick={() => setActiveTab('matrix')}
        >
          <SlidersHorizontal size={16} />
          <span>Permission Matrix</span>
        </button>
        <button 
          className={`iam-tab-btn ${activeTab === 'roles' ? 'active' : ''}`}
          onClick={() => setActiveTab('roles')}
        >
          <Shield size={16} />
          <span>Roles & Policies ({roles.length})</span>
        </button>
        <button 
          className={`iam-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <Users size={16} />
          <span>User Accounts & Switching</span>
        </button>
      </div>

      {/* TAB 1: PERMISSION MATRIX (Inspired by sasi-erp PermissionMatrix.tsx) */}
      {activeTab === 'matrix' && (
        <div className="matrix-view glass-panel">
          <div className="matrix-toolbar">
            <div className="role-selector-group">
              <label>Configuring Role:</label>
              <div className="role-pills">
                {roles.map(r => (
                  <button
                    key={r.slug}
                    className={`role-pill ${selectedRoleSlug === r.slug ? 'active' : ''}`}
                    onClick={() => handleSelectRole(r.slug)}
                  >
                    {r.name}
                    {r.is_system && <span className="system-tag">SYS</span>}
                  </button>
                ))}
              </div>
            </div>

            <button 
              className="btn btn-primary save-matrix-btn"
              onClick={handleSaveMatrix}
              disabled={!hasChanges || saving}
            >
              <Save size={16} />
              {saving ? 'Saving Changes...' : 'Save Matrix'}
            </button>
          </div>

          <div className="matrix-table-container">
            <table className="permission-matrix-table">
              <thead>
                <tr>
                  <th style={{ width: '35%' }}>Permission & Resource Action</th>
                  <th style={{ width: '20%', textAlign: 'center' }}>Granted</th>
                  <th style={{ width: '45%' }}>Scope Policy / Access Limit</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(modules).map(([moduleName, permList]) => (
                  <React.Fragment key={moduleName}>
                    <tr className="module-group-header">
                      <td colSpan={3}>
                        <div className="module-group-title">
                          <Lock size={14} />
                          <span>{moduleName.toUpperCase()}</span>
                          <span className="badge-count">{permList.length} actions</span>
                        </div>
                      </td>
                    </tr>
                    {permList.map(perm => {
                      const isChecked = activePermissions.has(perm.codename);
                      const currentScope = scopeMap[perm.codename] || '*';

                      return (
                        <tr key={perm.id} className={`perm-row ${isChecked ? 'row-enabled' : ''}`}>
                          <td>
                            <div className="perm-info">
                              <span className="perm-name">{perm.name}</span>
                              <code className="perm-codename">{perm.codename}</code>
                            </div>
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              className="perm-checkbox"
                              checked={isChecked}
                              onChange={() => togglePermission(perm.codename)}
                            />
                          </td>
                          <td>
                            <div className="scope-select-wrap">
                              <select 
                                className="scope-dropdown"
                                value={currentScope}
                                disabled={!isChecked}
                                onChange={(e) => handleScopeChange(perm.codename, e.target.value)}
                              >
                                <option value="*">Full Access (*)</option>
                                <option value="user_id">Self Only (user_id)</option>
                                <option value="workspace_id">Workspace Only (workspace_id)</option>
                              </select>
                              <span className="scope-hint">
                                {currentScope === '*' ? 'Unrestricted access across all jobs' :
                                 currentScope === 'user_id' ? 'Limited to resources created by user' :
                                 'Limited to organization workspace'}
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: ROLES MANAGEMENT */}
      {activeTab === 'roles' && (
        <div className="roles-view">
          <div className="roles-header">
            <h3>Enterprise Role Definitions</h3>
            <button className="btn btn-primary" onClick={() => setShowRoleModal(true)}>
              <Plus size={16} /> Create Custom Role
            </button>
          </div>

          <div className="roles-grid">
            {roles.map(r => (
              <div key={r.id} className="role-card glass-panel">
                <div className="role-card-top">
                  <div>
                    <h4>{r.name}</h4>
                    <code>{r.slug}</code>
                  </div>
                  <span className={`role-badge ${r.is_system ? 'system' : 'custom'}`}>
                    {r.is_system ? 'System Role' : 'Custom Role'}
                  </span>
                </div>
                <p className="role-desc">{r.description}</p>
                <div className="role-footer">
                  <span>{r.permissions?.length || 0} permissions assigned</span>
                  <button 
                    className="btn btn-sm btn-outline"
                    onClick={() => {
                      setSelectedRoleSlug(r.slug);
                      syncRoleState(r);
                      setActiveTab('matrix');
                    }}
                  >
                    Edit Matrix
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: USER ACCOUNTS & SESSION SWITCHER */}
      {activeTab === 'users' && (
        <div className="users-view glass-panel">
          <div className="users-header">
            <div>
              <h3>Accounts & Session Switcher</h3>
              <p className="text-muted">Seamlessly switch between your Creator account (User Portal) and Admin account.</p>
            </div>
          </div>

          <div className="user-cards-list">
            {users.map(u => {
              const isCurrent = currentUser?.username === u.username;

              return (
                <div key={u.id} className={`user-row ${isCurrent ? 'active-user' : ''}`}>
                  <div className="user-main-info">
                    <div className="user-avatar-large">{u.avatar}</div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <h4 className="user-display-name">{u.display_name}</h4>
                        {isCurrent && <span className="active-pill">CURRENT ACTIVE</span>}
                      </div>
                      <span className="user-meta-text">{u.email} · {u.department}</span>
                    </div>
                  </div>

                  <div className="user-actions-cluster">
                    <span className="role-chip">{u.role_slug.toUpperCase()}</span>
                    <button 
                      className={`btn ${isCurrent ? 'btn-secondary' : 'btn-primary'}`}
                      onClick={() => handleSwitchUser(u.username)}
                      disabled={isCurrent}
                    >
                      <UserCheck size={16} />
                      {isCurrent ? 'Active Account' : 'Switch to this Account'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Create Role Modal */}
      {showRoleModal && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <h3>Create New Role</h3>
            <form onSubmit={handleCreateRole}>
              <div className="form-group mb-3">
                <label>Role Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  required 
                  placeholder="e.g. Senior Producer"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                />
              </div>
              <div className="form-group mb-3">
                <label>Slug</label>
                <input 
                  type="text" 
                  className="form-control" 
                  required 
                  placeholder="e.g. senior_producer"
                  value={newRoleSlug}
                  onChange={(e) => setNewRoleSlug(e.target.value)}
                />
              </div>
              <div className="form-group mb-3">
                <label>Description</label>
                <textarea 
                  className="form-control" 
                  rows={3} 
                  placeholder="Describe role responsibilities..."
                  value={newRoleDesc}
                  onChange={(e) => setNewRoleDesc(e.target.value)}
                />
              </div>
              <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowRoleModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Role</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
