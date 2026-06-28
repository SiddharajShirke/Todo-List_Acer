import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import AddTaskBar from '../components/AddTaskBar';
import './Today.css';

function Today() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  const tabFromQuery = queryParams.get('tab') || 'planning';

  const [tasks, setTasks] = useState([]);
  const [channels, setChannels] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [events, setEvents] = useState([]);
  
  const [activeTab, setActiveTab] = useState(tabFromQuery);

  useEffect(() => {
    setActiveTab(tabFromQuery);
  }, [tabFromQuery]);

  const handleTabClick = (tab) => {
    navigate(`/today?tab=${tab}`);
  };
  const [filterChannel, setFilterChannel] = useState('all');
  const [calendarExpanded, setCalendarExpanded] = useState('none'); 
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [showMonthDropdown, setShowMonthDropdown] = useState(false);
  const [numDays, setNumDays] = useState(7);
  const [taskModalDate, setTaskModalDate] = useState(null);
  const [selectedStartDate, setSelectedStartDate] = useState(() => {
    const d = new Date();
    d.setHours(0,0,0,0);
    return d;
  });
  
  const today = new Date();
  const dates = Array.from({length: numDays}).map((_, i) => {
    const d = new Date(selectedStartDate);
    d.setDate(d.getDate() + i);
    return d.toISOString().split('T')[0];
  });

  const handleBoardScroll = (e) => {
    const { scrollLeft, scrollWidth, clientWidth } = e.target;
    // Load more days when scrolled near the right edge
    if (scrollLeft + clientWidth >= scrollWidth - 100) {
      setNumDays(prev => prev + 7);
    }
  };

  const fetchCalendarEvents = useCallback(async (expandedState, monthDate) => {
    try {
      if (expandedState === 'full') {
        const year = monthDate.getFullYear();
        const month = monthDate.getMonth();
        // Use local timezone boundaries to match UI
        const firstDay = new Date(year, month, 1, 0, 0, 0);
        const lastDay = new Date(year, month + 1, 0, 23, 59, 59);
        
        const res = await api.get(`/api/calendar/events?days=31&time_min=${firstDay.toISOString()}&time_max=${lastDay.toISOString()}`);
        setEvents(res.data || res);
      } else {
        const res = await api.get('/api/calendar/events');
        setEvents(res.data || res);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [tRes, cRes, hRes] = await Promise.all([
        api.get('/api/tasks'),
        api.get('/api/channels'),
        api.get('/api/rituals/highlights')
      ]);
      setTasks(tRes.data || tRes);
      setChannels(cRes.data || cRes);
      setHighlights(hRes.data || hRes);
      fetchCalendarEvents(calendarExpanded, currentMonth);
    } catch (e) {
      console.error(e);
    }
  }, [calendarExpanded, currentMonth, fetchCalendarEvents]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle exiting full screen -> reset to today
  useEffect(() => {
    if (calendarExpanded !== 'full') {
      setCurrentMonth(new Date());
    }
  }, [calendarExpanded]);

  const filteredTasks = tasks.filter(t => filterChannel === 'all' || t.channel_id === parseInt(filterChannel));

  const generateHighlight = async () => {
    try {
      await api.post('/api/rituals/shutdown', { date: today.toISOString().split('T')[0] });
      fetchData(); 
    } catch (e) {
      console.error(e);
      alert("Failed to generate highlight");
    }
  };

  const getDayName = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { weekday: 'long' });
  };
  const getShortDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const changeMonth = (offset) => {
    const d = new Date(currentMonth);
    d.setMonth(d.getMonth() + offset);
    setCurrentMonth(d);
  };

  const renderMonthGrid = () => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startOffset = firstDay.getDay(); 
    const totalDays = lastDay.getDate();

    const gridCells = [];
    
    for (let i = 0; i < startOffset; i++) {
      gridCells.push(<div key={`empty-start-${i}`} className="month-grid-cell empty"></div>);
    }
    
    for (let day = 1; day <= totalDays; day++) {
      // Create local date ensuring we don't drift on timezone bounds
      const cellDate = new Date(year, month, day);
      // Format YYYY-MM-DD manually to avoid UTC offset issues causing wrong dates
      const dateStr = `${year}-${String(month+1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      
      const dayEvents = events.filter(e => {
        if (e.start?.date) return e.start.date === dateStr;
        if (e.start?.dateTime) return e.start.dateTime.split('T')[0] === dateStr;
        return false;
      });
      const dayTasks = tasks.filter(t => t.planned_date === dateStr);

      const isToday = dateStr === new Date().toISOString().split('T')[0];

      gridCells.push(
        <div key={day} className={`month-grid-cell ${isToday ? 'today' : ''}`} style={{ cursor: 'pointer' }} onClick={() => {
          setTaskModalDate(dateStr);
        }}>
          <div className="cell-date">
            <span className={isToday ? 'date-badge' : ''}>{day}</span>
          </div>
          <div className="cell-events">
            {dayTasks.map(t => (
              <div key={'task-'+t.id} className="month-event-chip local-task">
                <span className="month-evt-dot" style={{ color: t.is_done ? '#10B981' : 'var(--color-primary)' }}>●</span>
                <span className="month-evt-title" style={{ textDecoration: t.is_done ? 'line-through' : 'none', color: t.is_done ? 'var(--color-text-muted)' : 'inherit' }}>{t.title}</span>
              </div>
            ))}
            {dayEvents.map(evt => {
              const isAllDay = !!evt.start?.date;
              return (
                <div key={evt.id} className={`month-event-chip ${isAllDay ? 'all-day' : ''}`}>
                  {!isAllDay && <span className="month-evt-dot">●</span>}
                  <span className="month-evt-title">{evt.summary}</span>
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    return (
      <div className="month-view-container">
        <div className="month-header-nav" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setCurrentMonth(new Date())}>Today</button>
            <button className="icon-btn" onClick={() => changeMonth(-1)}>&lt;</button>
            <button className="icon-btn" onClick={() => changeMonth(1)}>&gt;</button>
            <h2>{currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}</h2>
          </div>
          <div style={{ position: 'relative' }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => setShowMonthDropdown(!showMonthDropdown)} 
              style={{ fontSize: '14px', fontWeight: 500, padding: '6px 16px', background: 'var(--color-surface)' }}
            >
              Month ▼
            </button>
            {showMonthDropdown && (
              <div className="month-dropdown" style={{ position: 'absolute', top: '100%', right: 0, background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', zIndex: 10, maxHeight: '200px', overflowY: 'auto', width: '200px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)', marginTop: '8px' }}>
                {months.map((m, idx) => (
                  <div key={m} style={{ padding: '8px 16px', cursor: 'pointer', borderBottom: '1px solid var(--color-bg)', color: 'var(--color-text)' }} 
                    onClick={() => {
                      const d = new Date(currentMonth);
                      d.setMonth(idx);
                      setCurrentMonth(d);
                      setShowMonthDropdown(false);
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'var(--color-surface-hover)'}
                    onMouseLeave={(e) => e.target.style.background = 'transparent'}
                  >
                    {m} {currentMonth.getFullYear()}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="month-grid-header">
          {['SUN','MON','TUE','WED','THU','FRI','SAT'].map(d => <div key={d}>{d}</div>)}
        </div>
        <div className="month-grid">
          {gridCells}
        </div>
      </div>
    );
  };

  return (
    <div className="today-page">
      <div className="board-area" onScroll={handleBoardScroll} style={{ position: 'relative' }}>
        {activeTab === 'planning' && (
          <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <AddTaskBar defaultDate={selectedStartDate.toISOString().split('T')[0]} channels={channels} onTaskAdded={fetchData} />
            <div className="filter-dropdown" style={{ marginLeft: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Filter:</label>
              <select value={filterChannel} onChange={e => setFilterChannel(e.target.value)} style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text)', borderRadius: '4px', padding: '4px 8px' }}>
                <option value="all"># all</option>
                {channels.map(c => <option key={c.id} value={c.id}># {c.name}</option>)}
              </select>
            </div>
          </div>
          <div className="board-grid">
            {dates.map(dateStr => {
              const colTasks = filteredTasks.filter(t => t.planned_date === dateStr);
              return (
                <div key={dateStr} className="board-column">
                  <div className="col-header">
                    <h4>{getDayName(dateStr)}</h4>
                    <span className="muted">{getShortDate(dateStr)}</span>
                  </div>
                  <div className="tasks-container">
                    {colTasks.map(t => (
                      <div key={t.id} className="board-task-card">
                        <span className={`status ${t.is_done ? 'done' : ''}`}></span>
                        <div className="task-info">
                          <p>{t.title}</p>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                            <span style={{ fontSize: '10px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <span>
                                {t.priority === 'urgent' && '❗'}
                                {t.priority === 'high' && '🔴'}
                                {t.priority === 'medium' && '🟡'}
                                {t.priority === 'low' && '🔵'}
                              </span>
                              <span className="muted" style={{ fontSize: '10px' }}>
                                {t.pomodoros_completed} 🍅 | {Math.round((t.actual_minutes||0)/60 * 10)/10}h
                              </span>
                            </span>
                            <span className="channel-tag"># {channels.find(c => c.id === t.channel_id)?.name || 'work'}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          </>
        )}

        {activeTab === 'shutdown' && (
          <div className="shutdown-view">
            <h2>Generate your daily highlights</h2>
            <p className="muted">Your daily highlights are auto-generated from the tasks you've completed.</p>
            <button className="btn btn-primary btn-large mt-6" onClick={generateHighlight}>Get started →</button>
          </div>
        )}

        {activeTab === 'highlights' && (
          <div className="highlights-view">
            <h2>Review your daily highlights</h2>
            <div className="highlights-feed mt-6">
              {highlights.map(h => (
                <div key={h.id} className="highlight-item">
                  <h4>{getDayName(h.date)} {h.date === today.toISOString().split('T')[0] ? '😌' : '🔥'}</h4>
                  <p>{h.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {activeTab === 'planning' && (
        <div className={`calendar-area ${calendarExpanded !== 'none' ? 'expanded' : ''} ${calendarExpanded === 'full' ? 'full-screen' : ''}`}>
          <div className="cal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: calendarExpanded === 'full' ? '0' : '24px' }}>
            {calendarExpanded !== 'full' && <span>Google Calendar</span>}
            <div className="cal-actions" style={{ display: 'flex', gap: '8px', marginLeft: 'auto' }}>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px', fontSize: '11px' }}
                onClick={() => setCalendarExpanded(prev => prev === 'none' ? 'side' : 'none')}
              >
                {calendarExpanded === 'none' ? '⤢ Expand' : '⤡ Collapse'}
              </button>
              {calendarExpanded !== 'none' && (
                <button 
                  className="btn btn-secondary" 
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                  onClick={() => setCalendarExpanded(prev => prev === 'full' ? 'side' : 'full')}
                >
                  {calendarExpanded === 'full' ? 'Exit Full Screen' : 'Full Screen'}
                </button>
              )}
            </div>
          </div>
          
          {calendarExpanded === 'full' ? (
            renderMonthGrid()
          ) : (
            <div className="cal-days-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
              {dates.map(dateStr => {
                const dayEvents = events.filter(e => {
                  if (e.start?.date) return e.start.date === dateStr;
                  if (e.start?.dateTime) return e.start.dateTime.split('T')[0] === dateStr;
                  return false;
                });

                const dayTasks = tasks.filter(t => t.planned_date === dateStr);

                return (
                  <div key={dateStr} className="cal-day-block">
                    <div className="cal-day-header" style={{ paddingBottom: '8px', borderBottom: '1px solid var(--color-border)', marginBottom: '8px' }}>
                      <span className="day" style={{ fontWeight: 600, marginRight: '8px', color: 'var(--color-primary)' }}>{getDayName(dateStr).substring(0,3).toUpperCase()}</span>
                      <span className="date">{new Date(dateStr).getDate()}</span>
                    </div>
                    <div className="cal-day-events" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {dayEvents.length === 0 && dayTasks.length === 0 && <div className="no-events" style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>No events</div>}
                      
                      {dayTasks.map(t => (
                          <div key={'task-'+t.id} className="cal-event-chip" style={{ 
                            background: 'var(--color-surface)', 
                            padding: '8px 12px', 
                            borderRadius: '6px', 
                            fontSize: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                            borderLeft: `3px solid ${t.is_done ? '#10B981' : 'var(--color-primary)'}`
                          }}>
                            <span className="evt-time" style={{ color: 'var(--color-text-muted)', fontSize: '11px', fontWeight: 600 }}>
                              {t.estimated_minutes > 0 ? `${t.estimated_minutes} min` : 'Task'}
                            </span>
                            <span className="evt-title" style={{ color: 'var(--color-text)', textDecoration: t.is_done ? 'line-through' : 'none' }}>{t.title}</span>
                          </div>
                      ))}
                      {dayEvents.map(evt => {
                        const isAllDay = !!evt.start?.date;
                        let timeLabel = "All Day";
                        if (!isAllDay && evt.start?.dateTime) {
                          const d = new Date(evt.start.dateTime);
                          timeLabel = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        }
                        return (
                          <div key={evt.id} className="cal-event-chip" style={{ 
                            background: 'var(--color-surface)', 
                            padding: '8px 12px', 
                            borderRadius: '6px', 
                            fontSize: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                            borderLeft: '3px solid var(--color-primary)'
                          }}>
                            <span className="evt-time" style={{ color: 'var(--color-text-muted)', fontSize: '11px', fontWeight: 600 }}>{timeLabel}</span>
                            <span className="evt-title" style={{ color: 'var(--color-text)' }}>{evt.summary}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {taskModalDate && (
        <div className="task-modal-overlay" onClick={(e) => { if (e.target.className === 'task-modal-overlay') setTaskModalDate(null); }}>
          <div className="task-modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '16px' }}>Add Task for {getShortDate(taskModalDate)}</h3>
              <button className="icon-btn" onClick={() => setTaskModalDate(null)}>✕</button>
            </div>
            <AddTaskBar defaultDate={taskModalDate} channels={channels} onTaskAdded={() => { fetchData(); setTaskModalDate(null); }} />
          </div>
        </div>
      )}
    </div>
  );
}

export default Today;
