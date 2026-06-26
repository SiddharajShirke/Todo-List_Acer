import { Outlet, NavLink } from 'react-router-dom';

function Layout({ user, onLogout }) {
  return (
    <div className="page" id="app-page">
      <nav className="sidebar">
        <div className="user-profile">
          <img src={user?.avatar_url || "https://ui-avatars.com/api/?name=" + (user?.name || 'U')} alt="Avatar" className="avatar" />
          <span>{user?.name || 'User'}</span>
        </div>
        <ul className="nav-links">
          <li><NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink></li>
          <li><NavLink to="/commitments" className={({isActive}) => isActive ? 'active' : ''}>Commitments</NavLink></li>
          <li><NavLink to="/focus" className={({isActive}) => isActive ? 'active' : ''}>Focus</NavLink></li>
          <li><NavLink to="/analytics" className={({isActive}) => isActive ? 'active' : ''}>Analytics</NavLink></li>
        </ul>
        <button onClick={onLogout} className="btn btn-ghost mt-auto">Logout</button>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
