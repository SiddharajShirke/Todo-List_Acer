import { Outlet, NavLink } from 'react-router-dom';
import { useStats } from '../context/StatsContext';

function Layout({ user, onLogout }) {
  const { todayStats } = useStats();

  return (
    <div className="page" id="app-page">
      <nav className="sidebar">
        <div className="user-profile">
          <img src={user?.avatar_url || "https://ui-avatars.com/api/?name=" + (user?.name || 'U')} alt="Avatar" className="avatar" />
          <span>{user?.name || 'User'}</span>
        </div>
        <ul className="nav-links">
          <li><NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink></li>
          <li><NavLink to="/today" className={({isActive}) => isActive ? 'active' : ''}>Today</NavLink></li>
          <li><NavLink to="/commitments" className={({isActive}) => isActive ? 'active' : ''}>Commitments</NavLink></li>
          <li><NavLink to="/focus" className={({isActive}) => isActive ? 'active' : ''}>Focus</NavLink></li>
          <li><NavLink to="/analytics" className={({isActive}) => isActive ? 'active' : ''}>Analytics</NavLink></li>
        </ul>
        <button onClick={onLogout} className="btn btn-ghost mt-auto">Logout</button>
      </nav>
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column' }}>
        {todayStats && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', fontSize: '0.875rem', padding: '16px 24px', background: 'var(--color-surface-1)', borderBottom: '1px solid var(--color-surface-2)' }}>
            <span>🕐 {todayStats.total_hours}h today</span>
            <span>🍅 {todayStats.pomodoros_completed} pomodoros</span>
            <span>🔥 {todayStats.streak_days}d streak</span>
          </div>
        )}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default Layout;
