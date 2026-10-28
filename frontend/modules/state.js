import { fixture } from "./fixtures.js";

export const screens = ["request", "review", "compare", "approval", "recovery"];
export const createState = () => ({ current: "request", maxScreen: 0, requirements: structuredClone(fixture.requirements), proposals: [], selected: null, inspected: null, hiddenComparisonKeys: [], candidateFilters: { category: "all", availability: "all", evidence: "all", maximumPrice: "" }, candidateShortlist: [], source: "fixture", evidence: structuredClone(fixture.evidence), authoritativePlan: null, authoritativeApproval: null, backendReadiness: null, error: null, approved: false, failed: false, graphSelection: null, evidenceSelection: null });
export const store = { value: createState() };
export const resetState = () => { store.value = createState(); };
export const canVisit = (screen) => screens.indexOf(screen) <= store.value.maxScreen;

export function invalidateFrom(screen) {
  const state = store.value;
  if (state.maxScreen <= screens.indexOf(screen)) return false;
  Object.assign(state, { maxScreen: screens.indexOf(screen), proposals: [], selected: null, inspected: null, hiddenComparisonKeys: [], authoritativePlan: null, authoritativeApproval: null, approved: false, failed: false, graphSelection: null, evidenceSelection: null });
  return true;
}
