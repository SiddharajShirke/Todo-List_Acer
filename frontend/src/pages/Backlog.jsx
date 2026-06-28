import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function Backlog() {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    fetchBacklog();
  }, []);

  const fetchBacklog = async () => {
    try {
      const res = await api.get('/api/tasks'); // For now fetch all, filter frontend
      const allTasks = Array.isArray(res) ? res : (res.data || []);
      
      const today = new Date();
      today.setHours(0,0,0,0);
      
      const overdue = allTasks.filter(t => {
        if (t.is_done) return false;
        if (!t.planned_date) return false;
        const pDate = new Date(t.planned_date);
        pDate.setHours(0,0,0,0);
        return pDate < today;
      });
      
      setTasks(overdue);
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkDone = async (task) => {
    try {
      await api.patch('/api/tasks/' + task.id + '/done');
      fetchBacklog();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: '24px', color: 'var(--text-main)', maxWidth: '800px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '8px' }}>Backlog</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '32px' }}>Unfinished tasks from past days.</p>
      
      {tasks.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No backlog tasks! You are all caught up.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {tasks.map(task => (
            <div key={task.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--color-surface)', padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
              <button 
                onClick={() => handleMarkDone(task)}
                style={{ width: '20px', height: '20px', borderRadius: '50%', border: '2px solid var(--color-border)', background: 'transparent', cursor: 'pointer', flexShrink: 0 }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '15px' }}>{task.title}</div>
                <div style={{ fontSize: '12px', color: '#ef4444', marginTop: '4px' }}>
                  Planned for {new Date(task.planned_date).toLocaleDateString()}
                </div>
              </div>
              {task.estimated_minutes > 0 && (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  {task.estimated_minutes} min
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}