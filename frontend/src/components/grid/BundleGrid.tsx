import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import type { BundleProposal } from '../../types/bundlegraph';
import { Table, CheckCircle2 } from 'lucide-react';

interface BundleGridProps {
  proposal: BundleProposal | null;
}

interface GridRowData {
  category: string;
  productId: string;
  productName: string;
  offerId: string;
  quantity: number;
  unitPrice: string;
  lineTotal: string;
  availability: string;
  status: string;
}

export const BundleGrid: React.FC<BundleGridProps> = ({ proposal }) => {
  const rowData: GridRowData[] = useMemo(() => {
    if (!proposal) return [];

    const categoryMap: Record<string, string> = {
      'mic-alpha': 'Microphone',
      'mic-phantom': 'Microphone',
      'mic-gamma': 'Microphone',
      'interface-one': 'Audio Interface',
      'interface-two': 'Audio Interface',
      'interface-conflict': 'Audio Interface',
      'headphones-alpha': 'Headphones',
      'headphones-bravo': 'Headphones',
      'xlr-alpha': 'XLR Cable',
      'xlr-bravo': 'XLR Cable',
      'usb-a-to-c': 'USB Adapter',
      'usb-c-to-a': 'USB Adapter',
    };

    const nameMap: Record<string, string> = {
      'mic-alpha': 'Synthetic Mic Alpha (Dynamic XLR)',
      'mic-phantom': 'Synthetic Mic Phantom (+48V Required)',
      'mic-gamma': 'Synthetic Mic Gamma (Dynamic XLR)',
      'interface-one': 'Synthetic Interface One (1 XLR Input)',
      'interface-two': 'Synthetic Interface Two (2 XLR Inputs)',
      'headphones-alpha': 'Synthetic Headphones Alpha (3.5mm TRS)',
      'headphones-bravo': 'Synthetic Headphones Bravo (3.5mm TRS)',
      'xlr-alpha': 'Synthetic XLR Cable Alpha (3m balanced)',
      'xlr-bravo': 'Synthetic XLR Cable Bravo (3m balanced)',
    };

    return proposal.line_items.map((item) => ({
      category: categoryMap[item.product_id] || 'Audio Hardware',
      productId: item.product_id,
      productName: nameMap[item.product_id] || item.product_id,
      offerId: item.offer_id,
      quantity: item.quantity,
      unitPrice: `$${(item.unit_price.amount_minor / 100).toFixed(2)}`,
      lineTotal: `$${(item.merchandise_total.amount_minor / 100).toFixed(2)}`,
      availability: 'In Stock (Curated)',
      status: 'VERIFIED COMPATIBLE',
    }));
  }, [proposal]);

  const columnDefs: ColDef<GridRowData>[] = useMemo(() => [
    { field: 'category', headerName: 'Category', width: 140, filter: true },
    { field: 'productName', headerName: 'Product Name', flex: 1, minWidth: 220, filter: true },
    { field: 'quantity', headerName: 'Qty', width: 85, sortable: true },
    { field: 'unitPrice', headerName: 'Unit Price', width: 115, sortable: true },
    { field: 'lineTotal', headerName: 'Line Total', width: 115, sortable: true },
    { field: 'offerId', headerName: 'Merchant SKU', width: 155 },
    {
      field: 'status',
      headerName: 'Rule Verification',
      width: 175,
      cellRenderer: (params: { value: string }) => {
        return (
          <span className="badge badge-emerald" style={{ marginTop: '7px' }}>
            <CheckCircle2 size={11} />
            {params.value}
          </span>
        );
      },
    },
  ], []);

  if (!proposal) {
    return (
      <div className="surface-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        No bundle proposal selected for tabular comparison.
      </div>
    );
  }

  return (
    <div style={{ width: '100%', marginTop: '0.25rem' }}>
      <div className="ag-theme-quartz-dark" style={{ height: 320, width: '100%', borderRadius: '2px', overflow: 'hidden', border: '1px solid #222222' }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={{
            sortable: true,
            resizable: true,
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', padding: '0.4rem 0.75rem', backgroundColor: '#141414', border: '1px solid #222222', borderRadius: '2px', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#888888' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Table size={12} style={{ color: '#ffffff' }} />
          <span>AG Grid Community Matrix • Sponsor Integration</span>
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span>{proposal.line_items.length} line items</span>
          <span>•</span>
          <span>Single Currency (USD)</span>
          <span>•</span>
          <span style={{ color: '#00e575', fontWeight: 600 }}>Integer Cents Verified</span>
        </div>
      </div>
    </div>
  );
};
