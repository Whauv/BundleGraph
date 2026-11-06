export function dollarsToMinorUnits(value: number): number | null {
  if (!Number.isFinite(value) || value <= 0 || value > 1_000_000) return null;
  const scaled = value * 100;
  if (!Number.isInteger(scaled)) return null;
  return scaled;
}

export function formatMoney(amountMinor: number, currency = 'USD'): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amountMinor / 100);
}
