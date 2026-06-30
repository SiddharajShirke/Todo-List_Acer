import React, { useState, useEffect } from 'react';
import api from '../services/api';
import ObjectivePopover from '../components/ObjectivePopover';

// Utility to create a local date at 00:00:00 from a 'YYYY-MM-DD' string
const parseLocalDate = (dateStr) => {
  if (!dateStr) return new Date();
  const [y, m, d] = dateStr.split('-');
  return new Date(y, m - 1, d);
};

// Utility to format a Date object as 'YYYY-MM-DD' locally
const formatLocalDate = (d) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export default function WeeklyPlanning() {
  const [objectives, setObjectives] = useState([]);
  const [channels, setChannels] = useState([]);
  const [editingObjective, setEditingObjective] = useState(null);
  const [futureWeekOffset, setFutureWeekOffset] = useState(1);

  useEffect(() => {
    fetchObjectives();
    fetchChannels();
  }, []);

  // Sync with AI Agent actions
  useEffect(() => {
    const handleAiSync = () => {
      console.log('AI action completed, syncing Weekly Planning...');
      fetchObjectives();
    };
    window.addEventListener('ai_action_completed', handleAiSync);
    return () => window.removeEventListener('ai_action_completed', handleAiSync);
  }, []);

  const fetchObjectives = async () => {
    try {
      const res = await api.get('/api/weekly-objectives');
      setObjectives(Array.isArray(res) ? res : (res.data || []));
    } catch (error) {
      console.error('Error fetching weekly objectives:', error);
    }
  };

  const fetchChannels = async () => {
    try {
      const res = await api.get('/api/channels');
      setChannels(res.data || res);
    } catch (e) {
      console.error('Error fetching channels', e);
    }
  };

  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const thisMonday = new Date(now.setDate(diff));
  thisMonday.setHours(0,0,0,0);
  
  const futureMonday = new Date(thisMonday);
  futureMonday.setDate(futureMonday.getDate() + (7 * futureWeekOffset));
  const futureSunday = new Date(futureMonday);
  futureSunday.setDate(futureSunday.getDate() + 6);

  const futureLabel = futureWeekOffset === 1 
    ? 'Next week' 
    : `${futureMonday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${futureSunday.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;

  const thisWeekObjectives = [];
  const futureWeekObjectives = [];
  const pastObjectivesByWeek = {};
  const upcomingObjectivesByWeek = {};
  
  objectives.forEach(obj => {
    const startDate = parseLocalDate(obj.week_start_date);
    const diffTime = startDate - thisMonday;
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24)); 
    
    const weekStr = formatLocalDate(startDate);
    
    if (diffDays >= 0 && diffDays <= 6) {
      thisWeekObjectives.push(obj);
    } else if (diffDays < 0) {
      // Past weeks
      if (!pastObjectivesByWeek[weekStr]) {
        pastObjectivesByWeek[weekStr] = { startDate, objectives: [] };
      }
      pastObjectivesByWeek[weekStr].objectives.push(obj);
    } else {
      // Future weeks
      if (diffDays === 7 * futureWeekOffset) {
        futureWeekObjectives.push(obj);
      }
      if (!upcomingObjectivesByWeek[weekStr]) {
        upcomingObjectivesByWeek[weekStr] = { startDate, objectives: [] };
      }
      upcomingObjectivesByWeek[weekStr].objectives.push(obj);
    }
  });

  const sortedPastWeeks = Object.values(pastObjectivesByWeek).sort((a, b) => b.startDate - a.startDate);
  const sortedUpcomingWeeks = Object.values(upcomingObjectivesByWeek).sort((a, b) => a.startDate - b.startDate);

  const handleAddObjective = async (weekType) => {
    let start, end;
    if (weekType === 'this_week') {
      start = new Date(thisMonday);
      end = new Date(thisMonday);
      end.setDate(end.getDate() + 6);
    } else {
      start = new Date(futureMonday);
      end = new Date(futureSunday);
    }
    
    try {
      const res = await api.post('/api/weekly-objectives', {
        title: 'New Objective',
        week_start_date: formatLocalDate(start),
        week_end_date: formatLocalDate(end),
        status: 'planned'
      });
      const newObj = res.data || res;
      fetchObjectives();
      setEditingObjective({ ...newObj, isNew: true });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="weekly-planning-container" style={{ padding: '24px', color: 'var(--text-main)', height: '100%', display: 'flex' }}>
      
      <div style={{ flex: '1', maxWidth: '350px', marginRight: '40px', overflowY: 'auto', paddingRight: '10px' }}>
        <h2 style={{ fontSize: '28px', marginBottom: '8px' }}>Weekly objectives</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '32px', fontSize: '16px' }}>Set your objectives for the week.</p>
        
        {/* THIS WEEK SUMMARY */}
        {thisWeekObjectives.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '16px', color: '#8a8a8e', textTransform: 'uppercase', marginBottom: '12px' }}>This Week</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {thisWeekObjectives.map(obj => (
                <div key={obj.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px' }}>
                  <span style={{ color: obj.status === 'done' ? '#10B981' : '#8a8a8e', width: '18px' }}>{obj.status === 'done' ? '✓' : '○'}</span>
                  <span style={{ color: obj.status === 'done' ? '#8a8a8e' : '#fff', textDecoration: obj.status === 'done' ? 'line-through' : 'none' }}>{obj.title || 'Untitled Objective'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* UPCOMING WEEKS OBJECTIVES */}
        {sortedUpcomingWeeks.length > 0 && (
          <div>
            <h3 style={{ fontSize: '16px', color: '#8a8a8e', textTransform: 'uppercase', marginBottom: '16px' }}>Upcoming Weeks</h3>
            {sortedUpcomingWeeks.map(week => {
              const endDate = new Date(week.startDate);
              endDate.setDate(endDate.getDate() + 6);
              const weekLabel = week.startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' - ' + endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              
              const completedCount = week.objectives.filter(o => o.status === 'done').length;

              return (
                <div key={formatLocalDate(week.startDate)} style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px' }}>{weekLabel}</div>
                  <div style={{ fontSize: '14px', color: '#8a8a8e', marginBottom: '12px' }}>{completedCount} / {week.objectives.length} objectives completed</div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {week.objectives.map(obj => (
                      <div key={obj.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px' }}>
                        <span style={{ color: obj.status === 'done' ? '#10B981' : '#8a8a8e', width: '18px' }}>{obj.status === 'done' ? '✓' : '○'}</span>
                        <span style={{ color: obj.status === 'done' ? '#8a8a8e' : '#fff', textDecoration: obj.status === 'done' ? 'line-through' : 'none' }}>{obj.title || 'Untitled Objective'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* PAST WEEKS OBJECTIVES */}
        {sortedPastWeeks.length > 0 && (
          <div>
            <h3 style={{ fontSize: '16px', color: '#8a8a8e', textTransform: 'uppercase', marginBottom: '16px', marginTop: '24px' }}>Past Weeks</h3>
            {sortedPastWeeks.map(week => {
              const endDate = new Date(week.startDate);
              endDate.setDate(endDate.getDate() + 6);
              const weekLabel = week.startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' - ' + endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              
              const completedCount = week.objectives.filter(o => o.status === 'done').length;

              return (
                <div key={formatLocalDate(week.startDate)} style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px' }}>{weekLabel}</div>
                  <div style={{ fontSize: '14px', color: '#8a8a8e', marginBottom: '12px' }}>{completedCount} / {week.objectives.length} objectives completed</div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {week.objectives.map(obj => (
                      <div key={obj.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px' }}>
                        <span style={{ color: obj.status === 'done' ? '#10B981' : '#8a8a8e', width: '18px' }}>{obj.status === 'done' ? '✓' : '○'}</span>
                        <span style={{ color: obj.status === 'done' ? '#8a8a8e' : '#fff', textDecoration: obj.status === 'done' ? 'line-through' : 'none' }}>{obj.title || 'Untitled Objective'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ flex: '1', marginRight: '20px' }}>
        <h3 style={{ fontSize: '20px' }}>This week</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '16px' }}>Your objectives for this week</p>
        
        <button className="btn btn-ghost" style={{ width: '100%', textAlign: 'left', marginBottom: '16px', background: 'var(--color-surface-1)', fontSize: '16px', padding: '16px', borderRadius: '8px', border: '1px solid #3f3f42', color: '#fff', cursor: 'pointer' }} onClick={() => handleAddObjective('this_week')}>
          + Add objective
        </button>

        <div className="objectives-list">
          {thisWeekObjectives.map(obj => (
            <div key={obj.id} className="objective-card" style={{ padding: '16px', marginBottom: '12px', fontSize: '16px', background: '#242426', borderRadius: '8px', border: '1px solid #3f3f42', cursor: 'pointer' }} onClick={() => setEditingObjective(obj)}>
              <div style={{ marginBottom: '12px', fontWeight: '500' }}>{obj.title || 'Untitled Objective'}</div>
              <div style={{ fontSize: '14px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="checkbox-icon" style={{ width: '18px', height: '18px', display: 'inline-block', border: '1px solid #5c5c5e', borderRadius: '4px' }}></span>
                {obj.channel_id && <span style={{ color: 'var(--color-primary)', fontWeight: 'bold' }}># {channels.find(c => c.id === obj.channel_id)?.name}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: '1' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0' }}>
          <h3 style={{ fontSize: '20px' }}>{futureLabel}</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              onClick={() => setFutureWeekOffset(Math.max(1, futureWeekOffset - 1))}
              disabled={futureWeekOffset === 1}
              style={{ background: 'transparent', border: 'none', color: futureWeekOffset === 1 ? '#3f3f42' : '#8a8a8e', cursor: futureWeekOffset === 1 ? 'default' : 'pointer', fontSize: '20px', padding: '0 8px' }}
            >
              &lt;
            </button>
            <button 
              onClick={() => setFutureWeekOffset(futureWeekOffset + 1)}
              style={{ background: 'transparent', border: 'none', color: '#8a8a8e', cursor: 'pointer', fontSize: '20px', padding: '0 8px' }}
            >
              &gt;
            </button>
          </div>
        </div>
        
        <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '16px', marginTop: '6px' }}>Your objectives for {futureLabel.toLowerCase()}</p>
        
        <button className="btn btn-ghost" style={{ width: '100%', textAlign: 'left', marginBottom: '16px', background: 'var(--color-surface-1)', fontSize: '16px', padding: '16px', borderRadius: '8px', border: '1px solid #3f3f42', color: '#fff', cursor: 'pointer' }} onClick={() => handleAddObjective('future_week')}>
          + Add objective
        </button>

        <div className="objectives-list">
          {futureWeekObjectives.map(obj => (
            <div key={obj.id} className="objective-card" style={{ padding: '16px', marginBottom: '12px', fontSize: '16px', background: '#242426', borderRadius: '8px', border: '1px solid #3f3f42', cursor: 'pointer' }} onClick={() => setEditingObjective(obj)}>
              <div style={{ marginBottom: '12px', fontWeight: '500' }}>{obj.title || 'Untitled Objective'}</div>
              <div style={{ fontSize: '14px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="checkbox-icon" style={{ width: '18px', height: '18px', display: 'inline-block', border: '1px solid #5c5c5e', borderRadius: '4px' }}></span>
                {obj.channel_id && <span style={{ color: 'var(--color-primary)', fontWeight: 'bold' }}># {channels.find(c => c.id === obj.channel_id)?.name}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      <ObjectivePopover 
        objective={editingObjective} 
        channels={channels}
        onClose={() => setEditingObjective(null)} 
        onUpdate={() => { fetchObjectives(); fetchChannels(); }} 
      />
    </div>
  );
}