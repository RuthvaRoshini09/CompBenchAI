// COMPBENCH AI - Frontend Application Logic & Industrial Visualization Engine

let allComponents = [];
let currentFilter = "ALL";
let lastComparisonData = null;

// Chart.js Instances
let weightChartInstance = null;
let costChartInstance = null;
let materialChartInstance = null;

/**
 * Configurable USD to INR conversion rate for automotive engineering estimations.
 * Reads from window.USD_TO_INR_RATE or window.COMPBENCH_CONFIG if provided, defaulting to 85.0.
 * The original USD numbers in data/components.csv remain the canonical source of truth.
 * All percentage calculations are computed strictly from base USD data to ensure currency independence.
 */
const USD_TO_INR_RATE = (typeof window !== "undefined" && (window.USD_TO_INR_RATE || (window.COMPBENCH_CONFIG && window.COMPBENCH_CONFIG.USD_TO_INR_RATE))) || 85.0;

/**
 * Format currency with estimated INR as primary and USD as secondary.
 * e.g. "+₹18,062.50 (estimated)" with secondary "(+$212.50 USD)"
 */
function formatInrPrimary(usdAmount, showSign = false) {
  if (typeof usdAmount !== "number" || isNaN(usdAmount)) return "--";
  const absUsd = Math.abs(usdAmount);
  const inrVal = absUsd * USD_TO_INR_RATE;
  const sign = showSign ? (usdAmount >= 0 ? "+" : "-") : "";
  const inrFormatted = inrVal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${sign}₹${inrFormatted} (estimated)`;
}

function formatInrEstimate(usdAmount, compact = false) {
  if (typeof usdAmount !== "number" || isNaN(usdAmount)) return "--";
  const inrVal = Math.round(usdAmount * USD_TO_INR_RATE);
  const formatted = `₹${inrVal.toLocaleString("en-IN")}`;
  if (compact) {
    return `${formatted} (est.)`;
  }
  return `${formatted} (est. @ ₹${USD_TO_INR_RATE}/$)`;
}

/**
 * Safe HTML string escaping utility.
 */
function escapeHtml(str) {
  if (typeof str !== "string") return str == null ? "" : String(str);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// DOM Element References
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
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const themeToggleText = document.getElementById("theme-toggle-text");
const selectionValidationMsg = document.getElementById("selection-validation-msg");
const btnToggleGuide = document.getElementById("btn-toggle-guide");
const guidePanel = document.getElementById("guide-panel");

// Initialize application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initDashboard();
  setupEventListeners();
  setupKpiNavigation();
});

/* =========================================================
   1. Theme Management (Light & Dark Modes)
   ========================================================= */

function initTheme() {
  const savedTheme = localStorage.getItem("compbench_theme");
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (prefersDark ? "dark" : "light");

  applyTheme(initialTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("compbench_theme", theme);

  if (themeIcon && themeToggleText) {
    if (theme === "dark") {
      themeIcon.textContent = "🌙";
      themeToggleText.textContent = "Dark";
    } else {
      themeIcon.textContent = "☀️";
      themeToggleText.textContent = "Light";
    }
  }

  // Update chart visual styles to match active theme
  updateAllChartsTheme();
}

function getChartThemeColors() {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  return {
    grid: isLight ? "rgba(0, 0, 0, 0.08)" : "rgba(255, 255, 255, 0.08)",
    text: isLight ? "#475569" : "#94a3b8",
    tooltipBg: isLight ? "#1e293b" : "#0f172a",
    tooltipText: "#ffffff",
    tooltipBorder: isLight ? "#475569" : "#334155"
  };
}

function updateAllChartsTheme() {
  const themeColors = getChartThemeColors();

  [weightChartInstance, costChartInstance].forEach(chart => {
    if (chart && chart.options && chart.options.scales) {
      if (chart.options.scales.x) {
        chart.options.scales.x.grid.color = themeColors.grid;
        chart.options.scales.x.ticks.color = themeColors.text;
      }
      if (chart.options.scales.y) {
        chart.options.scales.y.grid.color = themeColors.grid;
        chart.options.scales.y.ticks.color = themeColors.text;
      }
      if (chart.options.plugins && chart.options.plugins.tooltip) {
        chart.options.plugins.tooltip.backgroundColor = themeColors.tooltipBg;
        chart.options.plugins.tooltip.titleColor = themeColors.tooltipText;
        chart.options.plugins.tooltip.bodyColor = themeColors.tooltipText;
        chart.options.plugins.tooltip.borderColor = themeColors.tooltipBorder;
      }
      chart.update();
    }
  });

  if (materialChartInstance && materialChartInstance.options) {
    if (materialChartInstance.options.plugins && materialChartInstance.options.plugins.legend) {
      materialChartInstance.options.plugins.legend.labels.color = themeColors.text;
    }
    if (materialChartInstance.options.plugins && materialChartInstance.options.plugins.tooltip) {
      materialChartInstance.options.plugins.tooltip.backgroundColor = themeColors.tooltipBg;
      materialChartInstance.options.plugins.tooltip.titleColor = themeColors.tooltipText;
      materialChartInstance.options.plugins.tooltip.bodyColor = themeColors.tooltipText;
      materialChartInstance.options.plugins.tooltip.borderColor = themeColors.tooltipBorder;
    }
    materialChartInstance.update();
  }
}

/* =========================================================
   2. Dashboard Initialization & Metric Summaries
   ========================================================= */

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
    renderFleetMaterialDistribution(allComponents);

    // Update dynamically configured exchange rate display
    const rateDisplay = document.getElementById("rate-display");
    if (rateDisplay) {
      rateDisplay.textContent = `1 USD ≈ ₹${USD_TO_INR_RATE.toFixed(1)} est.`;
    }

    // Default benchmarking pair: CB001 (Steel Door Panel) & CB002 (Aluminum Door Panel)
    selectCompA.value = "CB001";
    selectCompB.value = "CB002";
    updatePreviews();

    // Trigger initial benchmark comparison
    runComparison();

  } catch (error) {
    console.error("Dashboard initialization error:", error);
    showAlert(`Error loading component database: ${error.message}`, true, "error");
  }
}

function updateDashboardMetrics(components) {
  const totalElem = document.getElementById("kpi-total-components");
  if (totalElem) totalElem.textContent = components.length;

  const materials = new Set(components.map(c => c.Material));
  const matElem = document.getElementById("kpi-material-types");
  if (matElem) matElem.textContent = `${materials.size} Materials`;

  const totalWeight = components.reduce((sum, c) => sum + (Number(c.Weight_kg) || 0), 0);
  const avgWeight = components.length > 0 ? (totalWeight / components.length).toFixed(2) : "0.00";
  const weightElem = document.getElementById("kpi-avg-weight");
  if (weightElem) weightElem.textContent = `${avgWeight} kg`;
}

/**
 * Filter and populate options for Component A or Component B selector.
 * - Searchable by Part_ID, Part_Name, Material, or Vehicle_Model.
 * - Organized / grouped by Part_Name using <optgroup>.
 * - Formatted concisely as: CB030 — Seat Frame — Cast Iron.
 * - Shows only the selected component when the dropdown is closed.
 */
function filterSelectorOptions(slot) {
  const selectElem = slot === "A" ? selectCompA : selectCompB;
  const searchInput = slot === "A" ? document.getElementById("search-comp-a") : document.getElementById("search-comp-b");
  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
  const currentVal = selectElem.value;

  selectElem.innerHTML = "";

  let baseList = currentFilter === "ALL"
    ? allComponents
    : allComponents.filter(c => c.Part_Name === currentFilter);

  if (query.length > 0) {
    baseList = baseList.filter(c =>
      c.Part_ID.toLowerCase().includes(query) ||
      c.Part_Name.toLowerCase().includes(query) ||
      c.Material.toLowerCase().includes(query) ||
      (c.Vehicle_Model && c.Vehicle_Model.toLowerCase().includes(query))
    );
  }

  if (baseList.length === 0) {
    const emptyOpt = new Option("No matching components found", "");
    emptyOpt.disabled = true;
    selectElem.appendChild(emptyOpt);
    return;
  }

  // Group components by Part_Name
  const grouped = {};
  baseList.forEach(c => {
    if (!grouped[c.Part_Name]) grouped[c.Part_Name] = [];
    grouped[c.Part_Name].push(c);
  });

  Object.keys(grouped).sort().forEach(partName => {
    const group = document.createElement("optgroup");
    group.label = partName;

    grouped[partName].forEach(c => {
      // Display options as: CB030 — Seat Frame — Cast Iron
      const label = `${c.Part_ID} — ${c.Part_Name} — ${c.Material}`;
      const opt = new Option(label, c.Part_ID);
      group.appendChild(opt);
    });

    selectElem.appendChild(group);
  });

  // Preserve previous selection if still available
  if (currentVal && [...selectElem.options].some(o => o.value === currentVal)) {
    selectElem.value = currentVal;
  } else if (selectElem.options.length > 0 && !selectElem.options[0].disabled) {
    selectElem.selectedIndex = 0;
  }

  updatePreviews();
}

function populateDropdowns() {
  filterSelectorOptions("A");
  filterSelectorOptions("B");
}

function setupEventListeners() {
  selectCompA.addEventListener("change", updatePreviews);
  selectCompB.addEventListener("change", updatePreviews);

  // Search input listeners for Component A and B selectors
  const searchA = document.getElementById("search-comp-a");
  const searchB = document.getElementById("search-comp-b");
  if (searchA) searchA.addEventListener("input", () => filterSelectorOptions("A"));
  if (searchB) searchB.addEventListener("input", () => filterSelectorOptions("B"));

  btnSwap.addEventListener("click", () => {
    const temp = selectCompA.value;
    selectCompA.value = selectCompB.value;
    selectCompB.value = temp;
    updatePreviews();
    runComparison();
  });

  btnCompare.addEventListener("click", runComparison);
  btnAnalyze.addEventListener("click", runAnalysis);

  // Benchmarking Guide Expandable Toggle (Requirement 3)
  if (btnToggleGuide && guidePanel) {
    btnToggleGuide.addEventListener("click", () => {
      const isExpanded = btnToggleGuide.classList.contains("active");
      if (isExpanded) {
        btnToggleGuide.classList.remove("active");
        btnToggleGuide.setAttribute("aria-expanded", "false");
        guidePanel.style.display = "none";
      } else {
        btnToggleGuide.classList.add("active");
        btnToggleGuide.setAttribute("aria-expanded", "true");
        guidePanel.style.display = "block";
      }
    });
  }

  // Quick Part Category filter buttons
  document.querySelectorAll(".part-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".part-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.getAttribute("data-filter");
      populateDropdowns();
    });
  });
}

/**
 * Validate that Component A and Component B belong to the same Part_Name.
 * Compares actual Part_Name values (not just Subsystem equality).
 * Displays an explicit mismatch explanation and provides a one-click auto-alignment action.
 */
function validateSubsystemMatch(compA, compB) {
  if (!selectionValidationMsg) return true;

  if (!compA || !compB) {
    selectionValidationMsg.style.display = "none";
    return true;
  }

  const nameA = String(compA.Part_Name || "").trim();
  const nameB = String(compB.Part_Name || "").trim();

  if (nameA !== nameB) {
    selectionValidationMsg.style.display = "block";
    selectionValidationMsg.innerHTML = `
      <div class="mismatch-content">
        <div style="display: flex; align-items: flex-start; gap: 0.65rem;">
          <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="mismatch-icon">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div class="mismatch-text">
            <strong>Component Mismatch Detected:</strong> Please select two records with the same Part_Name.
            <div class="mismatch-details">
              Component A is <strong>"${escapeHtml(compA.Part_Name)}"</strong> (${escapeHtml(compA.Part_ID)}), but Component B is <strong>"${escapeHtml(compB.Part_Name)}"</strong> (${escapeHtml(compB.Part_ID)}).
            </div>
          </div>
        </div>
        <button id="btn-fix-selection" class="btn-fix-match" onclick="autoMatchComponentB('${escapeHtml(compA.Part_Name)}')">
          Align Component B to ${escapeHtml(compA.Part_Name)} &rarr;
        </button>
      </div>
    `;
    return false;
  } else {
    selectionValidationMsg.style.display = "none";
    return true;
  }
}

/**
 * Helper to automatically correct mismatched selection by aligning Component B to Component A's Part_Name.
 * Guarantees that the matched record has the exact same Part_Name.
 */
window.autoMatchComponentB = function(targetPartName) {
  const currentA = selectCompA.value;
  const targetClean = String(targetPartName || "").trim();
  const match = allComponents.find(c => String(c.Part_Name || "").trim() === targetClean && c.Part_ID !== currentA) ||
                allComponents.find(c => String(c.Part_Name || "").trim() === targetClean);
  if (match) {
    selectCompB.value = match.Part_ID;
    updatePreviews();
    runComparison();
  }
};

function updatePreviews() {
  const a = allComponents.find(c => c.Part_ID === selectCompA.value);
  const b = allComponents.find(c => c.Part_ID === selectCompB.value);

  // Validate subsystem alignment
  validateSubsystemMatch(a, b);

  if (a) {
    const inrA = formatInrPrimary(Number(a.Total_Cost_USD), false);
    document.getElementById("prev-a-material").textContent = a.Material;
    document.getElementById("prev-a-weight").textContent = `${Number(a.Weight_kg).toFixed(2)} kg`;
    document.getElementById("prev-a-process").textContent = a.Manufacturing_Process;
    document.getElementById("prev-a-cost").textContent = `${inrA} ($${Number(a.Total_Cost_USD).toFixed(2)} USD)`;
  }

  if (b) {
    const inrB = formatInrPrimary(Number(b.Total_Cost_USD), false);
    document.getElementById("prev-b-material").textContent = b.Material;
    document.getElementById("prev-b-weight").textContent = `${Number(b.Weight_kg).toFixed(2)} kg`;
    document.getElementById("prev-b-process").textContent = b.Manufacturing_Process;
    document.getElementById("prev-b-cost").textContent = `${inrB} ($${Number(b.Total_Cost_USD).toFixed(2)} USD)`;
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

/* =========================================================
   3. Interactive KPI Navigation & Modal Controllers
   ========================================================= */

function setupKpiNavigation() {
  const cardTotal = document.getElementById("card-total-components");
  const cardMaterials = document.getElementById("card-material-categories");
  const cardWeight = document.getElementById("card-avg-weight");
  const cardDataset = document.getElementById("card-dataset-info");

  // Total Components -> Opens Complete Catalog Modal
  if (cardTotal) {
    cardTotal.addEventListener("click", openComponentCatalogModal);
    cardTotal.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openComponentCatalogModal();
      }
    });
  }

  // Material Categories -> Scrolls to Material Distribution Chart
  if (cardMaterials) {
    cardMaterials.addEventListener("click", navigateToMaterialDistribution);
    cardMaterials.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        navigateToMaterialDistribution();
      }
    });
  }

  // Avg Component Weight -> Scrolls to Weight Analysis Chart
  if (cardWeight) {
    cardWeight.addEventListener("click", navigateToWeightAnalysis);
    cardWeight.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        navigateToWeightAnalysis();
      }
    });
  }

  // Data Fidelity -> Opens Dataset Information Modal
  if (cardDataset) {
    cardDataset.addEventListener("click", openDatasetInfoModal);
    cardDataset.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openDatasetInfoModal();
      }
    });
  }

  // Modal Close buttons
  const catalogCloseBtn = document.getElementById("modal-catalog-close");
  if (catalogCloseBtn) {
    catalogCloseBtn.addEventListener("click", closeComponentCatalogModal);
  }

  const datasetCloseBtn = document.getElementById("modal-dataset-close");
  if (datasetCloseBtn) {
    datasetCloseBtn.addEventListener("click", closeDatasetInfoModal);
  }

  // Close modals on background backdrop click
  const catalogModal = document.getElementById("modal-components-catalog");
  if (catalogModal) {
    catalogModal.addEventListener("click", (e) => {
      if (e.target === catalogModal) closeComponentCatalogModal();
    });
  }

  const datasetModal = document.getElementById("modal-dataset-info");
  if (datasetModal) {
    datasetModal.addEventListener("click", (e) => {
      if (e.target === datasetModal) closeDatasetInfoModal();
    });
  }

  // Close modals on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeComponentCatalogModal();
      closeDatasetInfoModal();
    }
  });

  // Modal Catalog search & filter input listeners
  const searchInput = document.getElementById("catalog-search-input");
  const matFilter = document.getElementById("catalog-material-filter");

  if (searchInput) searchInput.addEventListener("input", filterAndRenderCatalog);
  if (matFilter) matFilter.addEventListener("change", filterAndRenderCatalog);
}

function openComponentCatalogModal() {
  const modal = document.getElementById("modal-components-catalog");
  if (!modal) return;
  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
  filterAndRenderCatalog();
  const searchInput = document.getElementById("catalog-search-input");
  if (searchInput) searchInput.focus();
}

function closeComponentCatalogModal() {
  const modal = document.getElementById("modal-components-catalog");
  if (!modal) return;
  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
}

function openDatasetInfoModal() {
  const modal = document.getElementById("modal-dataset-info");
  if (!modal) return;
  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");
}

function closeDatasetInfoModal() {
  const modal = document.getElementById("modal-dataset-info");
  if (!modal) return;
  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
}

function navigateToMaterialDistribution() {
  resultsSection.style.display = "block";
  const chartCanvas = document.getElementById("materialChart");
  if (!chartCanvas) return;
  const card = chartCanvas.closest(".chart-card");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    triggerCardPulse(card);
  }
}

function navigateToWeightAnalysis() {
  resultsSection.style.display = "block";
  const chartCanvas = document.getElementById("weightChart");
  if (!chartCanvas) return;
  const card = chartCanvas.closest(".chart-card");
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    triggerCardPulse(card);
  }
}

function triggerCardPulse(elem) {
  elem.classList.remove("card-highlight-pulse");
  void elem.offsetWidth; // Force CSS reflow
  elem.classList.add("card-highlight-pulse");
}

function filterAndRenderCatalog() {
  const tbody = document.getElementById("catalog-table-body");
  const countBadge = document.getElementById("catalog-count-badge");
  const searchInput = document.getElementById("catalog-search-input");
  const matFilter = document.getElementById("catalog-material-filter");

  if (!tbody) return;

  const query = (searchInput?.value || "").toLowerCase().trim();
  const matSelected = matFilter?.value || "ALL";

  const filtered = allComponents.filter(c => {
    const matchesMat = matSelected === "ALL" || c.Material === matSelected;
    const matchesQuery = !query ||
      (c.Part_ID && c.Part_ID.toLowerCase().includes(query)) ||
      (c.Part_Name && c.Part_Name.toLowerCase().includes(query)) ||
      (c.Vehicle_Model && c.Vehicle_Model.toLowerCase().includes(query)) ||
      (c.OEM && c.OEM.toLowerCase().includes(query)) ||
      (c.Material && c.Material.toLowerCase().includes(query)) ||
      (c.Manufacturing_Process && c.Manufacturing_Process.toLowerCase().includes(query));
    return matchesMat && matchesQuery;
  });

  if (countBadge) {
    countBadge.textContent = `${filtered.length} / ${allComponents.length} Records`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No matching component records found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(c => {
    const inrPrimary = formatInrPrimary(Number(c.Total_Cost_USD), false);
    return `
      <tr>
        <td><strong>${escapeHtml(c.Part_ID)}</strong></td>
        <td>${escapeHtml(c.Part_Name)}</td>
        <td>${escapeHtml(c.Vehicle_Model)} <span style="font-size: 0.72rem; color: var(--text-muted);">(${escapeHtml(c.OEM)})</span></td>
        <td><span class="badge-ai" style="font-size: 0.7rem;">${escapeHtml(c.Material)}</span></td>
        <td>${Number(c.Weight_kg).toFixed(2)} kg</td>
        <td><strong>${inrPrimary}</strong> <span style="font-size: 0.72rem; color: var(--text-muted);">($${Number(c.Total_Cost_USD).toFixed(2)} USD)</span></td>
        <td>${escapeHtml(c.Manufacturing_Process)}</td>
        <td style="text-align: right; white-space: nowrap;">
          <button class="btn-catalog-select" onclick="loadComponentIntoBenchmark('${c.Part_ID}', 'A')">Use as A</button>
          <button class="btn-catalog-select" onclick="loadComponentIntoBenchmark('${c.Part_ID}', 'B')">Use as B</button>
        </td>
      </tr>
    `;
  }).join("");
}

// Global hook to allow modal catalog buttons to load components into slots
window.loadComponentIntoBenchmark = function(partId, slot) {
  if (slot === "A") {
    selectCompA.value = partId;
  } else {
    selectCompB.value = partId;
  }
  updatePreviews();
  closeComponentCatalogModal();
  runComparison();
};

/* =========================================================
   4. Benchmark Comparison Execution
   ========================================================= */

async function runComparison() {
  const idA = selectCompA.value;
  const idB = selectCompB.value;

  if (!idA || !idB) {
    showAlert("Please select both Component A and Component B to benchmark.", true, "warning");
    return;
  }

  const compA = allComponents.find(c => c.Part_ID === idA);
  const compB = allComponents.find(c => c.Part_ID === idB);

  // Validate exact Part_Name equality before sending request
  if (compA && compB && String(compA.Part_Name || "").trim() !== String(compB.Part_Name || "").trim()) {
    showAlert(`Please select two records with the same Part_Name. Currently selected: Component A is "${compA.Part_Name}" (${compA.Part_ID}) and Component B is "${compB.Part_Name}" (${compB.Part_ID}).`, true, "warning");
    validateSubsystemMatch(compA, compB);
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
      let errorMsg = `Server returned HTTP ${res.status}`;
      if (data && data.detail) {
        if (typeof data.detail === "string") {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
        } else {
          errorMsg = JSON.stringify(data.detail);
        }
      }
      throw new Error(errorMsg);
    }

    lastComparisonData = data;
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

  const wtDiff = analysis.weight_difference_kg;
  const wtRedPct = analysis.weight_reduction_percent;
  const isLighter = analysis.lighter_design;

  const costDiff = analysis.cost_difference_usd;
  const costChgPct = analysis.cost_change_percent; // Mathematically independent percentage
  const isCheaper = analysis.lower_cost_design;

  // Format primary INR values (Requirement 2)
  const costDiffInrPrimary = formatInrPrimary(costDiff, true);
  const costDiffUsdText = `${costDiff >= 0 ? "+" : "-"}$${Math.abs(costDiff).toFixed(2)} USD`;

  // 1. Weight Reduction KPI Card
  const wtDiffElem = document.getElementById("kpi-weight-diff");
  const wtBadgeElem = document.getElementById("kpi-weight-reduction-badge");
  const wtCardElem = document.getElementById("kpi-weight-card");
  const wtDescElem = document.getElementById("kpi-weight-desc");

  wtDiffElem.textContent = `${wtDiff > 0 ? "-" : "+"}${Math.abs(wtDiff).toFixed(2)} kg`;
  wtBadgeElem.textContent = `${wtRedPct.toFixed(2)}% ${isLighter ? "Reduction" : "Increase"}`;
  wtCardElem.className = `kpi-card ${isLighter ? "green" : "amber"}`;
  wtDescElem.textContent = isLighter
    ? `Component B reduces mass by ${Math.abs(wtDiff).toFixed(2)} kg (${wtRedPct.toFixed(2)}% lighter), enhancing dynamic handling and EV range.`
    : `Component B adds ${Math.abs(wtDiff).toFixed(2)} kg (+${Math.abs(wtRedPct).toFixed(2)}% heavier) relative to Component A.`;

  // 2. Manufacturing Cost KPI Card (Primary INR with secondary USD - Requirement 2)
  const costDiffElem = document.getElementById("kpi-cost-diff");
  const costSecondaryElem = document.getElementById("kpi-cost-secondary");
  const costBadgeElem = document.getElementById("kpi-cost-change-badge");
  const costCardElem = document.getElementById("kpi-cost-card");
  const costDescElem = document.getElementById("kpi-cost-desc");

  costDiffElem.textContent = costDiffInrPrimary;
  if (costSecondaryElem) {
    costSecondaryElem.textContent = costDiffUsdText;
  }
  costBadgeElem.textContent = `${costChgPct >= 0 ? "+" : ""}${costChgPct.toFixed(2)}% Change`;
  costCardElem.className = `kpi-card ${isCheaper ? "green" : "amber"}`;
  costDescElem.textContent = costDiff >= 0
    ? `Component B carries a unit cost premium of ${costDiffInrPrimary} / $${Math.abs(costDiff).toFixed(2)} USD (+${costChgPct.toFixed(2)}%) due to material and tooling differences.`
    : `Component B yields a unit cost savings of ${costDiffInrPrimary} / $${Math.abs(costDiff).toFixed(2)} USD (${costChgPct.toFixed(2)}%) per manufactured unit.`;

  // 3. Material & Process Transition KPI Cards
  document.getElementById("kpi-mat-transition").textContent = `${a.material} → ${b.material}`;
  document.getElementById("kpi-mat-badge").textContent = analysis.material_changed ? "Alloy/Polymer Altered" : "Identical Material";
  document.getElementById("kpi-mat-desc").textContent = analysis.material_changed
    ? `Transition from ${a.material} to ${b.material} alters structural stiffness, corrosion resistance, and scrap value.`
    : `Both designs utilize ${a.material}; structural variances derive from geometry and manufacturing tooling.`;

  document.getElementById("kpi-proc-transition").textContent = `${a.manufacturing_process} → ${b.manufacturing_process}`;
  document.getElementById("kpi-proc-badge").textContent = analysis.process_changed ? "Tooling Process Shift" : "Identical Process";
  document.getElementById("kpi-proc-desc").textContent = analysis.process_changed
    ? `Shifted from ${a.manufacturing_process} to ${b.manufacturing_process}, affecting press line cycle times and capital tooling amortization.`
    : `Both designs utilize ${a.manufacturing_process}; tooling and cycle times remain structurally consistent.`;

  // 4. Comparison Summary Bar (Requirement 5)
  const summaryPairElem = document.getElementById("summary-component-pair");
  const summaryPartElem = document.getElementById("summary-part-name");
  const summaryWeightVal = document.getElementById("summary-weight-val");
  const summaryWeightPct = document.getElementById("summary-weight-pct");
  const summaryCostInrVal = document.getElementById("summary-cost-inr-val");
  const summaryCostPct = document.getElementById("summary-cost-pct");
  const summaryCostUsdVal = document.getElementById("summary-cost-usd-val");

  if (summaryPairElem) {
    summaryPairElem.textContent = `[${a.id}] ${a.vehicle} (${a.material}) vs [${b.id}] ${b.vehicle} (${b.material})`;
  }
  if (summaryPartElem) summaryPartElem.textContent = component_name;
  if (summaryWeightVal) summaryWeightVal.textContent = `${wtDiff > 0 ? "-" : "+"}${Math.abs(wtDiff).toFixed(2)} kg`;
  if (summaryWeightPct) summaryWeightPct.textContent = `${wtRedPct.toFixed(2)}% ${isLighter ? "reduction" : "increase"}`;
  if (summaryCostInrVal) summaryCostInrVal.textContent = costDiffInrPrimary;
  if (summaryCostPct) summaryCostPct.textContent = `${costChgPct >= 0 ? "+" : ""}${costChgPct.toFixed(2)}% cost ${isCheaper ? "savings" : "increase"}`;
  if (summaryCostUsdVal) summaryCostUsdVal.textContent = costDiffUsdText;

  // 5. Detailed Technical Specifications Comparison Table
  const tbody = document.getElementById("specs-table-body");
  const fullA = allComponents.find(c => c.Part_ID === a.id) || a;
  const fullB = allComponents.find(c => c.Part_ID === b.id) || b;

  const inrCostA = formatInrPrimary(Number(a.cost_usd), false);
  const inrCostB = formatInrPrimary(Number(b.cost_usd), false);

  const rows = [
    { label: "Part ID", a: a.id, b: b.id, delta: `${a.id} vs ${b.id}` },
    { label: "Component Name", a: component_name, b: component_name, delta: "Equivalent Assembly" },
    { label: "Vehicle Model", a: a.vehicle, b: b.vehicle, delta: a.vehicle !== b.vehicle ? "Model Variant" : "Identical Model" },
    { label: "OEM Architecture", a: fullA.OEM || "OEM A", b: fullB.OEM || "OEM B", delta: fullA.OEM !== fullB.OEM ? "Cross-OEM" : "Same OEM" },
    { label: "Subsystem Category", a: fullA.Subsystem || "Chassis", b: fullB.Subsystem || "Chassis", delta: "Same Subsystem" },
    { label: "Material Composition", a: a.material, b: b.material, delta: analysis.material_changed ? "Material Shift" : "Identical" },
    { label: "Manufacturing Process", a: a.manufacturing_process, b: b.manufacturing_process, delta: analysis.process_changed ? "Process Shift" : "Identical" },
    { label: "Component Weight (kg)", a: `${Number(a.weight_kg).toFixed(2)} kg`, b: `${Number(b.weight_kg).toFixed(2)} kg`, delta: `${wtDiff > 0 ? "-" : "+"}${Math.abs(wtDiff).toFixed(2)} kg (${wtRedPct.toFixed(2)}% ${isLighter ? "lighter" : "heavier"})` },
    { label: "Total Unit Cost (Est. INR & USD)", a: `<strong>${inrCostA}</strong><br><small style="color:var(--text-muted);">($${Number(a.cost_usd).toFixed(2)} USD)</small>`, b: `<strong>${inrCostB}</strong><br><small style="color:var(--text-muted);">($${Number(b.cost_usd).toFixed(2)} USD)</small>`, delta: `<strong>${costDiffInrPrimary}</strong><br><small style="color:var(--text-muted);">(${costDiffUsdText}, ${costChgPct >= 0 ? "+" : ""}${costChgPct.toFixed(2)}%)</small>` },
    { label: "Design Complexity", a: fullA.Design_Complexity || "Medium", b: fullB.Design_Complexity || "Medium", delta: fullA.Design_Complexity !== fullB.Design_Complexity ? "Complexity Shift" : "Identical Complexity" }
  ];

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td class="param-name">${r.label}</td>
      <td class="col-a">${r.a}</td>
      <td class="col-b">${r.b}</td>
      <td><span style="font-size: 0.78rem; opacity: 0.9;">${r.delta}</span></td>
    </tr>
  `).join("");

  // 6. Render Visual Comparison Charts (Standardized - Requirement 4)
  renderComparisonCharts(a, b);
}

/* =========================================================
   5. Standardized Visual Comparison Charts (Chart.js)
   ========================================================= */

function renderComparisonCharts(a, b) {
  const themeColors = getChartThemeColors();

  // ---------------------------------------------------------
  // Graph 1: Component Mass Benchmark (kg) - Horizontal Bar Chart
  // Shows both component names and exact kg values
  // ---------------------------------------------------------
  const ctxWeight = document.getElementById("weightChart").getContext("2d");
  if (weightChartInstance) weightChartInstance.destroy();

  const isLighter = b.weight_kg < a.weight_kg;
  const colorBWeight = isLighter ? "#10b981" : "#f59e0b";

  weightChartInstance = new Chart(ctxWeight, {
    type: "bar",
    data: {
      labels: [
        `[${a.id}] ${a.vehicle} (${a.material})`,
        `[${b.id}] ${b.vehicle} (${b.material})`
      ],
      datasets: [{
        label: "Mass (kg)",
        data: [Number(a.weight_kg), Number(b.weight_kg)],
        backgroundColor: ["#3b82f6", colorBWeight],
        borderColor: ["#2563eb", isLighter ? "#059669" : "#d97706"],
        borderWidth: 1.5,
        borderRadius: 5,
        barThickness: 28
      }]
    },
    options: {
      indexAxis: "y", // Horizontal comparison chart
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipText,
          bodyColor: themeColors.tooltipText,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (context) => ` Component Mass: ${context.parsed.x.toFixed(2)} kg`
          }
        }
      },
      scales: {
        x: {
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.text,
            callback: (val) => `${val} kg`
          },
          title: {
            display: true,
            text: "Mass in Kilograms (kg)",
            color: themeColors.text,
            font: { size: 11, weight: "600" }
          },
          beginAtZero: true
        },
        y: {
          grid: { display: false },
          ticks: { color: themeColors.text, font: { weight: "600", size: 11 } }
        }
      }
    }
  });

  // ---------------------------------------------------------
  // Graph 2: Total Unit Cost Benchmark - Bar Chart
  // Primary displayed currency: Estimated INR, USD in tooltips/secondary
  // ---------------------------------------------------------
  const ctxCost = document.getElementById("costChart").getContext("2d");
  if (costChartInstance) costChartInstance.destroy();

  const isCheaper = b.cost_usd < a.cost_usd;
  const colorBCost = isCheaper ? "#10b981" : "#f59e0b";

  const inrCostAVal = a.cost_usd * USD_TO_INR_RATE;
  const inrCostBVal = b.cost_usd * USD_TO_INR_RATE;

  costChartInstance = new Chart(ctxCost, {
    type: "bar",
    data: {
      labels: [
        `[${a.id}] ${a.vehicle} (${a.material})`,
        `[${b.id}] ${b.vehicle} (${b.material})`
      ],
      datasets: [{
        label: `Unit Cost (₹ estimated @ ₹${USD_TO_INR_RATE}/$)`,
        data: [inrCostAVal, inrCostBVal],
        backgroundColor: ["#3b82f6", colorBCost],
        borderColor: ["#2563eb", isCheaper ? "#059669" : "#d97706"],
        borderWidth: 1.5,
        borderRadius: 5,
        barThickness: 34
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipText,
          bodyColor: themeColors.tooltipText,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (context) => {
              const inrVal = context.parsed.y;
              const usdVal = inrVal / USD_TO_INR_RATE;
              const formattedInr = inrVal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
              return ` Unit Cost: ₹${formattedInr} (estimated) [$${usdVal.toFixed(2)} USD]`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: themeColors.text, font: { weight: "600", size: 11 } }
        },
        y: {
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.text,
            callback: (val) => `₹${Number(val).toLocaleString("en-IN")}`
          },
          title: {
            display: true,
            text: `Unit Cost in INR (₹ estimated @ ₹${USD_TO_INR_RATE}/USD)`,
            color: themeColors.text,
            font: { size: 11, weight: "600" }
          },
          beginAtZero: true
        }
      }
    }
  });
}

function renderFleetMaterialDistribution(components) {
  const ctxMaterial = document.getElementById("materialChart").getContext("2d");
  if (materialChartInstance) materialChartInstance.destroy();

  const themeColors = getChartThemeColors();

  // Aggregate material counts
  const counts = {};
  components.forEach(c => {
    counts[c.Material] = (counts[c.Material] || 0) + 1;
  });

  const labels = Object.keys(counts);
  const dataValues = Object.values(counts);
  const total = components.length;

  const materialColorMap = {
    "Steel": "#64748b",
    "Aluminum": "#0284c7",
    "Plastic": "#10b981",
    "Magnesium": "#a855f7",
    "Cast Iron": "#f59e0b"
  };

  const bgColors = labels.map(mat => materialColorMap[mat] || "#3b82f6");

  materialChartInstance = new Chart(ctxMaterial, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: bgColors,
        borderWidth: 2,
        borderColor: document.documentElement.getAttribute("data-theme") === "light" ? "#ffffff" : "#111a2e"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: {
            color: themeColors.text,
            boxWidth: 12,
            font: { size: 11 }
          }
        },
        tooltip: {
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipText,
          bodyColor: themeColors.tooltipText,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (context) => {
              const val = context.parsed;
              const pct = ((val / total) * 100).toFixed(1);
              return ` ${context.label}: ${val} parts (${pct}%)`;
            }
          }
        }
      },
      cutout: "62%"
    }
  });
}

/* =========================================================
   6. AI Engineering Insights Execution & RAG Rendering
   ========================================================= */

async function runAnalysis() {
  const idA = selectCompA.value;
  const idB = selectCompB.value;

  if (!idA || !idB) {
    showAlert("Please select Component A and Component B before generating AI insights.", true, "warning");
    return;
  }

  const compA = allComponents.find(c => c.Part_ID === idA);
  const compB = allComponents.find(c => c.Part_ID === idB);

  // Validate exact Part_Name equality before sending request
  if (compA && compB && String(compA.Part_Name || "").trim() !== String(compB.Part_Name || "").trim()) {
    const mismatchMsg = `Please select two records with the same Part_Name. Currently selected: Component A is "${compA.Part_Name}" (${compA.Part_ID}) and Component B is "${compB.Part_Name}" (${compB.Part_ID}).`;
    showAlert(mismatchMsg, true, "warning");
    validateSubsystemMatch(compA, compB);
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
      let errorMsg = `Server returned HTTP ${res.status}`;
      if (data && data.detail) {
        if (typeof data.detail === "string") {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
        } else {
          errorMsg = JSON.stringify(data.detail);
        }
      }
      throw new Error(errorMsg);
    }

    // Ensure benchmark comparison cards and charts are displayed
    lastComparisonData = data.comparison;
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

/**
 * Strips markdown asterisks, hashes, and formatting for clean plain-text excerpts.
 */
function stripMarkdown(text) {
  if (!text || typeof text !== "string") return "";
  return text
    .replace(/\\(\*|_)/g, "$1")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/(\*|_)(.*?)\1/g, "$2")
    .replace(/#{1,6}\s+/g, "")
    .replace(/^[-*]\s+/gm, "")
    .trim();
}

/**
 * Safely renders basic Markdown formatting (bold, italics, lists, paragraphs).
 * Completely eliminates raw asterisks and broken symbols.
 */
function renderMarkdownBasic(text) {
  if (!text || typeof text !== "string") return "";

  // 1. Unescape escaped asterisks/underscores
  let processed = text.replace(/\\(\*|_)/g, "$1");

  // 2. Escape HTML
  let clean = escapeHtml(processed);

  // 3. Bold: **text**
  clean = clean.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // 4. Italics: *text* (excluding already formatted strong tags)
  clean = clean.replace(/(^|[^*])\*([^*]+?)\*/g, "$1<em>$2</em>");

  // 5. Lists and Paragraphs
  const lines = clean.split("\n");
  const output = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (/^[-*]\s+/.test(line)) {
      if (!inList) {
        output.push('<ul class="report-bullet-list">');
        inList = true;
      }
      const itemContent = line.replace(/^[-*]\s+/, "");
      output.push(`<li>${itemContent}</li>`);
    } else {
      if (inList) {
        output.push("</ul>");
        inList = false;
      }
      if (line.length > 0) {
        output.push(`<p>${line}</p>`);
      }
    }
  }

  if (inList) {
    output.push("</ul>");
  }

  return output.join("");
}

/**
 * Resilient helper to extract section text from structured object or markdown report text.
 */
function extractSectionContent(sections, reportText, key, altPatterns = [], fallbackKeys = []) {
  if (sections && sections[key] && typeof sections[key] === "string" && sections[key].trim().length > 0) {
    return sections[key].trim();
  }
  if (sections && Array.isArray(fallbackKeys)) {
    for (const fbKey of fallbackKeys) {
      if (sections[fbKey] && typeof sections[fbKey] === "string" && sections[fbKey].trim().length > 0) {
        return sections[fbKey].trim();
      }
    }
  }
  if (reportText && typeof reportText === "string") {
    for (const pat of altPatterns) {
      const match = reportText.match(pat);
      if (match && match[1] && match[1].trim().length > 0) {
        return match[1].trim();
      }
    }
  }
  return "";
}

function renderAiInsights(data) {
  const insight = data.insight || {};
  const sections = insight.sections || {};
  const reportText = insight.report || "";

  // Only display Gemini Live AI when a Gemini request actually succeeds with non-empty report.
  // Merely having an API key configured does not qualify; if Gemini fails or is unconfigured, show deterministic fallback.
  const isGeminiSuccess = Boolean(
    insight &&
    insight.status === "success" &&
    typeof insight.report === "string" &&
    insight.report.trim().length > 0
  );

  // Provider Badge & Fallback Warning
  const badge = document.getElementById("ai-model-badge");
  const fallbackWarning = document.getElementById("ai-fallback-warning");
  const warningText = document.getElementById("ai-warning-text");

  if (!isGeminiSuccess) {
    badge.className = "ai-badge fallback";
    badge.textContent = "Deterministic Engineering Report";
    fallbackWarning.style.display = "flex";
    warningText.textContent = insight.message || "Deterministic engineering report generated from exact Python calculations and retrieved automotive knowledge.";
  } else {
    badge.className = "ai-badge live";
    badge.textContent = `Gemini Live AI (${insight.model || "Gemini"})`;
    fallbackWarning.style.display = "none";
  }

  // Regex patterns to extract sections if Gemini altered heading Markdown syntax
  const secPatterns = {
    comparison_summary: [
      /(?:###\s*1\.\s*Comparison Summary|\*\*1\.\s*Comparison Summary\*\*|1\.\s*Comparison Summary):?\s*([\s\S]*?)(?=(?:###\s*2\.|\*\*2\.\s*Weight|2\.\s*Weight|$))/i
    ],
    weight_analysis: [
      /(?:###\s*2\.\s*Weight Analysis|\*\*2\.\s*Weight Analysis\*\*|2\.\s*Weight Analysis):?\s*([\s\S]*?)(?=(?:###\s*3\.|\*\*3\.\s*Cost|3\.\s*Cost|$))/i
    ],
    cost_analysis: [
      /(?:###\s*3\.\s*Cost Analysis|\*\*3\.\s*Cost Analysis\*\*|3\.\s*Cost Analysis):?\s*([\s\S]*?)(?=(?:###\s*4\.|\*\*4\.\s*Material|4\.\s*Material|$))/i
    ],
    material_and_manufacturing: [
      /(?:###\s*4\.\s*Material\s*&?\s*Manufacturing|\*\*4\.\s*Material\s*&?\s*Manufacturing\*\*|4\.\s*Material\s*&?\s*Manufacturing):?\s*([\s\S]*?)(?=(?:###\s*5\.|\*\*5\.\s*Engineering|5\.\s*Engineering|$))/i
    ],
    engineering_conclusion: [
      /(?:###\s*5\.\s*Engineering Conclusion|\*\*5\.\s*Engineering Conclusion\*\*|5\.\s*Engineering Conclusion):?\s*([\s\S]*?)(?=(?:\*INR estimates|###|$))/i
    ]
  };

  const compData = data.comparison || {};
  const a = compData.component_a || {};
  const b = compData.component_b || {};
  const analysis = compData.analysis || {};

  const inrDeltaFormatted = formatInrPrimary(analysis.cost_difference_usd, true);

  const summaryText = extractSectionContent(sections, reportText, "comparison_summary", secPatterns.comparison_summary) ||
    `${compData.component_name || "Component"}: ${a.id || "CB001"} (${a.material || "Material"}) vs ${b.id || "CB002"} (${b.material || "Material"}).`;

  const weightText = extractSectionContent(sections, reportText, "weight_analysis", secPatterns.weight_analysis, ["weight_reduction_analysis"]) ||
    `- Baseline: ${a.weight_kg != null ? a.weight_kg.toFixed(2) : "--"} kg\n- Candidate: ${b.weight_kg != null ? b.weight_kg.toFixed(2) : "--"} kg\n- Reduction: ${analysis.weight_difference_kg} kg (${analysis.weight_reduction_percent}%)`;

  const costText = extractSectionContent(sections, reportText, "cost_analysis", secPatterns.cost_analysis, ["cost_trade_off_analysis"]) ||
    `- Baseline: $${a.cost_usd != null ? a.cost_usd.toFixed(2) : "--"} USD\n- Candidate: $${b.cost_usd != null ? b.cost_usd.toFixed(2) : "--"} USD\n- Increase: ${inrDeltaFormatted} ($${analysis.cost_difference_usd != null ? analysis.cost_difference_usd.toFixed(2) : "--"} USD, or ${analysis.cost_change_percent}%)`;

  const materialText = extractSectionContent(sections, reportText, "material_and_manufacturing", secPatterns.material_and_manufacturing, ["material_and_manufacturing_differences"]) ||
    `Material changes from ${a.material} to ${b.material}. Manufacturing process: ${a.manufacturing_process} vs ${b.manufacturing_process}.`;

  const conclText = extractSectionContent(sections, reportText, "engineering_conclusion", secPatterns.engineering_conclusion, ["engineering_considerations_and_conclusion", "engineering_considerations", "final_recommendation"]) ||
    `Candidate B is lighter but costs more. Final selection requires structural, fatigue and manufacturing validation.`;

  const summaryElem = document.getElementById("rep-summary");
  const weightElem = document.getElementById("rep-weight");
  const costElem = document.getElementById("rep-cost");
  const materialElem = document.getElementById("rep-material");
  const conclElem = document.getElementById("rep-considerations-conclusion");

  if (summaryElem) summaryElem.innerHTML = renderMarkdownBasic(summaryText);
  if (weightElem) weightElem.innerHTML = renderMarkdownBasic(weightText);
  if (costElem) costElem.innerHTML = renderMarkdownBasic(costText);
  if (materialElem) materialElem.innerHTML = renderMarkdownBasic(materialText);
  if (conclElem) conclElem.innerHTML = renderMarkdownBasic(conclText);

  // Render RAG references with compact preview, clean text, and expandable full passage
  const sourcesContainer = document.getElementById("rag-sources-list");
  const ragSources = data.retrieved_knowledge || [];

  if (ragSources.length === 0) {
    sourcesContainer.innerHTML = "<p style='color: var(--text-muted); font-size: 0.82rem;'>No specific automotive engineering passages retrieved for this query.</p>";
  } else {
    sourcesContainer.innerHTML = ragSources.map((s, idx) => {
      const fullContent = (s.content || "").trim();
      const stripped = stripMarkdown(fullContent);
      const previewText = stripped.length > 140 ? stripped.substring(0, 140) + "..." : stripped;
      const simScore = (Number(s.similarity_score || 0) * 100).toFixed(1);

      return `
        <div class="rag-source-item">
          <div class="rag-source-header">
            <div class="rag-source-title">
              <span class="rag-badge">Ref ${idx + 1}</span>
              <strong>${escapeHtml(s.source_title || "Engineering Reference")}</strong> &mdash; <span>${escapeHtml(s.section || "Overview")}</span>
            </div>
            <span class="rag-source-file">${escapeHtml(s.source_file || "")} &bull; ${simScore}% Match</span>
          </div>

          <div class="rag-source-preview">${escapeHtml(previewText)}</div>

          <details class="rag-expandable">
            <summary class="rag-expand-btn">
              <span>View Reference</span>
            </summary>
            <div class="rag-source-excerpt">${renderMarkdownBasic(fullContent)}</div>
          </details>
        </div>
      `;
    }).join("");
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
