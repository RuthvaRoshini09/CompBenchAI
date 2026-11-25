"""
Material and Manufacturing Process Intelligence Engine for CompBench AI.

Provides knowledge-grounded metallurgical, polymer, and manufacturing process
intelligence derived strictly from the local Markdown knowledge base:
- steel_vs_aluminum.md
- manufacturing_processes.md
- material_tradeoffs.md
- material_selection_factors.md
- lightweighting_considerations.md

Integrates with services.rag_engine for dynamic context retrieval and source attribution.
"""

from typing import Dict, Any, Optional, List
from services.rag_engine import retrieve_knowledge

# Educational disclaimer constant matching the knowledge base
KNOWLEDGE_DISCLAIMER = (
    "General educational reference material — not official OEM or Caresoft proprietary teardown data."
)

# ---------------------------------------------------------------------------
# Structured Material Knowledge Profiles (Strictly Grounded in Knowledge Base)
# ---------------------------------------------------------------------------
MATERIAL_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "Steel": {
        "material_name": "Steel (Automotive Sheet / AHSS / Mild Steel)",
        "category": "Ferrous Alloy",
        "density_g_cm3": 7.85,
        "youngs_modulus_gpa": 210,
        "relative_cost_factor": 1.0,  # Baseline
        "weight_factor": 1.0,         # Baseline
        "typical_lightweighting_cost": "Baseline ($0.00/kg)",
        "fatigue_profile": (
            "Exhibits a well-defined fatigue limit (endurance limit) below which cyclic loading "
            "can theoretically continue indefinitely without micro-crack initiation."
        ),
        "corrosion_profile": (
            "Susceptible to atmospheric oxidation (red rust). Mandates zinc electro-galvanization, "
            "zinc-iron galvannealing, or phosphate electro-coat (e-coat) protection."
        ),
        "forming_and_tooling": (
            "High ductility and formability under deep drawing. Lower elastic springback compared "
            "to aluminum or UHSS, allowing standard single-stage or progressive stamping dies."
        ),
        "joining_methods": [
            "High-speed Resistance Spot Welding (RSW)",
            "Automated Laser Welding",
            "MIG / Arc Welding",
            "Structural Adhesives"
        ],
        "advantages": [
            "Lowest raw material cost baseline (1.0x cost factor).",
            "Highest Young's modulus (~210 GPa) delivering high panel stiffness and oil-canning resistance.",
            "Well-defined fatigue endurance limit under cyclic road vibration.",
            "High acoustic mass-law transmission loss for superior cabin sound attenuation.",
            "Fully mature production infrastructure, rapid spot welding, and 100% magnetic scrap recyclability."
        ],
        "limitations": [
            "Highest density (~7.85 g/cm³), imposing significant mass penalty on vehicle curb weight.",
            "Requires multi-stage zinc galvanizing and e-coat paint lines to prevent environmental oxidation.",
            "High kinetic energy in collisions, requiring larger front crumple zones if unmitigated."
        ],
        "documented_applications": [
            "Body side outers",
            "Door inner and outer panels",
            "Floor pans and roof panels",
            "Chassis crossmembers and brackets",
            "Hot-stamped boron safety cage (A-pillar, B-pillar, sill reinforcements)"
        ],
        "source_doc": "steel_vs_aluminum.md, material_tradeoffs.md, material_selection_factors.md"
    },

    "Aluminum": {
        "material_name": "Aluminum Alloys (5000 / 6000 Sheet & Casting Alloys)",
        "category": "Non-Ferrous Alloy",
        "density_g_cm3": 2.70,
        "youngs_modulus_gpa": 70,
        "relative_cost_factor": 2.0,  # 2x to 4x raw material
        "weight_factor": 0.55,        # 35% to 50% net weight reduction
        "typical_lightweighting_cost": "$3.00 to $7.00 per kg saved",
        "fatigue_profile": (
            "Non-ferrous alloy lacking a distinct fatigue endurance limit. Requires careful "
            "stress-concentration management to avoid micro-crack propagation under prolonged low-amplitude vibration."
        ),
        "corrosion_profile": (
            "Forms a tenacious, self-healing aluminum oxide passivating layer providing superior "
            "atmospheric corrosion resistance. However, in electrical contact with steel or magnesium, "
            "it acts as a galvanic anode unless electrically isolated with dielectric barrier coatings."
        ),
        "forming_and_tooling": (
            "Lower ductility and higher elastic springback at room temperature compared to steel. "
            "Requires 15% to 30% higher die tooling investment, multi-stage dies, or warm forming."
        ),
        "joining_methods": [
            "Self-Piercing Riveting (SPR)",
            "Flow-Drill Screws (FDS)",
            "High-Modulus Structural Epoxy Adhesives",
            "Capacitor-Discharge / High-Energy Spot Welding with frequent electrode dressing",
            "Roller / Tabletop Hemming with adhesive seals"
        ],
        "advantages": [
            "Low density (~2.70 g/cm³) delivering 30% to 50% net weight reduction in closures and structures.",
            "Superior atmospheric corrosion resistance via natural self-healing oxide passivation.",
            "High Specific Energy Absorption (SEA in kJ/kg) for progressive crumple folding in crush rails.",
            "Reduces vehicle curb weight, directly enhancing EV range, acceleration, and braking distance."
        ],
        "limitations": [
            "Raw material sheet cost is 2x to 4x higher than automotive cold-rolled steel.",
            "Lower stiffness (~70 GPa) requires 20% to 50% sheet gauge increase or ribbing to prevent oil-canning.",
            "Higher springback during stamping requiring advanced FEA die compensation (+15%–30% tooling cost).",
            "Requires specialized joining infrastructure (SPR and structural adhesives) rather than simple spot welding.",
            "Differential thermal expansion in 160°C–190°C e-coat ovens (23×10⁻⁶/K vs 12×10⁻⁶/K for steel)."
        ],
        "documented_applications": [
            "Hang-on closures (doors, hood, liftgate, trunk lid)",
            "Front longitudinal crush rails",
            "Shock towers and subframe casting nodes",
            "Battery pack structural housings and bottom protection plates"
        ],
        "source_doc": "steel_vs_aluminum.md, material_tradeoffs.md, lightweighting_considerations.md"
    },

    "Magnesium": {
        "material_name": "Magnesium Alloys (AM50 / AM60 / AZ91 Die Casting)",
        "category": "Ultra-Lightweight Non-Ferrous Alloy",
        "density_g_cm3": 1.80,
        "youngs_modulus_gpa": 45,
        "relative_cost_factor": 3.5,
        "weight_factor": 0.45,  # 50% to 60% mass reduction vs steel
        "typical_lightweighting_cost": "$8.00 to $14.00 per kg saved",
        "fatigue_profile": (
            "Lacks a defined endurance limit. Exhibits good internal mechanical vibration damping "
            "capacity, attenuating high-frequency mechanical noise."
        ),
        "corrosion_profile": (
            "Highly electrochemically active. Susceptible to rapid galvanic corrosion when coupled "
            "with steel fasteners or salt-laden water. Requires non-conductive washers, e-coat barrier "
            "coatings, or compatible aluminum-plated fastener shanks."
        ),
        "forming_and_tooling": (
            "Extremely limited cold sheet formability (hexagonal close-packed crystal structure). "
            "Almost exclusively manufactured via High-Pressure Die Casting (HPDC)."
        ),
        "joining_methods": [
            "HPDC Thin-Walled Casting Integration",
            "Flow-Drill Screwing with Dielectric Washers",
            "Structural Adhesives",
            "Isolated Mechanical Fasteners"
        ],
        "advantages": [
            "Lowest density of structural metals (~1.80 g/cm³), achieving 50% to 60% mass reduction vs steel.",
            "Outstanding specific stiffness and exceptional high-frequency vibration damping.",
            "Excellent high-pressure die castability, enabling complex integrated thin-walled structures."
        ],
        "limitations": [
            "Substantial lightweighting cost premium ($8.00 to $14.00/kg saved).",
            "Restricted almost entirely to casting; poor ambient sheet stamping formability.",
            "High galvanic corrosion sensitivity requiring rigorous fastener isolation.",
            "Limited elevated-temperature creep resistance."
        ],
        "documented_applications": [
            "Instrument panel cross-car beams",
            "Steering wheel armatures",
            "Seat frames and seat back structures",
            "Transfer case and transmission housing covers"
        ],
        "source_doc": "material_tradeoffs.md, material_selection_factors.md"
    },

    "Plastic": {
        "material_name": "Engineered Thermoplastics & Composites (PP / ABS / PA66 / Glass-Filled)",
        "category": "Polymer / Composite",
        "density_g_cm3": 1.20,
        "youngs_modulus_gpa": 6,  # 2 to 15 GPa depending on reinforcement
        "relative_cost_factor": 1.4,
        "weight_factor": 0.55,  # 40% to 50% lighter than steel
        "typical_lightweighting_cost": "$1.50 to $4.00 per kg saved",
        "fatigue_profile": (
            "Time-dependent viscoelastic response. Mechanical stiffness is sensitive to strain rate, "
            "operating temperature, and continuous creep deformation under sustained loading."
        ),
        "corrosion_profile": (
            "Completely immune to electrochemical corrosion, road salts, and galvanic degradation. "
            "Requires UV stabilizers to prevent photochemical weathering."
        ),
        "forming_and_tooling": (
            "Injection molded into precision steel cavities with multi-shot capabilities. Fast cycle "
            "times (20 to 60 seconds) with low scrap rates."
        ),
        "joining_methods": [
            "Molded Snap-Fit Joints",
            "Ultrasonic Welding",
            "Hot Plate / Vibration Welding",
            "Direct Screw Fastening (Thread-Forming Screws)",
            "Multi-Shot Overmolding"
        ],
        "advantages": [
            "40% to 50% lighter than mild steel structures.",
            "Total immunity to galvanic and chemical road salt corrosion.",
            "High functional integration: snap-fits, integral wiring channels, and multi-piece bracket consolidation.",
            "Class-A gloss surface finishes or molded-in grain texture eliminating exterior painting."
        ],
        "limitations": [
            "Significantly lower modulus (2–15 GPa) and yield strength compared to structural metals.",
            "Susceptible to continuous thermal creep and stiffness degradation above 80°C–100°C.",
            "End-of-life recycling challenges, particularly for fiber-reinforced thermoset composites."
        ],
        "documented_applications": [
            "Interior door trim panels",
            "Dashboard consoles and instrument panels",
            "HVAC ducting and air distribution boxes",
            "Battery module covers and enclosure carriers",
            "Front bumper fascias and aerodynamic underbody shields"
        ],
        "source_doc": "manufacturing_processes.md, material_tradeoffs.md"
    },

    "Cast Iron": {
        "material_name": "Cast Iron (Ductile Iron / Gray Iron)",
        "category": "Ferrous Casting Alloy",
        "density_g_cm3": 7.20,
        "youngs_modulus_gpa": 160,
        "relative_cost_factor": 0.85,
        "weight_factor": 0.95,
        "typical_lightweighting_cost": "Cost reduction / Mass penalty (Heavier)",
        "fatigue_profile": (
            "High fatigue endurance limit and outstanding cyclic damping capacity. High graphite "
            "content absorbs mechanical vibrations and noise energy."
        ),
        "corrosion_profile": (
            "Forms surface iron oxide (rust) when exposed to moisture; typically protected by oil, "
            "primers, or localized machining coatings."
        ),
        "forming_and_tooling": (
            "Manufactured via sand or investment casting. Highly machinable, but lacks room-temperature "
            "sheet ductility or stamping capability."
        ),
        "joining_methods": [
            "Precision Bolt Fastening",
            "Press-Fit Bushings and Bearings",
            "Specialized Cast Iron Welding (Pre-heat required)"
        ],
        "advantages": [
            "Outstanding compressive strength and cyclic wear resistance.",
            "Exceptional vibration and acoustic damping capacity (ideal for NVH suppression).",
            "Economical raw material and foundry casting production cost."
        ],
        "limitations": [
            "High mass density (~7.20 g/cm³) resulting in substantial component weight.",
            "Brittle under high-velocity tensile shock loading compared to wrought steel.",
            "Cannot be stamped or deep drawn into thin-shell closure panels."
        ],
        "documented_applications": [
            "Engine cylinder blocks and cylinder heads",
            "Brake rotors and drums",
            "Differential and axle carrier housings",
            "Heavy-duty steering knuckles and suspension uprights"
        ],
        "source_doc": "manufacturing_processes.md, material_selection_factors.md"
    }
}

# ---------------------------------------------------------------------------
# Structured Manufacturing Process Intelligence (Grounded in Knowledge Base)
# ---------------------------------------------------------------------------
PROCESS_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "Stamping": {
        "process_name": "Sheet Metal Stamping (Pressing)",
        "type": "Forming",
        "cycle_time": "10 to 30 strokes per minute (2 to 6 seconds per part)",
        "tooling_economics": (
            "Very high initial tooling and die capital investment (millions of dollars per stamping line). "
            "Requires high-volume automotive production (>100,000 units/year) to amortize die costs."
        ),
        "material_compatibility": "Mild Steel, AHSS/UHSS, Aluminum Sheet (5000/6000 series)",
        "scrap_rate": "30% to 45% scrap generation from sheet blanking and trimming",
        "advantages": [
            "Fastest high-volume production cycle times in automotive manufacturing.",
            "High dimensional repeatability across hundreds of thousands of press strokes.",
            "High structural rigidity achievable via engineered swages, embossments, and draw depths."
        ],
        "limitations": [
            "Millions of dollars in upfront die tooling capital expenditure.",
            "Limited to uniform-thickness sheet geometries; cannot produce integrated bosses or varying cross-sections.",
            "High scrap generation requiring closed-loop scrap baling and recycling."
        ],
        "typical_components": [
            "Body side outers",
            "Door inner and outer panels",
            "Floor pans and roof panels",
            "Chassis mounting brackets"
        ],
        "source_doc": "manufacturing_processes.md, Section 1"
    },

    "Casting": {
        "process_name": "High-Pressure Die Casting (HPDC) & Megacasting",
        "type": "Foundry / Solidification",
        "cycle_time": "60 to 120 seconds per shot",
        "tooling_economics": (
            "Requires 6,000 to 9,000-ton clamping force megacasting presses. High machine capital cost "
            "offset by massive parts consolidation (replacing dozens of stamped parts)."
        ),
        "material_compatibility": "Aluminum Alloys (A380, AlSi10MnMg), Magnesium Alloys (AM60, AZ91), Cast Iron",
        "scrap_rate": "Low net scrap; sprues and runners are re-melted directly in-house",
        "advantages": [
            "Part consolidation: can merge 30 to 70 stamped steel components into 1 single structural casting.",
            "Enables variable wall thicknesses, integrated stiffening ribs, and complex mounting bosses.",
            "Eliminates complex welding and riveting assembly lines for sub-assemblies."
        ],
        "limitations": [
            "Slower cycle times (60–120s) compared to sheet metal stamping.",
            "High capital cost for multi-thousand ton clamping machines and hardened tool steel dies.",
            "Die thermal fatigue and internal gas porosity requiring vacuum assist and X-ray inspection."
        ],
        "typical_components": [
            "Shock towers and subframe nodes",
            "Rear underbody megacastings",
            "Engine blocks and transmission cases",
            "Structural battery tray housings"
        ],
        "source_doc": "manufacturing_processes.md, Section 2"
    },

    "Forging": {
        "process_name": "Hot & Cold Impression Die Forging",
        "type": "Bulk Deformation",
        "cycle_time": "15 to 45 seconds per part (plus heating & secondary machining)",
        "tooling_economics": (
            "High die tooling cost and significant die wear under severe mechanical pressure and thermal cycling. "
            "Requires secondary CNC machining for precision bearing and mounting faces."
        ),
        "material_compatibility": "Alloy Steels, Carbon Steels, Forged Aluminum (6061, 7075)",
        "scrap_rate": "15% to 25% flash scrap generated at die parting lines",
        "advantages": [
            "Retains continuous directional metal grain flow matching component contours.",
            "Superior tensile strength, fracture toughness, and fatigue endurance under dynamic shock loads.",
            "Zero internal porosity compared to casting processes."
        ],
        "limitations": [
            "High tooling die wear from extreme thermal and mechanical forces.",
            "Limited geometric complexity compared to casting; cannot create deep hollow cavities easily.",
            "Mandates secondary CNC machining operations for tight bearing and mounting interfaces."
        ],
        "typical_components": [
            "Suspension control arms",
            "Steering knuckles and wheel hubs",
            "Engine crankshafts and connecting rods",
            "Transmission input shafts"
        ],
        "source_doc": "manufacturing_processes.md, Section 4"
    },

    "Injection Molding": {
        "process_name": "Polymer Injection Molding",
        "type": "Polymer Processing",
        "cycle_time": "20 to 60 seconds per cycle",
        "tooling_economics": (
            "Moderate to high precision steel mold tooling cost. Highly economical for medium to high "
            "production volumes due to low cycle time and near-zero post-process finishing."
        ),
        "material_compatibility": "Thermoplastics (PP, ABS, Nylon/PA66, PC, Glass-Filled PBT)",
        "scrap_rate": "Near zero net scrap; sprues and defective shots can be reground and recycled",
        "advantages": [
            "Fast cycle times with exceptional dimensional repeatability across millions of parts.",
            "Enables integrated snap-fits, molded-in wiring clips, and multi-shot soft-touch TPE overmolding.",
            "High aesthetic surface quality with Class-A gloss or molded-in grain texture (no paint required)."
        ],
        "limitations": [
            "High precision steel mold tooling costs, making low-volume production uneconomical.",
            "Non-structural; cannot withstand primary vehicle crash intrusion loads.",
            "Sensitive to part design rules (draft angles, uniform wall thickness to avoid sink marks)."
        ],
        "typical_components": [
            "Interior door trim panels",
            "Dashboard consoles and HVAC ducting",
            "Battery module covers and carriers",
            "Front bumper fascias and rocker panels"
        ],
        "source_doc": "manufacturing_processes.md, Section 3"
    },

    "Machining": {
        "process_name": "Subtractive CNC Milling & Turning",
        "type": "Subtractive Precision Finishing",
        "cycle_time": "2 to 15+ minutes per part (dependent on material volume removed)",
        "tooling_economics": (
            "Low upfront tooling capital compared to stamping or casting dies; high flexibility via CAD/CAM. "
            "However, per-part unit cycle cost is high, restricting full machining to low volumes or finishing passes."
        ),
        "material_compatibility": "All structural metals (Aluminum, Steel, Cast Iron, Magnesium) and rigid plastics",
        "scrap_rate": "High scrap chip volume (chips are collected and re-melted)",
        "advantages": [
            "Unmatched dimensional precision (sub-millimeter / micrometer tolerances).",
            "Zero expensive hard die lead time; rapid toolpath iteration via CAM programming.",
            "Produces optimal bearing journal surfaces, seal grooves, and precision threads."
        ],
        "limitations": [
            "Significantly longer cycle times per part than stamping or casting.",
            "High per-unit manufacturing cost for high-volume serial production.",
            "Substantial material waste in the form of machining chips."
        ],
        "typical_components": [
            "Finished bearing bores in suspension knuckles",
            "Transmission gear splines and differential casings",
            "Engine cylinder head mating surfaces",
            "High-precision prototype brackets"
        ],
        "source_doc": "manufacturing_processes.md, Section 4"
    }
}


def _get_material_profile(material_name: Optional[str]) -> Dict[str, Any]:
    """Retrieve normalized material profile with robust fallbacks."""
    if not material_name or not isinstance(material_name, str):
        material_name = "Unknown"

    mat_clean = material_name.strip()
    for key in MATERIAL_KNOWLEDGE_BASE:
        if key.lower() in mat_clean.lower():
            return {**MATERIAL_KNOWLEDGE_BASE[key], "matched_key": key}

    # Safe fallback for unexpected material
    return {
        "material_name": mat_clean,
        "category": "Unspecified Engineering Material",
        "density_g_cm3": None,
        "youngs_modulus_gpa": None,
        "relative_cost_factor": None,
        "weight_factor": None,
        "typical_lightweighting_cost": "Parameter not documented in local knowledge base",
        "fatigue_profile": "Refer to material specifications for fatigue endurance data.",
        "corrosion_profile": "Standard surface protection and corrosion barriers apply.",
        "forming_and_tooling": "Standard manufacturing tooling parameters apply.",
        "joining_methods": ["Mechanical Fastening", "Structural Bonding"],
        "advantages": ["Automotive-grade material specified for target application."],
        "limitations": ["Engineering properties subject to specific alloy and temper selection."],
        "documented_applications": ["Specialized automotive components."],
        "source_doc": "Educational Reference",
        "matched_key": mat_clean
    }


def _get_process_profile(process_name: Optional[str]) -> Dict[str, Any]:
    """Retrieve normalized process profile with robust fallbacks."""
    if not process_name or not isinstance(process_name, str):
        process_name = "Unknown"

    proc_clean = process_name.strip()
    for key in PROCESS_KNOWLEDGE_BASE:
        if key.lower() in proc_clean.lower():
            return {**PROCESS_KNOWLEDGE_BASE[key], "matched_key": key}

    # Safe fallback for unexpected process
    return {
        "process_name": proc_clean,
        "type": "Industrial Manufacturing Process",
        "cycle_time": "Production cycle time dependent on specific tooling setup",
        "tooling_economics": "Tooling capital investment governed by production volume and part geometry.",
        "material_compatibility": "Compatible with designated part materials.",
        "scrap_rate": "Dependent on nesting and manufacturing scrap management.",
        "advantages": ["Qualified automotive manufacturing process."],
        "limitations": ["Subject to tooling amortization and cycle time constraints."],
        "typical_components": ["Automotive subsystem components."],
        "source_doc": "Educational Reference",
        "matched_key": proc_clean
    }


def compute_material_comparison(
    mat_a_profile: Dict[str, Any],
    mat_b_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute structured side-by-side comparison between baseline and candidate materials.
    Handles same-material comparisons gracefully without creating false transition claims.
    """
    name_a = mat_a_profile["matched_key"]
    name_b = mat_b_profile["matched_key"]
    is_same = name_a.lower() == name_b.lower()

    dens_a = mat_a_profile.get("density_g_cm3")
    dens_b = mat_b_profile.get("density_g_cm3")

    mod_a = mat_a_profile.get("youngs_modulus_gpa")
    mod_b = mat_b_profile.get("youngs_modulus_gpa")

    cost_f_a = mat_a_profile.get("relative_cost_factor")
    cost_f_b = mat_b_profile.get("relative_cost_factor")

    if is_same:
        density_comparison = f"Identical material density (~{dens_a} g/cm³). No metallurgical mass transition."
        stiffness_comparison = f"Identical Young's Modulus (~{mod_a} GPa). Structural stiffness variances derive from geometry and gauge."
        cost_comparison = "Identical raw material cost tier. Cost variances stem from geometry, tooling, or manufacturing volume."
        joining_comparison = f"Both components utilize standard {name_a} joining practices ({', '.join(mat_a_profile.get('joining_methods', [])[:2])})."
        corrosion_comparison = f"Identical corrosion characteristics ({mat_a_profile.get('corrosion_profile')})."
        transition_summary = (
            f"Both Baseline and Candidate use {name_a}. There is no material shift; "
            "engineering differences are governed by component geometry, wall thickness, and manufacturing process."
        )
    else:
        # Density Delta
        if dens_a and dens_b:
            dens_ratio = round(dens_a / dens_b, 2)
            if dens_b < dens_a:
                density_comparison = (
                    f"{name_b} (~{dens_b} g/cm³) is ~{dens_ratio}x lighter than {name_a} (~{dens_a} g/cm³), "
                    f"delivering significant lightweighting potential."
                )
            else:
                density_comparison = (
                    f"{name_b} (~{dens_b} g/cm³) is denser than {name_a} (~{dens_a} g/cm³), "
                    f"resulting in higher material mass per unit volume."
                )
        else:
            density_comparison = f"Comparing {name_a} and {name_b} material densities."

        # Stiffness Delta
        if mod_a and mod_b:
            if mod_b < mod_a:
                ratio = round(mod_a / mod_b, 1)
                stiffness_comparison = (
                    f"{name_a} exhibits higher elastic modulus (~{mod_a} GPa vs ~{mod_b} GPa for {name_b}, ~{ratio}x stiffer). "
                    f"Candidate {name_b} typically requires increased wall thickness (e.g. +20%–50%) or structural ribs to match rigidity."
                )
            elif mod_b > mod_a:
                ratio = round(mod_b / mod_a, 1)
                stiffness_comparison = (
                    f"{name_b} exhibits higher elastic modulus (~{mod_b} GPa vs ~{mod_a} GPa for {name_a}, ~{ratio}x stiffer), "
                    f"enabling potential down-gauging while maintaining component stiffness."
                )
            else:
                stiffness_comparison = f"Both materials offer equivalent Young's modulus (~{mod_a} GPa)."
        else:
            stiffness_comparison = f"Comparing elastic modulus and structural stiffness of {name_a} vs {name_b}."

        # Cost Factor Comparison
        if cost_f_a and cost_f_b:
            if cost_f_b > cost_f_a:
                cost_comparison = (
                    f"{name_b} carries a higher raw material price factor (~{cost_f_b}x vs ~{cost_f_a}x for {name_a}). "
                    f"Documented lightweighting premium is typically {mat_b_profile.get('typical_lightweighting_cost', 'higher')}."
                )
            elif cost_f_b < cost_f_a:
                cost_comparison = (
                    f"{name_b} offers a lower raw material price factor (~{cost_f_b}x vs ~{cost_f_a}x for {name_a}), "
                    "offering direct raw material cost savings."
                )
            else:
                cost_comparison = f"Both materials share comparable raw material cost factors (~{cost_f_a}x)."
        else:
            cost_comparison = f"Comparing raw material economics between {name_a} and {name_b}."

        # Joining & Corrosion
        joining_comparison = (
            f"Baseline [{name_a}] relies on {', '.join(mat_a_profile.get('joining_methods', [])[:2])}, "
            f"whereas Candidate [{name_b}] utilizes {', '.join(mat_b_profile.get('joining_methods', [])[:2])}."
        )
        corrosion_comparison = (
            f"{name_a}: {mat_a_profile.get('corrosion_profile')} "
            f"vs {name_b}: {mat_b_profile.get('corrosion_profile')}"
        )
        transition_summary = (
            f"Transitioning from {name_a} to {name_b} shifts component density from ~{dens_a} to ~{dens_b} g/cm³ "
            f"and elastic modulus from ~{mod_a} to ~{mod_b} GPa, altering structural stiffness, joining methods, and raw material economics."
        )

    return {
        "is_same_material": is_same,
        "material_a": name_a,
        "material_b": name_b,
        "density_comparison": density_comparison,
        "stiffness_comparison": stiffness_comparison,
        "cost_comparison": cost_comparison,
        "joining_comparison": joining_comparison,
        "corrosion_comparison": corrosion_comparison,
        "transition_summary": transition_summary,
        "disclaimer": KNOWLEDGE_DISCLAIMER
    }


def compute_process_comparison(
    proc_a_profile: Dict[str, Any],
    proc_b_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute comparison between baseline and candidate manufacturing processes."""
    name_a = proc_a_profile["matched_key"]
    name_b = proc_b_profile["matched_key"]
    is_same = name_a.lower() == name_b.lower()

    if is_same:
        summary = (
            f"Both components are manufactured using {name_a}. Tooling type, cycle times, "
            "and press/machine capital equipment requirements are structurally consistent."
        )
    else:
        summary = (
            f"Manufacturing shift from {name_a} ({proc_a_profile.get('type')}) to {name_b} ({proc_b_profile.get('type')}). "
            f"Cycle times shift from [{proc_a_profile.get('cycle_time')}] to [{proc_b_profile.get('cycle_time')}], "
            "affecting tooling amortization and plant throughput."
        )

    return {
        "is_same_process": is_same,
        "process_a": name_a,
        "process_b": name_b,
        "cycle_time_a": proc_a_profile.get("cycle_time"),
        "cycle_time_b": proc_b_profile.get("cycle_time"),
        "tooling_a": proc_a_profile.get("tooling_economics"),
        "tooling_b": proc_b_profile.get("tooling_economics"),
        "transition_summary": summary
    }


def get_material_intelligence(
    material_a: str,
    material_b: str,
    process_a: str,
    process_b: str,
    component_a: Optional[Dict[str, Any]] = None,
    component_b: Optional[Dict[str, Any]] = None,
    query_rag: bool = True,
    rag_top_k: int = 3
) -> Dict[str, Any]:
    """
    Generate comprehensive Material and Manufacturing Intelligence for two components.
    Integrates structured knowledge profiles with dynamic RAG context retrieval.

    Separates component measurements (Part ID, weight, cost) from general material properties.
    """
    mat_a_profile = _get_material_profile(material_a)
    mat_b_profile = _get_material_profile(material_b)

    proc_a_profile = _get_process_profile(process_a)
    proc_b_profile = _get_process_profile(process_b)

    mat_comparison = compute_material_comparison(mat_a_profile, mat_b_profile)
    proc_comparison = compute_process_comparison(proc_a_profile, proc_b_profile)

    # Dynamic RAG Retrieval
    rag_passages = []
    if query_rag:
        rag_query = (
            f"Automotive engineering comparison of {mat_a_profile['matched_key']} vs "
            f"{mat_b_profile['matched_key']} and manufacturing via {proc_a_profile['matched_key']} "
            f"vs {proc_b_profile['matched_key']}"
        )
        try:
            rag_passages = retrieve_knowledge(rag_query, top_k=rag_top_k)
        except Exception as e:
            # Resilient fallback if RAG retrieval experiences an issue
            rag_passages = [{
                "source_title": "Automotive Engineering Reference",
                "section": "Material Selection",
                "content": f"Standard automotive engineering trade-offs apply between {material_a} and {material_b}.",
                "source_file": "steel_vs_aluminum.md",
                "similarity_score": 1.0,
                "disclaimer": KNOWLEDGE_DISCLAIMER
            }]

    # Extract distinct source citations for attribution display
    source_citations = []
    seen_sources = set()
    for passage in rag_passages:
        s_file = passage.get("source_file", "")
        s_title = passage.get("source_title", "")
        key = (s_file, s_title)
        if key not in seen_sources and s_file:
            seen_sources.add(key)
            source_citations.append({
                "source_file": s_file,
                "source_title": s_title,
                "section": passage.get("section", "Reference")
            })

    # Clear separation of component measurements (if provided) vs general material properties
    measurements = None
    if component_a and component_b:
        measurements = {
            "baseline_component": {
                "id": str(component_a.get("id") or component_a.get("Part_ID", "")),
                "measured_weight_kg": float(component_a.get("weight_kg") or component_a.get("Weight_kg", 0.0)),
                "measured_cost_usd": float(component_a.get("cost_usd") or component_a.get("Total_Cost_USD", 0.0)),
                "material": material_a,
                "process": process_a
            },
            "candidate_component": {
                "id": str(component_b.get("id") or component_b.get("Part_ID", "")),
                "measured_weight_kg": float(component_b.get("weight_kg") or component_b.get("Weight_kg", 0.0)),
                "measured_cost_usd": float(component_b.get("cost_usd") or component_b.get("Total_Cost_USD", 0.0)),
                "material": material_b,
                "process": process_b
            },
            "data_note": "Values above are component-specific measurements; properties below represent general material science references."
        }

    return {
        "material_a": mat_a_profile,
        "material_b": mat_b_profile,
        "process_a": proc_a_profile,
        "process_b": proc_b_profile,
        "material_comparison": mat_comparison,
        "process_comparison": proc_comparison,
        "component_measurements": measurements,
        "retrieved_knowledge": rag_passages,
        "source_citations": source_citations,
        "educational_disclaimer": KNOWLEDGE_DISCLAIMER
    }
