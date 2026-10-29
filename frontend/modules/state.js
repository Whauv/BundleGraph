import { fixture } from "./fixtures.js";

export const screens = ["request", "review", "compare", "approval", "recovery"];
export const createState = () => ({ current: "request", maxScreen: 0, requirements: structuredClone(fixture.requirements), proposals: [], selected: null, inspected: null, hiddenComparisonKeys: [], candidateFilters: { category: "all", availability: "all", evidence: "all", maximumPrice: "" }, candidates: null, candidateMode: "fixture", candidateShortlist: [], source: "fixture", evidence: structuredClone(fixture.evidence), authoritativePlan: null, authoritativeApproval: null, generatedReplan: null, backendReadiness: null, error: null, approved: false, failed: false, graphSelection: null, evidenceSelection: null });
export const store = { value: createState() };
export const resetState = () => { store.value = createState(); };
export const canVisit = (screen) => screens.includes(screen) && screens.indexOf(screen) <= store.value.maxScreen;

const SESSION_KEY = "bundlegraph-ui-v1";
export function persistSession() { try { const { requirements, current, maxScreen } = store.value; sessionStorage.setItem(SESSION_KEY, JSON.stringify({ requirements, current: screens.indexOf(current) <= 1 ? current : "review", maxScreen: Math.min(maxScreen, 1) })); } catch { /* Storage may be disabled; the in-memory journey still works. */ } }
export function restoreSession() { try { const saved = JSON.parse(sessionStorage.getItem(SESSION_KEY)); if (saved?.requirements) Object.assign(store.value, { requirements: saved.requirements, current: saved.current || "request", maxScreen: saved.maxScreen || 0 }); } catch { try { sessionStorage.removeItem(SESSION_KEY); } catch { /* Storage may be disabled. */ } } }
export function clearSession() { try { sessionStorage.removeItem(SESSION_KEY); } catch { /* Storage may be disabled. */ } }

export function invalidateFrom(screen) {
  const state = store.value;
  if (state.maxScreen <= screens.indexOf(screen)) return false;
  Object.assign(state, { maxScreen: screens.indexOf(screen), proposals: [], selected: null, inspected: null, hiddenComparisonKeys: [], authoritativePlan: null, authoritativeApproval: null, generatedReplan: null, approved: false, failed: false, graphSelection: null, evidenceSelection: null });
  return true;
}
