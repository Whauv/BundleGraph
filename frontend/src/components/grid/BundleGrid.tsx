import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ClientSideRowModelModule, ModuleRegistry, TextFilterModule, type ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import type { BundleProposal, Money } from '../../types/bundlegraph';

ModuleRegistry.registerModules([ClientSideRowModelModule, TextFilterModule]);

interface GridRowData { category: string; productName: string; productId: string; offerId: string; quantity: number; unitPrice: string; lineTotal: string; evidence: string; }
const money = (value: Money) => new Intl.NumberFormat(undefined, { style: 'currency', currency: value.currency }).format(value.amount_minor / 100);

export const BundleGrid: React.FC<{ proposal: BundleProposal | null }> = ({ proposal }) => {
  const rows = useMemo<GridRowData[]>(() => {
    if (!proposal) return [];
    const nodes = new Map(proposal.compatibility_report.nodes.map((node) => [node.node_id.replace(/^product:/, ''), node]));
    return proposal.line_items.map((item) => {
      const node = nodes.get(item.product_id);
      const evidence = proposal.compatibility_report.findings.filter((finding) => finding.affected_product_ids.includes(item.product_id)).flatMap((finding) => finding.evidence_ids);
      return {
        category: String(node?.data.role || node?.data.category || 'Equipment'),
        productName: String(node?.data.name || item.product_id),
        productId: item.product_id,
        offerId: item.offer_id,
        quantity: item.quantity,
        unitPrice: money(item.unit_price),
        lineTotal: money(item.merchandise_total),
        evidence: [...new Set(evidence)].join(', ') || 'No evidence reference',
      };
    });
  }, [proposal]);
  const columns = useMemo<ColDef<GridRowData>[]>(() => [
    { field: 'category', headerName: 'Category', minWidth: 130 },
    { field: 'productName', headerName: 'Product', flex: 1, minWidth: 190, filter: true },
    { field: 'quantity', headerName: 'Qty', width: 80 },
    { field: 'unitPrice', headerName: 'Unit price', width: 115 },
    { field: 'lineTotal', headerName: 'Line total', width: 115 },
    { field: 'offerId', headerName: 'Offer reference', minWidth: 155 },
  ], []);

  if (!proposal) return <div className="empty-state-panel"><p>Select a bundle to inspect its equipment.</p></div>;
  if (rows.length <= 6) return <div className="equipment-table-wrap"><table className="equipment-table"><thead><tr><th>Equipment</th><th>Category</th><th>Qty</th><th>Unit price</th><th>Line total</th><th>Details</th></tr></thead><tbody>{rows.map((row) => <tr key={row.offerId}><td><strong>{row.productName}</strong><small>{row.productId}</small></td><td>{row.category}</td><td>{row.quantity}</td><td>{row.unitPrice}</td><td>{row.lineTotal}</td><td><details><summary>Evidence</summary><p>{row.evidence}</p><p>Offer: {row.offerId}</p></details></td></tr>)}</tbody></table></div>;
  return <div className="equipment-grid ag-theme-quartz"><AgGridReact theme="legacy" rowData={rows} columnDefs={columns} defaultColDef={{ sortable: true, resizable: true }} domLayout="autoHeight" /></div>;
};
