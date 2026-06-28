import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useStats } from '../context/StatsContext';

function Layout({ user, onLogout }) {
  const { todayStats } = useStats();
  const location = useLocation();

  return (
    <div className="page" id="app-page">
      <nav className="sidebar">
        <div className="user-profile">
          <img src={user?.avatar_url || "https://ui-avatars.com/api/?name=" + (user?.name || 'U')} alt="Avatar" className="avatar" />
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <span>{user?.name || 'User'}</span>
            {!user?.google_id && (
              <a 
                href={`http://localhost:8000/auth/google/login?token=${localStorage.getItem('auth_token')}`}
                style={{ fontSize: '10px', color: 'var(--color-primary)', textDecoration: 'none', marginTop: '2px', fontWeight: 600 }}
                title="Connect Google Calendar for 2-way sync"
              >
                + Connect Calendar
              </a>
            )}
          </div>
        </div>
        
        <ul className="nav-links">
          <li><NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>🏠 Home</NavLink></li>
          <li><NavLink to="/today" className={({isActive}) => isActive ? 'active' : ''}>📅 Today</NavLink></li>
          <li><NavLink to="/focus" className={({isActive}) => isActive ? 'active' : ''}>⏱️ Focus</NavLink></li>
        </ul>

        <div className="sidebar-section">
          <div className="section-title">DAILY RITUALS</div>
          <ul className="nav-links">
            <li><NavLink to="/today?tab=planning" className={() => location.pathname === '/today' && location.search.includes('tab=planning') ? 'active' : ''}>📝 Daily planning</NavLink></li>
            <li><NavLink to="/today?tab=shutdown" className={() => location.pathname === '/today' && location.search.includes('tab=shutdown') ? 'active' : ''}>🏁 Daily shutdown</NavLink></li>
            <li><NavLink to="/today?tab=highlights" className={() => location.pathname === '/today' && location.search.includes('tab=highlights') ? 'active' : ''}>✨ Daily highlights</NavLink></li>
          </ul>
        </div>

        <div className="sidebar-section">
          <div className="section-title">WEEKLY RITUALS</div>
          <ul className="nav-links">
            <li><NavLink to="/weekly-planning" className={({isActive}) => isActive ? 'active' : ''}>📅 Weekly planning</NavLink></li>
            <li><NavLink to="/weekly-review" className={({isActive}) => isActive ? 'active' : ''}>🔍 Weekly review</NavLink></li>
          </ul>
        </div>

        <ul className="nav-links">
          <li><NavLink to="/commitments" className={({isActive}) => isActive ? 'active' : ''}>📋 Backlog</NavLink></li>
          <li><NavLink to="/analytics" className={({isActive}) => isActive ? 'active' : ''}>📊 Analytics</NavLink></li>
        </ul>

        <button onClick={onLogout} className="btn btn-ghost mt-auto" style={{marginTop: 'auto'}}>Logout</button>
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
