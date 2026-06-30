import React, { useState } from 'react';
import api from '../services/api';
import './WeeklyReview.css';

const parseInlineMarkdown = (text) => {
  return text.split('**').map((part, i) => i % 2 === 1 ? <strong key={i} style={{ color: 'var(--color-text)' }}>{part}</strong> : part);
};

const MarkdownSubCards = ({ content, type }) => {
  if (!content) return <div style={{ color: 'var(--color-text-muted)' }}>No data available.</div>;
  
  const lines = content.split('\n');
  const cards = [];
  const headerText = [];
  
  lines.forEach((line, index) => {
    line = line.trim();
    if (!line) return;
    
    // Check if it's a list item
    const isBullet = line.startsWith('* ') || line.startsWith('- ');
    const isNumber = /^\d+\.\s/.test(line);
    
    if (isBullet || isNumber) {
      const cleanLine = line.replace(/^[\*\-]\s|^\d+\.\s/, '');
      
      let bgStyle = 'rgba(255, 255, 255, 0.03)';
      let borderLeft = '3px solid var(--color-border)';
      
      if (type === 'wins') {
        bgStyle = 'rgba(16, 185, 129, 0.06)';
        borderLeft = '3px solid rgba(16, 185, 129, 0.5)';
      } else if (type === 'bottlenecks') {
        bgStyle = 'rgba(239, 68, 68, 0.06)';
        borderLeft = '3px solid rgba(239, 68, 68, 0.5)';
      } else if (type === 'focus') {
        bgStyle = 'rgba(99, 102, 241, 0.06)';
        borderLeft = '3px solid rgba(99, 102, 241, 0.5)';
      }

      cards.push(
        <div key={index} className={`subcard ${type}-card`} style={{
          background: bgStyle,
          borderLeft: borderLeft,
          padding: '16px',
          borderRadius: '0 8px 8px 0',
          marginBottom: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          transition: 'all 0.3s ease',
          color: 'var(--color-text-muted)',
          lineHeight: '1.5'
        }}>
          {parseInlineMarkdown(cleanLine)}
        </div>
      );
    } else {
      headerText.push(
        <p key={index} style={{ marginBottom: '16px', color: 'var(--color-text)', fontSize: '15px', fontWeight: 500 }}>
          {parseInlineMarkdown(line)}
        </p>
      );
    }
  });
  
  return (
    <div>
      {headerText}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '16px' }}>
        {cards}
      </div>
    </div>
  );
};

export default function WeeklyReview() {
  const [loading, setLoading] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  
  const generateReview = async () => {
    setLoading(true);
    try {
      const today = new Date();
      const lastWeek = new Date();
      lastWeek.setDate(today.getDate() - 7);
      
      const startStr = lastWeek.toISOString().split('T')[0];
      const endStr = today.toISOString().split('T')[0];
      
      const res = await api.post('/api/rituals/weekly-review', {
        start_date: startStr,
        end_date: endStr
      });
      setReviewData(res);
    } catch (e) {
      console.error(e);
      alert("Failed to generate weekly review. Ensure the backend server is running and accessible.");
    } finally {
      setLoading(false);
    }
  };

  // Simple parser to extract sections based on the prompt's Markdown output
  const extractSection = (content, headerEmoji) => {
    if (!content) return "";
    const lines = content.split('\n');
    let capture = false;
    let sectionText = "";
    
    for (const line of lines) {
      if (line.includes('###') || line.includes('**The') || line.startsWith('##')) {
        if (line.includes(headerEmoji)) {
          capture = true;
          continue;
        } else if (capture) {
          break; // Stop when hitting next header
        }
      }
      if (capture) {
        sectionText += line + '\n';
      }
    }
    // If emoji parsing fails, fallback to basic text splitting
    if (!sectionText && content.includes(headerEmoji)) {
      sectionText = content.split(headerEmoji)[1].split('###')[0];
    }
    return sectionText.replace(/#/g, '').trim();
  };

  return (
    <div style={{ padding: '40px', maxWidth: '900px', margin: '0 auto', color: 'var(--color-text)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--color-border)', paddingBottom: '24px', marginBottom: '32px' }}>
        <div>
          <h1 style={{ margin: '0 0 8px 0', fontSize: '32px', color: 'var(--color-primary)' }}>Weekly Performance Review</h1>
          <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: '16px' }}>
            Let the AI analyze your past 7 days and provide actionable recommendations.
          </p>
        </div>
        <button 
          className="btn btn-primary generate-btn"
          onClick={generateReview}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px', fontSize: '15px', transition: 'all 0.3s ease' }}
        >
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="pulsing-circle"></div>
              <span>AI Strategy Engine running...</span>
            </div>
          ) : (
            <><span>🧠</span> Generate AI Review</>
          )}
        </button>
      </div>
      
      {loading && !reviewData && (
        <div style={{ textAlign: 'center', padding: '80px', background: 'var(--color-surface)', borderRadius: '16px', border: '1px solid var(--color-border)', boxShadow: '0 10px 30px rgba(99, 102, 241, 0.1)' }}>
          <div className="ai-loader-container">
            <div className="ai-loader-ring"></div>
            <span style={{ fontSize: '48px', display: 'block', marginBottom: '24px', animation: 'pulse-slow 2s infinite' }}>✨</span>
          </div>
          <h3 className="loading-gradient-text" style={{ margin: '0 0 12px 0', fontSize: '24px' }}>Deep diving into your week...</h3>
          <p style={{ color: 'var(--color-text-muted)', maxWidth: '450px', margin: '0 auto', lineHeight: '1.6' }}>
            The AI is gathering your completed tasks, analyzing friction points, and structuring a highly personalized action plan. This takes about 10-15 seconds.
          </p>
        </div>
      )}

      {!reviewData && !loading && (
        <div style={{ textAlign: 'center', padding: '80px', background: 'var(--color-surface)', borderRadius: '16px', border: '1px dashed var(--color-border)' }}>
          <span style={{ fontSize: '48px', display: 'block', marginBottom: '16px' }}>📊</span>
          <h3 style={{ margin: '0 0 12px 0' }}>Ready for your weekly insights?</h3>
          <p style={{ color: 'var(--color-text-muted)', maxWidth: '400px', margin: '0 auto' }}>
            Click the button above to aggregate all your completed and pending tasks into a highly personalized strategic review.
          </p>
        </div>
      )}
      
      {reviewData && !loading && (
        <div className="review-results-container fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ padding: '16px 24px', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--color-primary)', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 600 }}>
            <span>📅</span> Review Period: {reviewData.start_date} to {reviewData.end_date}
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Wins Card */}
            <div style={{ background: 'var(--color-surface)', borderRadius: '16px', border: '1px solid var(--color-border)', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}>
              <div style={{ background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%)', padding: '20px 24px', borderBottom: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <h3 style={{ margin: 0, color: '#10B981', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '20px' }}>
                  <span style={{ fontSize: '24px' }}>🏆</span> The Wins
                </h3>
              </div>
              <div style={{ padding: '24px' }}>
                <MarkdownSubCards content={extractSection(reviewData.content, '🏆')} type="wins" />
              </div>
            </div>
            
            {/* Bottlenecks Card */}
            <div style={{ background: 'var(--color-surface)', borderRadius: '16px', border: '1px solid var(--color-border)', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}>
              <div style={{ background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%)', padding: '20px 24px', borderBottom: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <h3 style={{ margin: 0, color: '#ef4444', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '20px' }}>
                  <span style={{ fontSize: '24px' }}>🚧</span> The Bottlenecks
                </h3>
              </div>
              <div style={{ padding: '24px' }}>
                <MarkdownSubCards content={extractSection(reviewData.content, '🚧')} type="bottlenecks" />
              </div>
            </div>
          </div>
          
          {/* Recommendations Card */}
          <div style={{ background: 'var(--color-surface)', borderRadius: '16px', border: '1px solid var(--color-border)', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}>
            <div style={{ background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0.05) 100%)', padding: '20px 24px', borderBottom: '1px solid rgba(99, 102, 241, 0.2)' }}>
              <h3 style={{ margin: 0, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '20px' }}>
                <span style={{ fontSize: '24px' }}>🚀</span> Focus for Next Week
              </h3>
            </div>
            <div style={{ padding: '24px' }}>
              <MarkdownSubCards content={extractSection(reviewData.content, '🚀')} type="focus" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
