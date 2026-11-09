import React from 'react';
import { CalendarDays, CircleHelp, Truck } from 'lucide-react';

export const ScheduleTimeline: React.FC<{ deadline?: string | null }> = ({ deadline }) => <section className="delivery-view">
  <div className="section-heading"><div><p className="eyebrow">Delivery</p><h2>Timing remains unverified</h2></div><span className="status-label status-label--warning">Unknown</span></div>
  <div className="status-notice status-notice--warning"><Truck size={19} /><div><strong>No merchant or carrier delivery evidence was supplied.</strong><p>Availability is not an arrival estimate, so BundleGraph cannot claim that this setup will arrive by a target date.</p></div></div>
  <dl className="delivery-facts"><div><dt><CalendarDays size={16} /> Recording target</dt><dd>{deadline ? new Date(deadline).toLocaleDateString() : 'Not provided'}</dd></div><div><dt><CircleHelp size={16} /> Deadline feasibility</dt><dd>Unknown</dd></div></dl>
</section>;
