(() => {
  "use strict";

  const CONFIG = {
    task_id: "WILD0_B1_sonar_triage",
    version: "2.10.2-occam",
    base_rate: 0.25,
    noise_model: {
      sensitivity: 0.85,
      false_positive_rate: 0.10
    },
    budget: 32,
    strike_cards_per_trial: 12,
    b05_strike_cards_per_trial: 12,
    b06_strike_cards_per_trial: 12,
    b0_strike_cards_per_trial: 8,
    practice_strike_cards: 8,
    target_strata: { anchor: 3, inference: 6, trap: 3 },
    b05_target_strata: { anchor: 3, inference: 6, trap: 3 },
    b06_target_strata: { anchor: 3, inference: 6, trap: 3 },
    b0_target_strata: { anchor: 4, inference: 4, trap: 0 },
    b05_m_values: [256, 512],
    b06_m_values: [512],
    b06_repeats_per_cell: 3,
    m_values: [128, 256, 512],
    repeats_per_cell: 2,
    practice_trials: [
      { phase: "practice", condition: "K1_ONE_FLEET", K: 1, M: 128, repeat_idx: 0, seed_offset: 101, budget: 32 },
      { phase: "practice", condition: "K2_TWO_FLEETS", K: 2, M: 128, repeat_idx: 1, seed_offset: 202, budget: 32 }
    ],
    grid_shapes: {
      64: [8, 8],
      128: [16, 8],
      256: [16, 16],
      512: [32, 16]
    },
    rectangle_area_tolerance: 0.10,
    aspect_min: 0.40,
    aspect_max: 2.50,
    k2_gap_min: 2,
    k2_gap_max: 6,
    local_knn: 5,
    le_sparse_fraction: 0.40,
    le_epsilon: 1e-6,
    delta_k_min: 0.20,
    delta_k_bands: [
      { label: "0.20-0.45", min: 0.20, max: 0.45 },
      { label: "0.45-0.70", min: 0.45, max: 0.70 },
      { label: "0.70-1.00", min: 0.70, max: 1.0000001 }
    ],
    inference_band_target: { "0.20-0.45": 2, "0.45-0.70": 2, "0.70-1.00": 2 },
    inference_band_slack: 1,
    b0_inference_band_target: {},
    inference_le_threshold: 0.10,
    inference_le_target: { supporting: 3, conflicting: 3 },
    b0_inference_le_target: {},
    posterior_samples_default: 12000,
    posterior_samples_max: 48000,
    posterior_ess_min: 800,
    posterior_sampler: "smc",
    smc_resample_ess_fraction: 0.50,
    exact_posterior_max_configs: 60000,
    reuse_cap: { anchor: 2, inference: 1, trap: 2 },
    scored_A_cell_reuse_cap: 1,
    k2_min_A_cells_per_block: 2,
    pair_match: { d_probe: 2.0, knn_dist: 2.0, d_border: 4.0 },
    primary_fill_strata: ["inference"],
    primary_stratum: "inference",
    floor_guard_by_m: { 128: 0.30, 256: 0.35, 512: 0.38 },
    reveal_truth_after_each_trial: false,
    cell_size_px: 40
  };

  let session = null;
  let current = null;
  let hasDownloaded = false;
  let hasUploaded = false;
  let uploadInFlight = false;
  let lastUploadStartedAt = null;
  let hoverTimer = null;
  const configCache = new Map();

  function qs() {
    return new URLSearchParams(window.location.search);
  }

  function makeRng(seed) {
    let x = seed >>> 0;
    return function rand() {
      x ^= x << 13;
      x ^= x >>> 17;
      x ^= x << 5;
      return (x >>> 0) / 4294967296;
    };
  }

  function hashString(text) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function shuffle(arr, rand) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function choice(arr, rand) {
    return arr[Math.floor(rand() * arr.length)];
  }

  function nowMs() {
    return Math.round(performance.now());
  }

  function signalLikelihood(trueBit, observedSignal) {
    const { sensitivity, false_positive_rate: fpr } = CONFIG.noise_model;
    if (trueBit) return observedSignal ? sensitivity : 1 - sensitivity;
    return observedSignal ? fpr : 1 - fpr;
  }

  function sampleSonarSignal(trueBit, rand) {
    const pPositive = trueBit ? CONFIG.noise_model.sensitivity : CONFIG.noise_model.false_positive_rate;
    return rand() < pPositive ? 1 : 0;
  }

  function deltaKBand(deltaK) {
    for (const band of CONFIG.delta_k_bands) {
      if (deltaK >= band.min && deltaK < band.max) return band.label;
    }
    return null;
  }

  function isCalibrationMode() {
    return session?.mode === "B0.5" || session?.mode === "B0.6";
  }

  function isFullPilotLikeMode() {
    return session?.mode === "B0.5" || session?.mode === "B0.6" || session?.mode === "B1";
  }

  function inferenceBandTargetsForTrial(trial) {
    return (trial.phase === "practice" || session?.mode === "B0")
      ? CONFIG.b0_inference_band_target
      : CONFIG.inference_band_target;
  }

  function inferenceLETargetsForTrial(trial) {
    return (trial.phase === "practice" || session?.mode === "B0")
      ? CONFIG.b0_inference_le_target
      : CONFIG.inference_le_target;
  }

  function inferenceLEClass(deltaLE) {
    if (deltaLE >= CONFIG.inference_le_threshold) return "supporting";
    if (deltaLE <= -CONFIG.inference_le_threshold) return "conflicting";
    return "neutral";
  }

  function reuseCapForStratum(stratum) {
    return CONFIG.reuse_cap[stratum] ?? 1;
  }

  function show(id) {
    for (const el of document.querySelectorAll(".screen")) el.classList.remove("active");
    document.getElementById(id).classList.add("active");
  }

  function gridShape(M) {
    return CONFIG.grid_shapes[M] || [Math.ceil(Math.sqrt(M)), Math.ceil(M / Math.ceil(Math.sqrt(M)))];
  }

  function xy(idx, cols) {
    return { x: idx % cols, y: Math.floor(idx / cols) };
  }

  function idxOf(x, y, cols) {
    return y * cols + x;
  }

  function distIdx(a, b, cols) {
    const aa = xy(a, cols);
    const bb = xy(b, cols);
    return Math.hypot(aa.x - bb.x, aa.y - bb.y);
  }

  function rectCells(rect, cols) {
    const cells = [];
    for (let y = rect.y; y < rect.y + rect.h; y++) {
      for (let x = rect.x; x < rect.x + rect.w; x++) cells.push(idxOf(x, y, cols));
    }
    return cells;
  }

  function rectArea(rect) {
    return rect.w * rect.h;
  }

  function rectPerimeter(rect) {
    return 2 * (rect.w + rect.h);
  }

  function rectGap(a, b) {
    const ax1 = a.x;
    const ay1 = a.y;
    const ax2 = a.x + a.w - 1;
    const ay2 = a.y + a.h - 1;
    const bx1 = b.x;
    const by1 = b.y;
    const bx2 = b.x + b.w - 1;
    const by2 = b.y + b.h - 1;
    const dx = ax2 < bx1 ? bx1 - ax2 - 1 : bx2 < ax1 ? ax1 - bx2 - 1 : 0;
    const dy = ay2 < by1 ? by1 - ay2 - 1 : by2 < ay1 ? ay1 - by2 - 1 : 0;
    return Math.hypot(Math.max(0, dx), Math.max(0, dy));
  }

  function rectOptions(cols, rows, targetArea, tol = CONFIG.rectangle_area_tolerance) {
    const minArea = Math.max(1, targetArea * (1 - tol));
    const maxArea = Math.max(minArea, targetArea * (1 + tol));
    const opts = [];
    for (let w = 2; w <= cols; w++) {
      for (let h = 2; h <= rows; h++) {
        const area = w * h;
        const ratio = w / h;
        if (area < minArea || area > maxArea) continue;
        if (ratio < CONFIG.aspect_min || ratio > CONFIG.aspect_max) continue;
        for (let y = 0; y <= rows - h; y++) {
          for (let x = 0; x <= cols - w; x++) {
            opts.push({ x, y, w, h, area, perimeter: 2 * (w + h), aspect_ratio: ratio });
          }
        }
      }
    }
    return opts;
  }

  function lifeFromBlocks(M, cols, blocks) {
    const life = new Array(M).fill(0);
    for (const block of blocks) {
      for (const c of block.cells) life[c] = 1;
    }
    return life;
  }

  function blockRecord(rect, cols, blockIndex) {
    return {
      block_index: blockIndex,
      x: rect.x,
      y: rect.y,
      w: rect.w,
      h: rect.h,
      area: rectArea(rect),
      perimeter: rectPerimeter(rect),
      aspect_ratio: rect.w / rect.h,
      cells: rectCells(rect, cols)
    };
  }

  function samplePattern(M, condition, seedOrRand) {
    const rand = typeof seedOrRand === "function" ? seedOrRand : makeRng(seedOrRand);
    const [cols, rows] = gridShape(M);
    const targetAlive = Math.max(1, Math.round(CONFIG.base_rate * M));
    if (condition === "K1_ONE_FLEET") {
      const opts = rectOptions(cols, rows, targetAlive);
      if (!opts.length) throw new Error(`No K1 rectangle options for M=${M}`);
      const rect = choice(opts, rand);
      const blocks = [blockRecord(rect, cols, 0)];
      const life = lifeFromBlocks(M, cols, blocks);
      return {
        life,
        blocks,
        params: {
          K: 1,
          target_alive_count: targetAlive,
          alive_count: life.reduce((a, b) => a + b, 0),
          total_perimeter: blocks[0].perimeter,
          area_tolerance: CONFIG.rectangle_area_tolerance,
          grid_cols: cols,
          grid_rows: rows
        }
      };
    }

    const halfTarget = Math.max(2, Math.round(targetAlive / 2));
    const halfOpts = rectOptions(cols, rows, halfTarget);
    if (!halfOpts.length) throw new Error(`No K2 rectangle options for M=${M}`);
    for (let attempt = 0; attempt < 20000; attempt++) {
      const r1 = choice(halfOpts, rand);
      const r2 = choice(halfOpts, rand);
      const gap = rectGap(r1, r2);
      if (gap < CONFIG.k2_gap_min || gap > CONFIG.k2_gap_max) continue;
      const cells1 = new Set(rectCells(r1, cols));
      let overlap = false;
      for (const c of rectCells(r2, cols)) {
        if (cells1.has(c)) {
          overlap = true;
          break;
        }
      }
      if (overlap) continue;
      const totalArea = rectArea(r1) + rectArea(r2);
      const minArea = targetAlive * (1 - CONFIG.rectangle_area_tolerance);
      const maxArea = targetAlive * (1 + CONFIG.rectangle_area_tolerance);
      if (totalArea < minArea || totalArea > maxArea) continue;
      const blocks = [blockRecord(r1, cols, 0), blockRecord(r2, cols, 1)];
      const life = lifeFromBlocks(M, cols, blocks);
      return {
        life,
        blocks,
        params: {
          K: 2,
          target_alive_count: targetAlive,
          alive_count: life.reduce((a, b) => a + b, 0),
          total_perimeter: blocks.reduce((a, b) => a + b.perimeter, 0),
          inter_block_gap_width: gap,
          area_tolerance: CONFIG.rectangle_area_tolerance,
          grid_cols: cols,
          grid_rows: rows
        }
      };
    }
    throw new Error(`Could not sample K2 separated blocks for M=${M}`);
  }

  function lifeIndices(life) {
    const xs = [];
    for (let i = 0; i < life.length; i++) if (life[i]) xs.push(i);
    return xs;
  }

  function enumerateAliveLists(M, condition) {
    const key = `${M}|${condition}`;
    if (configCache.has(key)) return configCache.get(key);
    const [cols, rows] = gridShape(M);
    const targetAlive = Math.max(1, Math.round(CONFIG.base_rate * M));
    const out = [];
    if (condition === "K1_ONE_FLEET") {
      for (const rect of rectOptions(cols, rows, targetAlive)) {
        out.push(rectCells(rect, cols));
      }
    } else {
      const halfTarget = Math.max(2, Math.round(targetAlive / 2));
      const halfOpts = rectOptions(cols, rows, halfTarget);
      for (const r1 of halfOpts) {
        const cells1 = new Set(rectCells(r1, cols));
        for (const r2 of halfOpts) {
          const gap = rectGap(r1, r2);
          if (gap < CONFIG.k2_gap_min || gap > CONFIG.k2_gap_max) continue;
          let overlap = false;
          const cells2 = rectCells(r2, cols);
          for (const c of cells2) {
            if (cells1.has(c)) {
              overlap = true;
              break;
            }
          }
          if (overlap) continue;
          const totalArea = rectArea(r1) + rectArea(r2);
          if (totalArea < targetAlive * (1 - CONFIG.rectangle_area_tolerance)) continue;
          if (totalArea > targetAlive * (1 + CONFIG.rectangle_area_tolerance)) continue;
          out.push([...cells1, ...cells2]);
          if (out.length > CONFIG.exact_posterior_max_configs) {
            configCache.set(key, null);
            return null;
          }
        }
      }
    }
    configCache.set(key, out);
    return out;
  }

  function conditionLabel(condition) {
    return condition === "K1_ONE_FLEET" ? "K1: one rectangle" : "K2: two rectangles";
  }

  function buildScoredPlan(seedBase, mode) {
    if (mode === "B0") {
      return shuffle([
        { phase: "scored", condition: "K1_ONE_FLEET", K: 1, M: 128, repeat_idx: 0, seed_offset: 1000, budget: CONFIG.budget },
        { phase: "scored", condition: "K2_TWO_FLEETS", K: 2, M: 128, repeat_idx: 0, seed_offset: 1100, budget: CONFIG.budget }
      ], makeRng(seedBase + 707));
    }
    if (mode === "B0.5") {
      const calibration = [];
      let idx = 0;
      for (const M of CONFIG.b05_m_values) {
        for (const condition of ["K1_ONE_FLEET", "K2_TWO_FLEETS"]) {
          calibration.push({
            phase: "scored",
            condition,
            K: condition === "K1_ONE_FLEET" ? 1 : 2,
            M,
            repeat_idx: 0,
            seed_offset: 1500 + idx * 113,
            budget: CONFIG.budget
          });
          idx += 1;
        }
      }
      return shuffle(calibration, makeRng(seedBase + 1505));
    }
    if (mode === "B0.6") {
      const calibration = [];
      let idx = 0;
      for (const M of CONFIG.b06_m_values) {
        for (const condition of ["K1_ONE_FLEET", "K2_TWO_FLEETS"]) {
          for (let repeat = 0; repeat < CONFIG.b06_repeats_per_cell; repeat++) {
            calibration.push({
              phase: "scored",
              condition,
              K: condition === "K1_ONE_FLEET" ? 1 : 2,
              M,
              repeat_idx: repeat,
              seed_offset: 2200 + idx * 131,
              budget: CONFIG.budget
            });
            idx += 1;
          }
        }
      }
      return shuffle(calibration, makeRng(seedBase + 1606));
    }
    const trials = [];
    let idx = 0;
    for (const M of CONFIG.m_values) {
      for (const condition of ["K1_ONE_FLEET", "K2_TWO_FLEETS"]) {
        for (let repeat = 0; repeat < CONFIG.repeats_per_cell; repeat++) {
          trials.push({
            phase: "scored",
            condition,
            K: condition === "K1_ONE_FLEET" ? 1 : 2,
            M,
            repeat_idx: repeat,
            seed_offset: 1000 + idx * 97,
            budget: CONFIG.budget
          });
          idx += 1;
        }
      }
    }
    return shuffle(trials, makeRng(seedBase + 9090));
  }

  function initSession() {
    const params = qs();
    const prolificPid = params.get("PROLIFIC_PID") || params.get("participant") || "";
    const typed = document.getElementById("participantId").value.trim();
    const participantId = typed || prolificPid || `anon_${Date.now().toString(36)}`;
    const seedBase = hashString(`${participantId}|${Date.now()}|WILD0B1SONAR`);
    const mode = document.getElementById("taskMode").value;
    const completionUrl = params.get("completion_url") || params.get("completion") || "";
    const uploadUrl = params.get("upload_url") || params.get("datapipe_url") || params.get("DATAPIPE_URL") || "";
    const scored = buildScoredPlan(seedBase, mode);
    const practice = CONFIG.practice_trials.map((t, i) => ({ ...t, repeat_idx: i }));
    hasDownloaded = false;
    hasUploaded = false;
    uploadInFlight = false;
    session = {
      task_id: CONFIG.task_id,
      version: CONFIG.version,
      mode,
      participant_id: participantId,
      platform_ids: {
        PROLIFIC_PID: params.get("PROLIFIC_PID") || null,
        STUDY_ID: params.get("STUDY_ID") || null,
        SESSION_ID: params.get("SESSION_ID") || null
      },
      completion_url: completionUrl || null,
      upload_url: uploadUrl || null,
      upload_status: uploadUrl ? "pending" : "not_configured",
      uploaded_at: null,
      perceived_ease: null,
      perceived_ease_at: null,
      consent_timestamp: new Date().toISOString(),
      seed_base: seedBase,
      config: CONFIG,
      device: {
        user_agent: navigator.userAgent,
        language: navigator.language,
        screen_width: window.screen.width,
        screen_height: window.screen.height,
        viewport_width: window.innerWidth,
        viewport_height: window.innerHeight
      },
      trials: [],
      plan: [...practice, ...scored],
      current_plan_index: 0,
      started_at: new Date().toISOString(),
      finished_at: null,
      autosave_key: `wild0_b1_sonar_autosave_${participantId}`
    };
    const completionBtn = document.getElementById("completionBtn");
    if (completionUrl) {
      completionBtn.classList.remove("hidden");
      completionBtn.disabled = true;
    }
    document.getElementById("downloadBtn").disabled = false;
    autosaveSession();
  }

  function startCurrentTrial() {
    if (session.current_plan_index >= session.plan.length) {
      finishSession();
      return;
    }
    const plan = session.plan[session.current_plan_index];
    const patternSeed = (session.seed_base + plan.seed_offset) >>> 0;
    const pairGenSeed = (patternSeed ^ 0x6d2b79f5) >>> 0;
    const generated = samplePattern(plan.M, plan.condition, patternSeed);
    const [cols, rows] = gridShape(plan.M);
    current = {
      trial_id: `${plan.phase}_${session.current_plan_index + 1}`,
      phase: plan.phase,
      plan_index: session.current_plan_index,
      trial_index: session.current_plan_index + 1,
      M: plan.M,
      grid_cols: cols,
      grid_rows: rows,
      condition: plan.condition,
      K: plan.K,
      block_count: plan.K,
      repeat_idx: plan.repeat_idx ?? null,
      pattern_seed: patternSeed,
      pair_gen_seed: pairGenSeed,
      budget_B: Math.min(plan.budget, plan.M),
      requested_budget_B: plan.budget,
      noise_model: { ...CONFIG.noise_model },
      sensitivity: CONFIG.noise_model.sensitivity,
      false_positive_rate: CONFIG.noise_model.false_positive_rate,
      life: generated.life,
      alive_cells: lifeIndices(generated.life),
      blocks: generated.blocks,
      concept_params: generated.params,
      signals_by_cell: Array.from({ length: plan.M }, () => []),
      click_events: [],
      strike_cards: [],
      strike_generation: {},
      response_choice_events: [],
      derived: {},
      started_at: new Date().toISOString(),
      started_ms: nowMs(),
      viewport_at_trial_start: { width: window.innerWidth, height: window.innerHeight },
      early_finish_used: false,
      phase_state: "click",
      clicks: 0,
      rand: makeRng(patternSeed ^ 0x9e3779b9)
    };
    updateTaskChrome();
    document.getElementById("breakPanel").classList.add("hidden");
    document.getElementById("taskLayout").classList.remove("hidden");
    document.getElementById("clickSide").classList.remove("hidden");
    document.getElementById("responseSide").classList.add("hidden");
    show("taskScreen");
    renderBoard();
    autosaveSession();
  }

  function updateTaskChrome() {
    const scoredTotal = session.plan.filter(t => t.phase === "scored").length;
    const scoredDone = session.trials.filter(t => t.phase === "scored").length;
    const practiceTotal = session.plan.filter(t => t.phase === "practice").length;
    const practiceDone = session.trials.filter(t => t.phase === "practice").length;
    document.getElementById("phaseMetric").textContent = current.phase === "practice" ? "Practice" : "Scored";
    document.getElementById("trialMetric").textContent = current.phase === "practice"
      ? `${practiceDone + 1} / ${practiceTotal}`
      : `${scoredDone + 1} / ${scoredTotal}`;
    document.getElementById("conditionMetric").textContent = conditionLabel(current.condition);
    document.getElementById("mMetric").textContent = `${current.M}`;
    document.getElementById("clickMetric").textContent = `${current.clicks} / ${current.budget_B}`;
    document.getElementById("uniqueMetric").textContent = `${uniqueClickedCount()}`;
    const strikeDone = current.strike_cards.filter(c => c.chosen_cell !== null).length;
    const strikeTotal = current.strike_cards.length || strikeCardCountForTrial(current);
    const pct = current.phase_state === "click"
      ? current.clicks / Math.max(1, current.budget_B) * 100
      : strikeDone / Math.max(1, strikeTotal) * 100;
    document.getElementById("progressBar").style.width = `${pct}%`;
    document.getElementById("progressText").textContent = current.phase_state === "click" ? "Sonar phase" : "Strike phase";
    document.getElementById("budgetText").textContent = current.phase_state === "click"
      ? `${current.budget_B - current.clicks} checks left`
      : `${Math.max(0, strikeTotal - strikeDone)} strikes left`;
    const help = current.condition === "K1_ONE_FLEET"
      ? "This round has one filled rectangular target patch. Target cells touch by shared sides."
      : "This round has two separate filled rectangular target patches. Each patch is solid and side-connected.";
    document.getElementById("conditionHelp").textContent = help;
    document.getElementById("trialInstruction").textContent = current.phase_state === "click"
      ? "Use sonar checks to infer the hidden rectangle pattern. Each check is noisy, so one clue is not certainty."
      : "Click one of the two bright highlighted sectors. Checked sonar clues remain visible for reasoning.";
    const finishBtn = document.getElementById("finishEarlyBtn");
    const allowEarlyFinish = current.phase === "practice" || session.mode === "B0";
    finishBtn.classList.toggle("hidden", !allowEarlyFinish);
    finishBtn.disabled = !allowEarlyFinish;
    document.getElementById("taskLayout").classList.toggle("strike-mode", current.phase_state === "response");
  }

  function uniqueClickedCount() {
    if (!current) return 0;
    return current.signals_by_cell.filter(xs => xs.length > 0).length;
  }

  function latestSignal(i) {
    const xs = current.signals_by_cell[i];
    return xs.length ? xs[xs.length - 1].revealed_signal : null;
  }

  function currentStrikeCard() {
    if (!current || current.phase_state !== "response") return null;
    return current.strike_cards[current.current_strike_index] || null;
  }

  function currentStrikeCellSet() {
    const s = new Set();
    if (!current || current.phase_state !== "response") return s;
    const card = currentStrikeCard();
    if (card) {
      s.add(card.display_left_cell);
      s.add(card.display_right_cell);
    }
    return s;
  }

  function chosenStrikeCellSet() {
    const s = new Set();
    if (!current || current.phase_state !== "response") return s;
    for (const card of current.strike_cards) {
      if (card.chosen_cell !== null && card.chosen_cell !== undefined) s.add(card.chosen_cell);
    }
    return s;
  }

  function renderBoard() {
    const board = document.getElementById("board");
    board.style.setProperty("--cell-size", `${CONFIG.cell_size_px}px`);
    board.style.gridTemplateColumns = `repeat(${current.grid_cols}, var(--cell-size))`;
    board.classList.toggle("strike-select-mode", current.phase_state === "response");
    board.innerHTML = "";
    const currentStrikeSet = currentStrikeCellSet();
    const chosenStrikeSet = chosenStrikeCellSet();
    const clickPhaseLocked = current.phase_state === "click" && current.clicks >= current.budget_B;
    for (let i = 0; i < current.M; i++) {
      const sig = latestSignal(i);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cell";
      btn.dataset.idx = String(i);
      if (sig !== null) btn.classList.add("clicked", sig === 1 ? "alive" : "dead");
      if (currentStrikeSet.has(i)) btn.classList.add("probe", "strike-cell", "current-strike");
      if (chosenStrikeSet.has(i)) btn.classList.add("strike-chosen");
      btn.disabled = current.phase_state === "click" ? clickPhaseLocked : !currentStrikeSet.has(i);
      const count = current.signals_by_cell[i].length;
      const signalBadge = sig === null ? "" : `<span class="signal">${sig === 1 ? "T" : "E"}</span>`;
      btn.innerHTML = `<span class="idx">${i + 1}</span>${signalBadge}${count ? `<span class="count">${count}x</span>` : ""}`;
      btn.title = sig === null ? `Sector ${i + 1}, unchecked` : `Sector ${i + 1}, latest sonar ${sig ? "target" : "empty"}, checked ${count} time(s)`;
      btn.addEventListener("click", () => {
        if (current.phase_state === "response" && currentStrikeSet.has(i)) chooseStrikeCell(i);
        else clickCell(i);
      });
      board.appendChild(btn);
    }
    updateTaskChrome();
  }

  function setCellCardHighlight(idx, on) {
    const cell = document.querySelector(`.cell[data-idx="${idx}"]`);
    if (cell) cell.classList.toggle("probe-hover", on);
    for (const row of document.querySelectorAll(`.probe-row[data-left="${idx}"], .probe-row[data-right="${idx}"]`)) {
      row.classList.toggle("probe-hover", on);
    }
  }

  function clearHighlights() {
    for (const el of document.querySelectorAll(".probe-hover")) el.classList.remove("probe-hover");
  }

  function highlightCard(cardIndex, on) {
    const card = current.strike_cards[cardIndex];
    if (!card) return;
    for (const idx of [card.display_left_cell, card.display_right_cell]) {
      const cell = document.querySelector(`.cell[data-idx="${idx}"]`);
      if (cell) cell.classList.toggle("probe-hover", on);
    }
    const row = document.querySelector(`.probe-row[data-card="${cardIndex}"]`);
    if (row) row.classList.toggle("probe-hover", on);
  }

  function focusCardsForCell(idx) {
    clearHighlights();
    const row = document.querySelector(`.probe-row[data-left="${idx}"], .probe-row[data-right="${idx}"]`);
    if (row) {
      row.scrollIntoView({ block: "center", behavior: "smooth" });
      const cardIndex = parseInt(row.dataset.card, 10);
      highlightCard(cardIndex, true);
      if (hoverTimer) clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => highlightCard(cardIndex, false), 1800);
    }
  }

  function clickCell(i) {
    if (!current || current.phase_state !== "click" || current.clicks >= current.budget_B) return;
    const trueBit = current.life[i];
    const revealed = sampleSonarSignal(trueBit, current.rand);
    const signalMatchesTruth = revealed === trueBit;
    const event = {
      order_idx: current.clicks + 1,
      cell_index: i,
      x: i % current.grid_cols,
      y: Math.floor(i / current.grid_cols),
      revealed_signal: revealed,
      true_bit: trueBit,
      signal_matches_truth: signalMatchesTruth,
      correct: signalMatchesTruth,
      signal_likelihood: signalLikelihood(trueBit, revealed),
      timestamp_ms: nowMs() - current.started_ms
    };
    current.signals_by_cell[i].push(event);
    current.click_events.push(event);
    current.clicks += 1;
    autosaveSession();
    if (current.clicks >= current.budget_B) enterStrikePhase();
    renderBoard();
  }

  function finishClicksNow() {
    if (!current || current.phase_state !== "click") return;
    current.early_finish_used = true;
    autosaveSession();
    enterStrikePhase();
    renderBoard();
  }

  function computeLocalEvidence(trial) {
    const M = trial.M;
    const cols = trial.grid_cols;
    const metrics = Array.from({ length: M }, () => ({
      LE: 0,
      d_probe: null,
      knn_dist: null,
      d_border: null,
      effective_weight: 0
    }));
    for (let i = 0; i < M; i++) {
      metrics[i].d_border = distanceToFleetBorder(trial, i);
      if (!trial.click_events.length) continue;
      const ds = trial.click_events.map(e => ({
        d: distIdx(i, e.cell_index, cols),
        sign: e.revealed_signal ? 1 : -1
      })).sort((a, b) => a.d - b.d).slice(0, CONFIG.local_knn);
      const kth = ds.length ? Math.max(ds[ds.length - 1].d, 1.0) : 1.0;
      const sigma = Math.max(kth / 2, 0.75);
      let num = 0;
      let den = 0;
      for (const item of ds) {
        const w = Math.exp(-0.5 * Math.pow(item.d / sigma, 2));
        num += w * item.sign;
        den += w;
      }
      metrics[i].effective_weight = den;
      metrics[i].LE = den > CONFIG.le_epsilon ? num / den : 0;
      metrics[i].d_probe = ds.length ? ds[0].d : null;
      metrics[i].knn_dist = ds.length ? ds.reduce((a, b) => a + b.d, 0) / ds.length : null;
    }
    const eligible = trial.life.map((_, i) => i).filter(i => trial.signals_by_cell[i].length === 0);
    const sparse = eligible.length
      ? eligible.filter(i => Math.abs(metrics[i].LE) < CONFIG.le_epsilon).length / eligible.length > CONFIG.le_sparse_fraction
      : true;
    return { metrics, LE_sparse_trial: sparse };
  }

  function distanceToFleetBorder(trial, idx) {
    const p = xy(idx, trial.grid_cols);
    let best = Infinity;
    for (const block of trial.blocks) {
      const x1 = block.x;
      const y1 = block.y;
      const x2 = block.x + block.w - 1;
      const y2 = block.y + block.h - 1;
      if (p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2) {
        best = Math.min(best, p.x - x1, x2 - p.x, p.y - y1, y2 - p.y);
      } else {
        const dx = p.x < x1 ? x1 - p.x : p.x > x2 ? p.x - x2 : 0;
        const dy = p.y < y1 ? y1 - p.y : p.y > y2 ? p.y - y2 : 0;
        best = Math.min(best, Math.hypot(dx, dy));
      }
    }
    return Number.isFinite(best) ? best : null;
  }

  function blockIdForCell(trial, idx) {
    for (const block of trial.blocks || []) {
      if (block.cells && block.cells.includes(idx)) return block.block_index;
    }
    return null;
  }

  function estimatePosteriorTarget(trial) {
    const exactAliveLists = enumerateAliveLists(trial.M, trial.condition);
    if (exactAliveLists && exactAliveLists.length > 0) {
      const logWeights = [];
      const aliveSets = [];
      for (const alive of exactAliveLists) {
        const aliveSet = new Set(alive);
        aliveSets.push(aliveSet);
        let logw = 0;
        for (const e of trial.click_events) {
          const predicted = aliveSet.has(e.cell_index) ? 1 : 0;
          logw += Math.log(signalLikelihood(predicted, e.revealed_signal));
        }
        logWeights.push(logw);
      }
      const maxLog = Math.max(...logWeights);
      const weights = logWeights.map(v => Math.exp(v - maxLog));
      const sw = weights.reduce((a, b) => a + b, 0);
      const sw2 = weights.reduce((a, b) => a + b * b, 0);
      const posteriorConcentration = sw2 > 0 ? (sw * sw) / sw2 : 0;
      const posterior = new Array(trial.M).fill(0);
      for (let s = 0; s < exactAliveLists.length; s++) {
        const w = weights[s] / sw;
        for (const c of exactAliveLists[s]) posterior[c] += w;
      }
      return {
        posterior,
        samples: exactAliveLists.length,
        posterior_ess: null,
        posterior_concentration: posteriorConcentration,
        low_ess: false,
        method: "exact_enumeration",
        exact_config_count: exactAliveLists.length
      };
    }
    if (CONFIG.posterior_sampler === "smc") return estimatePosteriorTargetSmc(trial);
    let samples = CONFIG.posterior_samples_default;
    let final = null;
    while (samples <= CONFIG.posterior_samples_max) {
      const rand = makeRng((trial.pair_gen_seed + samples + 99173) >>> 0);
      const aliveLists = [];
      const logWeights = [];
      for (let s = 0; s < samples; s++) {
        const pat = samplePattern(trial.M, trial.condition, rand);
        const alive = lifeIndices(pat.life);
        let logw = 0;
        for (const e of trial.click_events) {
          const predicted = pat.life[e.cell_index] ? 1 : 0;
          logw += Math.log(signalLikelihood(predicted, e.revealed_signal));
        }
        aliveLists.push(alive);
        logWeights.push(logw);
      }
      const maxLog = Math.max(...logWeights);
      const weights = logWeights.map(v => Math.exp(v - maxLog));
      const sw = weights.reduce((a, b) => a + b, 0);
      const sw2 = weights.reduce((a, b) => a + b * b, 0);
      const ess = sw2 > 0 ? (sw * sw) / sw2 : 0;
      const posterior = new Array(trial.M).fill(0);
      for (let s = 0; s < samples; s++) {
        const w = weights[s] / sw;
        for (const c of aliveLists[s]) posterior[c] += w;
      }
      final = {
        posterior,
        samples,
        posterior_ess: ess,
        posterior_concentration: null,
        low_ess: ess < CONFIG.posterior_ess_min,
        method: "importance_sampling",
        exact_config_count: null
      };
      if (ess >= CONFIG.posterior_ess_min || samples >= CONFIG.posterior_samples_max) break;
      samples *= 2;
    }
    return final;
  }

  function normalizeLogWeights(logWeights) {
    const maxLog = Math.max(...logWeights);
    const raw = logWeights.map(v => Math.exp(v - maxLog));
    const sw = raw.reduce((a, b) => a + b, 0);
    const weights = sw ? raw.map(v => v / sw) : raw.map(() => 1 / Math.max(1, raw.length));
    const sw2 = weights.reduce((a, b) => a + b * b, 0);
    return { weights, ess: sw2 > 0 ? 1 / sw2 : 0 };
  }

  function systematicResample(weights, rand) {
    const n = weights.length;
    const out = new Array(n);
    const step = 1 / n;
    let u = rand() * step;
    let c = weights[0] || 0;
    let i = 0;
    for (let j = 0; j < n; j++) {
      const threshold = u + j * step;
      while (threshold > c && i < n - 1) {
        i += 1;
        c += weights[i] || 0;
      }
      out[j] = i;
    }
    return out;
  }

  function estimatePosteriorTargetSmc(trial) {
    const samples = CONFIG.posterior_samples_default;
    const rand = makeRng((trial.pair_gen_seed ^ 0x5eed5eed) >>> 0);
    let particles = [];
    let aliveSets = [];
    let logWeights = new Array(samples).fill(0);
    let minEss = samples;
    let resampleCount = 0;
    for (let s = 0; s < samples; s++) {
      const pat = samplePattern(trial.M, trial.condition, rand);
      const alive = lifeIndices(pat.life);
      particles.push(alive);
      aliveSets.push(new Set(alive));
    }
    for (const e of trial.click_events) {
      for (let s = 0; s < samples; s++) {
        const predicted = aliveSets[s].has(e.cell_index) ? 1 : 0;
        logWeights[s] += Math.log(signalLikelihood(predicted, e.revealed_signal));
      }
      const norm = normalizeLogWeights(logWeights);
      minEss = Math.min(minEss, norm.ess);
      if (norm.ess < samples * CONFIG.smc_resample_ess_fraction) {
        const indexes = systematicResample(norm.weights, rand);
        particles = indexes.map(i => particles[i]);
        aliveSets = particles.map(p => new Set(p));
        logWeights = new Array(samples).fill(0);
        resampleCount += 1;
      }
    }
    let norm = normalizeLogWeights(logWeights);
    if (norm.ess < CONFIG.posterior_ess_min) {
      const indexes = systematicResample(norm.weights, rand);
      particles = indexes.map(i => particles[i]);
      aliveSets = particles.map(p => new Set(p));
      logWeights = new Array(samples).fill(0);
      norm = { weights: new Array(samples).fill(1 / samples), ess: samples };
      resampleCount += 1;
    }
    const posterior = new Array(trial.M).fill(0);
    for (let s = 0; s < samples; s++) {
      const w = norm.weights[s];
      for (const c of particles[s]) posterior[c] += w;
    }
    const uniqueParticles = new Set(particles.map(p => p.join(","))).size;
    return {
      posterior,
      samples,
      posterior_ess: norm.ess,
      posterior_concentration: null,
      low_ess: norm.ess < CONFIG.posterior_ess_min,
      method: "smc_resample",
      exact_config_count: null,
      posterior_min_ess: minEss,
      posterior_resample_count: resampleCount,
      posterior_unique_particles: uniqueParticles
    };
  }

  function classifyPair(deltaLE, stratum, leRelax) {
    if (stratum === "anchor") return deltaLE >= 0.5 - leRelax;
    if (stratum === "inference") return Math.abs(deltaLE) < 0.5 + leRelax;
    if (stratum === "trap") return deltaLE <= -0.5 + leRelax;
    return false;
  }

  function trapSubtype(trial, deadCell) {
    if (trial.condition === "K1_ONE_FLEET") {
      return distanceToFleetBorder(trial, deadCell) <= 2 ? "trap_boundary" : "trap_other";
    }
    if (trial.condition === "K2_TWO_FLEETS" && trial.blocks.length >= 2) {
      const p = xy(deadCell, trial.grid_cols);
      const a = trial.blocks[0];
      const b = trial.blocks[1];
      const minX = Math.min(a.x + a.w, b.x + b.w);
      const maxX = Math.max(a.x, b.x);
      const minY = Math.min(a.y + a.h, b.y + b.h);
      const maxY = Math.max(a.y, b.y);
      const inBetweenX = p.x >= minX && p.x <= maxX;
      const inBetweenY = p.y >= minY && p.y <= maxY;
      return (inBetweenX || inBetweenY) ? "trap_gap" : "trap_other";
    }
    return "trap_other";
  }

  function buildCandidatePairs(trial, metrics, posterior, options) {
    const clicked = new Set(trial.click_events.map(e => e.cell_index));
    const alivePool = [];
    const deadPool = [];
    for (let i = 0; i < trial.M; i++) {
      if (clicked.has(i)) continue;
      if (trial.life[i]) alivePool.push(i);
      else deadPool.push(i);
    }
    const candidates = { anchor: [], inference: [], trap: [] };
    const dProbeTol = CONFIG.pair_match.d_probe * options.matchMult;
    const knnTol = CONFIG.pair_match.knn_dist * options.matchMult;
    const borderTol = CONFIG.pair_match.d_border * options.matchMult;
    for (const a of alivePool) {
      for (const b of deadPool) {
        const ma = metrics[a];
        const mb = metrics[b];
        if (ma.d_probe === null || mb.d_probe === null || ma.knn_dist === null || mb.knn_dist === null) continue;
        if (Math.abs(ma.d_probe - mb.d_probe) > dProbeTol) continue;
        if (Math.abs(ma.knn_dist - mb.knn_dist) > knnTol) continue;
        if (Math.abs(ma.d_border - mb.d_border) > borderTol) continue;
        const deltaK = posterior[a] - posterior[b];
        if (deltaK < CONFIG.delta_k_min) continue;
        const band = deltaKBand(deltaK);
        const deltaLE = ma.LE - mb.LE;
        const aBlockId = blockIdForCell(trial, a);
        const bBlockId = blockIdForCell(trial, b);
        for (const stratum of ["anchor", "inference", "trap"]) {
          if (!classifyPair(deltaLE, stratum, options.leRelax)) continue;
          candidates[stratum].push({
            A_cell: a,
            B_cell: b,
            A_cell_block_id: aBlockId,
            B_cell_block_id: bBlockId,
            delta_LE: deltaLE,
            inference_LE_class: inferenceLEClass(deltaLE),
            delta_K: deltaK,
            LE_A: ma.LE,
            LE_B: mb.LE,
            d_probe_A: ma.d_probe,
            d_probe_B: mb.d_probe,
            knn_dist_A: ma.knn_dist,
            knn_dist_B: mb.knn_dist,
            d_border_A: ma.d_border,
            d_border_B: mb.d_border,
            delta_K_band: band,
            stratum_realized: stratum,
            trap_subtype: stratum === "trap" ? trapSubtype(trial, b) : null
          });
        }
      }
    }
    return candidates;
  }

  function strikeCardCountForTrial(trial) {
    if (trial.phase === "practice") return CONFIG.practice_strike_cards;
    if (session?.mode === "B0.5") return CONFIG.b05_strike_cards_per_trial;
    if (session?.mode === "B0.6") return CONFIG.b06_strike_cards_per_trial;
    return session?.mode === "B0" ? CONFIG.b0_strike_cards_per_trial : CONFIG.strike_cards_per_trial;
  }

  function targetStrataForTrial(trial) {
    if (trial.phase === "practice" || session?.mode === "B0") return CONFIG.b0_target_strata;
    if (session?.mode === "B0.5") return CONFIG.b05_target_strata;
    if (session?.mode === "B0.6") return CONFIG.b06_target_strata;
    return CONFIG.target_strata;
  }

  function makeSelectionState() {
    return {
      reuseByStratum: { anchor: new Map(), inference: new Map(), trap: new Map() },
      cellStratum: new Map(),
      globalAReuse: new Map(),
      seenPairs: new Set()
    };
  }

  function stratumCount(selected, stratum) {
    return selected.filter(x => x.stratum_realized === stratum).length;
  }

  function shouldEnforceScoredAReuse() {
    return current?.phase !== "practice" && isFullPilotLikeMode();
  }

  function canUseCandidate(cand, stratum, state) {
    const key = `${cand.A_cell}:${cand.B_cell}`;
    if (state.seenPairs.has(key)) return false;
    if (shouldEnforceScoredAReuse() && (state.globalAReuse.get(cand.A_cell) || 0) >= CONFIG.scored_A_cell_reuse_cap) {
      return false;
    }
    const cap = reuseCapForStratum(stratum);
    for (const cell of [cand.A_cell, cand.B_cell]) {
      const usedStratum = state.cellStratum.get(cell);
      if (usedStratum && usedStratum !== stratum) return false;
      const count = state.reuseByStratum[stratum].get(cell) || 0;
      if (count >= cap) return false;
    }
    return true;
  }

  function addCandidate(selected, cand, stratum, state) {
    const reuse = state.reuseByStratum[stratum];
    const ra = (reuse.get(cand.A_cell) || 0) + 1;
    const rb = (reuse.get(cand.B_cell) || 0) + 1;
    selected.push({ ...cand, stratum_realized: stratum, reuse_A: ra, reuse_B: rb });
    reuse.set(cand.A_cell, ra);
    reuse.set(cand.B_cell, rb);
    state.globalAReuse.set(cand.A_cell, (state.globalAReuse.get(cand.A_cell) || 0) + 1);
    state.cellStratum.set(cand.A_cell, stratum);
    state.cellStratum.set(cand.B_cell, stratum);
    state.seenPairs.add(`${cand.A_cell}:${cand.B_cell}`);
  }

  function k2BlockCoverageCounts(selected, includeTrap = false) {
    const counts = {};
    for (const cand of selected) {
      if (!includeTrap && cand.stratum_realized === "trap") continue;
      const blockId = cand.A_cell_block_id;
      if (blockId === null || blockId === undefined) continue;
      counts[blockId] = (counts[blockId] || 0) + 1;
    }
    return counts;
  }

  function k2BlockCoverageSatisfied(selected) {
    if (current?.condition !== "K2_TWO_FLEETS" || !shouldEnforceScoredAReuse()) return true;
    const expectedBlocks = current.blocks || [];
    if (expectedBlocks.length < 2) return true;
    const counts = k2BlockCoverageCounts(selected, false);
    return expectedBlocks.every(block => (counts[block.block_index] || 0) >= CONFIG.k2_min_A_cells_per_block);
  }

  function selectCardsFromCandidates(candidateMap, rand, targets, bandTargets) {
    const selected = [];
    const state = makeSelectionState();
    const warnings = [];
    const diagnosticWarnings = [];
    const bandCounts = Object.fromEntries(CONFIG.delta_k_bands.map(b => [b.label, 0]));
    const bandShortages = {};
    const leTargets = inferenceLETargetsForTrial(current);
    const leCounts = Object.fromEntries(Object.keys(leTargets).map(k => [k, 0]));
    const leShortages = {};

    function canUseInferenceCandidate(cand, enforceLETarger = true) {
      if (!canUseCandidate(cand, "inference", state)) return false;
      if (!Object.keys(leTargets).length || !enforceLETarger) return true;
      const cls = cand.inference_LE_class || inferenceLEClass(cand.delta_LE);
      if (!(cls in leTargets)) return false;
      return (leCounts[cls] || 0) < leTargets[cls];
    }

    function addInferenceCandidate(cand) {
      addCandidate(selected, cand, "inference", state);
      if (cand.delta_K_band) bandCounts[cand.delta_K_band] = (bandCounts[cand.delta_K_band] || 0) + 1;
      const cls = cand.inference_LE_class || inferenceLEClass(cand.delta_LE);
      if (cls in leCounts) leCounts[cls] += 1;
    }

    const inferencePool = [...candidateMap.inference];
    shuffle(inferencePool, rand);
    if (current?.condition === "K2_TWO_FLEETS" && shouldEnforceScoredAReuse()) {
      for (const block of current.blocks || []) {
        const blockPool = inferencePool.filter(c => c.A_cell_block_id === block.block_index);
        shuffle(blockPool, rand);
        for (const cand of blockPool) {
          if (stratumCount(selected, "inference") >= targets.inference) break;
          const currentCount = k2BlockCoverageCounts(selected, false)[block.block_index] || 0;
          if (currentCount >= CONFIG.k2_min_A_cells_per_block) break;
          if (!canUseInferenceCandidate(cand)) continue;
          addInferenceCandidate(cand);
        }
      }
    }
    for (const band of CONFIG.delta_k_bands) {
      const target = bandTargets[band.label] || 0;
      const pool = inferencePool.filter(c => c.delta_K_band === band.label);
      shuffle(pool, rand);
      for (const cand of pool) {
        if (bandCounts[band.label] >= target) break;
        if (!canUseInferenceCandidate(cand)) continue;
        addInferenceCandidate(cand);
      }
      if (bandCounts[band.label] < Math.max(0, target - CONFIG.inference_band_slack)) {
        bandShortages[band.label] = { got: bandCounts[band.label], target };
      }
    }

    if (stratumCount(selected, "inference") < targets.inference) {
      const before = stratumCount(selected, "inference");
      for (const cand of inferencePool) {
        if (stratumCount(selected, "inference") >= targets.inference) break;
        if (!canUseInferenceCandidate(cand)) continue;
        addInferenceCandidate(cand);
      }
      if (Object.keys(bandTargets).length && stratumCount(selected, "inference") > before) {
        diagnosticWarnings.push("inference_band_borrow_used");
      }
    }

    if (stratumCount(selected, "inference") < targets.inference && Object.keys(leTargets).length) {
      const before = stratumCount(selected, "inference");
      for (const cand of inferencePool) {
        if (stratumCount(selected, "inference") >= targets.inference) break;
        if (!canUseInferenceCandidate(cand, false)) continue;
        addInferenceCandidate(cand);
      }
      if (stratumCount(selected, "inference") > before) {
        warnings.push("inference_LE_balance_borrow_used");
      }
    }

    for (const stratum of ["anchor", "trap"]) {
      const pool = [...candidateMap[stratum]];
      shuffle(pool, rand);
      for (const cand of pool) {
        if (stratumCount(selected, stratum) >= targets[stratum]) break;
        if (!canUseCandidate(cand, stratum, state)) continue;
        addCandidate(selected, cand, stratum, state);
      }
    }
    if (Object.keys(bandShortages).length) {
      diagnosticWarnings.push(`inference_delta_K_band_shortage:${JSON.stringify(bandShortages)}`);
    }
    for (const [cls, target] of Object.entries(leTargets)) {
      if ((leCounts[cls] || 0) < target) leShortages[cls] = { got: leCounts[cls] || 0, target };
    }
    if (Object.keys(leShortages).length) {
      warnings.push(`inference_LE_balance_shortage:${JSON.stringify(leShortages)}`);
    }
    return { selected, state, warnings, diagnosticWarnings, bandCounts, bandTargets, bandShortages, leCounts, leTargets, leShortages };
  }

  function fillBestEffort(trial, selected, state, metrics, posterior, rand, targetCount) {
    const clicked = new Set(trial.click_events.map(e => e.cell_index));
    const alivePool = [];
    const deadPool = [];
    for (let i = 0; i < trial.M; i++) {
      if (clicked.has(i)) continue;
      if (trial.life[i]) alivePool.push(i);
      else deadPool.push(i);
    }
    const any = [];
    for (const a of alivePool) {
      for (const b of deadPool) {
        const key = `${a}:${b}`;
        if (state.seenPairs.has(key)) continue;
        const ma = metrics[a];
        const mb = metrics[b];
        const deltaK = posterior[a] - posterior[b];
        if (deltaK < CONFIG.delta_k_min) continue;
        const deltaLE = ma.LE - mb.LE;
        any.push({
          A_cell: a,
          B_cell: b,
          A_cell_block_id: blockIdForCell(trial, a),
          B_cell_block_id: blockIdForCell(trial, b),
          delta_LE: deltaLE,
          inference_LE_class: inferenceLEClass(deltaLE),
          delta_K: deltaK,
          LE_A: ma.LE,
          LE_B: mb.LE,
          d_probe_A: ma.d_probe,
          d_probe_B: mb.d_probe,
          knn_dist_A: ma.knn_dist,
          knn_dist_B: mb.knn_dist,
        d_border_A: ma.d_border,
        d_border_B: mb.d_border,
        delta_K_band: deltaKBand(deltaK),
        stratum_realized: Math.abs(deltaLE) < 0.5 ? "inference" : (deltaLE >= 0.5 ? "anchor" : "trap"),
        trap_subtype: deltaLE <= -0.5 ? trapSubtype(trial, b) : null,
        _score: deltaK - 0.02 * Math.abs(deltaLE)
        });
      }
    }
    shuffle(any, rand);
    any.sort((a, b) => b._score - a._score);
    for (const cand of any) {
      if (selected.length >= targetCount) break;
      const stratum = cand.stratum_realized;
      if (!canUseCandidate(cand, stratum, state)) continue;
      addCandidate(selected, cand, stratum, state);
    }
  }

  function generateStrikeCards(trial) {
    const rand = makeRng(trial.pair_gen_seed);
    const local = computeLocalEvidence(trial);
    const posteriorResult = estimatePosteriorTarget(trial);
    const targetCount = strikeCardCountForTrial(trial);
    const targets = targetStrataForTrial(trial);
    const bandTargets = inferenceBandTargetsForTrial(trial);
    const primaryFill = new Set(CONFIG.primary_fill_strata || ["anchor", "inference", "trap"]);
    const primaryTarget = Object.entries(targets)
      .filter(([stratum]) => primaryFill.has(stratum))
      .reduce((acc, [, n]) => acc + n, 0);
    const primaryCount = (cards) => cards.filter(c => primaryFill.has(c.stratum_realized)).length;
    const attempts = [
      { matchMult: 1.0, leRelax: 0.0, label: "strict" },
      { matchMult: 1.5, leRelax: 0.0, label: "match_x1.5" },
      { matchMult: 1.5, leRelax: 0.1, label: "match_x1.5_le_relax_0.1" }
    ];
    let best = null;
    let degradation = "none";
    for (const attempt of attempts) {
      const cand = buildCandidatePairs(trial, local.metrics, posteriorResult.posterior, attempt);
      const selected = selectCardsFromCandidates(cand, rand, targets, bandTargets);
      if (!best
        || primaryCount(selected.selected) > primaryCount(best.selected)
        || (primaryCount(selected.selected) === primaryCount(best.selected) && selected.selected.length > best.selected.length)) {
        best = selected;
        degradation = attempt.label;
      }
      const counts = Object.fromEntries(["anchor", "inference", "trap"].map(s => [s, selected.selected.filter(c => c.stratum_realized === s).length]));
      if (primaryCount(selected.selected) >= primaryTarget) {
        best = selected;
        degradation = attempt.label;
        break;
      }
    }
    let selected = best ? best.selected : [];
    const state = best ? best.state : makeSelectionState();
    if (selected.length < targetCount) {
      fillBestEffort(trial, selected, state, local.metrics, posteriorResult.posterior, rand, targetCount);
      degradation = `${degradation}_best_effort`;
    }
    selected = selected.slice(0, targetCount);
    shuffle(selected, rand);
    const cards = selected.map((cand, cardIndex) => {
      const aliveLeft = rand() < 0.5;
      const left = aliveLeft ? cand.A_cell : cand.B_cell;
      const right = aliveLeft ? cand.B_cell : cand.A_cell;
      return {
        card_index: cardIndex,
        A_cell: cand.A_cell,
        B_cell: cand.B_cell,
        A_cell_block_id: cand.A_cell_block_id ?? blockIdForCell(trial, cand.A_cell),
        B_cell_block_id: cand.B_cell_block_id ?? blockIdForCell(trial, cand.B_cell),
        A_true_label: 1,
        B_true_label: 0,
        display_left_cell: left,
        display_right_cell: right,
        alive_display_side: aliveLeft ? "left" : "right",
        LE_A: cand.LE_A,
        LE_B: cand.LE_B,
        delta_LE: cand.delta_LE,
        inference_LE_class: cand.inference_LE_class || inferenceLEClass(cand.delta_LE),
        delta_K: cand.delta_K,
        delta_K_band: cand.delta_K_band,
        d_probe_A: cand.d_probe_A,
        d_probe_B: cand.d_probe_B,
        knn_dist_A: cand.knn_dist_A,
        knn_dist_B: cand.knn_dist_B,
        d_border_A: cand.d_border_A,
        d_border_B: cand.d_border_B,
        stratum_realized: cand.stratum_realized,
        trap_subtype: cand.trap_subtype,
        reuse_A: cand.reuse_A,
        reuse_B: cand.reuse_B,
        chosen_side: null,
        chosen_cell: null,
        correct: null,
        response_time_ms: null
      };
    });
    const stratumCounts = {};
    for (const c of cards) stratumCounts[c.stratum_realized] = (stratumCounts[c.stratum_realized] || 0) + 1;
    const nonTrapCards = cards.filter(c => c.stratum_realized !== "trap");
    const k2BlockCounts = {};
    for (const c of nonTrapCards) {
      if (c.A_cell_block_id === null || c.A_cell_block_id === undefined) continue;
      k2BlockCounts[c.A_cell_block_id] = (k2BlockCounts[c.A_cell_block_id] || 0) + 1;
    }
    const k2BlockCoverageRequired = trial.condition === "K2_TWO_FLEETS" && trial.phase !== "practice" && isFullPilotLikeMode();
    const missedBlockStrikeFlag = k2BlockCoverageRequired
      ? (trial.blocks || []).some(block => (k2BlockCounts[block.block_index] || 0) < CONFIG.k2_min_A_cells_per_block)
      : false;
    const AReuseCounts = {};
    for (const c of cards) AReuseCounts[c.A_cell] = (AReuseCounts[c.A_cell] || 0) + 1;
    const maxAReuse = Object.values(AReuseCounts).reduce((a, b) => Math.max(a, b), 0);
    const missingStrata = {};
    const diagnosticUnderfill = {};
    for (const s of ["anchor", "inference", "trap"]) {
      const got = stratumCounts[s] || 0;
      if (got < targets[s]) {
        if (primaryFill.has(s)) missingStrata[s] = { got, target: targets[s] };
        else diagnosticUnderfill[s] = { got, target: targets[s] };
      }
    }
    const warnings = [];
    const diagnosticWarnings = [];
    if (best?.warnings?.length) warnings.push(...best.warnings);
    if (best?.diagnosticWarnings?.length) diagnosticWarnings.push(...best.diagnosticWarnings);
    if (degradation.includes("best_effort")) {
      const hasPrimaryShortage = Object.keys(missingStrata).length > 0;
      (hasPrimaryShortage ? warnings : diagnosticWarnings).push(`pair_generator_best_effort:${degradation}`);
    }
    if (cards.length < targetCount) {
      diagnosticWarnings.push(`strike_card_shortage:${cards.length}/${targetCount}`);
    }
    if (Object.keys(missingStrata).length) {
      warnings.push(`stratum_shortage:${JSON.stringify(missingStrata)}`);
    }
    if (missedBlockStrikeFlag) {
      warnings.push(`k2_block_coverage_shortage:${JSON.stringify(k2BlockCounts)}`);
    }
    if (Object.keys(diagnosticUnderfill).length) {
      diagnosticWarnings.push(`diagnostic_stratum_underfill:${JSON.stringify(diagnosticUnderfill)}`);
    }
    return {
      cards,
      meta: {
        pair_gen_degraded: warnings.length > 0,
        pair_gen_degradation: degradation,
        pair_gen_relaxation_used: degradation !== "strict" && degradation !== "none",
        warnings,
        diagnostic_warnings: diagnosticWarnings,
        missing_strata: missingStrata,
        diagnostic_underfill: diagnosticUnderfill,
        k2_block_coverage: {
          required: k2BlockCoverageRequired,
          min_A_cells_per_block: CONFIG.k2_min_A_cells_per_block,
          nontrap_A_cells_per_block: k2BlockCounts,
          missed_block_strike_flag: missedBlockStrikeFlag
        },
        nontrap_card_count: nonTrapCards.length,
        A_cell_reuse_max: maxAReuse,
        chosen_cell_reuse_max_expected: maxAReuse,
        A_cell_reuse_relaxed: false,
        structural_resolvability_unchecked: false,
        agent_posterior_low_ess: posteriorResult.low_ess,
        posterior_method: posteriorResult.method,
        exact_config_count: posteriorResult.exact_config_count,
        posterior_samples: posteriorResult.samples,
        posterior_ess: posteriorResult.posterior_ess,
        posterior_concentration: posteriorResult.posterior_concentration,
        posterior_min_ess: posteriorResult.posterior_min_ess ?? null,
        posterior_resample_count: posteriorResult.posterior_resample_count ?? null,
        posterior_unique_particles: posteriorResult.posterior_unique_particles ?? null,
        LE_sparse_trial: local.LE_sparse_trial,
        stratum_counts: stratumCounts,
        target_strata: targets,
        delta_K_band_targets: bandTargets,
        delta_K_band_counts: best?.bandCounts || {},
        delta_K_band_shortages: best?.bandShortages || {},
        inference_LE_targets: best?.leTargets || {},
        inference_LE_counts: best?.leCounts || {},
        inference_LE_shortages: best?.leShortages || {},
        inference_LE_threshold: CONFIG.inference_le_threshold,
        reuse_cap: CONFIG.reuse_cap,
        requested_strike_cards: targetCount
      }
    };
  }

  function enterStrikePhase() {
    current.phase_state = "response";
    current.current_strike_index = 0;
    current.response_started_at = new Date().toISOString();
    current.response_started_ms = nowMs() - current.started_ms;
    document.getElementById("clickSide").classList.add("hidden");
    document.getElementById("responseSide").classList.remove("hidden");
    const generated = generateStrikeCards(current);
    current.strike_cards = generated.cards;
    current.strike_generation = generated.meta;
    if (generated.meta.warnings && generated.meta.warnings.length) {
      console.warn("WILD0 strike generator warnings", generated.meta);
    }
    renderStrikePanel();
    updateTaskChrome();
  }

  function renderStrikePanel() {
    const list = document.getElementById("probeList");
    const total = current.strike_cards.length;
    const idx = Math.min(current.current_strike_index || 0, Math.max(0, total - 1));
    const card = current.strike_cards[idx] || null;
    const done = current.strike_cards.filter(c => c.chosen_cell !== null).length;
    const allDone = done >= total && total > 0;
    const dots = current.strike_cards.map((c, i) => {
      const classes = ["strike-dot"];
      if (c.chosen_cell !== null) classes.push("done");
      if (i === idx && done < total) classes.push("current");
      return `<span class="${classes.join(" ")}" title="Strike ${i + 1}"></span>`;
    }).join("");
    const warning = (session.mode === "B0" || session.mode === "B0.5") && current.strike_generation?.warnings?.length
      ? `<div class="notice warn small">Generator warning recorded for this trial. This should be reviewed before using scored data.</div>`
      : "";
    list.innerHTML = "";
    const row = document.createElement("div");
    row.className = "strike-status";
    row.innerHTML = `
      <div>
        <strong>${allDone ? `Review strike ${idx + 1} of ${total}` : `Strike ${idx + 1} of ${total}`}</strong>
        <div class="muted small">${allDone
          ? "All decisions are made. You can submit, or click a highlighted sector to change this one."
          : "Click one of the two bright sectors directly on the board."}</div>
      </div>
      <div class="dot-row">${dots}</div>
    `;
    list.appendChild(row);
    if (warning) {
      const warn = document.createElement("div");
      warn.innerHTML = warning;
      list.appendChild(warn.firstElementChild);
    }
    document.getElementById("previousStrikeBtn").disabled = idx <= 0;
    validateStrikeReadout();
  }

  function chooseStrikeCell(cellIndex) {
    const cardIndex = current.current_strike_index || 0;
    const card = current.strike_cards[cardIndex];
    if (!card) return;
    if (cellIndex !== card.display_left_cell && cellIndex !== card.display_right_cell) return;
    const side = cellIndex === card.display_left_cell ? "left" : "right";
    card.chosen_side = side;
    card.chosen_cell = cellIndex;
    card.correct = card.chosen_cell === card.A_cell;
    card.response_time_ms = nowMs() - current.started_ms;
    current.response_choice_events = current.response_choice_events.filter(e => e.card_index !== cardIndex);
    current.response_choice_events.push({
      card_index: cardIndex,
      chosen_side: side,
      chosen_cell: card.chosen_cell,
      correct: card.correct,
      timestamp_ms: card.response_time_ms
    });
    if (current.current_strike_index < current.strike_cards.length - 1) {
      current.current_strike_index += 1;
    }
    renderStrikePanel();
    renderBoard();
    autosaveSession();
  }

  function previousStrike() {
    if (!current || current.phase_state !== "response") return;
    current.current_strike_index = Math.max(0, (current.current_strike_index || 0) - 1);
    renderStrikePanel();
    renderBoard();
    validateStrikeReadout();
  }

  function validateStrikeReadout() {
    const complete = current.strike_cards.length > 0 && current.strike_cards.every(c => c.chosen_side);
    document.getElementById("submitTrialBtn").disabled = !complete;
  }

  function coverageEntropy(events, cols, rows) {
    if (!events.length) return null;
    const bins = [0, 0, 0, 0];
    for (const e of events) {
      const xSide = e.x < cols / 2 ? 0 : 1;
      const ySide = e.y < rows / 2 ? 0 : 1;
      bins[ySide * 2 + xSide] += 1;
    }
    const total = events.length;
    let ent = 0;
    for (const b of bins) {
      if (b) {
        const p = b / total;
        ent -= p * Math.log(p);
      }
    }
    return ent / Math.log(4);
  }

  function spanGrid(events) {
    const xs = events.map(e => e.x);
    const ys = events.map(e => e.y);
    return Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
  }

  function meanFinite(xs) {
    const vals = xs.filter(x => Number.isFinite(x));
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  }

  function medianFinite(xs) {
    const vals = xs.filter(x => Number.isFinite(x)).sort((a, b) => a - b);
    if (!vals.length) return null;
    const mid = Math.floor(vals.length / 2);
    return vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
  }

  function difficultySummaryForCards(cards) {
    const out = {};
    for (const stratum of ["anchor", "inference", "trap"]) {
      const group = cards.filter(c => c.stratum_realized === stratum);
      out[stratum] = {
        n: group.length,
        mean_delta_K: meanFinite(group.map(c => c.delta_K)),
        median_delta_K: medianFinite(group.map(c => c.delta_K)),
        mean_delta_LE: meanFinite(group.map(c => c.delta_LE)),
        median_delta_LE: medianFinite(group.map(c => c.delta_LE)),
        mean_abs_delta_LE: meanFinite(group.map(c => Math.abs(c.delta_LE))),
        mean_d_probe_A: meanFinite(group.map(c => c.d_probe_A)),
        mean_d_probe_B: meanFinite(group.map(c => c.d_probe_B)),
        mean_d_border_A: meanFinite(group.map(c => c.d_border_A)),
        mean_d_border_B: meanFinite(group.map(c => c.d_border_B))
      };
    }
    return out;
  }

  function cardAccuracy(cards) {
    return cards.length ? cards.filter(c => c.correct).length / cards.length : null;
  }

  function inferenceConflictMetrics(cards) {
    const inference = cards.filter(c => c.stratum_realized === "inference");
    const supporting = inference.filter(c => c.delta_LE >= CONFIG.inference_le_threshold);
    const conflicting = inference.filter(c => c.delta_LE <= -CONFIG.inference_le_threshold);
    const neutral = inference.filter(c => Math.abs(c.delta_LE) < CONFIG.inference_le_threshold);
    return {
      support_n: supporting.length,
      conflict_n: conflicting.length,
      neutral_n: neutral.length,
      support_accuracy: cardAccuracy(supporting),
      override_accuracy: cardAccuracy(conflicting),
      neutral_accuracy: cardAccuracy(neutral),
      threshold: CONFIG.inference_le_threshold
    };
  }

  function deriveTrialMetrics(trial) {
    const total = trial.click_events.length;
    const unique = new Set(trial.click_events.map(e => e.cell_index)).size;
    const repeats = total - unique;
    const steps = [];
    for (let i = 1; i < trial.click_events.length; i++) {
      const a = trial.click_events[i - 1];
      const b = trial.click_events[i];
      steps.push(Math.hypot(a.x - b.x, a.y - b.y));
    }
    const diag = Math.hypot(trial.grid_cols - 1, trial.grid_rows - 1);
    const localThreshold = 0.15 * diag;
    const meanStep = steps.length ? steps.reduce((a, b) => a + b, 0) / steps.length : 0;
    const localFraction = steps.length ? steps.filter(x => x <= localThreshold).length / steps.length : null;
    const first10 = trial.click_events.slice(0, 10);
    const clickedAlive = trial.click_events.filter(e => e.true_bit === 1).length;
    const signalTruth = trial.click_events.filter(e => Boolean(e.signal_matches_truth ?? e.correct)).length;
    const positiveSignals = trial.click_events.filter(e => e.revealed_signal === 1);
    const negativeSignals = trial.click_events.filter(e => e.revealed_signal === 0);
    const positiveAlive = positiveSignals.filter(e => e.true_bit === 1).length;
    const negativeAlive = negativeSignals.filter(e => e.true_bit === 1).length;
    const byStratum = {};
    for (const stratum of ["anchor", "inference", "trap"]) {
      const cards = trial.strike_cards.filter(c => c.stratum_realized === stratum);
      byStratum[stratum] = {
        n: cards.length,
        accuracy: cards.length ? cards.filter(c => c.correct).length / cards.length : null
      };
    }
    const visibleScoreCards = trial.strike_cards.filter(c => c.stratum_realized !== "trap");
    const visibleCorrect = visibleScoreCards.filter(c => c.correct).length;
    const allCorrect = trial.strike_cards.filter(c => c.correct).length;
    const requiredNonTrap = (trial.strike_generation?.target_strata?.anchor || 0) + (trial.strike_generation?.target_strata?.inference || 0);
    const nonTrapCardCount = trial.strike_generation?.nontrap_card_count ?? visibleScoreCards.length;
    const missedBlockStrikeFlag = Boolean(trial.strike_generation?.k2_block_coverage?.missed_block_strike_flag);
    const extremeDeltaKImbalance = false;
    const interpretableForKComparison = !trial.strike_generation?.pair_gen_degraded
      && !missedBlockStrikeFlag
      && !extremeDeltaKImbalance
      && nonTrapCardCount >= requiredNonTrap;
    return {
      score_points: visibleCorrect * 10,
      score_max: visibleScoreCards.length * 10,
      visible_score_points: visibleCorrect * 10,
      visible_score_max: visibleScoreCards.length * 10,
      all_score_points: allCorrect * 10,
      all_score_max: trial.strike_cards.length * 10,
      strike_accuracy: trial.strike_cards.length ? trial.strike_cards.filter(c => c.correct).length / trial.strike_cards.length : null,
      visible_strike_accuracy: visibleScoreCards.length ? visibleCorrect / visibleScoreCards.length : null,
      per_stratum_accuracy: byStratum,
      primary_inference_accuracy: byStratum.inference.accuracy,
      difficulty_by_stratum: difficultySummaryForCards(trial.strike_cards),
      inference_conflict_metrics: inferenceConflictMetrics(trial.strike_cards),
      missed_block_strike_flag: missedBlockStrikeFlag,
      nontrap_card_count: nonTrapCardCount,
      required_nontrap_card_count: requiredNonTrap,
      extreme_delta_K_imbalance: extremeDeltaKImbalance,
      interpretable_for_K_comparison: interpretableForKComparison,
      A_cell_reuse_max: trial.strike_generation?.A_cell_reuse_max ?? null,
      chosen_cell_reuse_max_expected: trial.strike_generation?.chosen_cell_reuse_max_expected ?? null,
      n_clicks: total,
      unique_clicks: unique,
      repeat_clicks: repeats,
      repeat_fraction: total ? repeats / total : 0,
      early_finish_used: Boolean(trial.early_finish_used),
      trial_duration_click_ms: trial.response_started_ms ?? null,
      trial_duration_strike_ms: trial.finished_ms && trial.response_started_ms !== null && trial.response_started_ms !== undefined
        ? trial.finished_ms - trial.started_ms - trial.response_started_ms
        : null,
      mean_step_distance_grid: meanStep,
      local_step_fraction: localFraction,
      first10_unique_clicks: first10.length ? new Set(first10.map(e => e.cell_index)).size : null,
      first10_span_grid: first10.length ? spanGrid(first10) : null,
      coverage_entropy: coverageEntropy(trial.click_events, trial.grid_cols, trial.grid_rows),
      signal_truth_rate: total ? signalTruth / total : null,
      clicked_alive_rate: total ? clickedAlive / total : null,
      positive_signal_rate: total ? positiveSignals.length / total : null,
      positive_signal_ppv_realized: positiveSignals.length ? positiveAlive / positiveSignals.length : null,
      negative_signal_fn_rate_realized: negativeSignals.length ? negativeAlive / negativeSignals.length : null,
      boundary_probing_index: boundaryProbingIndex(trial)
    };
  }

  function boundaryProbingIndex(trial) {
    if (!trial.click_events.length) return null;
    const near = trial.click_events.filter(e => distanceToFleetBorder(trial, e.cell_index) <= 2).length;
    return near / trial.click_events.length;
  }

  function submitTrial() {
    if (!current || current.phase_state !== "response") return;
    current.finished_at = new Date().toISOString();
    current.finished_ms = nowMs();
    current.pair_gen_degraded = Boolean(current.strike_generation.pair_gen_degraded);
    current.structural_resolvability_unchecked = Boolean(current.strike_generation.structural_resolvability_unchecked);
    current.LE_sparse_trial = Boolean(current.strike_generation.LE_sparse_trial);
    current.agent_posterior_low_ess = Boolean(current.strike_generation.agent_posterior_low_ess);
    current.missed_block_strike_flag = Boolean(current.strike_generation.k2_block_coverage?.missed_block_strike_flag);
    current.truth_reveal_after_trial = current.phase === "practice";
    current.derived = deriveTrialMetrics(current);
    const exportTrial = { ...current };
    delete exportTrial.rand;
    delete exportTrial.phase_state;
    session.trials.push(exportTrial);
    session.current_plan_index += 1;
    autosaveSession();
    if (session.upload_url) uploadSessionData(true, "trial_checkpoint");
    const msg = current.phase === "practice"
      ? `Practice feedback: ${qualitativeFeedback(current)}. Diagnostic stress checks are not included.`
      : `Round feedback: ${qualitativeFeedback(current)}. Diagnostic stress checks are not included.`;
    if (current.phase === "practice") {
      showTrialReveal(exportTrial, msg);
    } else {
      showRoundScore(exportTrial, msg);
    }
  }

  function qualitativeFeedback(trial) {
    const acc = trial?.derived?.visible_strike_accuracy;
    if (acc === null || acc === undefined || Number.isNaN(acc)) return "round complete";
    if (acc >= 0.75) return "strong reconnaissance";
    if (acc >= 0.5) return "steady reconnaissance";
    return "keep training";
  }

  function renderTruthReveal(trial) {
    const checked = new Set((trial.click_events || []).map(e => e.cell_index));
    const strikeChoices = new Map();
    for (const card of trial.strike_cards || []) {
      if (card.chosen_cell !== null && card.chosen_cell !== undefined) {
        strikeChoices.set(card.chosen_cell, Boolean(card.correct));
      }
    }
    const cells = [];
    for (let i = 0; i < trial.M; i++) {
      const cls = ["reveal-cell"];
      if (trial.life[i]) cls.push("target");
      if (checked.has(i)) cls.push("checked");
      if (strikeChoices.has(i)) cls.push("strike-choice", strikeChoices.get(i) ? "correct" : "incorrect");
      cells.push(`<span class="${cls.join(" ")}" title="Sector ${i + 1}${trial.life[i] ? ", target" : ", empty"}${checked.has(i) ? ", sonar checked" : ""}${strikeChoices.has(i) ? ", strike choice" : ""}"></span>`);
    }
    return `
      <div class="reveal-wrap">
        <div class="reveal-board" style="grid-template-columns: repeat(${trial.grid_cols}, minmax(0, 1fr));">
          ${cells.join("")}
        </div>
        <div class="reveal-legend">
          <span class="reveal-key"><span class="target"></span>true target</span>
          <span class="reveal-key"><span class="checked"></span>your sonar check</span>
          <span class="reveal-key"><span class="strike-choice"></span>your strike choice</span>
        </div>
      </div>
    `;
  }

  function continueAfterReveal(trial) {
    if (trial.phase === "practice") {
      startCurrentTrial();
    } else if (shouldShowBreak()) {
      showBreak();
    } else {
      startCurrentTrial();
    }
  }

  function showTrialReveal(trial, text) {
    document.getElementById("taskLayout").classList.add("hidden");
    const breakPanel = document.getElementById("breakPanel");
    breakPanel.classList.remove("hidden");
    breakPanel.innerHTML = `
      <h2>${trial.phase === "practice" ? "Practice complete" : "Round complete"}</h2>
      <p class="mission-score">${text}</p>
      <h3>True layout</h3>
      ${renderTruthReveal(trial)}
      <p class="muted">Remember: a single sonar clue is noisy. Use the named one-rectangle or two-rectangle structure when choosing strike sectors.</p>
      <button id="revealNextBtn">Continue</button>
    `;
    window.scrollTo({ top: 0, behavior: "instant" });
    document.getElementById("revealNextBtn").addEventListener("click", () => continueAfterReveal(trial));
  }

  function showRoundScore(trial, text) {
    document.getElementById("taskLayout").classList.add("hidden");
    const breakPanel = document.getElementById("breakPanel");
    breakPanel.classList.remove("hidden");
    breakPanel.innerHTML = `
      <h2>Round complete</h2>
      <p class="mission-score">${text}</p>
      <p class="muted">The true map is kept hidden during scored rounds so later rounds stay fair. All scored maps will be shown together at the end.</p>
      <button id="scoreNextBtn">Continue</button>
    `;
    window.scrollTo({ top: 0, behavior: "instant" });
    document.getElementById("scoreNextBtn").addEventListener("click", () => continueAfterReveal(trial));
  }

  function shouldShowBreak() {
    const scoredDone = session.trials.filter(t => t.phase === "scored").length;
    const scoredTotal = session.plan.filter(t => t.phase === "scored").length;
    return scoredDone > 0 && scoredDone === Math.floor(scoredTotal / 2);
  }

  function showBreak() {
    document.getElementById("taskLayout").classList.add("hidden");
    const breakPanel = document.getElementById("breakPanel");
    breakPanel.classList.remove("hidden");
    breakPanel.innerHTML = `
      <h2>Short pause</h2>
      <p class="muted">You are halfway through the scored missions. Take a moment if you want.</p>
      <button id="continueAfterBreakBtn2">Continue</button>
    `;
    document.getElementById("continueAfterBreakBtn2").addEventListener("click", () => startCurrentTrial());
  }

  function finishSession() {
    session.finished_at = new Date().toISOString();
    show("finishScreen");
    document.getElementById("downloadBtn").disabled = false;
    document.getElementById("finishMessage").textContent = "Thank you. The task is complete. Please answer the final question below.";
    renderFinalReview();
    prepareFinishControls();
    autosaveSession();
    if (session.upload_url) uploadSessionData(true, "task_finished");
  }

  function prepareFinishControls() {
    const uploadNotice = document.getElementById("uploadNotice");
    const uploadRetryBtn = document.getElementById("uploadRetryBtn");
    const completionBtn = document.getElementById("completionBtn");
    const radios = document.querySelectorAll("input[name='perceivedEase']");
    for (const radio of radios) {
      radio.checked = session?.perceived_ease === radio.value;
      radio.addEventListener("change", onPerceivedEaseChange);
    }
    uploadRetryBtn.classList.toggle("hidden", !session?.upload_url);
    uploadRetryBtn.addEventListener("click", () => uploadSessionData(true, "manual_retry"));
    if (session?.upload_url) {
      uploadNotice.textContent = "This hosted build uploads session JSON automatically during the task and again after the final question. You can still download a local copy.";
    } else {
      uploadNotice.textContent = "This public static build has no upload endpoint configured. Download the JSON file and keep it with the study records.";
    }
    if (session?.completion_url) {
      completionBtn.classList.remove("hidden");
    }
    updateUploadStatus();
    updateCompletionButton();
    updateDownloadButtons();
  }

  function onPerceivedEaseChange(event) {
    if (!session) return;
    session.perceived_ease = event.target.value;
    session.perceived_ease_at = new Date().toISOString();
    autosaveSession();
    updateUploadStatus();
    updateDownloadButtons();
    if (session.upload_url) uploadSessionData(true, "final_question");
  }

  function updateDownloadButtons() {
    const disabled = Boolean(session?.finished_at && !session?.perceived_ease);
    for (const id of ["downloadBtn", "downloadFinalBtn"]) {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = disabled;
    }
  }

  function updateCompletionButton() {
    const completionBtn = document.getElementById("completionBtn");
    if (!session?.completion_url) {
      completionBtn.classList.add("hidden");
      completionBtn.disabled = true;
      return;
    }
    completionBtn.classList.remove("hidden");
    completionBtn.disabled = !(session.upload_url && hasUploaded && session.perceived_ease);
  }

  function updateUploadStatus(message = null, cls = "") {
    const status = document.getElementById("uploadStatus");
    if (!status || !session) return;
    status.className = `upload-status${cls ? ` ${cls}` : ""}`;
    if (message) {
      status.textContent = message;
      return;
    }
    if (!session.upload_url) {
      status.textContent = session.perceived_ease
        ? "Final question saved locally. Download the JSON to keep this session."
        : "Please answer the final question, then download the JSON to keep this session.";
      return;
    }
    if (session.upload_status === "succeeded") {
      status.classList.add("ok");
      status.textContent = session.perceived_ease
        ? "Upload succeeded. You may return to Prolific if this is a hosted session."
        : "Task data uploaded. Please answer the final question to complete the session.";
    } else if (session.upload_status === "failed") {
      status.classList.add("warn");
      status.textContent = "Upload failed. Please retry before returning to Prolific.";
    } else if (session.upload_status === "uploading") {
      status.textContent = "Uploading session data...";
    } else {
      status.textContent = "Automatic upload is configured.";
    }
  }

  async function uploadSessionData(force = false, reason = "manual") {
    if (!session?.upload_url || uploadInFlight) return;
    if (hasUploaded && !force) return;
    uploadInFlight = true;
    lastUploadStartedAt = new Date().toISOString();
    session.upload_status = "uploading";
    session.last_upload_reason = reason;
    session.last_upload_started_at = lastUploadStartedAt;
    updateUploadStatus();
    autosaveSession();
    try {
      const response = await fetch(session.upload_url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(exportSession())
      });
      if (!response.ok) throw new Error(`Upload failed with status ${response.status}`);
      hasUploaded = true;
      session.upload_status = "succeeded";
      session.uploaded_at = new Date().toISOString();
      session.upload_response_status = response.status;
      session.upload_response_reason = reason;
      updateUploadStatus();
      updateCompletionButton();
      autosaveSession();
    } catch (err) {
      console.warn("WILD0 upload failed", err);
      hasUploaded = false;
      session.upload_status = "failed";
      session.upload_error = String(err && err.message ? err.message : err);
      updateUploadStatus();
      updateCompletionButton();
      autosaveSession();
    } finally {
      uploadInFlight = false;
    }
  }

  function renderFinalReview() {
    const target = document.getElementById("finalReview");
    if (!target || !session) return;
    const scored = session.trials.filter(t => t.phase === "scored");
    if (!scored.length) {
      target.innerHTML = `<p class="muted">No scored rounds were completed.</p>`;
      return;
    }
    target.innerHTML = scored.map((trial, i) => `
      <details class="panel" ${i === 0 ? "open" : ""}>
        <summary><strong>Scored round ${i + 1}</strong> · ${conditionLabel(trial.condition)} · M=${trial.M} · ${qualitativeFeedback(trial)}</summary>
        ${renderTruthReveal(trial)}
      </details>
    `).join("");
  }

  function summarizeSession() {
    if (!session) return {};
    const scored = session.trials.filter(t => t.phase === "scored");
    const byCell = {};
    const overrideByCell = {};
    const supportByCell = {};
    for (const t of scored) {
      const key = `${t.condition}_M${t.M}`;
      byCell[key] ||= [];
      byCell[key].push(t.derived.primary_inference_accuracy);
      const conflict = t.derived.inference_conflict_metrics || {};
      if (conflict.override_accuracy !== null && conflict.override_accuracy !== undefined) {
        overrideByCell[key] ||= [];
        overrideByCell[key].push(conflict.override_accuracy);
      }
      if (conflict.support_accuracy !== null && conflict.support_accuracy !== undefined) {
        supportByCell[key] ||= [];
        supportByCell[key].push(conflict.support_accuracy);
      }
    }
    const means = {};
    for (const [k, vals] of Object.entries(byCell)) {
      means[k] = vals.reduce((a, b) => a + b, 0) / vals.length;
    }
    const overrideMeans = {};
    for (const [k, vals] of Object.entries(overrideByCell)) {
      overrideMeans[k] = vals.reduce((a, b) => a + b, 0) / vals.length;
    }
    const supportMeans = {};
    for (const [k, vals] of Object.entries(supportByCell)) {
      supportMeans[k] = vals.reduce((a, b) => a + b, 0) / vals.length;
    }
    const scoredInterpretable = scored.filter(t => t.derived.interpretable_for_K_comparison);
    const rawInferenceMeans = {};
    const rawInferenceNs = {};
    const interpretableInferenceMeans = {};
    const interpretableInferenceNs = {};
    const rawSupportMeans = {};
    const rawOverrideMeans = {};
    const rawTrapMeans = {};
    const interpretableSupportMeans = {};
    const interpretableOverrideMeans = {};
    const interpretableTrapMeans = {};

    function addMean(map, nMap, key, value) {
      if (value === null || value === undefined || Number.isNaN(value)) return;
      map[key] ||= [];
      map[key].push(value);
      if (nMap) nMap[key] = (nMap[key] || 0) + 1;
    }

    function finalizeMeanMap(map) {
      const out = {};
      for (const [key, vals] of Object.entries(map)) {
        out[key] = vals.reduce((a, b) => a + b, 0) / vals.length;
      }
      return out;
    }

    for (const t of scored) {
      const key = `${t.condition}_M${t.M}`;
      const conflict = t.derived.inference_conflict_metrics || {};
      addMean(rawInferenceMeans, rawInferenceNs, key, t.derived.primary_inference_accuracy);
      addMean(rawSupportMeans, null, key, conflict.support_accuracy);
      addMean(rawOverrideMeans, null, key, conflict.override_accuracy);
      addMean(rawTrapMeans, null, key, t.derived.per_stratum_accuracy?.trap?.accuracy);
    }
    for (const t of scoredInterpretable) {
      const key = `${t.condition}_M${t.M}`;
      const conflict = t.derived.inference_conflict_metrics || {};
      addMean(interpretableInferenceMeans, interpretableInferenceNs, key, t.derived.primary_inference_accuracy);
      addMean(interpretableSupportMeans, null, key, conflict.support_accuracy);
      addMean(interpretableOverrideMeans, null, key, conflict.override_accuracy);
      addMean(interpretableTrapMeans, null, key, t.derived.per_stratum_accuracy?.trap?.accuracy);
    }
    return {
      n_trials_total: session.trials.length,
      n_scored_trials: scored.length,
      perceived_ease: session.perceived_ease || null,
      upload_status: session.upload_status || null,
      mean_inference_accuracy_by_condition_M: means,
      mean_override_accuracy_by_condition_M: overrideMeans,
      mean_support_accuracy_by_condition_M: supportMeans,
      raw_mean_inference_accuracy_by_condition_M: finalizeMeanMap(rawInferenceMeans),
      raw_n_by_condition_M: rawInferenceNs,
      interpretable_mean_inference_accuracy_by_condition_M: finalizeMeanMap(interpretableInferenceMeans),
      interpretable_n_by_condition_M: interpretableInferenceNs,
      raw_support_accuracy_by_condition_M: finalizeMeanMap(rawSupportMeans),
      raw_override_accuracy_by_condition_M: finalizeMeanMap(rawOverrideMeans),
      raw_trap_accuracy_by_condition_M: finalizeMeanMap(rawTrapMeans),
      interpretable_support_accuracy_by_condition_M: finalizeMeanMap(interpretableSupportMeans),
      interpretable_override_accuracy_by_condition_M: finalizeMeanMap(interpretableOverrideMeans),
      interpretable_trap_accuracy_by_condition_M: finalizeMeanMap(interpretableTrapMeans),
      interpretable_for_K_comparison_fraction: scored.length
        ? scored.filter(t => t.derived.interpretable_for_K_comparison).length / scored.length
        : null,
      missed_block_strike_trials: scored.filter(t => t.derived.missed_block_strike_flag).length,
      mean_repeat_fraction: scored.length ? scored.reduce((a, t) => a + t.derived.repeat_fraction, 0) / scored.length : null,
      mean_unique_clicks: scored.length ? scored.reduce((a, t) => a + t.derived.unique_clicks, 0) / scored.length : null
    };
  }

  function exportSession() {
    if (!session) return {};
    let inProgress = null;
    if (current && !current.finished_at && session.current_plan_index === current.plan_index) {
      inProgress = { ...current };
      delete inProgress.rand;
    }
    return {
      ...session,
      exported_at: new Date().toISOString(),
      in_progress_trial: inProgress,
      summary: summarizeSession()
    };
  }

  function beaconUpload(reason = "beforeunload") {
    if (!session?.upload_url || !navigator.sendBeacon) return false;
    try {
      session.last_upload_reason = reason;
      session.last_upload_started_at = new Date().toISOString();
      const payload = JSON.stringify(exportSession());
      const blob = new Blob([payload], { type: "application/json" });
      return navigator.sendBeacon(session.upload_url, blob);
    } catch (err) {
      console.warn("WILD0 beacon upload failed", err);
      return false;
    }
  }

  function autosaveSession() {
    if (!session || !session.autosave_key) return;
    try {
      localStorage.setItem(session.autosave_key, JSON.stringify(exportSession()));
      localStorage.setItem("wild0_b1_sonar_last_autosave_key", session.autosave_key);
    } catch (err) {
      console.warn("WILD0 autosave failed", err);
    }
  }

  function latestAutosave() {
    try {
      const key = localStorage.getItem("wild0_b1_sonar_last_autosave_key");
      if (!key) return null;
      const raw = localStorage.getItem(key);
      return raw ? { key, raw } : null;
    } catch (err) {
      return null;
    }
  }

  function updateRecoverButton() {
    const btn = document.getElementById("recoverBtn");
    btn.classList.toggle("hidden", !latestAutosave());
  }

  function downloadRecoveredSession() {
    const saved = latestAutosave();
    if (!saved) return;
    const blob = new Blob([saved.raw], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wild0_b1_sonar_recovered_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function downloadJson() {
    if (!session) return;
    if (session.finished_at && !session.perceived_ease) {
      updateUploadStatus("Please answer the final question before downloading the completed session.", "warn");
      return;
    }
    const payload = exportSession();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const safeId = String(session.participant_id || "anonymous").replace(/[^a-zA-Z0-9_-]+/g, "_");
    const a = document.createElement("a");
    a.href = url;
    a.download = `wild0_b1_sonar_${safeId}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    hasDownloaded = true;
    session.downloaded_at = new Date().toISOString();
    autosaveSession();
    updateCompletionButton();
  }

  function updateConsentButton() {
    const ok = document.getElementById("adultCheck").checked && document.getElementById("consentCheck").checked;
    document.getElementById("beginTutorialBtn").disabled = !ok;
  }

  function showSummary() {
    const out = document.getElementById("summaryOut");
    out.classList.toggle("hidden");
    out.textContent = JSON.stringify(summarizeSession(), null, 2);
  }

  function goCompletion() {
    if (session && session.completion_url && session.upload_url && hasUploaded) window.location.href = session.completion_url;
  }

  function hydrateFromUrl() {
    const params = qs();
    const pid = params.get("PROLIFIC_PID") || params.get("participant") || "";
    if (pid) document.getElementById("participantId").value = pid;
    const mode = params.get("mode");
    if (mode && ["B0", "B0.5", "B0.6", "B1"].includes(mode.toUpperCase())) {
      document.getElementById("taskMode").value = mode.toUpperCase();
    }
    const hasUploadEndpoint = Boolean(params.get("upload_url") || params.get("datapipe_url") || params.get("DATAPIPE_URL"));
    document.getElementById("headerSub").textContent = hasUploadEndpoint
      ? `Adult feasibility task · upload endpoint configured · v${CONFIG.version}`
      : `Adult feasibility task · public static build · no server upload · v${CONFIG.version}`;
    updateRecoverButton();
  }

  document.getElementById("adultCheck").addEventListener("change", updateConsentButton);
  document.getElementById("consentCheck").addEventListener("change", updateConsentButton);
  document.getElementById("beginTutorialBtn").addEventListener("click", () => {
    initSession();
    show("tutorialScreen");
  });
  document.getElementById("startPracticeBtn").addEventListener("click", () => startCurrentTrial());
  document.getElementById("finishEarlyBtn").addEventListener("click", finishClicksNow);
  document.getElementById("previousStrikeBtn").addEventListener("click", previousStrike);
  document.getElementById("submitTrialBtn").addEventListener("click", submitTrial);
  document.getElementById("downloadBtn").addEventListener("click", downloadJson);
  document.getElementById("downloadFinalBtn").addEventListener("click", downloadJson);
  document.getElementById("copySummaryBtn").addEventListener("click", showSummary);
  document.getElementById("completionBtn").addEventListener("click", goCompletion);
  document.getElementById("recoverBtn").addEventListener("click", downloadRecoveredSession);
  window.addEventListener("beforeunload", event => {
    const unfinished = session && !session.finished_at && session.trials.length > 0;
    const uploadPending = session && session.finished_at && session.upload_url && !hasUploaded;
    const finalQuestionPending = session && session.finished_at && !session.perceived_ease;
    if (session?.upload_url && (unfinished || uploadPending || finalQuestionPending)) {
      beaconUpload(unfinished ? "beforeunload_checkpoint" : "beforeunload_final");
    }
    if (unfinished || uploadPending || finalQuestionPending) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  hydrateFromUrl();
})();
