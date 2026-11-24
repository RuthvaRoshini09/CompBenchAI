// COMPBENCH AI - Frontend Application Logic

let allComponents = [];
let currentFilter = "ALL";
let weightChartInstance = null;
let costChartInstance = null;

// DOM Elements
const selectCompA = document.getElementById("select-comp-a");
const selectCompB = document.getElementById("select-comp-b");
const btnSwap = document.getElementById("btn-swap");
const btnCompare = document.getElementById("btn-compare");
const btnCompareText = document.getElementById("btn-compare-text");
const btnAnalyze = document.getElementById("btn-analyze");
const btnAnalyzeText = document.getElementById("btn-analyze-text");
const alertBanner = document.getElementById("alert-banner");
const alertBannerText = document.getElementById("alert-banner-text");
const resultsSection = document.getElementById("results-section");
const aiInsightsContainer = document.getElementById("ai-insights-container");

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
  setupEventListeners();
});

async function initDashboard() {
  try {
    showAlert("", false);
    const response = await fetch("/components");
    if (!response.ok) {
      throw new Error(`Failed to load components: HTTP ${response.status}`);
    }
    allComponents = await response.json();

    updateDashboardMetrics(allComponents);
    populateDropdowns();

    // Default selection: CB001 (Door Panel - Steel) & CB002 (Door Panel - Aluminum)
    selectCompA.value = "CB001";
    selectCompB.value = "CB002";
    updatePreviews();

    // Automatically trigger initial comparison for instant feedback
    runComparison();

  } catch (error) {
    console.error("Dashboard initialization error:", error);
    showAlert(`Error loading component database: ${error.message}`, true, "error");
  }
}

function updateDashboardMetrics(components) {
  document.getElementById("kpi-total-components").textContent = components.length;

  const materials = new Set(components.map(c => c.Material));
  document.getElementById("kpi-material-types").textContent = `${materials.size} Materials`;

  const totalWeight = components.reduce((sum, c) => sum + (Number(c.Weight_kg) || 0), 0);
  const avgWeight = components.length > 0 ? (totalWeight / components.length).toFixed(2) : "0.00";
  document.getElementById("kpi-avg-weight").textContent = `${avgWeight} kg`;
}

function populateDropdowns() {
  const compAVal = selectCompA.value;
  const compBVal = selectCompB.value;

  selectCompA.innerHTML = "";
  selectCompB.innerHTML = "";

  const filtered = currentFilter === "ALL" 
    ? allComponents 
    : allComponents.filter(c => c.Part_Name === currentFilter);

  // Group by Part_Name
  const grouped = {};
  filtered.forEach(c => {
    if (!grouped[c.Part_Name]) grouped[c.Part_Name] = [];
    grouped[c.Part_Name].push(c);
  });

  Object.keys(grouped).sort().forEach(partName => {
    const groupA = document.createElement("optgroup");
    groupA.label = partName;
    const groupB = document.createElement("optgroup");
    groupB.label = partName;

    grouped[partName].forEach(c => {
      const label = `[${c.Part_ID}] ${c.Part_Name} — ${c.Material} (${c.Weight_kg}kg, $${c.Total_Cost_USD})`;
      
      const optA = new Option(label, c.Part_ID);
      const optB = new Option(label, c.Part_ID);

      groupA.appendChild(optA);
      groupB.appendChild(optB);
    });

    selectCompA.appendChild(groupA);
    selectCompB.appendChild(groupB);
  });

  // Restore values if still in options
  if (compAVal && [...selectCompA.options].some(o => o.value === compAVal)) {
    selectCompA.value = compAVal;
  }
  if (compBVal && [...selectCompB.options].some(o => o.value === compBVal)) {
    selectCompB.value = compBVal;
  }

  updatePreviews();
}

function setupEventListeners() {
  selectCompA.addEventListener("change", updatePreviews);
  selectCompB.addEventListener("change", updatePreviews);

  btnSwap.addEventListener("click", () => {
    const temp = selectCompA.value;
    selectCompA.value = selectCompB.value;
    selectCompB.value = temp;
    updatePreviews();
    runComparison();
  });

  btnCompare.addEventListener("click", runComparison);
  btnAnalyze.addEventListener("click", runAnalysis);

  // Part filter buttons
  document.querySelectorAll(".part-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".part-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.getAttribute("data-filter");
      populateDropdowns();
    });
  });
}

function updatePreviews() {
  const a = allComponents.find(c => c.Part_ID === selectCompA.value);
  const b = allComponents.find(c => c.Part_ID === selectCompB.value);

  if (a) {
    document.getElementById("prev-a-material").textContent = a.Material;
    document.getElementById("prev-a-weight").textContent = `${a.Weight_kg} kg`;
    document.getElementById("prev-a-process").textContent = a.Manufacturing_Process;
    document.getElementById("prev-a-cost").textContent = `$${Number(a.Total_Cost_USD).toFixed(2)}`;
  }

  if (b) {
    document.getElementById("prev-b-material").textContent = b.Material;
    document.getElementById("prev-b-weight").textContent = `${b.Weight_kg} kg`;
    document.getElementById("prev-b-process").textContent = b.Manufacturing_Process;
    document.getElementById("prev-b-cost").textContent = `$${Number(b.Total_Cost_USD).toFixed(2)}`;
  }
}

function showAlert(message, show = true, type = "warning") {
  if (!show) {
    alertBanner.style.display = "none";
    return;
  }
  alertBanner.className = `notification-banner ${type}`;
  alertBannerText.textContent = message;
  alertBanner.style.display = "flex";
}

async function runComparison() {
  const idA = selectCompA.value;
  const idB = selectCompB.value;

  if (!idA || !idB) {
    showAlert("Please select both Component A and Component B to benchmark.", true, "warning");
    return;
  }

  showAlert("", false);
  setLoading(btnCompare, btnCompareText, true, "Benchmarking...");

  try {
    const res = await fetch("/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ component_a_id: idA, component_b_id: idB })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || `Server returned HTTP ${res.status}`);
    }

    renderBenchmarkResults(data);
    resultsSection.style.display = "block";

  } catch (error) {
    console.error("Comparison error:", error);
    showAlert(`Benchmark Error: ${error.message}`, true, "error");
  } finally {
    setLoading(btnCompare, btnCompareText, false, "Run Benchmark Comparison");
  }
}

function renderBenchmarkResults(data) {
  const { component_a: a, component_b: b, analysis, component_name } = data;

  // KPI cards
  const wtDiff = analysis.weight_difference_kg;
  const wtRedPct = analysis.weight_reduction_percent;
  document.getElementById("kpi-weight-diff").textContent = `${wtDiff > 0 ? "-" : "+"}${Math.abs(wtDiff).toFixed(2)} kg`;
  document.getElementById("kpi-weight-reduction-badge").textContent = `${wtRedPct.toFixed(2)}% Reduction`;

  const costDiff = analysis.cost_difference_usd;
  const costChgPct = analysis.cost_change_percent;
  document.getElementById("kpi-cost-diff").textContent = `${costDiff >= 0 ? "+" : "-"}$${Math.abs(costDiff).toFixed(2)}`;
  document.getElementById("kpi-cost-change-badge").textContent = `${costChgPct >= 0 ? "+" : ""}${costChgPct.toFixed(2)}% Cost Change`;

  document.getElementById("kpi-mat-transition").textContent = `${a.material} → ${b.material}`;
  document.getElementById("kpi-mat-badge").textContent = analysis.material_changed ? "Material Altered" : "Same Material";

  document.getElementById("kpi-proc-transition").textContent = `${a.manufacturing_process} → ${b.manufacturing_process}`;
  document.getElementById("kpi-proc-badge").textContent = analysis.process_changed ? "Process Shift" : "Same Process";

  // Detailed Specifications Table
  const tbody = document.getElementById("specs-table-body");
  const fullA = allComponents.find(c => c.Part_ID === a.id) || a;
  const fullB = allComponents.find(c => c.Part_ID === b.id) || b;

  const rows = [
    { label: "Part ID", a: a.id, b: b.id, delta: `${a.id} vs ${b.id}` },
    { label: "Component Name", a: component_name, b: component_name, delta: "Equivalent" },
    { label: "Vehicle Model", a: a.vehicle, b: b.vehicle, delta: a.vehicle !== b.vehicle ? "Model Shift" : "Same Model" },
    { label: "OEM", a: fullA.OEM || "OEM A", b: fullB.OEM || "OEM B", delta: fullA.OEM !== fullB.OEM ? "Cross-OEM" : "Same OEM" },
    { label: "Subsystem", a: fullA.Subsystem || "Chassis", b: fullB.Subsystem || "Chassis", delta: "Same System" },
    { label: "Material", a: a.material, b: b.material, delta: analysis.material_changed ? "Changed" : "Identical" },
    { label: "Manufacturing Process", a: a.manufacturing_process, b: b.manufacturing_process, delta: analysis.process_changed ? "Changed" : "Identical" },
    { label: "Weight", a: `${a.weight_kg} kg`, b: `${b.weight_kg} kg`, delta: `${wtDiff.toFixed(2)} kg (${wtRedPct.toFixed(2)}% lighter)` },
    { label: "Total Unit Cost", a: `$${a.cost_usd.toFixed(2)}`, b: `$${b.cost_usd.toFixed(2)}`, delta: `${costDiff >= 0 ? "+" : ""}$${costDiff.toFixed(2)} (${costChgPct.toFixed(2)}%)` },
    { label: "Design Complexity", a: fullA.Design_Complexity || "Medium", b: fullB.Design_Complexity || "Medium", delta: fullA.Design_Complexity !== fullB.Design_Complexity ? "Shift" : "Same" }
  ];

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td class="param-name">${r.label}</td>
      <td class="col-a">${r.a}</td>
      <td class="col-b">${r.b}</td>
      <td><span style="font-size: 0.78rem; opacity: 0.85;">${r.delta}</span></td>
    </tr>
  `).join("");

  // Update Visual Charts
  renderCharts(a, b);
}

function renderCharts(a, b) {
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: {
        grid: { color: "rgba(255,255,255,0.06)" },
        ticks: { color: "#94a3b8" }
      },
      y: {
        grid: { color: "rgba(255,255,255,0.06)" },
        ticks: { color: "#94a3b8" },
        beginAtZero: true
      }
    }
  };

  // 1. Weight Chart
  const ctxWeight = document.getElementById("weightChart").getContext("2d");
  if (weightChartInstance) weightChartInstance.destroy();

  weightChartInstance = new Chart(ctxWeight, {
    type: "bar",
    data: {
      labels: [`A: ${a.id} (${a.material})`, `B: ${b.id} (${b.material})`],
      datasets: [{
        label: "Weight (kg)",
        data: [a.weight_kg, b.weight_kg],
        backgroundColor: ["#3b82f6", "#10b981"],
        borderColor: ["#2563eb", "#059669"],
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: chartOptions
  });

  // 2. Cost Chart
  const ctxCost = document.getElementById("costChart").getContext("2d");
  if (costChartInstance) costChartInstance.destroy();

  costChartInstance = new Chart(ctxCost, {
    type: "bar",
    data: {
      labels: [`A: ${a.id} (${a.material})`, `B: ${b.id} (${b.material})`],
      datasets: [{
        label: "Cost (USD)",
        data: [a.cost_usd, b.cost_usd],
        backgroundColor: ["#60a5fa", "#f59e0b"],
        borderColor: ["#3b82f6", "#d97706"],
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: chartOptions
  });
}

async function runAnalysis() {
  const idA = selectCompA.value;
  const idB = selectCompB.value;

  if (!idA || !idB) {
    showAlert("Please select Component A and B before generating AI insight.", true, "warning");
    return;
  }

  showAlert("", false);
  setLoading(btnAnalyze, btnAnalyzeText, true, "Synthesizing AI Insights...");

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ component_a_id: idA, component_b_id: idB, top_k: 3 })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || `Server returned HTTP ${res.status}`);
    }

    // Ensure benchmark results are displayed
    renderBenchmarkResults(data.comparison);
    resultsSection.style.display = "block";

    // Render AI Intelligence Report
    renderAiInsights(data);
    aiInsightsContainer.style.display = "block";
    aiInsightsContainer.scrollIntoView({ behavior: "smooth" });

  } catch (error) {
    console.error("Analysis error:", error);
    showAlert(`AI Analysis Error: ${error.message}`, true, "error");
  } finally {
    setLoading(btnAnalyze, btnAnalyzeText, false, "Generate AI Engineering Insight");
  }
}

function renderAiInsights(data) {
  const insight = data.insight || {};
  const sections = insight.sections || {};
  const isFallback = insight.status !== "success";

  // Provider Badge
  const badge = document.getElementById("ai-model-badge");
  const fallbackWarning = document.getElementById("ai-fallback-warning");
  const warningText = document.getElementById("ai-warning-text");

  if (isFallback) {
    badge.className = "ai-badge fallback";
    badge.textContent = "Deterministic Fallback Engine";
    fallbackWarning.style.display = "flex";
    warningText.textContent = insight.message || "Gemini API key is not configured in .env. A deterministic benchmark report was generated using Python calculations and RAG engineering knowledge.";
  } else {
    badge.className = "ai-badge live";
    badge.textContent = `Gemini Live AI (${insight.model || "Gemini"})`;
    fallbackWarning.style.display = "none";
  }

  // Populate 8 Report Section Cards
  document.getElementById("rep-summary").textContent = sections.comparison_summary || "Comparison summary unavailable.";
  document.getElementById("rep-weight").textContent = sections.weight_reduction_analysis || "Weight reduction analysis unavailable.";
  document.getElementById("rep-cost").textContent = sections.cost_trade_off_analysis || "Cost trade-off analysis unavailable.";
  document.getElementById("rep-material").textContent = sections.material_and_manufacturing_differences || "Material differences unavailable.";
  document.getElementById("rep-considerations").textContent = sections.engineering_considerations || "Engineering considerations unavailable.";
  document.getElementById("rep-advantages").textContent = sections.potential_advantages || "Advantages unavailable.";
  document.getElementById("rep-risks").textContent = sections.risks_and_limitations || "Risks and limitations unavailable.";
  document.getElementById("rep-recommendation").textContent = sections.final_recommendation || "Final recommendation unavailable.";

  // Populate RAG Context Sources List
  const sourcesContainer = document.getElementById("rag-sources-list");
  const ragSources = data.retrieved_knowledge || [];

  if (ragSources.length === 0) {
    sourcesContainer.innerHTML = "<p style='color: var(--text-muted); font-size: 0.85rem;'>No specific RAG references retrieved for this query.</p>";
  } else {
    sourcesContainer.innerHTML = ragSources.map(s => `
      <div class="rag-source-item">
        <div class="rag-source-header">
          <span>${s.source_title} &bull; ${s.section}</span>
          <span class="rag-source-file">${s.source_file} (Similarity: ${(s.similarity_score * 100).toFixed(1)}%)</span>
        </div>
        <div class="rag-source-excerpt">${s.content}</div>
      </div>
    `).join("");
  }
}

function setLoading(button, textSpan, isLoading, loadingText) {
  if (isLoading) {
    button.disabled = true;
    textSpan.innerHTML = `<span class="loading-overlay"></span> ${loadingText}`;
  } else {
    button.disabled = false;
    textSpan.textContent = loadingText;
  }
}
