function Dashboard({ user }) {
  return (
    <div id="dashboard-tab" className="tab-content">
      <header className="top-header">
        <h2>Dashboard</h2>
        <button className="btn btn-primary">+ Add Commitment</button>
      </header>
      <div className="stats-grid">
        <div className="stat-card"><h3>Focus Hours</h3><div className="stat-value">—</div></div>
        <div className="stat-card"><h3>Pomodoros</h3><div className="stat-value">—</div></div>
        <div className="stat-card"><h3>Streak</h3><div className="stat-value">—</div></div>
        <div className="stat-card"><h3>Sessions</h3><div className="stat-value">—</div></div>
      </div>
      <div className="dashboard-grid">
        <div className="commitments-section">
          <h3>Top Commitments</h3>
          <div className="list-container">Loading...</div>
        </div>
        <div className="reminders-section">
          <h3>Recent Reminders</h3>
          <div className="list-container">Loading...</div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
