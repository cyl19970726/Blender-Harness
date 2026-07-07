#!/usr/bin/env node
// run-regression.mjs — npm test entry for the gate-status checker.
//
// Runs check-gate-status.mjs and check-artifacts.mjs as real subprocesses
// against fixtures and tampered copies. It asserts the exit codes demanded by
// the issue #131 aggregation contract and the reusable 3D asset evidence
// contract:
//
//   (a) golden negative fixture (gate-d-v01-negative)        -> exit 1 (rejected)
//   (b) synthetic-accepted-control                            -> exit 0 (accepted)
//   (c) tamper: delete a required review from a copy          -> exit 1 (missing review)
//   (d) tamper: flip downstream_allowed=true while status
//       stays rejected                                        -> exit 2 (contract violation)
//   (e) long-creature artifact contract accepted              -> exit 0
//   (f) head-neck helper-overlay negative                     -> exit 1
//   (g) humanoid artifact contract accepted                   -> exit 0
//   (h) tamper: artifact manifest candidate mismatch          -> exit 2
//   (i) tamper: delete required prompt from manifest          -> exit 1
//   (j) tamper: prompt path escapes harness package           -> exit 2
//   (k) gate-status prompt manifest without review prompt_id  -> exit 2
//   (l) gate-status prompt manifest with review prompt_id     -> exit 0
//
// Any failed assertion prints details and exits 1.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CHECKER = path.join(__dirname, "check-gate-status.mjs");
const ARTIFACT_CHECKER = path.join(__dirname, "check-artifacts.mjs");
const PKG_ROOT = path.resolve(__dirname, "..");
const FIXTURES = path.join(PKG_ROOT, "fixtures");
const NEGATIVE = path.join(FIXTURES, "gate-d-v01-negative");
const CONTROL = path.join(FIXTURES, "synthetic-accepted-control");
const LONG_CREATURE_CONTROL = path.join(FIXTURES, "asset-contract-long-creature-accepted");
const HEAD_NECK_NEGATIVE = path.join(FIXTURES, "asset-art-head-neck-negative");
const HUMANOID_CONTROL = path.join(FIXTURES, "asset-contract-humanoid-accepted");

// ---- run the checker CLI and capture exit code + streams ------------------
function runChecker(candidateDir, extraArgs = []) {
  const res = spawnSync(process.execPath, [CHECKER, candidateDir, ...extraArgs], {
    encoding: "utf8",
  });
  return { code: res.status, stdout: res.stdout || "", stderr: res.stderr || "" };
}

function runArtifactChecker(candidateDir, extraArgs = []) {
  const res = spawnSync(process.execPath, [ARTIFACT_CHECKER, candidateDir, ...extraArgs], {
    encoding: "utf8",
  });
  return { code: res.status, stdout: res.stdout || "", stderr: res.stderr || "" };
}

// ---- recursive copy of a candidate dir into a scratch location ------------
function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const ent of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, ent.name);
    const d = path.join(dst, ent.name);
    if (ent.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

// ---- assertion bookkeeping ------------------------------------------------
const failures = [];
function assertExit(label, actual, expected, run) {
  if (actual === expected) {
    console.log(`  ok   ${label} -> exit ${actual}`);
  } else {
    console.log(`  FAIL ${label} -> exit ${actual}, expected ${expected}`);
    failures.push({ label, expected, actual, run });
  }
}

function main() {
  console.log("blender-harness gate-status regression");
  console.log("======================================");

  // (a) golden negative fixture -> exit 1
  {
    const run = runChecker(NEGATIVE);
    assertExit("(a) golden negative fixture (gate-d-v01-negative)", run.code, 1, run);
  }

  // (b) synthetic-accepted-control -> exit 0
  {
    const run = runChecker(CONTROL);
    assertExit("(b) synthetic-accepted-control", run.code, 0, run);
  }

  // Prepare an isolated scratch root under os.tmpdir for the tamper tests so we
  // never mutate the tracked fixtures.
  const scratchRoot = fs.mkdtempSync(path.join(os.tmpdir(), "blender-harness-regression-"));
  try {
    // (c) tamper: delete a required review -> exit 1
    // Rule 1: a role in required_reviews that has no entry in reviews[] must
    // force aggregate rejection. We remove the fresh_visual entry from reviews[]
    // (and its now-orphaned file) so the required role is genuinely absent —
    // this exercises the "required review missing" path, not "review file
    // unreadable" (which would be a different, exit-2 input error).
    {
      const dir = path.join(scratchRoot, "tamper-missing-review");
      copyDir(CONTROL, dir);
      const statusFile = path.join(dir, "gate-status.json");
      const gs = JSON.parse(fs.readFileSync(statusFile, "utf8"));
      if (!gs.required_reviews.includes("fresh_visual") || !gs.reviews.some((r) => r.role === "fresh_visual")) {
        failures.push({
          label: "(c) setup",
          error: `expected control to require+declare fresh_visual, got required=${JSON.stringify(gs.required_reviews)} reviews=${JSON.stringify(gs.reviews.map((r) => r.role))}`,
        });
      }
      // Drop the review entry (role stays required, entry gone).
      const dropped = gs.reviews.find((r) => r.role === "fresh_visual");
      gs.reviews = gs.reviews.filter((r) => r.role !== "fresh_visual");
      fs.writeFileSync(statusFile, JSON.stringify(gs, null, 2) + "\n");
      // Remove the orphaned review file too, so nothing dangling remains.
      if (dropped) {
        const orphan = path.join(dir, dropped.file);
        if (fs.existsSync(orphan)) fs.rmSync(orphan);
      }
      const run = runChecker(dir);
      assertExit("(c) tamper: delete a required review", run.code, 1, run);
    }

    // (d) tamper: downstream_allowed=true while status stays rejected -> exit 2
    {
      const dir = path.join(scratchRoot, "tamper-downstream-flip");
      copyDir(NEGATIVE, dir);
      const statusFile = path.join(dir, "gate-status.json");
      const gs = JSON.parse(fs.readFileSync(statusFile, "utf8"));
      // Sanity: the source fixture must be a rejected-family status so the flip
      // is genuinely a contract violation, not an accepted candidate.
      if (gs.status !== "visual_rejected" || gs.downstream_allowed !== false) {
        failures.push({
          label: "(d) setup",
          error: `expected negative fixture status=visual_rejected/downstream_allowed=false, got ${gs.status}/${gs.downstream_allowed}`,
        });
      }
      gs.downstream_allowed = true; // status stays rejected -> inconsistent
      fs.writeFileSync(statusFile, JSON.stringify(gs, null, 2) + "\n");
      const run = runChecker(dir);
      assertExit("(d) tamper: downstream_allowed=true with rejected status", run.code, 2, run);
    }

    // (e) asset evidence contract: long creature accepted control -> exit 0
    {
      const run = runArtifactChecker(LONG_CREATURE_CONTROL);
      assertExit("(e) asset contract: long-creature accepted", run.code, 0, run);
    }

    // (f) asset evidence contract: head-neck helper overlay negative -> exit 1
    {
      const run = runArtifactChecker(HEAD_NECK_NEGATIVE);
      assertExit("(f) asset contract: head-neck helper-overlay negative", run.code, 1, run);
    }

    // (g) asset evidence contract: humanoid accepted control -> exit 0
    {
      const run = runArtifactChecker(HUMANOID_CONTROL);
      assertExit("(g) asset contract: humanoid accepted", run.code, 0, run);
    }

    // (h) tamper: artifact-manifest candidate_id mismatch -> exit 2
    {
      const dir = path.join(scratchRoot, "tamper-artifact-candidate-mismatch");
      copyDir(LONG_CREATURE_CONTROL, dir);
      const manifestFile = path.join(dir, "artifact-manifest.json");
      const manifest = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
      manifest.candidate_id = "wrong-candidate-id";
      fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + "\n");
      const run = runArtifactChecker(dir);
      assertExit("(h) tamper: artifact manifest candidate mismatch", run.code, 2, run);
    }

    // (i) tamper: delete a required prompt id -> exit 1
    {
      const dir = path.join(scratchRoot, "tamper-missing-required-prompt");
      copyDir(LONG_CREATURE_CONTROL, dir);
      const manifestFile = path.join(dir, "prompt-manifest.json");
      const manifest = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
      manifest.prompts = manifest.prompts.filter((p) => p.id !== "failure-case-checklist-v01");
      fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + "\n");
      const run = runArtifactChecker(dir);
      assertExit("(i) tamper: delete required prompt", run.code, 1, run);
    }

    // (j) tamper: prompt path escapes tools/blender-harness -> exit 2
    {
      const dir = path.join(scratchRoot, "tamper-prompt-path-escape");
      copyDir(LONG_CREATURE_CONTROL, dir);
      const manifestFile = path.join(dir, "prompt-manifest.json");
      const manifest = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
      const prompt = manifest.prompts.find((p) => p.id === "asset-art-review-v01");
      if (!prompt) {
        failures.push({ label: "(j) setup", error: "asset-art-review-v01 prompt missing from control fixture" });
      } else {
        prompt.path = "../README.md";
      }
      fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + "\n");
      const run = runArtifactChecker(dir);
      assertExit("(j) tamper: prompt path escapes harness package", run.code, 2, run);
    }

    // (k) gate-status: prompt manifest present but review omits prompt_id -> exit 2
    {
      const dir = path.join(scratchRoot, "tamper-gate-review-missing-prompt-id");
      copyDir(CONTROL, dir);
      fs.writeFileSync(
        path.join(dir, "prompt-manifest.json"),
        JSON.stringify({
          candidate_id: "synthetic-accepted-control",
          prompt_set_version: "prompt-set-v01",
          prompts: [
            {
              id: "asset-art-review-v01",
              version: "v01",
              path: "prompts/asset-art-review-v01.md",
              purpose: "Synthetic prompt binding control",
            },
          ],
        }, null, 2) + "\n",
      );
      const run = runChecker(dir);
      assertExit("(k) gate-status: prompt manifest requires review prompt_id", run.code, 2, run);
    }

    // (l) gate-status: prompt manifest present and review cites a known prompt -> exit 0
    {
      const dir = path.join(scratchRoot, "tamper-gate-review-known-prompt-id");
      copyDir(CONTROL, dir);
      fs.writeFileSync(
        path.join(dir, "prompt-manifest.json"),
        JSON.stringify({
          candidate_id: "synthetic-accepted-control",
          prompt_set_version: "prompt-set-v01",
          prompts: [
            {
              id: "asset-art-review-v01",
              version: "v01",
              path: "prompts/asset-art-review-v01.md",
              purpose: "Synthetic prompt binding control",
            },
          ],
        }, null, 2) + "\n",
      );
      const reviewFile = path.join(dir, "reviews", "fresh-visual-review.json");
      const review = JSON.parse(fs.readFileSync(reviewFile, "utf8"));
      review.prompt_id = "asset-art-review-v01";
      review.prompt_version = "v01";
      fs.writeFileSync(reviewFile, JSON.stringify(review, null, 2) + "\n");
      const run = runChecker(dir);
      assertExit("(l) gate-status: review cites known prompt_id", run.code, 0, run);
    }
  } finally {
    fs.rmSync(scratchRoot, { recursive: true, force: true });
  }

  console.log("======================================");
  if (failures.length) {
    console.error(`FAILED: ${failures.length} assertion(s) did not hold`);
    for (const f of failures) {
      console.error(`- ${f.label}: expected exit ${f.expected}, got ${f.actual}${f.error ? ` (${f.error})` : ""}`);
      if (f.run) {
        const out = (f.run.stdout || "").trim();
        const err = (f.run.stderr || "").trim();
        if (out) console.error(`    stdout: ${out.split("\n").slice(-6).join("\n            ")}`);
        if (err) console.error(`    stderr: ${err.split("\n").slice(-6).join("\n            ")}`);
      }
    }
    process.exit(1);
  }
  console.log("All 12 regression assertions passed.");
  process.exit(0);
}

main();
