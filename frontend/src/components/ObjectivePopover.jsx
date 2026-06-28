import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function ObjectivePopover({ objective, channels, onClose, onUpdate }) {
  const [tasks, setTasks] = useState([]);
  const [showChannelDropdown, setShowChannelDropdown] = useState(false);
  const [channelSearch, setChannelSearch] = useState('');
  const [activeDayIndex, setActiveDayIndex] = useState(null);
  
  // Local state for edit before save
  const [title, setTitle] = useState('');
  const [channelId, setChannelId] = useState(null);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (objective) {
      setTitle(objective.title || '');
      setChannelId(objective.channel_id);
      fetchTasks();
    }
  }, [objective]);

  const fetchTasks = async () => {
    try {
      const res = await api.get('/api/tasks?weekly_plan_id=' + objective.id);
      setTasks(res.data || res || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
  };

  const handleChannelSelect = (id) => {
    setChannelId(id);
    setShowChannelDropdown(false);
  };

  const handleCreateChannel = async () => {
    try {
      const res = await api.post('/api/channels', { name: channelSearch.toLowerCase(), color: '#10B981' });
      const newChannelId = res.data?.id || res.id;
      setChannelId(newChannelId);
      setShowChannelDropdown(false);
      setChannelSearch('');
    } catch (e) {
      console.error(e);
    }
  };

  const handleTimeSelect = async (dateStr, minutes) => {
    try {
      const existingTask = tasks.find(t => t.planned_date === dateStr);
      if (existingTask) {
        if (minutes === 0) {
          await api.delete('/api/tasks/' + existingTask.id);
        } else {
          await api.put('/api/tasks/' + existingTask.id, { estimated_minutes: minutes });
        }
      } else if (minutes > 0) {
        await api.post('/api/tasks', {
          title: title || 'New Objective',
          planned_date: dateStr,
          weekly_plan_id: objective.id,
          channel_id: channelId,
          estimated_minutes: minutes
        });
      }
      setActiveDayIndex(null);
      fetchTasks();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    try {
      await api.put('/api/weekly-objectives/' + objective.id, { title, channel_id: channelId });
      onUpdate();
      onClose();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancel = async () => {
    if (objective.isNew) {
      try {
        await api.delete('/api/weekly-objectives/' + objective.id);
        onUpdate();
      } catch (e) {
        console.error(e);
      }
    }
    onClose();
  };

  const confirmDelete = async () => {
    try {
      await api.delete('/api/weekly-objectives/' + objective.id);
      onUpdate();
      onClose();
    } catch (e) {
      console.error(e);
    }
  };

  if (!objective) return null;

  // Generate 7 days
  const startDate = new Date(objective.week_start_date);
  const dates = Array.from({length: 7}).map((_, i) => {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    return d;
  });

  const timeOptions = [
    { label: '--:--', value: 0 },
    { label: '5 min', value: 5 },
    { label: '10 min', value: 10 },
    { label: '15 min', value: 15 },
    { label: '20 min', value: 20 },
    { label: '25 min', value: 25 },
    { label: '30 min', value: 30 },
    { label: '45 min', value: 45 },
    { label: '60 min', value: 60 },
    { label: '90 min', value: 90 },
    { label: '120 min', value: 120 }
  ];

  const currentChannel = channels.find(c => c.id === channelId);

  return (
    <div className="objective-popover-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 100 }} onClick={handleCancel}>
      <div className="objective-popover" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: '#242426', borderRadius: '12px', padding: '28px', width: '540px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)', border: '1px solid #3f3f42' }} onClick={e => e.stopPropagation()}>
        <button onClick={handleCancel} style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: '#8a8a8e', cursor: 'pointer', fontSize: '18px' }}>X</button>
        
        <div style={{ marginBottom: '20px', position: 'relative' }}>
          <div style={{ fontSize: '12px', textTransform: 'uppercase', color: '#8a8a8e', marginBottom: '4px' }}>CHANNEL</div>
          <button onClick={() => setShowChannelDropdown(!showChannelDropdown)} style={{ background: 'transparent', border: 'none', color: currentChannel ? 'var(--color-primary)' : '#8a8a8e', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', padding: 0, fontWeight: 'bold', fontSize: '15px' }}>
            {currentChannel ? '# ' + currentChannel.name : '# No Channel'} v
          </button>
          
          {showChannelDropdown && (
            <div style={{ position: 'absolute', top: '40px', left: 0, background: '#1c1c1e', border: '1px solid #3f3f42', borderRadius: '8px', zIndex: 10, width: '220px', overflow: 'hidden' }}>
              <div style={{ padding: '10px', color: '#8a8a8e', fontSize: '14px' }}>Assign to channel:</div>
              <input 
                  type="text" 
                  autoFocus
                  placeholder="Search..." 
                  value={channelSearch}
                  onChange={e => setChannelSearch(e.target.value)}
                  style={{ width: '90%', margin: '0 5%', marginBottom: '10px', background: 'transparent', border: 'none', borderBottom: '1px solid #444', color: '#fff', outline: 'none', fontSize: '14px' }}
              />
              <div style={{ padding: '10px 14px', cursor: 'pointer', borderTop: '1px solid #2a2a2c', fontSize: '14px' }} onClick={() => handleChannelSelect(null)}># Unassigned</div>
              {channels.filter(c => c.name.toLowerCase().includes(channelSearch.toLowerCase())).map(c => (
                <div key={c.id} style={{ padding: '10px 14px', cursor: 'pointer', borderTop: '1px solid #2a2a2c', color: c.id === channelId ? 'var(--color-primary)' : 'inherit', fontSize: '14px' }} onClick={() => handleChannelSelect(c.id)}>
                  # {c.name}
                </div>
              ))}
              {channelSearch && !channels.find(c => c.name.toLowerCase() === channelSearch.toLowerCase()) && (
                <div style={{ padding: '10px 14px', cursor: 'pointer', borderTop: '1px solid #2a2a2c', color: '#10B981', fontSize: '14px' }} onClick={handleCreateChannel}>
                  + Create {channelSearch.toLowerCase()}
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', marginBottom: '28px' }}>
          <div style={{ color: 'var(--color-primary)', marginTop: '4px', fontSize: '16px' }}>O</div>
          <div style={{ flex: 1 }}>
            <div style={{ color: '#8a8a8e', fontSize: '14px', marginBottom: '4px' }}>Weekly objective</div>
            <input 
              type="text" 
              value={title} 
              onChange={handleTitleChange} 
              placeholder="Objective title..."
              style={{ width: '100%', background: 'transparent', border: 'none', color: '#fff', outline: 'none', fontSize: '22px', fontWeight: '500', padding: 0 }} 
            />
          </div>
        </div>

        {tasks.length > 0 && (
          <div style={{ marginBottom: '28px' }}>
            {tasks.sort((a,b) => new Date(b.planned_date) - new Date(a.planned_date)).map(t => {
              const d = new Date(t.planned_date);
              const dateString = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
              return (
                <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', color: '#8a8a8e', fontSize: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: '#10B981', border: '1px solid #10B981', borderRadius: '50%', width: '18px', height: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px' }}>✓</span>
                    <span>Planned for {dateString}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '28px', textAlign: 'right' }}>
                    <span>{dateString}</span>
                    <span style={{ width: '45px' }}>{Math.floor(t.estimated_minutes/60)}:{(t.estimated_minutes%60).toString().padStart(2, '0')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={{ display: 'flex', gap: '8px', justifyContent: 'space-between', marginBottom: '36px' }}>
          {dates.map((d, idx) => {
            const dateStr = d.toISOString().split('T')[0];
            const taskForDay = tasks.find(t => t.planned_date === dateStr);
            const plannedMins = taskForDay ? taskForDay.estimated_minutes : 0;
            const isHovered = activeDayIndex === idx;

            return (
              <div key={dateStr} style={{ position: 'relative' }}>
                <div 
                  onClick={() => setActiveDayIndex(isHovered ? null : idx)}
                  style={{ 
                    padding: '10px', 
                    borderRadius: '8px', 
                    background: plannedMins > 0 ? '#2a2a2c' : 'transparent',
                    border: '1px solid #3f3f42',
                    cursor: 'pointer',
                    textAlign: 'center',
                    minWidth: '60px'
                  }}>
                  <div style={{ fontSize: '13px', color: '#8a8a8e', marginBottom: '6px' }}>
                    {d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' }).replace(',', ' ·')}
                  </div>
                  <div style={{ fontSize: '15px', color: plannedMins > 0 ? 'var(--text-main)' : '#5c5c5e' }}>
                    {plannedMins > 0 ? Math.floor(plannedMins/60) + ':' + (plannedMins%60).toString().padStart(2, '0') : '--:--'}
                  </div>
                </div>

                {activeDayIndex === idx && (
                  <div style={{ position: 'absolute', top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: '10px', background: '#1c1c1e', border: '1px solid #3f3f42', borderRadius: '8px', zIndex: 10, width: '130px', maxHeight: '220px', overflowY: 'auto' }}>
                    <div style={{ padding: '10px', color: '#8a8a8e', fontSize: '13px' }}>Planned:</div>
                    {timeOptions.map(opt => (
                      <div key={opt.label} style={{ padding: '10px 14px', cursor: 'pointer', fontSize: '15px', borderTop: '1px solid #2a2a2c' }} onClick={() => handleTimeSelect(dateStr, opt.value)}>
                        {opt.label}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #3f3f42', paddingTop: '20px', marginTop: '20px' }}>
          <button className="btn btn-ghost" style={{ color: '#ef4444', fontSize: '15px', padding: '8px 16px' }} onClick={() => setShowDeleteConfirm(true)}>Delete</button>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="btn btn-ghost" style={{ fontSize: '15px', padding: '8px 16px' }} onClick={handleCancel}>Cancel</button>
            <button className="btn btn-primary" style={{ background: '#10B981', color: '#fff', border: 'none', fontSize: '15px', padding: '8px 16px' }} onClick={handleSave}>Save Objective</button>
          </div>
        </div>

        {/* Delete Confirmation Modal Overlay */}
        {showDeleteConfirm && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ background: '#1c1c1e', padding: '32px', borderRadius: '16px', border: '1px solid #3f3f42', maxWidth: '400px', textAlign: 'center', boxShadow: '0 20px 40px rgba(0,0,0,0.4)' }}>
              <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#fff' }}>Delete Objective?</h3>
              <p style={{ color: '#8a8a8e', fontSize: '15px', lineHeight: '1.5', marginBottom: '32px' }}>
                Are you sure you want to delete this objective? It will no longer be stored and will be completely removed from your Daily Planning and Google Calendar.
              </p>
              <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
                <button 
                  onClick={() => setShowDeleteConfirm(false)}
                  style={{ padding: '10px 24px', background: 'transparent', border: '1px solid #3f3f42', borderRadius: '8px', color: '#fff', cursor: 'pointer', fontSize: '15px', fontWeight: '500' }}>
                  Cancel
                </button>
                <button 
                  onClick={confirmDelete}
                  style={{ padding: '10px 24px', background: '#ef4444', border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer', fontSize: '15px', fontWeight: '500' }}>
                  Confirm Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}