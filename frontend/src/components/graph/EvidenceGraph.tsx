import React, { useMemo, useState } from 'react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { AnimatePresence, motion } from 'motion/react';
import { CircleHelp, FileText, Link2, X } from 'lucide-react';
import type { CompatibilityReport, EvidenceRecord, Finding, GraphEdge, GraphNode } from '../../types/bundlegraph';

interface EvidenceGraphProps { report?: CompatibilityReport; evidence?: EvidenceRecord[]; }
type Selection = { kind: 'node'; id: string } | { kind: 'edge'; id: string } | null;
const nodeLabel = (node: GraphNode) => String(node.data.name || node.data.label || node.data.role || node.node_id.replace(/^(product|requirement):/, '').replaceAll('-', ' '));
const productId = (nodeId: string) => nodeId.replace(/^product:/, '');
const findingForNode = (node: GraphNode, findings: Finding[]) => findings.find((finding) => finding.affected_product_ids.includes(productId(node.node_id))) || null;
const COLORS = { compatible: '#4c9b70', incompatible: '#c3615e', unknown: '#b68a43' };

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({ report, evidence = [] }) => {
  const [selection, setSelection] = useState<Selection>(null);
  const graph = useMemo(() => {
    const source = report?.nodes || [];
    const products = source.filter((node) => node.node_type === 'product');
    const capabilities = source.filter((node) => node.node_type !== 'product');
    const byId = new Map(source.map((node) => [node.node_id, node]));
    const edgeSource = report?.edges || [];
    const nodes: Node[] = [...products, ...capabilities].map((node) => {
      const product = node.node_type === 'product';
      const index = product ? products.indexOf(node) : capabilities.indexOf(node);
      const finding = findingForNode(node, report?.findings || []);
      const color = finding ? COLORS[finding.status] : COLORS.unknown;
      return { id: node.node_id, position: { x: product ? 24 : 410, y: 24 + index * 104 }, data: { label: <div><strong>{nodeLabel(node)}</strong><span>{product ? `${node.data.quantity || 1} × ${node.data.role || 'equipment'}` : 'Required capability'}</span></div> }, style: { width: 260, border: `1px solid ${color}`, borderLeftWidth: 4, borderRadius: 4, background: 'var(--surface)', color: 'var(--text-strong)', padding: '10px 12px', fontSize: 13 } };
    });
    const edges: Edge[] = edgeSource.map((edge, index) => {
      const related = [byId.get(edge.source_id), byId.get(edge.target_id)].filter(Boolean) as GraphNode[];
      const finding = related.map((node) => findingForNode(node, report?.findings || [])).find(Boolean);
      const status = finding?.status || 'unknown';
      return { id: `edge-${index}`, source: edge.source_id, target: edge.target_id, label: edge.relationship?.replaceAll('_', ' ') || edge.edge_type?.replaceAll('_', ' '), animated: false, style: { stroke: COLORS[status], strokeWidth: 1.6 }, labelStyle: { fill: 'var(--text-muted)', fontSize: 10 }, labelBgStyle: { fill: 'var(--canvas)', fillOpacity: 0.9 } };
    });
    return { nodes, edges, byId, edgeSource };
  }, [report]);

  if (!report?.nodes.length) return <div className="empty-state-panel"><CircleHelp size={23} /><div><strong>Connection map is unavailable.</strong><p>No backend topology was supplied for this candidate.</p></div></div>;
  const selectedNode = selection?.kind === 'node' ? graph.byId.get(selection.id) : null;
  const selectedEdge = selection?.kind === 'edge' ? graph.edgeSource[Number(selection.id.replace('edge-', ''))] : null;
  const finding = selectedNode ? findingForNode(selectedNode, report.findings) : selectedEdge ? findingForEdge(selectedEdge, graph.byId, report.findings) : null;
  const evidenceIds = [...new Set([...(finding?.evidence_ids || []), ...(selectedEdge?.evidence_ids || [])])];

  return <div className="connection-map">
    <div className="connection-map__intro"><div><p className="eyebrow">Connection map</p><h2>How the returned setup connects</h2><p>Only backend-provided nodes, edges, and findings appear here. Select an item or connection for details.</p></div><span className="map-legend"><i className="legend-compatible" /> Compatible <i className="legend-incompatible" /> Incompatible <i className="legend-unknown" /> Unknown</span></div>
    <div className="evidence-layout"><div className="connection-map__canvas"><ReactFlow nodes={graph.nodes} edges={graph.edges} fitView minZoom={0.45} maxZoom={1.4} onNodeClick={(_, node) => setSelection({ kind: 'node', id: node.id })} onEdgeClick={(_, edge) => setSelection({ kind: 'edge', id: edge.id })}><Background gap={16} color="var(--border-subtle)" /><Controls showInteractive={false} /></ReactFlow></div>
      <AnimatePresence mode="wait"><motion.aside key={selection ? `${selection.kind}-${selection.id}` : 'empty'} className="connection-detail" aria-live="polite" initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -4 }}>
        {selection ? <><div className="connection-detail__heading"><div><p className="eyebrow">{selection.kind === 'edge' ? 'Selected connection' : 'Selected item'}</p><h3>{selectedNode ? nodeLabel(selectedNode) : selectedEdge ? `${labelForId(selectedEdge.source_id, graph.byId)} → ${labelForId(selectedEdge.target_id, graph.byId)}` : 'Unknown'}</h3></div><button type="button" className="icon-button" aria-label="Clear selection" onClick={() => setSelection(null)}><X size={15} /></button></div>
          <p className={`finding-state finding-state--${finding?.status || 'unknown'}`}>{finding ? finding.status === 'compatible' ? 'Compatible' : finding.status === 'incompatible' ? 'Incompatible' : 'Not yet verified' : 'Not yet verified'}</p>
          <p>{finding?.explanation || (selectedEdge?.relationship ? `Connection type: ${selectedEdge.relationship.replaceAll('_', ' ')}.` : 'No compatibility finding is associated with this selection.')}</p>
          {finding?.missing_requirements_or_evidence?.length ? <div className="detail-block"><strong>Missing information</strong><ul>{finding.missing_requirements_or_evidence.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
          <EvidenceDetails evidenceIds={evidenceIds} evidence={evidence} />
        </> : <><Link2 size={22} /><h3>Select an item or connection</h3><p>The details panel will show the actual finding and available evidence references.</p></>}
      </motion.aside></AnimatePresence>
    </div>
    <details className="connection-list"><summary>Accessible connection list</summary><ul>{graph.edgeSource.map((edge, index) => <li key={`${edge.source_id}-${edge.target_id}-${index}`}><button type="button" onClick={() => setSelection({ kind: 'edge', id: `edge-${index}` })}>{labelForId(edge.source_id, graph.byId)} → {labelForId(edge.target_id, graph.byId)}</button><span>{edge.relationship?.replaceAll('_', ' ') || 'Relationship not labeled'}</span></li>)}</ul></details>
  </div>;
};

function findingForEdge(edge: GraphEdge, byId: Map<string, GraphNode>, findings: Finding[]) {
  return [byId.get(edge.source_id), byId.get(edge.target_id)].filter(Boolean).map((node) => findingForNode(node as GraphNode, findings)).find(Boolean) || null;
}
function labelForId(id: string, byId: Map<string, GraphNode>) { const node = byId.get(id); return node ? nodeLabel(node) : id; }
const EvidenceDetails: React.FC<{ evidenceIds: string[]; evidence: EvidenceRecord[] }> = ({ evidenceIds, evidence }) => <div className="detail-block"><strong><FileText size={15} /> Evidence</strong>{evidenceIds.length ? evidenceIds.map((id) => {
  const item = evidence.find((record) => record.evidence_id === id);
  return <details key={id}><summary>{item ? `${item.attribute} · ${item.origin === 'fixture' ? 'Synthetic fixture' : item.source_type}` : id}</summary>{item ? <div><p>{item.excerpt}</p><small>Observed {new Date(item.observed_at).toLocaleDateString()} · {item.freshness_status} · {item.conflict_status}</small>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source</a>}</div> : <p>The finding references this evidence ID, but its stored record is not available at this workflow stage.</p>}</details>;
}) : <p>No evidence reference was supplied for this finding.</p>}</div>;
