import { $, escapeHtml, evidenceMarkup, statusClass } from "./utils.js";

export function renderGraph(state, bundle) {
  const nodes = bundle.graphNodes || [], edges = bundle.graphEdges || [];
  const positions = { "mic-a": [65, 100], "mic-b": [170, 100], interface: [285, 100], laptop: [410, 52], headphones: [410, 148], cables: [285, 185] };
  nodes.forEach((node, index) => { positions[node.id] ||= [65 + (index % 4) * 120, 55 + Math.floor(index / 4) * 110]; });
  if (!nodes.length) {
    $("#graph").innerHTML = '<p class="muted">No dependency graph was supplied for this proposal. Its blocking findings remain available below.</p>';
    $("#graph-detail").innerHTML = '<p class="muted">No component detail is available.</p>';
    $("#graph-alternative").innerHTML = '<li>No graph relationships were supplied.</li>';
    return;
  }
  const lineMarkup = edges.map((edge) => { const start = positions[edge.from], end = positions[edge.to], linked = state.evidenceSelection && edge.evidence.includes(state.evidenceSelection); return `<g role="button" tabindex="0" class="graph-edge ${state.graphSelection === edge.id ? "active" : ""} ${linked ? "evidence-linked" : ""}" data-edge="${escapeHtml(edge.id)}" aria-label="${escapeHtml(edge.finding)}"><line x1="${start[0]}" y1="${start[1]}" x2="${end[0]}" y2="${end[1]}"></line></g><line class="graph-edge-line" x1="${start[0]}" y1="${start[1]}" x2="${end[0]}" y2="${end[1]}"></line>`; }).join("");
  const nodeMarkup = nodes.map((node) => { const position = positions[node.id], linked = state.evidenceSelection && node.evidence.includes(state.evidenceSelection); return `<g role="button" tabindex="0" data-node="${escapeHtml(node.id)}" aria-label="Inspect ${escapeHtml(node.label)}"><circle class="graph-node ${state.graphSelection === node.id ? "active" : ""} ${linked ? "evidence-linked" : ""}" cx="${position[0]}" cy="${position[1]}" r="36"></circle><text class="node-label" x="${position[0]}" y="${position[1] + 4}">${escapeHtml(node.label)}</text></g>`; }).join("");
  $("#graph").innerHTML = `<svg viewBox="0 0 500 225" role="img" aria-label="Selectable dependency graph">${lineMarkup}${nodeMarkup}</svg>`;
  $("#graph-alternative").innerHTML = [...nodes.map((node) => `${node.label}: ${node.finding}`), ...edges.map((edge) => `${edge.from} to ${edge.to}: ${edge.finding}`)].map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  $("#graph").querySelectorAll("[data-node],[data-edge]").forEach((element) => { const select = () => { state.graphSelection = element.dataset.node || element.dataset.edge; renderGraph(state, bundle, rerender); }; element.addEventListener("click", select); element.addEventListener("keydown", (event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); select(); } }); });
  const node = nodes.find((item) => item.id === state.graphSelection), edge = edges.find((item) => item.id === state.graphSelection), item = node || edge;
  $("#graph-detail").innerHTML = item ? `<span class="tag ${statusClass(item.status || "Passed")}">${escapeHtml(item.status || "Passed")}</span><h4>${escapeHtml(node ? node.label : "Connection")}</h4><dl class="kv"><dt>Role</dt><dd>${escapeHtml(node ? node.role : "Compatibility relationship")}</dd><dt>Quantity</dt><dd>${escapeHtml(node ? node.quantity : "Not applicable")}</dd><dt>What was checked</dt><dd>${escapeHtml(item.finding)}</dd></dl>${evidenceMarkup(item.evidence, state.evidence)}` : '<p class="muted">Select a component or connection. A readable relationship list is available below the graph.</p>';
}
