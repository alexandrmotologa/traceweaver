const fs = require('fs');
const path = require('path');
const { Resvg } = require('C:/Users/alexander/.gemini/antigravity-ide/scratch/node_modules/@resvg/resvg-js');

function buildLogoSvg(transparent = false) {
  const container = transparent
    ? ''
    : '<rect x="24" y="24" width="976" height="976" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="6" />';

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <clipPath id="squircle-badge-tw">
      <rect x="24" y="24" width="976" height="976" rx="220" />
    </clipPath>

    <!-- Linear Gradients for Seamless Planar Facets -->
    <!-- Golden Weaver Crown & Beak -->
    <linearGradient id="tw-gold-top" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="35%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
    <linearGradient id="tw-gold-deep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#c2410c"/>
    </linearGradient>
    <linearGradient id="tw-gold-shadow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ea580c"/>
      <stop offset="100%" stop-color="#9a3412"/>
    </linearGradient>

    <!-- Obsidian Predator Mask & Nape Armor -->
    <linearGradient id="tw-obsidian-dark" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#090d16"/>
    </linearGradient>
    <linearGradient id="tw-obsidian-deep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
    <linearGradient id="tw-slate-mid" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>

    <!-- Pure Ice White Contrast Plates -->
    <linearGradient id="tw-ice-white" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#f1f5f9"/>
    </linearGradient>

    <!-- Electric Cyan Telemetry Streams -->
    <linearGradient id="tw-cyan-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="45%" stop-color="#00f5ff"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <linearGradient id="tw-cyan-deep" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#0c4a6e"/>
    </linearGradient>

    <!-- Deep Royal Cobalt (Worker & Database Tier) -->
    <linearGradient id="tw-cobalt-glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#1e3a8a"/>
    </linearGradient>

    <!-- Soft Drop Shadow -->
    <filter id="tw-badge-shadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="20" stdDeviation="26" flood-color="#090d16" flood-opacity="0.14" />
    </filter>
  </defs>

  ${container}

  <g ${transparent ? '' : 'clip-path="url(#squircle-badge-tw)"'}>
    <g transform="translate(512, 512) scale(0.95) translate(-512, -512)" filter="url(#tw-badge-shadow)">

      <!-- Telemetry Flow Axis in Background (Ingress to Egress) -->
      <g stroke="#cbd5e1" stroke-width="3" stroke-dasharray="8,10" opacity="0.65">
        <line x1="210" y1="720" x2="810" y2="290" />
      </g>
      <circle cx="210" cy="720" r="6" fill="#0284c7" />
      <circle cx="810" cy="290" r="6" fill="#fbbf24" />

      <!-- ================= THE CAUSAL WEAVER (SEAMLESS PLANAR MESH) ================= -->

      <!-- 1. Crown Crest Top (Radiant Weaver Gold) -->
      <polygon points="430,220 540,260 480,340" fill="url(#tw-gold-top)" />

      <!-- 2. Forehead Diamond (Golden Amber) -->
      <polygon points="540,260 670,330 580,390 480,340" fill="url(#tw-gold-deep)" />

      <!-- 3. Conical Needle Beak Upper Mandible (Sharp Weaver Beak) -->
      <polygon points="670,330 830,410 710,450 580,390" fill="url(#tw-gold-top)" />

      <!-- 4. Needle Beak Lower Mandible (Deep Amber Shadow) -->
      <polygon points="710,450 830,410 760,470 690,460" fill="url(#tw-gold-shadow)" />

      <!-- 5. Ocular Mask Brow (Obsidian Dark) -->
      <polygon points="580,390 710,450 670,490 560,450" fill="url(#tw-obsidian-dark)" />

      <!-- 6. Acute Causal Lens Eye (Sub-millisecond Observation Node) -->
      <polygon points="610,425 660,435 635,465 595,450" fill="#ffffff" />
      <polygon points="615,428 655,437 632,460 602,448" fill="#00f5ff" />
      <polygon points="625,436 645,441 632,453 618,446" fill="#090d16" />
      <circle cx="638" cy="442" r="2.5" fill="#ffffff" />

      <!-- 7. Cheek Plate (Pure Ice White Contrast Shield) -->
      <polygon points="480,340 580,390 560,450 510,500 440,430" fill="url(#tw-ice-white)" />

      <!-- 8. Malar Mask Flank (Obsidian Slate) -->
      <polygon points="560,450 670,490 640,540 550,530 510,500" fill="url(#tw-slate-mid)" />

      <!-- 9. Throat Front Wedge (Ingress Stream - Electric Cyan) -->
      <polygon points="670,490 690,460 760,470 715,530 640,540" fill="url(#tw-cyan-glow)" />

      <!-- 10. Mid-Throat Connector (Electric Cyan Telemetry Stream) -->
      <polygon points="640,540 715,530 670,620 580,600 550,530" fill="url(#tw-cyan-glow)" />

      <!-- 11. Lower Throat & Sternal Keel (Deep Cyan / Cobalt) -->
      <polygon points="580,600 670,620 620,710 530,670" fill="url(#tw-cyan-deep)" />

      <!-- 12. Rear Crest Flank Upper (Obsidian Dark) -->
      <polygon points="310,310 430,220 480,340 370,390" fill="url(#tw-obsidian-dark)" />

      <!-- 13. Rear Crest Flank Lower (Deep Midnight) -->
      <polygon points="230,410 310,310 370,390 280,480" fill="url(#tw-obsidian-deep)" />

      <!-- 14. Nape Mid Facet (Slate Mid) -->
      <polygon points="370,390 480,340 440,430 350,470" fill="url(#tw-slate-mid)" />

      <!-- 15. Chest Center Hub (Pure Ice White Core Keel) -->
      <polygon points="440,430 510,500 550,530 480,610 400,530" fill="url(#tw-ice-white)" />

      <!-- 16. Breast Keel Plate (Electric Cyan Stream) -->
      <polygon points="550,530 580,600 530,670 480,610" fill="url(#tw-cyan-glow)" />

      <!-- 17. Wing Shoulder Plate (Radiant Amber Gold - Top Span) -->
      <polygon points="350,470 440,430 400,530 320,570" fill="url(#tw-gold-top)" />

      <!-- 18. Mid-Wing Feather Fold (Deep Amber Shadow) -->
      <polygon points="280,480 350,470 320,570 240,590" fill="url(#tw-gold-deep)" />

      <!-- 19. Breast Plate Lower (Deep Royal Cobalt) -->
      <polygon points="400,530 480,610 440,690 360,640" fill="url(#tw-cobalt-glow)" />

      <!-- 20. Belly Ventral Armor (Electric Cyan Ingress Flow) -->
      <polygon points="480,610 530,670 490,750 440,690" fill="url(#tw-cyan-glow)" />

      <!-- 21. Keel Base Point (Deep Midnight Navy) -->
      <polygon points="530,670 620,710 550,795 490,750" fill="url(#tw-obsidian-deep)" />

      <!-- 22. Wing Blade Primary 1 (Cobalt Worker Tier) -->
      <polygon points="320,570 400,530 360,640 280,680" fill="url(#tw-cobalt-glow)" />

      <!-- 23. Wing Blade Primary 2 (Obsidian Dark) -->
      <polygon points="240,590 320,570 280,680 190,690" fill="url(#tw-obsidian-dark)" />

      <!-- 24. Wing Tip Trailing Blade (Electric Cyan Accent) -->
      <polygon points="360,640 440,690 390,770 310,730" fill="url(#tw-cyan-glow)" />

      <!-- 25. Trailing Apex Quill (Radiant Amber Gold) -->
      <polygon points="440,690 490,750 450,810 390,770" fill="url(#tw-gold-top)" />

      <!-- 26. Tail Covert (Deep Midnight Navy) -->
      <polygon points="310,730 390,770 340,820 260,780" fill="url(#tw-obsidian-deep)" />

      <!-- 27. Tail Blade Apex (Obsidian Dark) -->
      <polygon points="390,770 450,810 400,850 340,820" fill="url(#tw-obsidian-dark)" />

      <!-- Central TraceWeaver Causal Node Jewel (DuckDB Sub-ms Engine) -->
      <circle cx="480" cy="520" r="14" fill="#090d16" />
      <circle cx="480" cy="520" r="9" fill="#00f5ff" />
      <circle cx="480" cy="520" r="4" fill="#ffffff" />

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
