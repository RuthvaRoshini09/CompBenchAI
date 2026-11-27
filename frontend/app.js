// COMPBENCH AI - Frontend Application Logic & Industrial Visualization Engine

let allComponents = [];
let currentFilter = "ALL";
let lastComparisonData = null;

// Chart.js Instances
let weightChartInstance = null;
let costChartInstance = null;
let materialChartInstance = null;
let expandedChartInstance = null;
let currentExpandedChartType = null;

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

// Authentication & Session Management
function getCsrfToken() {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)compbench_csrf=([^;]+)/);
  if (match) return decodeURIComponent(match[1]);
  if (typeof sessionStorage !== "undefined") {
    const cached = sessionStorage.getItem("compbench_csrf");
    if (cached) return cached;
  }
  return "";
}

function getAuthHeaders(customHeaders = {}) {
  const headers = Object.assign({}, customHeaders);
  // Session-bound CSRF header attached to protect cookie-authenticated state-changing requests
  const csrf = getCsrfToken();
  if (csrf) {
    headers["X-CompBench-CSRF"] = csrf;
  }
  return headers;
}

async function authFetch(url, options = {}) {
  const opt = Object.assign({}, options);
  opt.credentials = "include"; // Sends secure HttpOnly cookie automatically
  opt.headers = getAuthHeaders(opt.headers);

  const res = await fetch(url, opt);
  if (res.status === 401 && typeof window !== "undefined") {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.removeItem("compbench_user");
    }
    const currentPath = window.location.pathname;
    const redirectUrl = currentPath && currentPath !== "/login" ? `/login?redirect=${encodeURIComponent(currentPath)}` : "/login";
    window.location.href = redirectUrl;
  }
  return res;
}

async function verifySessionOrRedirect() {
  if (typeof window === "undefined") return true;
  try {
    const res = await authFetch("/api/auth/me");
    if (!res.ok) {
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.removeItem("compbench_user");
        sessionStorage.removeItem("compbench_csrf");
      }
      window.location.href = "/login";
      return false;
    }
    const data = await res.json();
    if (data && data.user) {
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.setItem("compbench_user", JSON.stringify(data.user));
        if (data.csrf_token) {
          sessionStorage.setItem("compbench_csrf", data.csrf_token);
        }
      }
      const emailElem = document.getElementById("user-email-display");
      if (emailElem && data.user.email) {
        emailElem.textContent = data.user.email;
      }
    }
    return true;
  } catch (err) {
    console.error("Session verification error:", err);
    window.location.href = "/login";
    return false;
  }
}

function setupLogoutListener() {
  const logoutBtn = document.getElementById("btn-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await authFetch("/api/auth/logout", {
          method: "POST"
        });
      } catch (e) {
        console.error("Logout request failed:", e);
      } finally {
        if (typeof sessionStorage !== "undefined") {
          sessionStorage.removeItem("compbench_user");
          sessionStorage.removeItem("compbench_csrf");
        }
        window.location.href = "/login";
      }
    });
  }
}

// Initialize application on DOM ready or immediately if already loaded
async function startApp() {
  initTheme();
  const authenticated = await verifySessionOrRedirect();
  if (!authenticated) return;
  initDashboard();
  setupEventListeners();
  setupKpiNavigation();
  setupLogoutListener();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startApp);
} else {
  startApp();
}

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

  [weightChartInstance, costChartInstance, materialChartInstance, expandedChartInstance].forEach(chart => {
    if (chart && chart.options && chart.options.scales) {
      if (chart.options.scales.x) {
        if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = themeColors.grid;
        if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = themeColors.text;
        if (chart.options.scales.x.title) chart.options.scales.x.title.color = themeColors.text;
      }
      if (chart.options.scales.y) {
        if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = themeColors.grid;
        if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = themeColors.text;
        if (chart.options.scales.y.title) chart.options.scales.y.title.color = themeColors.text;
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
}

/* =========================================================
   2. Dashboard Initialization & Metric Summaries
   ========================================================= */

async function initDashboard() {
  try {
    showAlert("", false);
    const response = await authFetch("/components");
    if (!response.ok) {
      throw new Error(`Failed to load components: HTTP ${response.status}`);
    }
    allComponents = await response.json();

    if (!Array.isArray(allComponents) || allComponents.length === 0) {
      throw new Error("Component dataset returned from API is empty.");
    }

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

    // Clear loading state and show explicit error message in both selectors
    if (selectCompA) {
      selectCompA.innerHTML = '<option value="" disabled selected>⚠️ Error loading components. Check API connection.</option>';
    }
    if (selectCompB) {
      selectCompB.innerHTML = '<option value="" disabled selected>⚠️ Error loading components. Check API connection.</option>';
    }

    // Reflect loading failure in KPI summary cards
    const totalElem = document.getElementById("kpi-total-components");
    if (totalElem) totalElem.textContent = "Error";
    const matElem = document.getElementById("kpi-material-types");
    if (matElem) matElem.textContent = "--";
    const weightElem = document.getElementById("kpi-avg-weight");
    if (weightElem) weightElem.textContent = "-- kg";
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

  // Interactive Chart Toolbars & Modal Controls
  setupChartInteractions();
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
window.autoMatchComponentB = function (targetPartName) {
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
  resetTradeoffAnalysis();
  resetMaterialIntelligence();
  if (resultsSection) resultsSection.style.display = "none";

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
window.loadComponentIntoBenchmark = function (partId, slot) {
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
    resetTradeoffAnalysis();
    resetMaterialIntelligence();
    return;
  }

  const compA = allComponents.find(c => c.Part_ID === idA);
  const compB = allComponents.find(c => c.Part_ID === idB);

  // Validate exact Part_Name equality before sending request
  if (compA && compB && String(compA.Part_Name || "").trim() !== String(compB.Part_Name || "").trim()) {
    showAlert(`Please select two records with the same Part_Name. Currently selected: Component A is "${compA.Part_Name}" (${compA.Part_ID}) and Component B is "${compB.Part_Name}" (${compB.Part_ID}).`, true, "warning");
    validateSubsystemMatch(compA, compB);
    resetTradeoffAnalysis();
    resetMaterialIntelligence();
    return;
  }

  showAlert("", false);
  setLoading(btnCompare, btnCompareText, true, "Benchmarking...");

  try {
    const res = await authFetch("/compare", {
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

    // Show comparison completion status indicator
    const statusPill = document.getElementById("comparison-status-pill");
    if (statusPill) {
      statusPill.style.display = "inline-flex";
      statusPill.classList.remove("pill-pulse");
      void statusPill.offsetWidth;
      statusPill.classList.add("pill-pulse");
    }

    // Automatically navigate to comparison results with smooth scrolling
    requestAnimationFrame(() => {
      setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
        const summaryBar = document.getElementById("comparison-summary-bar");
        if (summaryBar) triggerCardPulse(summaryBar);
      }, 70);
    });

  } catch (error) {
    console.error("Comparison error:", error);
    showAlert(`Benchmark Error: ${error.message}`, true, "error");
    resetTradeoffAnalysis();
    resetMaterialIntelligence();
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
  const costChgPct = analysis.cost_change_percent;
  const isCheaper = analysis.lower_cost_design;

  const fullA = allComponents.find(c => c.Part_ID === a.id) || a;
  const fullB = allComponents.find(c => c.Part_ID === b.id) || b;

  const inrCostA = formatInrPrimary(Number(a.cost_usd), false);
  const inrCostB = formatInrPrimary(Number(b.cost_usd), false);
  const costDiffInrPrimary = formatInrPrimary(costDiff, true);
  const costDiffUsdText = `${costDiff >= 0 ? "+" : "-"}$${Math.abs(costDiff).toFixed(2)} USD`;

  // ---------------------------------------------------------
  // SECTION 1: Comparison Header
  // ---------------------------------------------------------
  const subTag = document.getElementById("results-subsystem-tag");
  const titleA = document.getElementById("results-title-a");
  const titleB = document.getElementById("results-title-b");
  const subHeading = document.getElementById("results-comparison-subheading");

  if (subTag) subTag.textContent = `Subsystem: ${component_name}`;
  if (titleA) titleA.textContent = `[${a.id}] ${a.vehicle} (${a.material})`;
  if (titleB) titleB.textContent = `[${b.id}] ${b.vehicle} (${b.material})`;
  if (subHeading) {
    subHeading.textContent = `Direct mass benchmarking and technical parameter comparison between ${a.id} and ${b.id}.`;
  }

  // ---------------------------------------------------------
  // SECTION 2: Technical Specification Cards (Side-by-Side)
  // ---------------------------------------------------------
  // Baseline Component A
  const specAId = document.getElementById("spec-a-id");
  const specAName = document.getElementById("spec-a-name");
  const specAVehicle = document.getElementById("spec-a-vehicle");
  const specAMat = document.getElementById("spec-a-material");
  const specAProc = document.getElementById("spec-a-process");
  const specAWt = document.getElementById("spec-a-weight");
  const specACost = document.getElementById("spec-a-cost");
  const specACostInr = document.getElementById("spec-a-cost-inr");
  const specAComp = document.getElementById("spec-a-complexity");

  if (specAId) specAId.textContent = a.id;
  if (specAName) specAName.textContent = component_name;
  if (specAVehicle) specAVehicle.textContent = `Model: ${a.vehicle} (${fullA.OEM || "OEM"})`;
  if (specAMat) specAMat.textContent = a.material;
  if (specAProc) specAProc.textContent = a.manufacturing_process;
  if (specAWt) specAWt.textContent = `${Number(a.weight_kg).toFixed(2)} kg`;
  if (specACost) specACost.textContent = `$${Number(a.cost_usd).toFixed(2)} USD`;
  if (specACostInr) specACostInr.textContent = `est. ${inrCostA}`;
  if (specAComp) specAComp.textContent = fullA.Design_Complexity || "Medium";

  // Candidate Component B
  const specBId = document.getElementById("spec-b-id");
  const specBName = document.getElementById("spec-b-name");
  const specBVehicle = document.getElementById("spec-b-vehicle");
  const specBMat = document.getElementById("spec-b-material");
  const specBProc = document.getElementById("spec-b-process");
  const specBWt = document.getElementById("spec-b-weight");
  const specBCost = document.getElementById("spec-b-cost");
  const specBCostInr = document.getElementById("spec-b-cost-inr");
  const specBComp = document.getElementById("spec-b-complexity");

  if (specBId) specBId.textContent = b.id;
  if (specBName) specBName.textContent = component_name;
  if (specBVehicle) specBVehicle.textContent = `Model: ${b.vehicle} (${fullB.OEM || "OEM"})`;
  if (specBMat) specBMat.textContent = b.material;
  if (specBProc) specBProc.textContent = b.manufacturing_process;
  if (specBWt) specBWt.textContent = `${Number(b.weight_kg).toFixed(2)} kg`;
  if (specBCost) specBCost.textContent = `$${Number(b.cost_usd).toFixed(2)} USD`;
  if (specBCostInr) specBCostInr.textContent = `est. ${inrCostB}`;
  if (specBComp) specBComp.textContent = fullB.Design_Complexity || "Medium";

  // ---------------------------------------------------------
  // SECTION 3: Component Mass Benchmarking Graph
  // ---------------------------------------------------------
  const massLine = document.getElementById("mass-chart-summary-line");
  if (massLine) {
    if (wtDiff > 0.001) {
      massLine.textContent = `Candidate [${b.id}] achieves a ${Math.abs(wtDiff).toFixed(2)} kg (${wtRedPct.toFixed(2)}%) mass reduction relative to Baseline [${a.id}].`;
    } else if (wtDiff < -0.001) {
      massLine.textContent = `Candidate [${b.id}] adds ${Math.abs(wtDiff).toFixed(2)} kg (+${Math.abs(wtRedPct).toFixed(2)}% heavier) relative to Baseline [${a.id}].`;
    } else {
      massLine.textContent = `Both components have identical mass (${Number(a.weight_kg).toFixed(2)} kg).`;
    }
  }
  renderComparisonCharts(a, b);

  // ---------------------------------------------------------
  // SECTION 4: Detailed Technical Specifications Comparison Table
  // ---------------------------------------------------------
  const tbody = document.getElementById("specs-table-body");
  if (tbody) {
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
  }

  // ---------------------------------------------------------
  // SECTION 5: One Concise Engineering Decision Summary
  // ---------------------------------------------------------
  const tradeoff = data.tradeoff_analysis || (data.analysis && data.analysis.tradeoff_analysis);
  renderTradeoffAnalysis(tradeoff, a, b);
}

/* =========================================================
   5. Standardized Visual Comparison Charts (Chart.js)
   ========================================================= */

function renderComparisonCharts(a, b) {
  const themeColors = getChartThemeColors();
  const isNarrow = typeof window !== "undefined" && window.innerWidth < 480;

  // ---------------------------------------------------------
  // Graph 1: Component Mass Benchmark (kg) - Line Chart
  // Displays circular data-point markers, straight connecting line,
  // exact weight values near markers, and clear axis labels
  // ---------------------------------------------------------
  const weightCanvas = document.getElementById("weightChart");
  if (!weightCanvas) return;
  const ctxWeight = weightCanvas.getContext("2d");
  if (weightChartInstance) weightChartInstance.destroy();

  const isLighter = b.weight_kg < a.weight_kg;
  const colorBWeight = isLighter ? "#10b981" : "#f59e0b";
  const lineColor = isLighter ? "#10b981" : "#3b82f6";

  const weightLabelA = isNarrow ? `[${a.id}] ${a.vehicle}` : `[${a.id}] ${a.vehicle} (${a.material})`;
  const weightLabelB = isNarrow ? `[${b.id}] ${b.vehicle}` : `[${b.id}] ${b.vehicle} (${b.material})`;

  const maxWeightVal = Math.max(Number(a.weight_kg), Number(b.weight_kg));
  const suggestedYMax = maxWeightVal > 0 ? maxWeightVal * 1.35 : 10;

  // Custom inline Chart.js plugin to draw exact weight labels directly near circular markers
  const massDataLabelsPlugin = {
    id: "massDataLabels",
    afterDatasetsDraw(chart) {
      const { ctx, data } = chart;
      const meta = chart.getDatasetMeta(0);
      if (!meta || !meta.data || !meta.data.length) return;

      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      ctx.save();

      meta.data.forEach((point, index) => {
        const val = data.datasets[0].data[index];
        if (val === undefined || val === null) return;
        const formatted = `${Number(val).toFixed(2)} kg`;

        ctx.font = "bold 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        const textMetrics = ctx.measureText(formatted);
        const paddingX = 8;
        const boxHeight = 20;
        const boxWidth = textMetrics.width + paddingX * 2;
        const boxX = point.x - boxWidth / 2;
        const boxY = point.y - 30; // Positioned cleanly above circular point marker

        // Pill background for high legibility in light & dark modes
        ctx.fillStyle = isLight ? "#ffffff" : "#0f172a";
        ctx.strokeStyle = index === 0 ? "#3b82f6" : colorBWeight;
        ctx.lineWidth = 1.5;

        ctx.beginPath();
        if (typeof ctx.roundRect === "function") {
          ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 4);
        } else {
          ctx.rect(boxX, boxY, boxWidth, boxHeight);
        }
        ctx.fill();
        ctx.stroke();

        // Exact weight text
        ctx.fillStyle = isLight ? "#0f172a" : "#f8fafc";
        ctx.fillText(formatted, point.x, boxY + boxHeight / 2);
      });

      ctx.restore();
    }
  };

  weightChartInstance = new Chart(ctxWeight, {
    type: "line",
    data: {
      labels: [weightLabelA, weightLabelB],
      datasets: [{
        label: "Component Mass (kg)",
        data: [Number(a.weight_kg), Number(b.weight_kg)],
        borderColor: lineColor,
        backgroundColor: "rgba(59, 130, 246, 0.08)",
        borderWidth: 2.5,
        tension: 0, // Straight connecting line (no curved or smoothed lines)
        fill: false,
        pointStyle: "circle",
        pointRadius: isNarrow ? 6 : 8,
        pointHoverRadius: isNarrow ? 8 : 10,
        pointBackgroundColor: ["#3b82f6", colorBWeight],
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2
      }]
    },
    plugins: [massDataLabelsPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: themeColors.text,
            font: { weight: "600", size: isNarrow ? 10 : 11 },
            boxWidth: 16,
            boxHeight: 3
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
            label: (context) => ` Component Mass: ${Number(context.parsed.y).toFixed(2)} kg`
          }
        }
      },
      scales: {
        x: {
          offset: true, // Prevents circular points from clipping on the canvas edges
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11, weight: "600" }
          },
          title: {
            display: true,
            text: "Benchmarked Components (Baseline vs Candidate)",
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11, weight: "600" }
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: suggestedYMax,
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11 },
            callback: (val) => `${val} kg`
          },
          title: {
            display: true,
            text: "Component Mass (kg)",
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11, weight: "600" }
          }
        }
      }
    }
  });

  // ---------------------------------------------------------
  // Graph 2: Total Unit Cost Benchmark - Horizontal Bar Chart
  // Standardized horizontal style matching Graph 1
  // Primary displayed currency: Estimated INR, USD in tooltips/secondary
  // ---------------------------------------------------------
  const costCanvas = document.getElementById("costChart");
  if (costCanvas) {
    const ctxCost = costCanvas.getContext("2d");
    if (costChartInstance) costChartInstance.destroy();

    const isCheaper = b.cost_usd < a.cost_usd;
    const colorBCost = isCheaper ? "#10b981" : "#f59e0b";

    const inrCostAVal = a.cost_usd * USD_TO_INR_RATE;
    const inrCostBVal = b.cost_usd * USD_TO_INR_RATE;

    const costLabelA = isNarrow ? `[${a.id}] ${a.vehicle}` : `[${a.id}] ${a.vehicle} (${a.material})`;
    const costLabelB = isNarrow ? `[${b.id}] ${b.vehicle}` : `[${b.id}] ${b.vehicle} (${b.material})`;

    costChartInstance = new Chart(ctxCost, {
      type: "bar",
      data: {
        labels: [costLabelA, costLabelB],
        datasets: [{
          label: `Unit Cost (₹ estimated @ ₹${USD_TO_INR_RATE}/$)`,
          data: [inrCostAVal, inrCostBVal],
          backgroundColor: ["#3b82f6", colorBCost],
          borderColor: ["#2563eb", isCheaper ? "#059669" : "#d97706"],
          borderWidth: 1.5,
          borderRadius: 5,
          barThickness: isNarrow ? 22 : 28
        }]
      },
      options: {
        indexAxis: "y", // Standardized horizontal comparison chart
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
                const inrVal = context.parsed.x;
                const usdVal = inrVal / USD_TO_INR_RATE;
                const formattedInr = inrVal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                return ` Unit Cost: ₹${formattedInr} (estimated) [$${usdVal.toFixed(2)} USD]`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: themeColors.grid },
            ticks: {
              color: themeColors.text,
              font: { size: isNarrow ? 9.5 : 11 },
              callback: (val) => `₹${Number(val).toLocaleString("en-IN")}`
            },
            title: {
              display: true,
              text: `Unit Cost in INR (₹ estimated @ ₹${USD_TO_INR_RATE}/USD)`,
              color: themeColors.text,
              font: { size: isNarrow ? 9.5 : 11, weight: "600" }
            },
            beginAtZero: true
          },
          y: {
            grid: { display: false },
            ticks: { color: themeColors.text, font: { weight: "600", size: isNarrow ? 9.5 : 11 } }
          }
        }
      }
    });
  }
}

function renderFleetMaterialDistribution(components) {
  const matCanvas = document.getElementById("materialChart");
  if (!matCanvas) return;
  const ctxMaterial = matCanvas.getContext("2d");
  if (materialChartInstance) materialChartInstance.destroy();

  const themeColors = getChartThemeColors();
  const isNarrow = typeof window !== "undefined" && window.innerWidth < 480;

  // Standardized to horizontal bar style (formerly doughnut chart: "doughnut")
  const MATERIAL_CHART_LEGACY_TYPE = "doughnut";

  // Standardize 5 structural material categories
  const categories = ["Steel", "Aluminum", "Plastic", "Magnesium", "Cast Iron"];
  const counts = {};
  categories.forEach(cat => { counts[cat] = 0; });
  components.forEach(c => {
    if (counts[c.Material] !== undefined) {
      counts[c.Material]++;
    } else {
      counts[c.Material] = (counts[c.Material] || 0) + 1;
    }
  });

  const total = components.length || 50;
  const pctData = categories.map(cat => Number((((counts[cat] || 0) / total) * 100).toFixed(1)));
  const countData = categories.map(cat => counts[cat] || 0);

  const materialColorMap = {
    "Steel": "#64748b",
    "Aluminum": "#0284c7",
    "Plastic": "#10b981",
    "Magnesium": "#a855f7",
    "Cast Iron": "#f59e0b"
  };

  const bgColors = categories.map(cat => materialColorMap[cat] || "#3b82f6");

  materialChartInstance = new Chart(ctxMaterial, {
    type: "bar",
    data: {
      labels: categories,
      datasets: [{
        label: "Fleet Share (%)",
        data: pctData,
        backgroundColor: bgColors,
        borderColor: bgColors,
        borderWidth: 1.5,
        borderRadius: 5,
        barThickness: isNarrow ? 20 : 24
      }]
    },
    options: {
      indexAxis: "y", // Standardized horizontal bar chart
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
              const idx = context.dataIndex;
              const cat = categories[idx];
              const pct = pctData[idx];
              const cnt = countData[idx];
              return ` ${cat}: ${cnt} parts (${pct}% of fleet)`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: themeColors.grid },
          ticks: {
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11 },
            callback: (val) => `${val}%`
          },
          title: {
            display: true,
            text: "Fleet Share Percentage (%)",
            color: themeColors.text,
            font: { size: isNarrow ? 9.5 : 11, weight: "600" }
          },
          beginAtZero: true,
          suggestedMax: 30
        },
        y: {
          grid: { display: false },
          ticks: { color: themeColors.text, font: { weight: "600", size: isNarrow ? 9.5 : 11 } }
        }
      }
    }
  });
}

/* =========================================================
   5B. Interactive Chart Controls (Zoom, Reset, Modal, PNG)
   ========================================================= */

function getChartInstance(chartType) {
  if (chartType === "weight") return weightChartInstance;
  if (chartType === "cost") return costChartInstance;
  if (chartType === "material") return materialChartInstance;
  if (chartType === "expanded") return expandedChartInstance;
  return null;
}

function handleChartAction(chartType, action) {
  if (action === "zoom-in") {
    zoomChart(chartType, 0.8);
  } else if (action === "zoom-out") {
    zoomOutChart(chartType, 1.25);
  } else if (action === "reset") {
    resetChartZoom(chartType);
  } else if (action === "download") {
    handleChartDownload(chartType);
  } else if (action === "expand") {
    openExpandedChartModal(chartType);
  }
}

function zoomChart(chartType, factor = 0.8) {
  const chart = getChartInstance(chartType);
  if (!chart || !chart.scales) return;

  const isLine = chart.config && chart.config.type === "line";
  const scaleKey = isLine ? "y" : (chart.options.indexAxis === "y" ? "x" : "y");
  const scale = chart.scales[scaleKey];
  if (!scale) return;

  const scaleOpts = chart.options.scales[scaleKey];
  if (!scaleOpts) return;

  if (chart._originalMax === undefined || chart._originalMax === null) {
    chart._originalMax = scale.max !== undefined && scale.max !== null ? scale.max : scale.end;
  }

  const currentMax = scaleOpts.max !== undefined && scaleOpts.max !== null
    ? scaleOpts.max
    : scale.end;
  const currentMin = scaleOpts.min !== undefined && scaleOpts.min !== null
    ? scaleOpts.min
    : (scale.min || 0);

  const range = currentMax - currentMin;
  const newMax = currentMin + range * factor;

  if (newMax > currentMin + 0.05) {
    scaleOpts.min = currentMin;
    scaleOpts.max = newMax;
    chart.update();
  }
}

function zoomOutChart(chartType, factor = 1.25) {
  const chart = getChartInstance(chartType);
  if (!chart || !chart.scales) return;

  const isLine = chart.config && chart.config.type === "line";
  const scaleKey = isLine ? "y" : (chart.options.indexAxis === "y" ? "x" : "y");
  const scale = chart.scales[scaleKey];
  if (!scale) return;

  const scaleOpts = chart.options.scales[scaleKey];
  if (!scaleOpts) return;

  if (chart._originalMax === undefined || chart._originalMax === null) {
    chart._originalMax = scale.max !== undefined && scale.max !== null ? scale.max : scale.end;
  }

  const currentMax = scaleOpts.max !== undefined && scaleOpts.max !== null
    ? scaleOpts.max
    : scale.end;
  const currentMin = scaleOpts.min !== undefined && scaleOpts.min !== null
    ? scaleOpts.min
    : (scale.min || 0);

  const range = currentMax - currentMin;
  const originalMax = chart._originalMax || currentMax;
  const newMax = Math.min(currentMin + range * factor, originalMax * 2.5);

  scaleOpts.min = currentMin;
  scaleOpts.max = newMax;
  chart.update();
}

function resetChartZoom(chartType) {
  const chart = getChartInstance(chartType);
  if (!chart || !chart.options || !chart.options.scales) return;

  const isLine = chart.config && chart.config.type === "line";
  const scaleKey = isLine ? "y" : (chart.options.indexAxis === "y" ? "x" : "y");
  const scaleOpts = chart.options.scales[scaleKey];
  if (!scaleOpts) return;

  delete scaleOpts.min;
  delete scaleOpts.max;
  scaleOpts.beginAtZero = true;
  chart.update();
}

function handleChartDownload(chartType) {
  const chart = getChartInstance(chartType);
  if (!chart || !chart.canvas) return;

  let filename = "compbench-chart.png";
  if (chartType === "weight") filename = "compbench-mass-benchmark.png";
  else if (chartType === "cost") filename = "compbench-cost-benchmark.png";
  else if (chartType === "material") filename = "compbench-material-distribution.png";
  else if (chartType === "expanded") filename = "compbench-expanded-benchmark.png";

  const canvas = chart.canvas;
  const exportCanvas = document.createElement("canvas");
  exportCanvas.width = canvas.width;
  exportCanvas.height = canvas.height;
  const ctx = exportCanvas.getContext("2d");

  // Solid background matching active theme
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  ctx.fillStyle = isLight ? "#ffffff" : "#0d1527";
  ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

  // Render chart
  ctx.drawImage(canvas, 0, 0);

  // Engineering watermark
  ctx.fillStyle = isLight ? "#94a3b8" : "#64748b";
  ctx.font = "11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  ctx.textAlign = "right";
  ctx.fillText("CompBench AI • Automotive Engineering Intelligence", exportCanvas.width - 14, exportCanvas.height - 10);

  const link = document.createElement("a");
  link.href = exportCanvas.toDataURL("image/png", 1.0);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function openExpandedChartModal(chartType) {
  const modal = document.getElementById("modal-chart-expanded");
  const titleElem = document.getElementById("modal-chart-title");
  const subElem = document.getElementById("modal-chart-subtitle");
  const canvas = document.getElementById("expandedChartCanvas");

  if (!modal || !canvas) return;

  currentExpandedChartType = chartType;
  const srcChart = getChartInstance(chartType);
  if (!srcChart) return;

  let title = "Expanded Benchmark Chart";
  let subtitle = "High-resolution interactive engineering data view";

  if (chartType === "weight") {
    title = "Component Mass Benchmark (kg)";
    subtitle = "Line mass comparison showing exact kg data points and trajectory.";
  } else if (chartType === "cost") {
    title = "Total Unit Cost Benchmark (INR & USD)";
    subtitle = `Unit manufacturing cost in estimated INR (1 USD ≈ ₹${USD_TO_INR_RATE.toFixed(1)} est.) with secondary USD references.`;
  } else if (chartType === "material") {
    title = "Fleet Material Distribution (%)";
    subtitle = "Horizontal distribution showing 50 total records across 5 material categories.";
  }

  if (titleElem) titleElem.textContent = title;
  if (subElem) subElem.textContent = subtitle;

  modal.classList.add("active");
  modal.setAttribute("aria-hidden", "false");

  if (expandedChartInstance) {
    expandedChartInstance.destroy();
    expandedChartInstance = null;
  }

  const themeColors = getChartThemeColors();
  const clonedData = JSON.parse(JSON.stringify(srcChart.data));
  const clonedOptions = JSON.parse(JSON.stringify(srcChart.options));

  if (clonedData.datasets && clonedData.datasets[0]) {
    if (srcChart.config.type === "line") {
      clonedData.datasets[0].pointRadius = 10;
      clonedData.datasets[0].pointHoverRadius = 12;
      clonedData.datasets[0].borderWidth = 3.5;
    } else {
      clonedData.datasets[0].barThickness = 36;
    }
  }
  if (clonedOptions.scales && clonedOptions.scales.x && clonedOptions.scales.x.ticks) {
    clonedOptions.scales.x.ticks.font = { size: 12 };
  }
  if (clonedOptions.scales && clonedOptions.scales.y && clonedOptions.scales.y.ticks) {
    clonedOptions.scales.y.ticks.font = { size: 12, weight: "600" };
  }

  // Restore callbacks stripped by JSON serialization
  if (srcChart.options.plugins && srcChart.options.plugins.tooltip && srcChart.options.plugins.tooltip.callbacks) {
    clonedOptions.plugins.tooltip.callbacks = srcChart.options.plugins.tooltip.callbacks;
  }
  if (srcChart.options.scales && srcChart.options.scales.x && srcChart.options.scales.x.ticks && srcChart.options.scales.x.ticks.callback) {
    clonedOptions.scales.x.ticks.callback = srcChart.options.scales.x.ticks.callback;
  }

  const ctx = canvas.getContext("2d");
  expandedChartInstance = new Chart(ctx, {
    type: srcChart.config.type,
    data: clonedData,
    options: clonedOptions,
    plugins: srcChart.config.plugins || []
  });
}

function closeExpandedChartModal() {
  const modal = document.getElementById("modal-chart-expanded");
  if (!modal) return;
  modal.classList.remove("active");
  modal.setAttribute("aria-hidden", "true");
  if (expandedChartInstance) {
    expandedChartInstance.destroy();
    expandedChartInstance = null;
  }
  currentExpandedChartType = null;
}

function setupChartInteractions() {
  // Chart action buttons in card headers
  document.querySelectorAll(".chart-tool-btn[data-action]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const chartType = btn.getAttribute("data-chart");
      const action = btn.getAttribute("data-action");
      handleChartAction(chartType, action);
    });
  });

  // Modal Chart controls
  const modalExpanded = document.getElementById("modal-chart-expanded");
  const modalCloseBtn = document.getElementById("modal-chart-close");
  const modalDownloadBtn = document.getElementById("modal-chart-download-btn");

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeExpandedChartModal);
  }
  if (modalDownloadBtn) {
    modalDownloadBtn.addEventListener("click", () => {
      handleChartDownload("expanded");
    });
  }
  if (modalExpanded) {
    modalExpanded.addEventListener("click", (e) => {
      if (e.target === modalExpanded) closeExpandedChartModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalExpanded && modalExpanded.classList.contains("active")) {
      closeExpandedChartModal();
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
    const res = await authFetch("/analyze", {
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

/* =========================================================
   8. Engineering Trade-off Analysis & Decision Summary (Phase 2)
   ========================================================= */

function resetTradeoffAnalysis() {
  const panel = document.getElementById("tradeoff-decision-panel");
  if (panel) {
    const verdictBadge = document.getElementById("decision-verdict-badge");
    const summaryTextElem = document.getElementById("decision-summary-text");
    const scenarioNameElem = document.getElementById("decision-scenario-name");
    if (verdictBadge) {
      verdictBadge.textContent = "Verdict Pending";
      verdictBadge.className = "decision-verdict-badge";
    }
    if (scenarioNameElem) scenarioNameElem.textContent = "Multi-Criteria Engineering Decision Verdict";
    if (summaryTextElem) summaryTextElem.textContent = "Run benchmark comparison to generate deterministic engineering decision summary.";
    panel.className = "tradeoff-decision-panel";
  }
  const section = document.getElementById("tradeoff-analysis-section");
  if (section) section.style.display = "none";
}

function renderTradeoffAnalysis(tradeoff, a, b) {
  const decisionPanel = document.getElementById("tradeoff-decision-panel");
  const section = document.getElementById("tradeoff-analysis-section");

  if (!tradeoff) {
    if (decisionPanel) decisionPanel.style.display = "none";
    if (section) section.style.display = "none";
    return;
  }

  if (decisionPanel) decisionPanel.style.display = "block";
  if (section) section.style.display = "block";

  // 1. Weight Savings Analysis
  const wtDiffElem = document.getElementById("tradeoff-weight-diff");
  const wtPctElem = document.getElementById("tradeoff-weight-pct");
  const wtBadgeElem = document.getElementById("tradeoff-weight-badge");
  const baseWtElem = document.getElementById("tradeoff-base-weight");
  const candWtElem = document.getElementById("tradeoff-cand-weight");
  const wtDescElem = document.getElementById("tradeoff-weight-desc");

  const wtDiff = tradeoff.weight_difference_kg;
  const wtPct = tradeoff.weight_change_pct;

  if (baseWtElem) baseWtElem.textContent = `${Number(tradeoff.baseline_weight_kg).toFixed(2)} kg`;
  if (candWtElem) candWtElem.textContent = `${Number(tradeoff.candidate_weight_kg).toFixed(2)} kg`;

  if (tradeoff.weight_status === "lighter") {
    if (wtDiffElem) wtDiffElem.textContent = `-${Math.abs(wtDiff).toFixed(2)} kg`;
    if (wtPctElem) wtPctElem.textContent = `${Math.abs(wtPct).toFixed(2)}% Weight Reduction`;
    if (wtBadgeElem) {
      wtBadgeElem.className = "tradeoff-badge success";
      wtBadgeElem.textContent = "Weight Saved (Lighter)";
    }
    if (wtDescElem) {
      wtDescElem.textContent = `Candidate reduces component mass by ${Math.abs(wtDiff).toFixed(2)} kg (${Math.abs(wtPct).toFixed(2)}% lighter), supporting platform lightweighting and EV efficiency.`;
    }
  } else if (tradeoff.weight_status === "heavier") {
    if (wtDiffElem) wtDiffElem.textContent = `+${Math.abs(wtDiff).toFixed(2)} kg`;
    if (wtPctElem) wtPctElem.textContent = `+${Math.abs(wtPct).toFixed(2)}% Weight Increase`;
    if (wtBadgeElem) {
      wtBadgeElem.className = "tradeoff-badge warning";
      wtBadgeElem.textContent = "Weight Gained (Heavier)";
    }
    if (wtDescElem) {
      wtDescElem.textContent = `Candidate increases component mass by ${Math.abs(wtDiff).toFixed(2)} kg (+${Math.abs(wtPct).toFixed(2)}% heavier). Not classified as weight savings.`;
    }
  } else {
    if (wtDiffElem) wtDiffElem.textContent = `0.00 kg`;
    if (wtPctElem) wtPctElem.textContent = `0.00% (No Mass Variance)`;
    if (wtBadgeElem) {
      wtBadgeElem.className = "tradeoff-badge neutral";
      wtBadgeElem.textContent = "Equal Mass";
    }
    if (wtDescElem) {
      wtDescElem.textContent = "Both baseline and candidate components have identical mass values.";
    }
  }

  // 2. Cost Trade-off Analysis
  const costDiffElem = document.getElementById("tradeoff-cost-diff");
  const costSecElem = document.getElementById("tradeoff-cost-secondary");
  const costBadgeElem = document.getElementById("tradeoff-cost-badge");
  const baseCostElem = document.getElementById("tradeoff-base-cost");
  const candCostElem = document.getElementById("tradeoff-cand-cost");
  const costDescElem = document.getElementById("tradeoff-cost-desc");

  const costDiffUsd = tradeoff.additional_cost_usd;
  const costDiffInr = tradeoff.additional_cost_inr;
  const costPct = tradeoff.cost_change_pct != null ? tradeoff.cost_change_pct : 0.0;

  const inrFormatted = Math.abs(costDiffInr).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const usdFormatted = Math.abs(costDiffUsd).toFixed(2);

  if (baseCostElem) {
    const baseInr = formatInrPrimary(Number(tradeoff.baseline_cost_usd), false);
    baseCostElem.innerHTML = `${baseInr} <small style="color:var(--text-muted); font-size:0.75rem;">($${Number(tradeoff.baseline_cost_usd).toFixed(2)})</small>`;
  }
  if (candCostElem) {
    const candInr = formatInrPrimary(Number(tradeoff.candidate_cost_usd), false);
    candCostElem.innerHTML = `${candInr} <small style="color:var(--text-muted); font-size:0.75rem;">($${Number(tradeoff.candidate_cost_usd).toFixed(2)})</small>`;
  }

  if (tradeoff.cost_status === "cheaper") {
    if (costDiffElem) costDiffElem.textContent = `-₹${inrFormatted} (est.)`;
    if (costSecElem) costSecElem.textContent = `-$${usdFormatted} USD (-${Math.abs(costPct).toFixed(2)}% Cost Savings)`;
    if (costBadgeElem) {
      costBadgeElem.className = "tradeoff-badge success";
      costBadgeElem.textContent = "Cost Savings";
    }
    if (costDescElem) {
      costDescElem.textContent = `Candidate yields a manufacturing unit cost savings of $${usdFormatted} USD (est. ₹${inrFormatted} @ ₹85/$) per unit.`;
    }
  } else if (tradeoff.cost_status === "more_expensive") {
    if (costDiffElem) costDiffElem.textContent = `+₹${inrFormatted} (est.)`;
    if (costSecElem) costSecElem.textContent = `+$${usdFormatted} USD (+${Math.abs(costPct).toFixed(2)}% Additional Cost)`;
    if (costBadgeElem) {
      costBadgeElem.className = "tradeoff-badge warning";
      costBadgeElem.textContent = "Additional Investment";
    }
    if (costDescElem) {
      costDescElem.textContent = `Candidate carries an additional unit cost premium of $${usdFormatted} USD (est. ₹${inrFormatted} @ ₹85/$) due to material and tooling variance.`;
    }
  } else {
    if (costDiffElem) costDiffElem.textContent = `₹0.00 (est.)`;
    if (costSecElem) costSecElem.textContent = `$0.00 USD (0.00% Parity)`;
    if (costBadgeElem) {
      costBadgeElem.className = "tradeoff-badge neutral";
      costBadgeElem.textContent = "Equal Cost";
    }
    if (costDescElem) {
      costDescElem.textContent = "Both baseline and candidate components have identical unit manufacturing costs.";
    }
  }

  // 3. Additional Cost per kg Saved
  const costPerKgElem = document.getElementById("tradeoff-cost-per-kg");
  const costPerKgInrElem = document.getElementById("tradeoff-cost-per-kg-inr");
  const efficiencyBadge = document.getElementById("tradeoff-efficiency-badge");
  const efficiencyDesc = document.getElementById("tradeoff-efficiency-desc");

  if (tradeoff.cost_per_kg_saved_applicable) {
    const usdVal = tradeoff.cost_per_kg_saved_usd;
    const inrVal = tradeoff.cost_per_kg_saved_inr;
    const inrKgFormatted = inrVal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    if (tradeoff.cost_per_kg_type === "savings") {
      if (costPerKgElem) costPerKgElem.textContent = `-$${usdVal.toFixed(2)} / kg`;
      if (costPerKgInrElem) costPerKgInrElem.textContent = `Cost saving of ₹${inrKgFormatted} / kg saved (est. @ ₹85/$)`;
      if (efficiencyBadge) {
        efficiencyBadge.className = "tradeoff-badge success";
        efficiencyBadge.textContent = "Dual Benefit Efficiency";
      }
      if (efficiencyDesc) {
        efficiencyDesc.textContent = "Candidate reduces both mass and direct unit cost. Displayed metric reflects direct manufacturing cost savings generated per kilogram of reduced weight.";
      }
    } else if (tradeoff.cost_per_kg_type === "investment") {
      if (costPerKgElem) costPerKgElem.textContent = `$${usdVal.toFixed(2)} / kg`;
      if (costPerKgInrElem) costPerKgInrElem.textContent = `₹${inrKgFormatted} / kg saved (est. @ ₹85/$)`;
      if (efficiencyBadge) {
        efficiencyBadge.className = "tradeoff-badge warning";
        efficiencyBadge.textContent = "Lightweighting Metric";
      }
      if (efficiencyDesc) {
        efficiencyDesc.textContent = "Automotive lightweighting metric ($/kg saved). Measures additional manufacturing expenditure required to eliminate each kilogram of vehicle mass.";
      }
    } else {
      if (costPerKgElem) costPerKgElem.textContent = `$0.00 / kg`;
      if (costPerKgInrElem) costPerKgInrElem.textContent = `₹0.00 / kg saved (est. @ ₹85/$)`;
      if (efficiencyBadge) {
        efficiencyBadge.className = "tradeoff-badge neutral";
        efficiencyBadge.textContent = "Cost Parity";
      }
      if (efficiencyDesc) {
        efficiencyDesc.textContent = "Candidate achieves mass reduction at identical cost parity (zero additional capital investment per kilogram).";
      }
    }
  } else {
    if (costPerKgElem) costPerKgElem.textContent = "N/A";
    if (costPerKgInrElem) costPerKgInrElem.textContent = tradeoff.cost_per_kg_reason || "Not applicable";
    if (efficiencyBadge) {
      efficiencyBadge.className = "tradeoff-badge neutral";
      efficiencyBadge.textContent = "Metric Inapplicable";
    }
    if (efficiencyDesc) {
      efficiencyDesc.textContent = tradeoff.cost_per_kg_status === "not_applicable_heavier"
        ? "Not applicable – candidate weight increased relative to baseline. The $/kg saved metric only applies to mass reduction."
        : "Not applicable – no weight reduction detected between selected designs.";
    }
  }

  // 4. Engineering Decision Summary Panel
  const scenarioNameElem = document.getElementById("decision-scenario-name");
  const verdictBadge = document.getElementById("decision-verdict-badge");
  const summaryTextElem = document.getElementById("decision-summary-text");

  const dec = tradeoff.decision || {};

  if (scenarioNameElem) scenarioNameElem.textContent = dec.scenario_name || "Multi-Criteria Decision Analysis";
  if (verdictBadge) {
    verdictBadge.textContent = dec.verdict || "Decision Evaluated";
    verdictBadge.className = `decision-verdict-badge ${dec.recommendation_type || "neutral"}`;
  }
  if (decisionPanel) {
    decisionPanel.className = `tradeoff-decision-panel ${dec.recommendation_type || "neutral"}`;
  }
  if (summaryTextElem) {
    summaryTextElem.textContent = dec.summary_text || "Decision summary generated from Python deterministic rules.";
  }
}

/* =========================================================
   9. Material Intelligence & Manufacturing Analysis (Phase 3)
   ========================================================= */

function resetMaterialIntelligence() {
  const section = document.getElementById("material-intelligence-section");
  if (section) section.style.display = "none";
}

function renderMaterialIntelligence(data, a, b) {
  const section = document.getElementById("material-intelligence-section");
  if (!section) return;

  if (!data) {
    section.style.display = "none";
    return;
  }

  section.style.display = "block";

  const matA = data.material_a || {};
  const matB = data.material_b || {};
  const procA = data.process_a || {};
  const procB = data.process_b || {};
  const matComp = data.material_comparison || {};
  const procComp = data.process_comparison || {};

  // 1. Data Boundary Notice (Component measurement vs general property distinction)
  const boundaryText = document.getElementById("material-boundary-text");
  if (boundaryText) {
    const idA = (a && a.id) || (data.component_measurements && data.component_measurements.baseline_component && data.component_measurements.baseline_component.id) || "Baseline A";
    const idB = (b && b.id) || (data.component_measurements && data.component_measurements.candidate_component && data.component_measurements.candidate_component.id) || "Candidate B";
    const wtA = a ? `${Number(a.weight_kg).toFixed(2)} kg` : "--";
    const wtB = b ? `${Number(b.weight_kg).toFixed(2)} kg` : "--";
    boundaryText.innerHTML = `<strong>Data Boundary:</strong> Component measurements (${escapeHtml(idA)}: ${wtA}, ${escapeHtml(idB)}: ${wtB}) reflect measured teardown ground truth; metallurgical density, modulus, and raw cost factors represent general material science standards from the engineering knowledge base.`;
  }

  // 2. Material Transition Verdict Banner
  const transBadge = document.getElementById("mat-transition-badge");
  const transText = document.getElementById("mat-transition-text");

  if (transBadge) {
    if (matComp.is_same_material) {
      transBadge.textContent = "Identical Material Selection";
      transBadge.className = "mat-transition-badge identical";
    } else {
      transBadge.textContent = "Material Transition";
      transBadge.className = "mat-transition-badge";
    }
  }

  if (transText) {
    transText.textContent = matComp.transition_summary || "Analyzing metallurgical and material properties.";
  }

  // 3. Baseline Material Card (A)
  populateMaterialCard("a", matA);

  // 4. Candidate Material Card (B)
  populateMaterialCard("b", matB);

  // 5. Material Trade-off Matrix Table
  const matrixBody = document.getElementById("material-matrix-body");
  if (matrixBody) {
    const rows = [
      {
        dim: "Density & Mass Impact",
        valA: matA.density_g_cm3 ? `~${matA.density_g_cm3} g/cm³` : "N/A",
        valB: matB.density_g_cm3 ? `~${matB.density_g_cm3} g/cm³` : "N/A",
        delta: matComp.density_comparison || "--"
      },
      {
        dim: "Elastic Modulus (Rigidity)",
        valA: matA.youngs_modulus_gpa ? `~${matA.youngs_modulus_gpa} GPa` : "N/A",
        valB: matB.youngs_modulus_gpa ? `~${matB.youngs_modulus_gpa} GPa` : "N/A",
        delta: matComp.stiffness_comparison || "--"
      },
      {
        dim: "Raw Material Economics",
        valA: matA.relative_cost_factor ? `~${matA.relative_cost_factor}x baseline` : "N/A",
        valB: matB.relative_cost_factor ? `~${matB.relative_cost_factor}x baseline` : "N/A",
        delta: matComp.cost_comparison || "--"
      },
      {
        dim: "Joinability & Assembly",
        valA: (matA.joining_methods || []).slice(0, 2).join(", ") || "Standard Fastening",
        valB: (matB.joining_methods || []).slice(0, 2).join(", ") || "Standard Fastening",
        delta: matComp.joining_comparison || "--"
      },
      {
        dim: "Corrosion & Environmental",
        valA: matA.category === "Ferrous Alloy" ? "Atmospheric Oxidation (Red Rust) / e-coat required" : "Self-passivating oxide layer",
        valB: matB.category === "Ferrous Alloy" ? "Atmospheric Oxidation (Red Rust) / e-coat required" : "Self-passivating oxide (dielectric isolation if paired with steel)",
        delta: matComp.corrosion_comparison || "--"
      }
    ];

    matrixBody.innerHTML = rows.map(r => `
      <tr>
        <td class="matrix-dim-col">${escapeHtml(r.dim)}</td>
        <td><strong>${escapeHtml(r.valA)}</strong></td>
        <td><strong>${escapeHtml(r.valB)}</strong></td>
        <td><span style="font-size: 0.8rem; line-height: 1.4; display: block;">${escapeHtml(r.delta)}</span></td>
      </tr>
    `).join("");
  }

  // 6. Manufacturing Process Shift Banner & Cards
  const procTransText = document.getElementById("proc-transition-text");
  if (procTransText) {
    procTransText.textContent = procComp.transition_summary || "Tooling type and press setup evaluation.";
  }

  populateProcessCard("a", procA);
  populateProcessCard("b", procB);

  // 7. Knowledge Base Source Citations
  const citationsContainer = document.getElementById("material-citations-list");
  if (citationsContainer) {
    const citations = data.source_citations || [];
    if (citations.length > 0) {
      citationsContainer.innerHTML = citations.map(c => `
        <span class="attr-pill" title="${escapeHtml(c.source_title)} - ${escapeHtml(c.section)}">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          ${escapeHtml(c.source_file)} &bull; ${escapeHtml(c.section)}
        </span>
      `).join("");
    } else {
      citationsContainer.innerHTML = `
        <span class="attr-pill">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          steel_vs_aluminum.md &bull; Physical and Mechanical Comparisons
        </span>
        <span class="attr-pill">
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          manufacturing_processes.md &bull; Tooling and Cycle Times
        </span>
      `;
    }
  }
}

function populateMaterialCard(prefix, mat) {
  const nameElem = document.getElementById(`mat-${prefix}-name`);
  const catElem = document.getElementById(`mat-${prefix}-category`);
  const densElem = document.getElementById(`mat-${prefix}-density`);
  const modElem = document.getElementById(`mat-${prefix}-modulus`);
  const costElem = document.getElementById(`mat-${prefix}-cost-factor`);
  const lightElem = document.getElementById(`mat-${prefix}-lightweight-cost`);
  const fatigueElem = document.getElementById(`mat-${prefix}-fatigue`);
  const corrElem = document.getElementById(`mat-${prefix}-corrosion`);
  const formElem = document.getElementById(`mat-${prefix}-forming`);
  const joinElem = document.getElementById(`mat-${prefix}-joining`);
  const advElem = document.getElementById(`mat-${prefix}-advantages`);
  const limElem = document.getElementById(`mat-${prefix}-limitations`);
  const appElem = document.getElementById(`mat-${prefix}-applications`);

  if (nameElem) nameElem.textContent = mat.material_name || "Unspecified Alloy";
  if (catElem) catElem.textContent = mat.category || "Engineering Material";
  if (densElem) densElem.textContent = mat.density_g_cm3 != null ? `${mat.density_g_cm3} g/cm³` : "N/A";
  if (modElem) modElem.textContent = mat.youngs_modulus_gpa != null ? `${mat.youngs_modulus_gpa} GPa` : "N/A";
  if (costElem) costElem.textContent = mat.relative_cost_factor != null ? `${mat.relative_cost_factor}x baseline` : "N/A";
  if (lightElem) lightElem.textContent = mat.typical_lightweighting_cost || "--";
  if (fatigueElem) fatigueElem.textContent = mat.fatigue_profile || "--";
  if (corrElem) corrElem.textContent = mat.corrosion_profile || "--";
  if (formElem) formElem.textContent = mat.forming_and_tooling || "--";

  if (joinElem) {
    const methods = mat.joining_methods || [];
    joinElem.innerHTML = methods.map(m => `<span class="mat-tag-pill">${escapeHtml(m)}</span>`).join("");
  }

  if (advElem) {
    const advs = mat.advantages || [];
    advElem.innerHTML = advs.map(a => `<li>${escapeHtml(a)}</li>`).join("");
  }

  if (limElem) {
    const lims = mat.limitations || [];
    limElem.innerHTML = lims.map(l => `<li>${escapeHtml(l)}</li>`).join("");
  }

  if (appElem) {
    const apps = mat.documented_applications || [];
    appElem.innerHTML = apps.map(app => `<span class="mat-tag-pill">${escapeHtml(app)}</span>`).join("");
  }
}

function populateProcessCard(prefix, proc) {
  const nameElem = document.getElementById(`proc-${prefix}-name`);
  const typeElem = document.getElementById(`proc-${prefix}-type`);
  const cycleElem = document.getElementById(`proc-${prefix}-cycle`);
  const scrapElem = document.getElementById(`proc-${prefix}-scrap`);
  const toolElem = document.getElementById(`proc-${prefix}-tooling`);
  const compatElem = document.getElementById(`proc-${prefix}-compat`);
  const advElem = document.getElementById(`proc-${prefix}-advantages`);
  const limElem = document.getElementById(`proc-${prefix}-limitations`);
  const compElem = document.getElementById(`proc-${prefix}-components`);

  if (nameElem) nameElem.textContent = proc.process_name || "Manufacturing Process";
  if (typeElem) typeElem.textContent = proc.type || "Industrial";
  if (cycleElem) cycleElem.textContent = proc.cycle_time || "--";
  if (scrapElem) scrapElem.textContent = proc.scrap_rate || "--";
  if (toolElem) toolElem.textContent = proc.tooling_economics || "--";
  if (compatElem) compatElem.textContent = proc.material_compatibility || "--";

  if (advElem) {
    const advs = proc.advantages || [];
    advElem.innerHTML = advs.map(a => `<li>${escapeHtml(a)}</li>`).join("");
  }

  if (limElem) {
    const lims = proc.limitations || [];
    limElem.innerHTML = lims.map(l => `<li>${escapeHtml(l)}</li>`).join("");
  }

  if (compElem) {
    const comps = proc.typical_components || [];
    compElem.innerHTML = comps.map(c => `<span class="mat-tag-pill">${escapeHtml(c)}</span>`).join("");
  }
}
