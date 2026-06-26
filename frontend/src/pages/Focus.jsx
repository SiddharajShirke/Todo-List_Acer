function Focus() {
  return (
    <div className="tab-content">
      <h2>Focus</h2>
      <div className="focus-layout">
        <div className="timer-section">
           <div className="mode-selector">
              <button className="mode-btn active">Pomodoro</button>
              <button className="mode-btn">Flowtime</button>
              <button className="mode-btn">Deep Work</button>
              <button className="mode-btn">Break</button>
           </div>
           <div className="timer-display-container">
             <div className="timer-text" style={{ position: 'relative', height: 260, width: 260, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '8px solid var(--color-primary)', borderRadius: '50%' }}>
                <div id="mode-label">🍅 Pomodoro</div>
                <div id="timer-display" style={{ fontSize: '3rem', fontWeight: 'bold' }}>25:00</div>
                <div id="pomodoro-number" className="muted">Session #1</div>
             </div>
           </div>
           <div className="timer-controls mt-6" style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button className="btn btn-primary btn-large">Start</button>
           </div>
        </div>
      </div>
    </div>
  );
}

export default Focus;
