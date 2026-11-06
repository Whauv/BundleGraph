const WORKFLOW_KEY = 'bundlegraph.workflow';

export interface SavedWorkflow {
  promptText?: string;
  budgetDollars?: number;
  participants?: number;
  laptopConnector?: 'usb-c' | 'usb-a' | 'unknown';
  listeningRequirement?: 'independent_headphones' | 'shared_headphones' | 'no_monitoring' | 'unknown';
  deadlineDate?: string;
  requestReference?: string;
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const CONNECTORS = new Set(['usb-c', 'usb-a', 'unknown']);
const MONITORING = new Set(['independent_headphones', 'shared_headphones', 'no_monitoring', 'unknown']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function validateSavedWorkflow(value: unknown): SavedWorkflow {
  if (!isRecord(value)) return {};
  const result: SavedWorkflow = {};
  if (typeof value.promptText === 'string' && value.promptText.length <= 10_000) result.promptText = value.promptText;
  if (typeof value.budgetDollars === 'number' && Number.isFinite(value.budgetDollars) && value.budgetDollars > 0 && value.budgetDollars <= 1_000_000 && Number.isInteger(value.budgetDollars * 100)) result.budgetDollars = value.budgetDollars;
  if (typeof value.participants === 'number' && Number.isInteger(value.participants) && value.participants >= 1 && value.participants <= 20) result.participants = value.participants;
  if (typeof value.laptopConnector === 'string' && CONNECTORS.has(value.laptopConnector)) result.laptopConnector = value.laptopConnector as SavedWorkflow['laptopConnector'];
  if (typeof value.listeningRequirement === 'string' && MONITORING.has(value.listeningRequirement)) result.listeningRequirement = value.listeningRequirement as SavedWorkflow['listeningRequirement'];
  if (value.deadlineDate === '' || (typeof value.deadlineDate === 'string' && DATE.test(value.deadlineDate) && !Number.isNaN(Date.parse(`${value.deadlineDate}T12:00:00Z`)))) result.deadlineDate = value.deadlineDate;
  if (typeof value.requestReference === 'string' && /^[A-Za-z0-9._:-]{1,160}$/.test(value.requestReference)) result.requestReference = value.requestReference;
  return result;
}

export function readSavedWorkflow(storage: Storage = sessionStorage): SavedWorkflow {
  try {
    const raw = storage.getItem(WORKFLOW_KEY);
    return raw ? validateSavedWorkflow(JSON.parse(raw)) : {};
  } catch {
    try { storage.removeItem(WORKFLOW_KEY); } catch { /* Storage may be unavailable. */ }
    return {};
  }
}

export function writeSavedWorkflow(value: SavedWorkflow, storage: Storage = sessionStorage): boolean {
  try {
    storage.setItem(WORKFLOW_KEY, JSON.stringify(validateSavedWorkflow(value)));
    return true;
  } catch {
    return false;
  }
}
