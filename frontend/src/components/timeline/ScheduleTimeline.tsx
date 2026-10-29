import React from 'react';
import { Calendar, CheckCircle2, Clock, Truck, Package, Mic, Flag, AlertCircle } from 'lucide-react';

interface ScheduleTimelineProps {
  deadlineDays?: number;
  isDelayed?: boolean;
}

export const ScheduleTimeline: React.FC<ScheduleTimelineProps> = ({ deadlineDays = 7, isDelayed = false }) => {
  const steps = [
    { name: 'Order Authorized', day: 'DAY 0 (NOW)', desc: 'PayPal Sandbox payment confirmed', status: 'done', icon: CheckCircle2, progress: 100 },
    { name: 'Merchant Dispatch', day: 'DAY 1', desc: 'Hardware package picked & labeled', status: 'done', icon: Package, progress: 75 },
    { name: 'Carrier In Transit', day: isDelayed ? 'DAYS 2–4' : 'DAYS 2–3', desc: isDelayed ? 'Expedited alternative rerouted' : 'Ground transit on schedule', status: isDelayed ? 'warn' : 'active', icon: Truck, progress: 35 },
    { name: 'Studio Delivery', day: isDelayed ? 'DAY 4' : 'DAY 3', desc: 'All packages arrive at facility', status: 'upcoming', icon: Clock, progress: 0 },
    { name: 'Assembly & Soundcheck', day: isDelayed ? 'DAY 5' : 'DAY 4', desc: 'Cabling, gain staging & sound check', status: 'upcoming', icon: Mic, progress: 0 },
    { name: 'Production Launch', day: `DAY ${deadlineDays} (TARGET)`, desc: 'Live recording episode 1 date', status: 'deadline', icon: Flag, progress: 0 },
  ];

  return (
    <section className="studio-card" style={{ padding: '0.875rem' }}>
      {/* Card Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '2px', background: '#111111', border: '1px solid #282828', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Calendar size={15} style={{ color: '#ffffff' }} />
          </div>
          <div>
            <h2 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff', letterSpacing: '-0.01em', margin: 0 }}>
              Bryntum Delivery &amp; Milestones Timeline
            </h2>
            <p style={{ fontSize: '0.75rem', color: '#888888', margin: '0.1rem 0 0 0' }}>
              Maps fulfillment lead-times, transit windows, studio testing buffer, and hard deadlines.
            </p>
          </div>
        </div>
        <div className={`badge ${isDelayed ? 'badge-amber' : 'badge-emerald'}`}>
          {isDelayed ? (
            <>
              <AlertCircle size={12} />
              <span>+1 Day Re-planning Shift (Feasible)</span>
            </>
          ) : (
            <>
              <CheckCircle2 size={12} />
              <span>On Schedule (+2 Days Buffer)</span>
            </>
          )}
        </div>
      </div>

      {/* Horizontal 6-Stage Sequence Tracker */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.5rem' }}>
        {steps.map((st, i) => {
          const IconComp = st.icon;
          const isDone = st.status === 'done';
          const isWarn = st.status === 'warn';
          const isDeadline = st.status === 'deadline';

          let kickerColor = '#888888';
          let progressBarBg = '#222222';
          if (isDone) {
            kickerColor = '#00e575';
            progressBarBg = '#00e575';
          } else if (isWarn) {
            kickerColor = '#fabc45';
            progressBarBg = '#fabc45';
          } else if (isDeadline) {
            kickerColor = '#ffffff';
            progressBarBg = '#ffffff';
          }

          return (
            <div
              key={i}
              style={{
                backgroundColor: isDeadline ? '#0f0f0f' : '#0a0a0a',
                border: `1px solid ${isDeadline ? '#333333' : '#222222'}`,
                borderRadius: '2px',
                padding: '0.625rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.625rem', fontWeight: 600, color: kickerColor, letterSpacing: '0.06em' }}>
                  {st.day}
                </span>
                <IconComp size={14} style={{ color: kickerColor }} />
              </div>
              <div style={{ margin: '0.2rem 0' }}>
                <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
                  {st.name}
                </div>
                <div style={{ fontSize: '0.6875rem', color: '#888888', marginTop: '0.2rem', lineHeight: 1.3 }}>
                  {st.desc}
                </div>
              </div>
              <div style={{ width: '100%', height: '3px', background: '#000000', borderRadius: '1px', overflow: 'hidden' }}>
                <div style={{ width: `${st.progress}%`, height: '100%', background: progressBarBg }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Bryntum Engine Integration Footer */}
      <div style={{ marginTop: '0.625rem', paddingTop: '0.5rem', borderTop: '1px solid #1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#777777' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ffffff', display: 'inline-block' }}></span>
          <span>Bryntum Project Timeline Protocol • Sponsor Integration</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>Deterministic Buffer:</span>
          <span style={{ color: '#00e575', fontWeight: 600 }}>Soundcheck completed 48 hours prior to launch</span>
        </div>
      </div>
    </section>
  );
};

