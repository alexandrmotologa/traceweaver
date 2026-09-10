const fs = require('fs');
const path = require('path');
const { Resvg } = require('C:/Users/alexander/.gemini/antigravity-ide/scratch/node_modules/@resvg/resvg-js');

function buildLogoSvg(transparent = false) {
  const container = transparent
    ? ''
    : '<rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-clip-tw">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <!-- Obsidian & Stealth Slate -->
    <linearGradient id="tw-body-dark" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#090d16"/>
    </linearGradient>
    <linearGradient id="tw-body-slate" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>

    <!-- Golden Weaver Plumage & Beak (Radiant Amber Gold) -->
    <linearGradient id="tw-gold-bright" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="35%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
    <linearGradient id="tw-gold-deep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#c2410c"/>
    </linearGradient>

    <!-- Electric Cyan Telemetry & Ingress Stream -->
    <linearGradient id="tw-cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="45%" stop-color="#00f5ff"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <linearGradient id="tw-cyan-deep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#075985"/>
    </linearGradient>

    <!-- Deep Cobalt / Worker Stream -->
    <linearGradient id="tw-cobalt-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#1e3a8a"/>
    </linearGradient>

    <!-- Luxury Volumetric Drop Shadow -->
    <filter id="tw-shadow" x="-15%" y="-15%" width="130%" height="130%">
      <feDropShadow dx="0" dy="22" stdDeviation="26" flood-color="#090d16" flood-opacity="0.15" />
    </filter>
  </defs>

  ${container}

  <g ${transparent ? '' : 'clip-path="url(#squircle-clip-tw)"'}>
    <g transform="translate(512, 512) scale(1.06) translate(-512, -512)" filter="url(#tw-shadow)">

      <!-- Causal Trace Stitch Vector (Background Conduit with telemetry nodes) -->
      <g stroke="#cbd5e1" stroke-width="3.5" stroke-dasharray="8,10" opacity="0.75">
        <line x1="180" y1="720" x2="830" y2="300" />
      </g>
      <!-- Telemetry Nodes on Trace Line -->
      <circle cx="180" cy="720" r="6.5" fill="#0284c7" />
      <circle cx="830" cy="300" r="6.5" fill="#f59e0b" />

      <!-- ================= THE CAUSAL WEAVER (HERALDIC PROFILE) ================= -->

      <!-- 1. Weaver Crown Crest (Sharp Golden Plume) -->
      <polygon points="420,210 530,150 580,230 470,270" fill="url(#tw-gold-bright)" />
      <polygon points="530,150 610,200 580,230" fill="url(#tw-gold-deep)" />

      <!-- 2. Nape & Upper Crest Hood (Deep Obsidian & Slate) -->
      <polygon points="320,330 420,210 470,270 380,380" fill="url(#tw-body-dark)" />
      <polygon points="250,410 320,330 380,380 300,470" fill="url(#tw-body-slate)" />

      <!-- 3. Forehead & Facial Mask (Obsidian Predator Mask) -->
      <polygon points="470,270 580,230 650,320 530,350" fill="url(#tw-body-dark)" />

      <!-- 4. The Weaver Needle Beak (Conical, Razor-Sharp Gold Mandibles) -->
      <!-- Upper Mandible (High-specular gold) -->
      <polygon points="650,320 800,370 660,415 620,370" fill="url(#tw-gold-bright)" />
      <!-- Lower Mandible (Deep amber shadow) -->
      <polygon points="660,415 800,370 735,435 630,425" fill="url(#tw-gold-deep)" />

      <!-- 5. Causal Thread Woven Through Beak (The Stitched Trace Fiber) -->
      <path d="M 800,370 Q 860,395 835,450 T 735,435" fill="none" stroke="#00f5ff" stroke-width="4.5" stroke-linecap="round" />
      <circle cx="848" cy="415" r="5" fill="#00f5ff" />
      <circle cx="848" cy="415" r="2.5" fill="#ffffff" />

      <!-- 6. Acute Causal Lens Eye (Rhomboid with Cyan Core & Specular Glint) -->
      <polygon points="540,335 610,345 575,385 525,370" fill="#090d16" />
      <polygon points="550,340 600,348 573,378 533,367" fill="url(#tw-cyan-glow)" />
      <polygon points="562,347 590,353 572,372 550,363" fill="#090d16" />
      <circle cx="578" cy="357" r="3.5" fill="#ffffff" />

      <!-- 7. Cheek & Throat Keel (Brilliant Pure White Contrast Shield) -->
      <polygon points="380,380 530,350 620,370 630,425 580,515 460,525" fill="#ffffff" />

      <!-- 8. Wing Blade 1 - Critical Path Flow (Radiant Golden Amber - Top Feather) -->
      <polygon points="580,515 755,465 695,615 535,605 460,525" fill="url(#tw-gold-bright)" />
      <polygon points="695,615 755,465 785,515 715,635" fill="url(#tw-gold-deep)" />

      <!-- 9. Wing Blade 2 - Ingress & Stream Channel (Electric Cyan Flow - Mid Feather) -->
      <polygon points="535,605 695,615 625,725 455,675" fill="url(#tw-cyan-glow)" />
      <polygon points="625,725 695,615 715,635 645,745" fill="url(#tw-cyan-deep)" />

      <!-- 10. Wing Blade 3 - Asynchronous Worker Queue (Deep Cobalt - Base Feather) -->
      <polygon points="455,675 625,725 545,815 375,755" fill="url(#tw-cobalt-glow)" />
      <polygon points="545,815 625,725 645,745 565,830" fill="#1e3a8a" />

      <!-- 11. Breast Armor & Lower Body Keel (Obsidian Base) -->
      <polygon points="300,470 380,380 460,525 455,675 375,755 295,655" fill="url(#tw-body-dark)" />
      <polygon points="295,655 375,755 335,835 245,765" fill="url(#tw-body-slate)" />

      <!-- 12. Central Causal Correlation Knot (DuckDB Engine Core Token) -->
      <circle cx="510" cy="490" r="16" fill="#090d16" />
      <circle cx="510" cy="490" r="11" fill="url(#tw-cyan-glow)" />
      <circle cx="510" cy="490" r="5" fill="#ffffff" />

    </g>
  </g>
</svg>`;
}

function renderAll() {
  const imagesDir = path.join(__dirname, '..', 'docs', 'images');
  fs.mkdirSync(imagesDir, { recursive: true });

  const svgStandard = buildLogoSvg(false);
  const svgTransparent = buildLogoSvg(true);

  // Write SVGs
  fs.writeFileSync(path.join(imagesDir, 'logo.svg'), svgStandard);

  const targets = [
    { name: 'logo.png', size: 1024, svg: svgStandard },
    { name: 'logo-1024.png', size: 1024, svg: svgStandard },
    { name: 'logo-256.png', size: 256, svg: svgStandard },
    { name: 'logo-128.png', size: 128, svg: svgStandard },
    { name: 'logo-32.png', size: 32, svg: svgStandard },
    { name: 'logo-transparent.png', size: 1024, svg: svgTransparent },
  ];

  for (const t of targets) {
    const resvg = new Resvg(t.svg, {
      fitTo: { mode: 'width', value: t.size },
      font: { loadSystemFonts: true }
    });
    const png = resvg.render().asPng();
    const dest = path.join(imagesDir, t.name);
    fs.writeFileSync(dest, png);
    console.log(`Generated ${t.name} (${t.size}x${t.size}) - ${png.length} bytes`);
  }
}

renderAll();
