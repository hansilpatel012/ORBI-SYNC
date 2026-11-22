# 🛰️ ORBI SYNC
### AI-Assisted Cooperative Satellite Intelligence and Collision Avoidance Ecosystem

**Making Earth's orbital environment safer through shared intelligence, orbital awareness, and coordinated decision support.**

---

## 🌍 Overview

ORBI SYNC is a satellite intelligence and collision-avoidance ecosystem designed to address the growing congestion of Earth's orbital environment.

As the number of operational satellites, inactive spacecraft, and orbital debris increases, the possibility of dangerous close approaches also grows. ORBI SYNC aims to support better orbital awareness by bringing orbital information, conjunction screening, data reliability, and cooperative decision-making into one integrated platform.

The project explores how multiple satellite operators can exchange relevant information, assess potential collision risks, and compare avoidance strategies while considering mission constraints and fuel efficiency.

Our goal is to move beyond isolated collision warnings towards a more coordinated and sustainable approach to space operations.

## 🎯 Problem We Are Addressing

Earth's orbital environment is becoming increasingly congested.

- Growing numbers of operational satellites.
- Accumulation of inactive spacecraft and orbital debris.
- Potentially dangerous close approaches between orbital objects.
- Fragmented orbital information across different operators and sources.
- Need for better coordination when evaluating collision-avoidance manoeuvres.

ORBI SYNC explores a unified decision-support platform to help address these challenges.

## 💡 Our Approach

ORBI SYNC is designed around five interconnected capabilities:

1. **Orbital Intelligence:** Visualise and monitor orbital objects and their trajectories.
2. **Conjunction Screening:** Identify and analyse potentially dangerous close approaches.
3. **Data Reliability:** Assess the quality and reliability of orbital information.
4. **Cooperative Coordination:** Explore information exchange and coordination between simulated satellite operators.
5. **Manoeuvre Decision Support:** Compare potential avoidance strategies using parameters such as velocity change, predicted separation, and mission constraints.

## 🚀 Current Features

The current prototype includes:

- Interactive 3D Earth visualisation powered by CesiumJS.
- Animated orbital paths and object markers.
- Selectable orbital objects with detailed information.
- Classification of active satellites, debris, and rocket bodies.
- Orbital simulation with play, pause, restart, and speed controls.
- Camera-follow functionality for selected objects.
- Close-approach screening using a simplified orbital model.
- Time of Closest Approach (TCA) and predicted miss-distance calculations.
- Risk classification using configurable demonstration thresholds.
- Mission status, communication status, and data reliability panels.
- Mission event timeline and situation overview.

## 🖥️ Technology Stack

| Technology | Purpose |
|---|---|
| Next.js | Application framework |
| React | User interface |
| JavaScript / TypeScript | Application development |
| CesiumJS | 3D Earth and orbital visualisation |
| Framer Motion | Interface animations |
| Tailwind CSS | Styling |
| Lucide React | Icons |
| JSON | Demonstration orbital and mission data |

## 🏗️ Project Architecture

```text
orbi-sync/
│
├── app/
│   ├── page.jsx
│   ├── layout.tsx
│   └── globals.css
│
├── components/
│   ├── globe/
│   │   └── orbital-globe.jsx
│   │
│   ├── mission-control/
│   │   ├── mission-control.jsx
│   │   ├── key-metrics.jsx
│   │   ├── conjunction-alerts.jsx
│   │   ├── object-roster.jsx
│   │   ├── sim-controls.jsx
│   │   ├── situation-overview.jsx
│   │   ├── pipeline-section.jsx
│   │   └── ...
│   │
│   └── ui/
│
├── data/
│   ├── orbital-objects.json
│   └── mission-status.json
│
├── lib/
│   ├── data-source.js
│   ├── orbits.js
│   ├── load-cesium.js
│   ├── object-types.js
│   ├── satellite-icons.js
│   └── format.js
│
├── public/
├── scripts/
├── package.json
└── README.md
```

### Important Modules

- `components/globe/orbital-globe.jsx` — Handles the CesiumJS globe, orbital visualisation, object selection, and camera interactions.
- `components/mission-control/mission-control.jsx` — Coordinates the mission-control interface and simulation state.
- `lib/orbits.js` — Contains orbital calculations, position and velocity functions, and conjunction-screening logic.
- `lib/data-source.js` — Central data-access layer. Currently loads local JSON data and calculates close approaches.
- `data/orbital-objects.json` — Contains the demonstration orbital scenario.
- `data/mission-status.json` — Contains demonstration mission status, screening settings, communication information, and events.

## ⚙️ Getting Started

Follow these steps to run ORBI SYNC locally.

### Prerequisites

- Node.js compatible with the installed Next.js version.
- pnpm package manager.
- Git.
- VS Code or another code editor.

### 1. Clone the repository

```bash
git clone https://github.com/Riya0y/orbi-sync.git
```

### 2. Navigate to the project

```bash
cd orbi-sync
```

### 3. Install dependencies

```bash
pnpm install
```

### 4. Start the development server

```bash
pnpm dev
```

### 5. Open the application

Visit:

```text
http://localhost:3000
```

The application should now be running locally.

### Other Available Commands

```bash
pnpm build
```

Builds the application for production.

```bash
pnpm start
```

Starts the production server after a successful build.

## 🧮 Orbital Simulation

The current demonstration scenario uses a simplified circular two-body orbital model.

The implementation includes calculations for:

- Semi-major axis.
- Mean motion.
- Orbital period.
- Circular orbital velocity.
- Position and velocity in an Earth-centred inertial coordinate system.
- Orbital trajectories.
- Predicted separation between objects.
- Time of Closest Approach.

Conjunction screening currently evaluates the simulated objects over a configurable time window and classifies close approaches using demonstration thresholds.

## ⚠️ Current Prototype Limitations

Transparency is important to this project.

The current version is a demonstration prototype, not an operational satellite collision-avoidance system.

- The orbital objects and their identifiers are fictional.
- Orbital information is loaded from local JSON files.
- The current orbital model uses circular two-body assumptions.
- Atmospheric drag, Earth's J2 perturbation, and other orbital perturbations are not currently modelled.
- Communication statuses and data reliability values are simulated.
- Conjunction screening uses simplified demonstration thresholds.
- Operational collision probability is not calculated because the required orbital covariance information is not available.
- The current application does not issue commands to real satellites.

All demonstration data should be interpreted accordingly.

## 🔭 Future Development

Planned development directions include:

- Integration with publicly available orbital data sources such as CelesTrak.
- SGP4-based orbital propagation.
- Backend integration for orbital data management.
- Improved orbital data freshness and reliability assessment.
- More advanced conjunction analysis.
- First-person and third-person satellite camera perspectives.
- Relative position and velocity visualisation.
- Cooperative manoeuvre planning and comparison.
- Simulated operator communication and coordination.
- Before-and-after manoeuvre trajectory comparison.
- Orbital sustainability analytics.

## 🌌 Vision

We believe the future of space sustainability requires more than individual collision warnings.

It requires better information sharing, transparent risk assessment, and coordination between the organisations operating in Earth's orbital environment.

**ORBI SYNC aims to explore how cooperative satellite intelligence can contribute to a safer and more sustainable orbital future.**

---

**Project:** ORBI SYNC  
**Domain:** Aerospace Engineering | Space Technology | Orbital Sustainability  
**Repository:** https://github.com/Riya0y/orbi-sync

*Built as a collaborative aerospace technology project.*
