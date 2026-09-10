const fs = require('fs');
const path = require('path');
const { Resvg } = require('C:/Users/alexander/.gemini/antigravity-ide/scratch/node_modules/@resvg/resvg-js');

function buildLogoSvg(transparent = false) {
  const container = transparent
    ? ''
    : '<rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-clip">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <!-- Gradients -->
    <linearGradient id="cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>

    <linearGradient id="amber-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#ea580c"/>
    </linearGradient>

    <linearGradient id="indigo-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#818cf8"/>
      <stop offset="100%" stop-color="#4f46e5"/>
    </linearGradient>

    <linearGradient id="slate-dark" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0b0f19"/>
    </linearGradient>

    <linearGradient id="facet-light" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>

    <linearGradient id="facet-highlight" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#334155"/>
    </linearGradient>

    <filter id="subtle-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#000000" flood-opacity="0.14" />
    </filter>
  </defs>

  ${container}

  <g ${transparent ? '' : 'clip-path="url(#squircle-clip)"'}>
    <g transform="translate(512, 512)" filter="url(#subtle-shadow)">

      <!-- 1. Hexagonal Architectural Gateway Frame (40px) -->
      <polygon points="
        0,-390
        338,-195
        338,195
        0,390
        -338,195
        -338,-195
      " fill="none" stroke="#0f172a" stroke-width="40" stroke-linejoin="round" />

      <!-- Inner Dashed Telemetry Gateway -->
      <polygon points="
        0,-355
        307,-177
        307,177
        0,355
        -307,177
        -307,-177
      " fill="none" stroke="#38bdf8" stroke-width="4" opacity="0.45" stroke-dasharray="16, 12" />

      <!-- 2. The Weaver Mascot (Geometric Avian Weaver / Architect of Causal Traces) -->
      
      <!-- Outer Body Silhouette -->
      <path d="
        M 0,-330
        L 45,-260
        L 85,-220
        L 180,-140
        L 275,-40
        L 290,60
        L 225,120
        L 250,220
        L 180,260
        L 110,310
        L 0,355
        L -110,310
        L -180,260
        L -250,220
        L -225,120
        L -290,60
        L -275,-40
        L -180,-140
        L -85,-220
        L -45,-260
        Z
      " fill="url(#slate-dark)" stroke="#0f172a" stroke-width="6" stroke-linejoin="round" />

      <!-- Wing Timeline Tiers - Left Wing (Ingress Spans) -->
      <polygon points="-85,-220 -180,-140 -150,-80 -70,-130" fill="url(#facet-light)" stroke="#0f172a" stroke-width="3" />
      <polygon points="-180,-140 -275,-40 -210,10 -150,-80" fill="#1e293b" stroke="#0f172a" stroke-width="3" />
      <polygon points="-275,-40 -290,60 -225,120 -210,10" fill="#0f172a" stroke="#0f172a" stroke-width="3" />
      <polygon points="-210,10 -225,120 -160,150 -140,40" fill="url(#facet-light)" stroke="#0f172a" stroke-width="3" />

      <!-- Left Wing Ingress Thread Conduit (Cyan) -->
      <polygon points="-265,-20 -275,40 -220,80 -210,20" fill="url(#cyan-glow)" opacity="0.9" />

      <!-- Wing Timeline Tiers - Right Wing (Egress Spans) -->
      <polygon points="85,-220 180,-140 150,-80 70,-130" fill="url(#facet-highlight)" stroke="#0f172a" stroke-width="3" />
      <polygon points="180,-140 275,-40 210,10 150,-80" fill="url(#facet-light)" stroke="#0f172a" stroke-width="3" />
      <polygon points="275,-40 290,60 225,120 210,10" fill="#1e293b" stroke="#0f172a" stroke-width="3" />
      <polygon points="210,10 225,120 160,150 140,40" fill="#0f172a" stroke="#0f172a" stroke-width="3" />

      <!-- Right Wing Worker Thread Conduit (Indigo/Purple) -->
      <polygon points="265,-20 275,40 220,80 210,20" fill="url(#indigo-glow)" opacity="0.9" />

      <!-- Head Crest & Forehead -->
      <polygon points="0,-330 45,-260 0,-210 -45,-260" fill="url(#facet-highlight)" stroke="#0f172a" stroke-width="3" />
      <polygon points="0,-330 0,-210 -45,-260" fill="url(#facet-light)" />
      <polygon points="0,-210 50,-160 0,-110 -50,-160" fill="url(#facet-highlight)" stroke="#0f172a" stroke-width="3" />

      <!-- Cheeks & Temples -->
      <polygon points="-45,-260 -85,-220 -70,-130 -50,-160" fill="#0f172a" stroke="#0f172a" stroke-width="3" />
      <polygon points="45,-260 85,-220 70,-130 50,-160" fill="url(#facet-light)" stroke="#0f172a" stroke-width="3" />

      <!-- Eyes (Acute Causal Observability Lenses) -->
      <!-- Left Eye -->
      <polygon points="-65,-185 -30,-175 -40,-160 -75,-170" fill="url(#cyan-glow)" stroke="#38bdf8" stroke-width="2" />
      <circle cx="-50" cy="-172" r="3.5" fill="#ffffff" />

      <!-- Right Eye -->
      <polygon points="65,-185 30,-175 40,-160 75,-170" fill="url(#cyan-glow)" stroke="#38bdf8" stroke-width="2" />
      <circle cx="50" cy="-172" r="3.5" fill="#ffffff" />

      <!-- Precision Sculpted Beak (The Thread Weaver / Needle) -->
      <polygon points="0,-110 -25,-125 0,-40" fill="#d97706" stroke="#0f172a" stroke-width="2" />
      <polygon points="0,-110 25,-125 0,-40" fill="url(#amber-glow)" stroke="#0f172a" stroke-width="2" />
      <polygon points="0,-40 -12,-65 0,-95 12,-65" fill="#fef08a" />

      <!-- 3. Causal Loom Chest Armor (Negative Space & Thread Bridges) -->
      <!-- Left Pectoral -->
      <polygon points="0,-40 -50,-10 -120,40 -140,120 -60,130 0,60" fill="url(#facet-light)" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />
      
      <!-- Right Pectoral -->
      <polygon points="0,-40 50,-10 120,40 140,120 60,130 0,60" fill="url(#facet-highlight)" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />

      <!-- Center Heraldic Sternum Diamond (The Correlation Knot) -->
      <polygon points="0,60 -60,130 0,220 60,130" fill="#1e293b" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />
      <polygon points="0,60 0,220 60,130" fill="url(#facet-light)" />

      <!-- Woven Thread Interlock (Asynchronous Causal Stitch) -->
      <!-- Ingress Thread (Cyan) entering left of knot -->
      <path d="M -80,100 L -30,130 L 0,110" fill="none" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" />
      
      <!-- Queue Dwell Time Center Indicator (Glowing Amber Diamond) -->
      <polygon points="0,115 -18,140 0,165 18,140" fill="url(#amber-glow)" stroke="#ea580c" stroke-width="2" />

      <!-- Outbox / Worker Egress Thread (Indigo) leaving right of knot -->
      <path d="M 0,170 L 30,150 L 80,180" fill="none" stroke="#818cf8" stroke-width="6" stroke-linecap="round" />

      <!-- Lower Flanks & Tail Plumes (Waterfall Cascade) -->
      <polygon points="-60,130 -140,120 -160,150 -180,260 -100,280 0,220" fill="#0b0f19" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />
      <polygon points="60,130 140,120 160,150 180,260 100,280 0,220" fill="#1e293b" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />

      <!-- Waterfall Tail Center Plume -->
      <polygon points="0,220 -50,260 0,355 50,260" fill="#0f172a" stroke="#0f172a" stroke-width="4" stroke-linejoin="round" />
      <polygon points="0,220 0,355 50,260" fill="url(#facet-light)" />

      <!-- Tail Telemetry Anchors -->
      <circle cx="-35" cy="275" r="4" fill="#38bdf8" />
      <circle cx="0" cy="305" r="4" fill="#fbbf24" />
      <circle cx="35" cy="275" r="4" fill="#818cf8" />

    </g>
  </g>
</svg>`;
}

function render() {
  const svg = buildLogoSvg(false);
  const svgTransparent = buildLogoSvg(true);
  const outDir = path.join(__dirname, '..', 'docs', 'images');
  fs.mkdirSync(outDir, { recursive: true });

  const svgPath = path.join(outDir, 'logo.svg');
  const png1024 = path.join(outDir, 'logo-1024.png');
  const pngPath = path.join(outDir, 'logo.png');
  const png256 = path.join(outDir, 'logo-256.png');
  const png128 = path.join(outDir, 'logo-128.png');
  const png32 = path.join(outDir, 'logo-32.png');
  const pngTransparent = path.join(outDir, 'logo-transparent.png');

  fs.writeFileSync(svgPath, svg, 'utf-8');

  // Render 1024x1024
  const resvg1024 = new Resvg(svg, { fitTo: { mode: 'width', value: 1024 } });
  const buf1024 = resvg1024.render().asPng();
  fs.writeFileSync(pngPath, buf1024);
  fs.writeFileSync(png1024, buf1024);

  // Render sizes
  fs.writeFileSync(png256, new Resvg(svg, { fitTo: { mode: 'width', value: 256 } }).render().asPng());
  fs.writeFileSync(png128, new Resvg(svg, { fitTo: { mode: 'width', value: 128 } }).render().asPng());
  fs.writeFileSync(png32, new Resvg(svg, { fitTo: { mode: 'width', value: 32 } }).render().asPng());

  // Transparent
  fs.writeFileSync(pngTransparent, new Resvg(svgTransparent, { fitTo: { mode: 'width', value: 1024 } }).render().asPng());

  console.log('✓ Rendered all TraceWeaver logo assets (1024, 256, 128, 32, transparent)');
}

render();
