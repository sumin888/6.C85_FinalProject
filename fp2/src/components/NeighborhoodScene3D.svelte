<script>
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import * as d3 from 'd3';

  export let neighborhood = null;
  export let geoData      = null;
  export let properties   = [];
  export let maxRent      = 2000;
  export let scrollStep   = 0;

  let canvas, container;
  let renderer, scene, camera, controls, raycaster;
  let sceneGroup = null;
  let cityGroup  = null;
  let dotObjs    = [];
  let animId;

  // ── Camera ────────────────────────────────────────────────────────────────
  const CAM_OVERHEAD = new THREE.Vector3(0, 300, 200);
  const CAM_FRONT    = new THREE.Vector3(0, 110, 530);
  const CAM_LOOK     = new THREE.Vector3(0, 10, 0);
  let camFrom = null, camTo = null, camT = 1;

  // ── Colors ────────────────────────────────────────────────────────────────
  const C_NEUTRAL = new THREE.Color('#2563eb');  // same as individual landlord blue
  const C_CORP    = new THREE.Color('#d97706');
  const C_INDIV   = new THREE.Color('#2563eb');

  const FLOAT_Y = 55;
  const LAND_Y  = 1.5;

  // ── MBTA data ─────────────────────────────────────────────────────────────
  const MBTA = [
    { lat:42.3471,lng:-71.0765,c:'#E87722'},{ lat:42.3414,lng:-71.0836,c:'#E87722'},
    { lat:42.3367,lng:-71.1000,c:'#E87722'},{ lat:42.3314,lng:-71.0988,c:'#E87722'},
    { lat:42.3236,lng:-71.1004,c:'#E87722'},{ lat:42.3178,lng:-71.0997,c:'#E87722'},
    { lat:42.3103,lng:-71.1079,c:'#E87722'},{ lat:42.2983,lng:-71.1136,c:'#E87722'},
    { lat:42.3426,lng:-71.0567,c:'#DA291C'},{ lat:42.3306,lng:-71.0576,c:'#DA291C'},
    { lat:42.3204,lng:-71.0529,c:'#DA291C'},{ lat:42.3100,lng:-71.0530,c:'#DA291C'},
    { lat:42.2999,lng:-71.0633,c:'#DA291C'},{ lat:42.2929,lng:-71.0653,c:'#DA291C'},
    { lat:42.2843,lng:-71.0638,c:'#DA291C'},{ lat:42.3693,lng:-71.0397,c:'#003DA5'},
    { lat:42.3746,lng:-71.0208,c:'#003DA5'},{ lat:42.3794,lng:-71.0214,c:'#003DA5'},
    { lat:42.3862,lng:-71.0026,c:'#003DA5'},{ lat:42.3344,lng:-71.1050,c:'#00843D'},
    { lat:42.3312,lng:-71.1078,c:'#00843D'},{ lat:42.3289,lng:-71.1100,c:'#00843D'},
    { lat:42.3218,lng:-71.1095,c:'#00843D'},
  ];

  // ── Popup ─────────────────────────────────────────────────────────────────
  let selectedDot = null;
  let popupX = 0, popupY = 0;

  // ── Coordinate helpers ────────────────────────────────────────────────────
  let projection = null;
  function proj([lng, lat]) {
    const [px, py] = projection([lng, lat]);
    return [px - 200, -(py - 200)];
  }

  // ── Build a canvas "T" texture for MBTA sprites ───────────────────────────
  function makeTTexture(hex) {
    const size = 64;
    const cv   = document.createElement('canvas');
    cv.width = cv.height = size;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = hex;
    ctx.beginPath();
    ctx.arc(size/2, size/2, size/2-2, 0, Math.PI*2);
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${Math.round(size*0.5)}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('T', size/2, size/2+1);
    return new THREE.CanvasTexture(cv);
  }

  // ── Build a flat polygon mesh from a GeoJSON feature ─────────────────────
  function featureToGroup(feature, fillHex, edgeHex, yOff = 0) {
    const grp  = new THREE.Group();
    const geom = feature.geometry;
    const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;

    for (const poly of polys) {
      if (!poly[0]?.length) continue;
      const shape = new THREE.Shape();
      poly[0].forEach(([lng, lat], i) => {
        const [x, z] = proj([lng, lat]);
        i === 0 ? shape.moveTo(x, -z) : shape.lineTo(x, -z);
      });
      shape.closePath();
      for (let h = 1; h < poly.length; h++) {
        const hole = new THREE.Path();
        poly[h].forEach(([lng, lat], i) => {
          const [x, z] = proj([lng, lat]);
          i === 0 ? hole.moveTo(x, -z) : hole.lineTo(x, -z);
        });
        hole.closePath();
        shape.holes.push(hole);
      }
      const geo  = new THREE.ShapeGeometry(shape);
      const fill = new THREE.Mesh(geo,
        new THREE.MeshLambertMaterial({ color: fillHex, side: THREE.DoubleSide }));
      fill.rotation.x = -Math.PI / 2;
      fill.position.y = yOff;
      fill.receiveShadow = true;
      grp.add(fill);
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: edgeHex }));
      edge.rotation.x = -Math.PI / 2;
      edge.position.y = yOff + 0.3;
      grp.add(edge);
    }
    return grp;
  }

  // ── Neighborhood label sprite ─────────────────────────────────────────────
  function makeLabel(text, { fontSize = 22, color = '#5a5040', alpha = 1 } = {}) {
    const DPR = 3;  // 3× oversample for sharp retina-quality text
    const cv  = document.createElement('canvas');
    const ctx = cv.getContext('2d');
    ctx.font  = `600 ${fontSize * DPR}px Inter, Arial, sans-serif`;
    const w   = Math.ceil(ctx.measureText(text).width) + 24 * DPR;
    cv.width  = w;
    cv.height = (fontSize + 16) * DPR;
    ctx.font         = `600 ${fontSize * DPR}px Inter, Arial, sans-serif`;
    ctx.globalAlpha  = alpha;
    ctx.fillStyle    = color;
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 12 * DPR, cv.height / 2);
    const tex = new THREE.CanvasTexture(cv);
    tex.needsUpdate = true;
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
    const sp  = new THREE.Sprite(mat);
    const scale = fontSize * 1.1;
    sp.scale.set(scale * (w / cv.height), scale, 1);
    return sp;
  }

  // Compute the centroid of a GeoJSON feature (average of bounding-box center)
  function featureCentroid(feat) {
    const geom  = feat.geometry;
    const rings = geom.type === 'Polygon' ? [geom.coordinates[0]] : geom.coordinates.map(p => p[0]);
    let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity;
    for (const ring of rings) {
      for (const [lng, lat] of ring) {
        if (lng < minLng) minLng = lng; if (lng > maxLng) maxLng = lng;
        if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
      }
    }
    return [(minLng + maxLng) / 2, (minLat + maxLat) / 2];
  }

  // ── City context + MBTA sprites ───────────────────────────────────────────
  function buildCity() {
    if (cityGroup) scene.remove(cityGroup);
    cityGroup = new THREE.Group();
    if (!geoData) { scene.add(cityGroup); return; }

    // Other neighborhood polygons + subtle labels
    for (const feat of geoData.features) {
      if (feat.properties.name === neighborhood) continue;
      try {
        cityGroup.add(featureToGroup(feat, 0xF5EDD8, 0xD4C070, -0.5));
        // Faint neighborhood name
        const [lng, lat] = featureCentroid(feat);
        const [cx, cz]   = proj([lng, lat]);
        const lbl        = makeLabel(feat.properties.name, { fontSize: 16, color: '#9a8840', alpha: 0.65 });
        lbl.position.set(cx, 1, cz);
        cityGroup.add(lbl);
      } catch {}
    }

    // Active neighborhood name — larger, more prominent
    try {
      const activeFeat = geoData.features.find(f => f.properties.name === neighborhood);
      if (activeFeat) {
        const [lng, lat] = featureCentroid(activeFeat);
        const [cx, cz]   = proj([lng, lat]);
        const lbl        = makeLabel(neighborhood, { fontSize: 26, color: '#6b5a20', alpha: 0.9 });
        lbl.position.set(cx, 2, cz);
        cityGroup.add(lbl);
      }
    } catch {}

    // MBTA "T" sprites — billboard circles, always face camera
    for (const s of MBTA) {
      try {
        const [x, z] = proj([s.lng, s.lat]);
        const tex    = makeTTexture(s.c);
        const sp     = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
        sp.scale.set(12, 12, 1);
        sp.position.set(x, 10, z);
        cityGroup.add(sp);
      } catch {}
    }

    scene.add(cityGroup);
  }

  // ── Dot builder ───────────────────────────────────────────────────────────
  // Uses OPAQUE materials by default — no transparency artifacts.
  // Step 4 dims non-affordable dots by swapping to a new transparent material.
  function buildDots() {
    dotObjs.forEach(d => { scene.remove(d.mesh); d.mesh.geometry.dispose(); d.mesh.material.dispose(); });
    dotObjs = [];
    if (!projection) return;

    const geo = new THREE.SphereGeometry(2.2, 8, 6);

    properties
      .filter(p => p.neighborhood === neighborhood && p.lat && p.lng)
      .forEach(p => {
        const mat  = new THREE.MeshLambertMaterial({ color: C_NEUTRAL, transparent: true, opacity: 0.78 });
        const mesh = new THREE.Mesh(geo, mat);
        const [x, z] = proj([p.lng, p.lat]);
        mesh.position.set(x, FLOAT_Y, z);
        mesh.castShadow = true;
        scene.add(mesh);
        dotObjs.push({
          mesh,
          rawProp:      p,                          // keep for maxRent reactivity
          investor:     !!p.investor_buyer,
          wasAffordable:(p.monthly_rent     ?? 9999) <= maxRent,
          willFall:     (p.monthly_rent     ?? 9999) <= maxRent
                     && (p.monthly_rent_now ?? 0)    >  maxRent,
          baseColor:    !!p.investor_buyer ? C_CORP.clone() : C_INDIV.clone(),
          address:      p.address ?? '',
          monthlyRent:  p.monthly_rent     ?? null,
          rentNow:      p.monthly_rent_now  ?? null,
          falling: false, fallY: FLOAT_Y, fallV: 0,
          fallDelay: Math.floor(Math.random() * 100),
          landed: false,
        });
      });
  }

  // ── Apply step ────────────────────────────────────────────────────────────
  let prevStep = -1;

  function applyStep(step) {
    selectedDot = null;

    if (step < 4) {
      dotObjs.forEach(d => {
        // Reset fall state
        d.falling = false; d.landed = false;
        d.fallY = FLOAT_Y; d.fallV = 0;
        d.fallDelay = Math.floor(Math.random() * 100);
        d.mesh.position.y = FLOAT_Y;
        d.mesh.visible    = true;

        // Ensure opaque
        d.mesh.material.transparent = true;
        d.mesh.material.opacity     = 0.78;

        // Color: neutral → corp/individual split at step 2
        d.mesh.material.color.set(
          step >= 2 ? (d.investor ? C_CORP : C_INDIV) : C_NEUTRAL
        );
      });

    } else {
      // Step 4: same positions, non-affordable dots dimmed, affordable-then fall
      dotObjs.forEach(d => {
        d.mesh.visible = true;
        if (!d.wasAffordable) {
          d.mesh.material.transparent = true;
          d.mesh.material.opacity     = 0.07;
        } else {
          d.mesh.material.transparent = true;
          d.mesh.material.opacity     = 0.78;
          if (!d.falling && !d.landed)
            d.mesh.material.color.set(d.baseColor);   // keep blue/orange
          if (d.willFall && !d.falling && !d.landed)
            d.falling = true;
        }
      });
    }
  }

  // ── Easing ────────────────────────────────────────────────────────────────
  function ease(t) { return t < 0.5 ? 2*t*t : -1+(4-2*t)*t; }

  function startCam(to) {
    camFrom = camera.position.clone();
    camTo   = to.clone();
    camT    = 0;
    if (controls) controls.enabled = false;
  }

  // ── Render loop ───────────────────────────────────────────────────────────
  function animate() {
    animId = requestAnimationFrame(animate);

    // Camera transition
    if (camT < 1) {
      camT = Math.min(camT + 0.025, 1);
      camera.position.lerpVectors(camFrom, camTo, ease(camT));
      camera.lookAt(CAM_LOOK);
      if (camT >= 1 && controls) {
        controls.target.copy(CAM_LOOK);
        controls.update();
        controls.enabled = true;
      }
    } else if (controls) {
      controls.update();
    }

    // Gravity for step 4 falling dots (color unchanged)
    if (scrollStep >= 4) {
      dotObjs.forEach(d => {
        if (!d.falling || d.landed) return;
        if (d.fallDelay > 0) { d.fallDelay--; return; }
        d.fallV += -0.12;
        d.fallY += d.fallV;
        if (d.fallY <= LAND_Y) {
          d.fallY = LAND_Y; d.fallV = 0; d.landed = true;
          d.mesh.position.y = LAND_Y;
        } else {
          d.mesh.position.y = d.fallY;
        }
      });
    }

    renderer.render(scene, camera);
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function initScene() {
    if (!canvas) return;
    const w = Math.max(canvas.clientWidth,  100);
    const h = Math.max(canvas.clientHeight, 100);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h, false);
    renderer.shadowMap.enabled = true;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xF5FDFF);
    scene.fog        = new THREE.Fog(0xF5FDFF, 900, 1400);

    camera = new THREE.PerspectiveCamera(48, w / h, 0.1, 2000);
    camera.position.copy(CAM_OVERHEAD);
    camera.lookAt(CAM_LOOK);

    controls = new OrbitControls(camera, canvas);
    controls.target.copy(CAM_LOOK);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance   = 80;
    controls.maxDistance   = 900;
    controls.maxPolarAngle = Math.PI / 2.1;
    controls.update();

    raycaster = new THREE.Raycaster();

    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dir = new THREE.DirectionalLight(0xffffff, 0.5);
    dir.position.set(100, 300, 150);
    dir.castShadow = true;
    scene.add(dir);

    loadNeighborhood();
    animate();
  }

  function loadNeighborhood() {
    if (!geoData || !neighborhood || !scene) return;
    const feat = geoData.features.find(f => f.properties.name === neighborhood);
    if (!feat) return;

    projection = d3.geoMercator().fitExtent([[0, 0], [400, 400]], feat);

    buildCity();

    if (sceneGroup) scene.remove(sceneGroup);
    sceneGroup = featureToGroup(feat, 0xFDFBD4, 0xC8B864, 0);
    scene.add(sceneGroup);

    buildDots();
    prevStep = -1;
    applyStep(scrollStep);
  }

  // ── Click / raycasting ────────────────────────────────────────────────────
  let ptrDown = null;
  function onPD(e) { ptrDown = { x: e.clientX, y: e.clientY }; }
  function onPU(e) {
    if (!ptrDown) return;
    const dx = e.clientX - ptrDown.x, dy = e.clientY - ptrDown.y;
    ptrDown = null;
    if (Math.sqrt(dx*dx+dy*dy) > 6) return;

    const rect = canvas.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(
      ((e.clientX-rect.left)/rect.width)*2-1,
      ((e.clientY-rect.top)/rect.height)*-2+1,
    ), camera);

    const visible = dotObjs.filter(d => d.mesh.visible && d.mesh.material.opacity > 0.3);
    const hits    = raycaster.intersectObjects(visible.map(d => d.mesh));
    if (!hits.length) { selectedDot = null; return; }

    const rec = dotObjs.find(d => d.mesh === hits[0].object);
    if (!rec) return;
    selectedDot = rec;
    const cr = container.getBoundingClientRect();
    popupX = Math.min(e.clientX-cr.left+12, cr.width-270);
    popupY = Math.min(e.clientY-cr.top+12,  cr.height-200);
  }

  function onResize() {
    if (!canvas || !camera || !renderer) return;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  onMount(() => { initScene(); window.addEventListener('resize', onResize); });
  onDestroy(() => {
    cancelAnimationFrame(animId);
    controls?.dispose();
    renderer?.dispose();
    window.removeEventListener('resize', onResize);
  });


  // Re-compute affordability when budget slider moves (no mesh rebuild needed)
  function refreshAffordability() {
    dotObjs.forEach(d => {
      const p = d.rawProp;
      d.wasAffordable = (p.monthly_rent     ?? 9999) <= maxRent;
      d.willFall      = d.wasAffordable && (p.monthly_rent_now ?? 0) > maxRent;
      d.falling = false; d.landed = false;
      d.fallY = FLOAT_Y; d.fallV = 0;
      d.fallDelay = Math.floor(Math.random() * 100);
      d.mesh.position.y = FLOAT_Y;
      d.mesh.visible    = true;
    });
    prevStep = -1;
    applyStep(scrollStep);
  }

  let prevMaxRent = -1;
  $: if (scene && dotObjs.length && maxRent !== prevMaxRent) {
    prevMaxRent = maxRent;
    refreshAffordability();
  }

  // React to scroll step
  $: if (scene && scrollStep !== prevStep) {
    if (scrollStep >= 1 && prevStep === 0) startCam(CAM_FRONT);
    if (scrollStep === 0 && prevStep > 0)  startCam(CAM_OVERHEAD);
    applyStep(scrollStep);
    prevStep = scrollStep;
  }

  // Rebuild on neighborhood change
  let prevHood = null;
  $: if (neighborhood !== prevHood && scene) {
    prevHood = neighborhood;
    loadNeighborhood();
    if (controls) {
      camera.position.copy(scrollStep === 0 ? CAM_OVERHEAD : CAM_FRONT);
      camera.lookAt(CAM_LOOK);
      controls.target.copy(CAM_LOOK);
      controls.update();
    }
  }
</script>

<div class="wrap" bind:this={container}>
  <canvas bind:this={canvas} style="width:100%;height:100%;display:block;"
    on:pointerdown={onPD} on:pointerup={onPU}></canvas>

  {#if selectedDot}
    <div class="popup" style="left:{popupX}px;top:{popupY}px">
      <button class="x" on:click={() => selectedDot = null}>×</button>
      <div class="tag" class:corp={selectedDot.investor}>
        {selectedDot.investor ? 'Investor-owned' : 'Individually owned'}
      </div>
      <div class="addr">{selectedDot.address}</div>
      <div class="rents">
        <div><div class="rl">Rent then</div>
          <div class="rv">{selectedDot.monthlyRent ? `$${selectedDot.monthlyRent.toLocaleString()}` : '—'}/mo</div></div>
        <div class="arr">→</div>
        <div><div class="rl">Rent now</div>
          <div class="rv now">{selectedDot.rentNow ? `$${selectedDot.rentNow.toLocaleString()}` : '—'}/mo</div></div>
      </div>
      <div class="status">
        {selectedDot.willFall ? '⬇ No longer affordable' : selectedDot.wasAffordable ? '✓ Still within budget' : 'Above budget'}
      </div>
    </div>
  {/if}
</div>

<style>
  .wrap { position:relative; width:100%; height:100%; }
  .popup {
    position:absolute; width:250px;
    background:rgba(255,255,255,0.97); border:1px solid #ddd;
    border-radius:10px; box-shadow:0 4px 20px rgba(0,0,0,0.15);
    padding:12px 14px; font-family:'Inter',system-ui,sans-serif;
    font-size:0.78rem; z-index:30;
  }
  .x { position:absolute;top:6px;right:8px;background:none;border:none;font-size:1.1rem;color:#999;cursor:pointer; }
  .x:hover { color:#333; }
  .tag {
    display:inline-block; padding:2px 8px; border-radius:999px;
    font-size:0.68rem; font-weight:600;
    background:#e6efff; color:#2563eb; border:1px solid #bdd0f5; margin-bottom:6px;
  }
  .tag.corp { background:#fde8e6; color:#c0392b; border-color:#f0b3aa; }
  .addr { font-weight:700; color:#1a1a1a; margin-bottom:8px; line-height:1.3; }
  .rents {
    display:grid; grid-template-columns:1fr auto 1fr;
    align-items:center; gap:6px; padding:8px;
    background:#fff8ec; border:1px solid #f0d9c8; border-radius:6px;
  }
  .rents > div { display:flex; flex-direction:column; align-items:center; text-align:center; }
  .rl { font-size:0.6rem; font-weight:600; text-transform:uppercase; color:#8a7; margin-bottom:2px; }
  .rv { font-size:0.88rem; font-weight:700; color:#555; }
  .rv.now { color:#c0392b; }
  .arr { color:#aaa; }
  .status { margin-top:6px; font-size:0.72rem; font-weight:600; color:#555; }
</style>