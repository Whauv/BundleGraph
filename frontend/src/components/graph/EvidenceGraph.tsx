import React, { useState, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { CompatibilityReport, Finding } from '../../types/bundlegraph';
import { ShieldCheck, ChevronRight, X, FileText } from 'lucide-react';

interface EvidenceGraphProps {
  report?: CompatibilityReport;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({ report }) => {
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const initialNodes: Node[] = useMemo(() => [
    {
      id: 'mic-alpha',
      position: { x: 30, y: 40 },
      data: { label: '2x Mic Alpha (Dynamic XLR)' },
      style: {
        background: '#0b0f19',
        color: '#f8fafc',
        border: '1px solid rgba(16, 185, 129, 0.4)',
        borderRadius: '5px',
        padding: '8px 12px',
        fontSize: '12px',
        fontWeight: 500,
        fontFamily: 'Inter, sans-serif',
      },
    },
    {
      id: 'xlr-alpha',
      position: { x: 30, y: 130 },
      data: { label: '2x XLR Balanced Cables (3m)' },
      style: {
        background: '#0b0f19',
        color: '#f8fafc',
        border: '1px solid rgba(16, 185, 129, 0.4)',
        borderRadius: '5px',
        padding: '8px 12px',
        fontSize: '12px',
        fontWeight: 500,
        fontFamily: 'Inter, sans-serif',
      },
    },
    {
      id: 'interface-two',
      position: { x: 280, y: 80 },
      data: { label: 'Interface Two (2 XLR In / 2 TRS Out)' },
      style: {
        background: '#141c30',
        color: '#38bdf8',
        border: '1px solid #38bdf8',
        borderRadius: '5px',
        padding: '10px 14px',
        fontSize: '12px',
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
      },
    },
    {
      id: 'headphones-alpha',
      position: { x: 30, y: 220 },
      data: { label: '2x Headphones Alpha (Closed-Back)' },
      style: {
        background: '#0b0f19',
        color: '#f8fafc',
        border: '1px solid rgba(16, 185, 129, 0.4)',
        borderRadius: '5px',
        padding: '8px 12px',
        fontSize: '12px',
        fontWeight: 500,
        fontFamily: 'Inter, sans-serif',
      },
    },
    {
      id: 'laptop-host',
      position: { x: 550, y: 80 },
      data: { label: 'Host Laptop (Native USB-C Bus)' },
      style: {
        background: '#0b0f19',
        color: '#f8fafc',
        border: '1px solid rgba(56, 189, 248, 0.4)',
        borderRadius: '5px',
        padding: '8px 12px',
        fontSize: '12px',
        fontWeight: 500,
        fontFamily: 'Inter, sans-serif',
      },
    },
    {
      id: 'req-inputs',
      position: { x: 280, y: 200 },
      data: { label: 'Rule R2: 2 Input Minimum Sat.' },
      style: {
        background: 'rgba(16, 185, 129, 0.08)',
        color: '#34d399',
        border: '1px dashed rgba(16, 185, 129, 0.4)',
        borderRadius: '5px',
        padding: '6px 10px',
        fontSize: '11px',
        fontFamily: 'JetBrains Mono, monospace',
      },
    },
  ], []);

  const initialEdges: Edge[] = useMemo(() => [
    { id: 'e1', source: 'mic-alpha', target: 'xlr-alpha', animated: true, style: { stroke: '#10b981', strokeWidth: 1.5 } },
    { id: 'e2', source: 'xlr-alpha', target: 'interface-two', animated: true, style: { stroke: '#10b981', strokeWidth: 1.5 } },
    { id: 'e3', source: 'headphones-alpha', target: 'interface-two', style: { stroke: '#10b981', strokeWidth: 1.5 } },
    { id: 'e4', source: 'interface-two', target: 'laptop-host', animated: true, style: { stroke: '#38bdf8', strokeWidth: 2 } },
    { id: 'e5', source: 'interface-two', target: 'req-inputs', style: { stroke: '#10b981', strokeDasharray: '3 3' } },
  ], []);

  const findings = report?.findings || [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '0.75rem', marginTop: '0.25rem' }}>
      {/* React Flow Canvas */}
      <div style={{ height: 420, backgroundColor: '#030712', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', position: 'relative', overflow: 'hidden' }}>
        <ReactFlow nodes={initialNodes} edges={initialEdges} fitView>
          <Background color="rgba(255, 255, 255, 0.05)" gap={16} />
          <Controls />
        </ReactFlow>
        <div style={{ position: 'absolute', bottom: 8, left: 8, fontSize: '0.6875rem', color: 'var(--text-muted)', background: 'rgba(3, 7, 18, 0.85)', padding: '2px 6px', borderRadius: '3px', border: '1px solid var(--border-subtle)' }}>
          Topology: Mic → Cable → Interface → Laptop
        </div>
      </div>

      {/* Findings & Evidence Inspector */}
      <div className="surface-panel" style={{ display: 'flex', flexDirection: 'column', height: 420 }}>
        <div style={{ marginBottom: '0.5rem' }}>
          <h4 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <ShieldCheck size={14} style={{ color: '#38bdf8' }} />
            Deterministic Verification Rules
          </h4>
          <p style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
            Select rule to inspect underlying evidence citations:
          </p>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {findings.map((f) => {
            const isComp = f.status === 'compatible';
            const isSelected = selectedFinding?.rule_id === f.rule_id;
            return (
              <button
                key={f.rule_id}
                type="button"
                onClick={() => setSelectedFinding(f)}
                style={{
                  backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-app)',
                  border: isSelected ? '1px solid #38bdf8' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '0.45rem 0.6rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'all 0.12s ease',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {f.rule_id}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                    {f.reason_code}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span className={`badge ${isComp ? 'badge-emerald' : 'badge-rose'}`} style={{ fontSize: '0.625rem', padding: '0.1rem 0.35rem' }}>
                    {isComp ? 'PASS' : 'FAIL'}
                  </span>
                  <ChevronRight size={12} style={{ color: 'var(--text-dim)' }} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Finding Detail Modal / Panel */}
      {selectedFinding && (
        <div style={{ gridColumn: '1 / -1', background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', padding: '0.875rem 1rem', marginTop: '0.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
            <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <FileText size={14} style={{ color: '#38bdf8' }} />
              Rule Citation: <code style={{ fontFamily: 'var(--font-mono)' }}>{selectedFinding.rule_id}</code> ({selectedFinding.reason_code})
            </span>
            <button
              type="button"
              className="reset-btn"
              onClick={() => setSelectedFinding(null)}
              style={{ padding: '0.15rem 0.4rem', fontSize: '0.6875rem' }}
            >
              <X size={11} />
              <span>Dismiss</span>
            </button>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', lineHeight: 1.4 }}>
            {selectedFinding.explanation}
          </p>
          {selectedFinding.evidence_ids.length > 0 && (
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
              <strong>Verified Evidence IDs:</strong>
              {selectedFinding.evidence_ids.map((id) => (
                <span key={id} className="badge badge-neutral tabular-num" style={{ fontSize: '0.625rem' }}>
                  {id}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
