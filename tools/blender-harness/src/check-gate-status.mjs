#!/usr/bin/env node
// check-gate-status.mjs — aggregate a candidate's gate outcome from its
// gate-status.json + reviews/*.json into a single, contract-checked verdict.
//
//   node src/check-gate-status.mjs <candidate-dir> [--json]
//
// Exit codes (issue #131 aggregation contract):
//   0 = accepted   (all required reviews present and every one accept; status accepted-family)
//   1 = rejected / blocked  (a review rejected/conditional, a required review missing,
//                            a rejected-family/pending status, or a forbidden next output exists)
//   2 = contract violation OR missing/malformed input
//                            (downstream_allowed inconsistent with status; unreadable/invalid files)
//
// This checker is parameterized on <candidate-dir> and reads gate-status.json;
// it never hardcodes a specific candidate path. Structural validation is
// hand-written (zero npm deps) and mirrors schemas/gate-status.schema.json and
// schemas/review.schema.json.
//
// IMPORTANT (metrics have only reject power): an exit 0 here means "the review
// records are present and all accept" — it is NOT a visual endorsement. Visual
// backing lives only inside the referenced reviews/*.json files. This script can
// block promotion; it cannot certify visual quality.

import fs from "node:fs";
import path from "node:path";

// ---- status taxonomy (must match schemas/gate-status.schema.json) ---------
const STATUS_ENUM = new Set([
  "route_proof_only",
  "proxy_blocking_only",
  "asset_rejected",
  "rig_rejected",
  "animation_rejected",
  "pass_rejected",
  "visual_rejected",
  "runtime_smoke_passed",
  "production_accepted",
  "pending_review",
  "accepted",
]);

// Statuses that count as terminal accept for downstream promotion.
const ACCEPTED_STATUSES = new Set(["accepted", "production_accepted"]);

// The *_rejected family: a layer explicitly rejected the candidate.
const REJECTED_STATUSES = new Set([
  "asset_rejected",
  "rig_rejected",
  "animation_rejected",
  "pass_rejected",
  "visual_rejected",
]);

const VERDICT_ENUM = new Set(["accept", "conditional", "reject"]);

// ---- result-collection helpers -------------------------------------------
// We accumulate every judgment basis so the human-readable output can list each
// rule's decision, and so --json emits a machine-readable audit trail.
function makeResult(candidateDir) {
  return {
    candidate_dir: candidateDir,
    candidate_id: null,
    gate: null,
    status: null,
    downstream_allowed: null,
    // aggregate outcome: "accepted" | "rejected" | "contract_violation"
    outcome: null,
    exit_code: null,
    // ordered list of { rule, ok, detail } — one per rule evaluated
    checks: [],
    // the specific reasons the checker blocked or flagged, for quick reading
    blockers: [],
    violations: [],
  };
}

function record(result, rule, ok, detail) {
  result.checks.push({ rule, ok, detail });
  return ok;
}

// A contract violation (exit 2): the status/flags are internally inconsistent,
// or an input is missing/malformed. Distinct from a normal rejection.
function violation(result, rule, detail) {
  result.checks.push({ rule, ok: false, detail, severity: "contract_violation" });
  result.violations.push(`${rule}: ${detail}`);
}

// A normal block/reject (exit 1): the candidate is not promotable.
function blocker(result, rule, detail) {
  result.checks.push({ rule, ok: false, detail, severity: "rejected" });
  result.blockers.push(`${rule}: ${detail}`);
}

// ---- IO with fail-fast, typed errors --------------------------------------
class InputError extends Error {} // maps to exit 2 (missing/malformed input)

function readJson(file, label) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (err) {
    throw new InputError(`cannot read ${label} at ${file}: ${err.code || err.message}`);
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new InputError(`${label} at ${file} is not valid JSON: ${err.message}`);
  }
}

// ---- hand-written structural validation (mirrors the JSON Schemas) --------
function validateGateStatus(obj, file) {
  const problems = [];
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) {
    throw new InputError(`gate-status.json at ${file} must be a JSON object`);
  }
  const reqStr = ["candidate_id", "gate", "status"];
  for (const key of reqStr) {
    if (typeof obj[key] !== "string" || obj[key].length < 1) {
      problems.push(`missing/invalid required string field '${key}'`);
    }
  }
  if (typeof obj.downstream_allowed !== "boolean") {
    problems.push("missing/invalid required boolean field 'downstream_allowed'");
  }
  if (obj.status !== undefined && !STATUS_ENUM.has(obj.status)) {
    problems.push(`status '${obj.status}' is not one of the allowed enum values`);
  }
  if (!Array.isArray(obj.required_reviews) || obj.required_reviews.length < 1) {
    problems.push("required_reviews must be a non-empty array");
  } else if (!obj.required_reviews.every((r) => typeof r === "string" && r.length >= 1)) {
    problems.push("required_reviews entries must be non-empty strings");
  }
  if (!Array.isArray(obj.reviews)) {
    problems.push("reviews must be an array");
  } else {
    obj.reviews.forEach((rv, i) => {
      if (rv === null || typeof rv !== "object" || Array.isArray(rv)) {
        problems.push(`reviews[${i}] must be an object`);
        return;
      }
      if (typeof rv.role !== "string" || rv.role.length < 1) problems.push(`reviews[${i}].role must be a non-empty string`);
      if (typeof rv.file !== "string" || rv.file.length < 1) problems.push(`reviews[${i}].file must be a non-empty string`);
    });
  }
  if (obj.forbidden_next_outputs !== undefined) {
    if (!Array.isArray(obj.forbidden_next_outputs) || !obj.forbidden_next_outputs.every((s) => typeof s === "string" && s.length >= 1)) {
      problems.push("forbidden_next_outputs, if present, must be an array of non-empty strings");
    }
  }
  if (problems.length) {
    throw new InputError(`gate-status.json at ${file} failed schema-shape validation:\n  - ${problems.join("\n  - ")}`);
  }
}

function validateReview(obj, file, role) {
  const problems = [];
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) {
    throw new InputError(`review ${file} must be a JSON object`);
  }
  if (typeof obj.role !== "string" || obj.role.length < 1) problems.push("missing/invalid 'role'");
  if (typeof obj.rubric_version !== "string" || obj.rubric_version.length < 1) problems.push("missing/invalid 'rubric_version'");
  if (typeof obj.verdict !== "string" || !VERDICT_ENUM.has(obj.verdict)) problems.push(`'verdict' must be one of ${[...VERDICT_ENUM].join("/")}`);
  if (!Array.isArray(obj.hard_reject_hits)) problems.push("'hard_reject_hits' must be an array");
  if (!Array.isArray(obj.findings)) problems.push("'findings' must be an array");
  if (obj.downstream === null || typeof obj.downstream !== "object" || Array.isArray(obj.downstream)) {
    problems.push("'downstream' must be an object with full_render/wechat_runtime booleans");
  } else {
    if (typeof obj.downstream.full_render !== "boolean") problems.push("'downstream.full_render' must be boolean");
    if (typeof obj.downstream.wechat_runtime !== "boolean") problems.push("'downstream.wechat_runtime' must be boolean");
  }
  if (problems.length) {
    throw new InputError(`review for role '${role}' at ${file} failed schema-shape validation:\n  - ${problems.join("\n  - ")}`);
  }
}

function validatePromptManifest(obj, file) {
  const problems = [];
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) {
    throw new InputError(`prompt-manifest at ${file} must be a JSON object`);
  }
  if (typeof obj.candidate_id !== "string" || obj.candidate_id.length < 1) problems.push("missing/invalid 'candidate_id'");
  if (typeof obj.prompt_set_version !== "string" || obj.prompt_set_version.length < 1) problems.push("missing/invalid 'prompt_set_version'");
  if (!Array.isArray(obj.prompts)) {
    problems.push("'prompts' must be an array");
  } else {
    obj.prompts.forEach((p, i) => {
      if (p === null || typeof p !== "object" || Array.isArray(p)) {
        problems.push(`prompts[${i}] must be an object`);
        return;
      }
      for (const key of ["id", "version", "path", "purpose"]) {
        if (typeof p[key] !== "string" || p[key].length < 1) problems.push(`prompts[${i}].${key} must be a non-empty string`);
      }
    });
  }
  if (problems.length) {
    throw new InputError(`prompt-manifest at ${file} failed schema-shape validation:\n  - ${problems.join("\n  - ")}`);
  }
}

// ---- tiny glob matcher for forbidden_next_outputs -------------------------
// Supports '*' (within a path segment) and '**' (across segments). No deps.
function globToRegExp(glob) {
  let re = "^";
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === "*") {
      if (glob[i + 1] === "*") {
        // '**' — match across path separators
        re += ".*";
        i++;
        // consume an optional trailing slash so 'dir/**' also matches 'dir/'
        if (glob[i + 1] === "/") i++;
      } else {
        // single '*' — match within a segment
        re += "[^/]*";
      }
    } else if ("\\^$.|?+()[]{}".includes(c)) {
      re += "\\" + c;
    } else {
      re += c;
    }
  }
  re += "$";
  return new RegExp(re);
}

// List candidate-dir files as posix-relative paths (bounded walk).
function listRelativeFiles(dir) {
  const out = [];
  const walk = (abs, rel) => {
    let entries;
    try {
      entries = fs.readdirSync(abs, { withFileTypes: true });
    } catch {
      return;
    }
    for (const ent of entries) {
      const childRel = rel ? `${rel}/${ent.name}` : ent.name;
      if (ent.isDirectory()) {
        walk(path.join(abs, ent.name), childRel);
      } else {
        out.push(childRel);
      }
    }
  };
  walk(dir, "");
  return out;
}

function matchForbidden(pattern, relFiles) {
  // A bare path (no glob metachar) matches by existence of exactly that file.
  if (!pattern.includes("*")) {
    return relFiles.includes(pattern) ? [pattern] : [];
  }
  const re = globToRegExp(pattern);
  return relFiles.filter((f) => re.test(f));
}

// ---- core aggregation -----------------------------------------------------
function aggregate(candidateDir) {
  const result = makeResult(candidateDir);

  // Input presence (missing input => exit 2).
  const statusPath = path.join(candidateDir, "gate-status.json");
  if (!fs.existsSync(candidateDir) || !fs.statSync(candidateDir).isDirectory()) {
    throw new InputError(`candidate directory not found or not a directory: ${candidateDir}`);
  }
  if (!fs.existsSync(statusPath)) {
    throw new InputError(`missing gate-status.json in candidate directory: ${statusPath}`);
  }

  const gs = readJson(statusPath, "gate-status.json");
  validateGateStatus(gs, statusPath);

  const promptPath = path.join(candidateDir, "prompt-manifest.json");
  const promptManifest = fs.existsSync(promptPath) ? readJson(promptPath, "prompt-manifest.json") : null;
  if (promptManifest) validatePromptManifest(promptManifest, promptPath);

  result.candidate_id = gs.candidate_id;
  result.gate = gs.gate;
  result.status = gs.status;
  result.downstream_allowed = gs.downstream_allowed;

  const isAcceptedStatus = ACCEPTED_STATUSES.has(gs.status);
  const isRejectedStatus = REJECTED_STATUSES.has(gs.status);
  const promptIds = new Set((promptManifest?.prompts || []).map((p) => p.id));

  if (promptManifest && promptManifest.candidate_id !== gs.candidate_id) {
    violation(
      result,
      "prompt_manifest_candidate_match",
      `gate-status candidate_id=${gs.candidate_id}, prompt-manifest candidate_id=${promptManifest.candidate_id}`,
    );
  } else if (promptManifest) {
    record(result, "prompt_manifest_candidate_match", true, `prompt-manifest belongs to ${promptManifest.candidate_id}`);
  }

  // Load each declared review by role for lookup.
  const reviewByRole = new Map();
  for (const entry of gs.reviews) {
    const reviewPath = path.isAbsolute(entry.file) ? entry.file : path.join(candidateDir, entry.file);
    const rv = readJson(reviewPath, `review (${entry.role})`);
    validateReview(rv, reviewPath, entry.role);
    reviewByRole.set(entry.role, { entry, review: rv, path: reviewPath });
  }

  // If a candidate carries a prompt-manifest, reviews must cite the versioned
  // prompt they used. Older gate-status-only fixtures may omit the manifest and
  // retain legacy behavior, but full harness candidates cannot.
  if (promptManifest) {
    for (const [role, found] of reviewByRole.entries()) {
      const promptId = found.review.prompt_id;
      if (typeof promptId !== "string" || promptId.length < 1) {
        violation(result, "review_prompt_declared", `review '${role}' is missing prompt_id while prompt-manifest.json is present`);
      } else if (!promptIds.has(promptId)) {
        violation(result, "review_prompt_known", `review '${role}' prompt_id '${promptId}' is not declared in prompt-manifest.json`);
      } else {
        record(result, "review_prompt_known", true, `review '${role}' uses prompt '${promptId}'`);
      }
    }
  }

  // ================= RULE 3 (contract): status vs downstream_allowed ========
  // Any rejected-family OR non-accepted status must have downstream_allowed=false.
  // Inconsistency is a contract violation (exit 2), evaluated first so a
  // mislabeled "accepted-looking" downstream flag can never be masked by a
  // later reject that would only yield exit 1.
  if (!isAcceptedStatus && gs.downstream_allowed === true) {
    const why = isRejectedStatus
      ? `status '${gs.status}' is in the rejected family but downstream_allowed=true`
      : `status '${gs.status}' is not an accepted status but downstream_allowed=true`;
    violation(result, "rule3_status_downstream_consistency", why);
  } else if (isAcceptedStatus && gs.downstream_allowed !== true) {
    // The inverse is also a contract inconsistency: an accepted status that
    // still physically blocks downstream is self-contradictory.
    violation(
      result,
      "rule3_status_downstream_consistency",
      `status '${gs.status}' is an accepted status but downstream_allowed=${gs.downstream_allowed}`,
    );
  } else {
    record(
      result,
      "rule3_status_downstream_consistency",
      true,
      `status '${gs.status}' is consistent with downstream_allowed=${gs.downstream_allowed}`,
    );
  }

  // ================= RULE 4 (contract): runtime smoke never == production ====
  // runtime_smoke_passed proves only that the WeChat runtime path loads; it must
  // never be paired with a downstream unlock as if it were production_accepted.
  if (gs.status === "runtime_smoke_passed") {
    if (gs.downstream_allowed === true) {
      violation(
        result,
        "rule4_runtime_smoke_not_production",
        "status 'runtime_smoke_passed' must never unlock downstream; it is not production_accepted",
      );
    } else {
      record(
        result,
        "rule4_runtime_smoke_not_production",
        true,
        "status 'runtime_smoke_passed' correctly does not unlock downstream (not production_accepted)",
      );
    }
  }

  // ================= RULE 1 & 2: required reviews present + verdicts =========
  // Rule 1: any required review missing => rejected (exit 1).
  // Rule 2: any required review verdict=reject => rejected (exit 1);
  //         verdict=conditional does NOT unlock downstream (exit 1, distinct msg).
  let allRequiredAccept = true;
  for (const role of gs.required_reviews) {
    const found = reviewByRole.get(role);
    if (!found) {
      // -------- RULE 1 landing --------
      blocker(result, "rule1_required_review_present", `required review role '${role}' is missing from reviews[]`);
      allRequiredAccept = false;
      continue;
    }
    const v = found.review.verdict;
    if (v === "reject") {
      // -------- RULE 2 landing (hard reject) --------
      const hits = Array.isArray(found.review.hard_reject_hits) ? found.review.hard_reject_hits : [];
      blocker(
        result,
        "rule2_required_review_verdict",
        `required review '${role}' verdict=reject${hits.length ? ` (hard_reject_hits: ${hits.join("; ")})` : ""}`,
      );
      allRequiredAccept = false;
    } else if (v === "conditional") {
      // -------- RULE 2 landing (conditional does NOT unlock) --------
      blocker(
        result,
        "rule2_required_review_verdict",
        `required review '${role}' verdict=conditional — conditional does NOT unlock downstream`,
      );
      allRequiredAccept = false;
    } else {
      record(result, "rule2_required_review_verdict", true, `required review '${role}' verdict=accept`);
    }
  }
  record(
    result,
    "rule1_required_review_present",
    result.blockers.every((b) => !b.startsWith("rule1_required_review_present")),
    `${gs.required_reviews.length} required review role(s) declared; all present: ${
      gs.required_reviews.every((r) => reviewByRole.has(r))
    }`,
  );

  // ================= RULE 5: forbidden_next_outputs on non-accepted ==========
  // Any forbidden output that physically exists in the candidate dir while the
  // candidate is not accepted is a downstream-bypass => rejected (exit 1).
  const forbidden = Array.isArray(gs.forbidden_next_outputs) ? gs.forbidden_next_outputs : [];
  if (forbidden.length) {
    if (isAcceptedStatus) {
      record(
        result,
        "rule5_forbidden_next_outputs",
        true,
        `status is accepted ('${gs.status}'); forbidden_next_outputs not enforced`,
      );
    } else {
      const relFiles = listRelativeFiles(candidateDir);
      const present = [];
      for (const pattern of forbidden) {
        const hits = matchForbidden(pattern, relFiles);
        if (hits.length) present.push(`${pattern} -> ${hits.join(", ")}`);
      }
      if (present.length) {
        // -------- RULE 5 landing --------
        blocker(
          result,
          "rule5_forbidden_next_outputs",
          `forbidden next output(s) present on non-accepted candidate: ${present.join(" | ")}`,
        );
      } else {
        record(
          result,
          "rule5_forbidden_next_outputs",
          true,
          `none of ${forbidden.length} forbidden_next_outputs pattern(s) matched an existing file`,
        );
      }
    }
  }

  // ---- final aggregate outcome + exit code (RULE 6) ------------------------
  // Priority: contract violation (exit 2) > any block (exit 1) > accepted (exit 0).
  // Exit 0 requires: accepted-family status AND every required review accept
  // AND no blockers. metrics-only reject power: exit 0 asserts records齐全且全
  // accept, NOT visual endorsement.
  if (result.violations.length > 0) {
    result.outcome = "contract_violation";
    result.exit_code = 2;
  } else if (result.blockers.length > 0) {
    result.outcome = "rejected";
    result.exit_code = 1;
  } else if (isAcceptedStatus && allRequiredAccept) {
    result.outcome = "accepted";
    result.exit_code = 0;
  } else {
    // Non-accepted status (e.g. pending_review, route_proof_only) with no other
    // blocker still is not promotable => exit 1.
    blocker(
      result,
      "rule6_status_must_be_accepted",
      `status '${gs.status}' is not an accepted status; candidate is not promotable`,
    );
    result.outcome = "rejected";
    result.exit_code = 1;
  }

  return result;
}

// ---- human-readable rendering ---------------------------------------------
function renderHuman(result) {
  const lines = [];
  const bar = "─".repeat(72);
  lines.push(bar);
  lines.push(`Gate status check: ${result.candidate_id ?? "(unknown)"}  [${result.gate ?? "?"}]`);
  lines.push(`Candidate dir: ${result.candidate_dir}`);
  lines.push(`Declared status: ${result.status}   downstream_allowed: ${result.downstream_allowed}`);
  lines.push(bar);
  lines.push("Judgment basis (one line per rule evaluated):");
  for (const c of result.checks) {
    const mark = c.ok ? "PASS" : c.severity === "contract_violation" ? "VIOL" : "FAIL";
    lines.push(`  [${mark}] ${c.rule}: ${c.detail}`);
  }
  lines.push(bar);
  const verdictWord =
    result.outcome === "accepted" ? "ACCEPTED" : result.outcome === "contract_violation" ? "CONTRACT VIOLATION" : "REJECTED / BLOCKED";
  lines.push(`RESULT: ${verdictWord}  (exit ${result.exit_code})`);
  if (result.violations.length) {
    lines.push("Contract violations:");
    for (const v of result.violations) lines.push(`  - ${v}`);
  }
  if (result.blockers.length) {
    lines.push("Blockers:");
    for (const b of result.blockers) lines.push(`  - ${b}`);
  }
  if (result.outcome === "accepted") {
    lines.push(
      "NOTE: exit 0 means review records are present and all accept. It is NOT a visual",
    );
    lines.push("      endorsement — visual backing lives only in the referenced reviews/*.json.");
  }
  lines.push(bar);
  return lines.join("\n");
}

// ---- CLI ------------------------------------------------------------------
function main(argv) {
  const args = argv.slice(2);
  const jsonMode = args.includes("--json");
  const positionals = args.filter((a) => !a.startsWith("--"));
  const candidateDir = positionals[0];

  if (!candidateDir) {
    const msg = "usage: node src/check-gate-status.mjs <candidate-dir> [--json]";
    if (jsonMode) {
      process.stdout.write(JSON.stringify({ outcome: "input_error", exit_code: 2, error: msg }) + "\n");
    } else {
      process.stderr.write(msg + "\n");
    }
    process.exit(2);
  }

  const absDir = path.resolve(candidateDir);
  let result;
  try {
    result = aggregate(absDir);
  } catch (err) {
    if (err instanceof InputError) {
      // Missing/malformed input => exit 2.
      const payload = { outcome: "input_error", exit_code: 2, candidate_dir: absDir, error: err.message };
      if (jsonMode) {
        process.stdout.write(JSON.stringify(payload) + "\n");
      } else {
        process.stderr.write(`INPUT ERROR (exit 2): ${err.message}\n`);
      }
      process.exit(2);
    }
    throw err; // unexpected — let it crash loudly
  }

  if (jsonMode) {
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } else {
    const text = renderHuman(result);
    if (result.exit_code === 0) process.stdout.write(text + "\n");
    else process.stderr.write(text + "\n");
  }
  process.exit(result.exit_code);
}

// Exported for programmatic use (regression harness imports this).
export { aggregate, renderHuman, globToRegExp, matchForbidden, STATUS_ENUM, VERDICT_ENUM };

// Run as CLI when invoked directly.
const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
const selfPath = path.resolve(new URL(import.meta.url).pathname);
if (invokedPath === selfPath) {
  main(process.argv);
}
