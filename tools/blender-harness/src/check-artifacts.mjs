#!/usr/bin/env node
// check-artifacts.mjs — validate that a Blender candidate submitted the
// required evidence for its asset_profile + current_gate.
//
// This is a contract checker, not a visual judge. Exit 0 means the required
// files and manifest flags are present. It does not mean the asset looks good.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = path.resolve(__dirname, "..");
const PROFILES_FILE = path.join(PKG_ROOT, "profiles", "asset-profiles.json");

class InputError extends Error {}

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

function makeResult(candidateDir, gateArg) {
  return {
    candidate_dir: candidateDir,
    candidate_id: null,
    asset_id: null,
    asset_profile: null,
    gate: gateArg || null,
    outcome: null,
    exit_code: null,
    checks: [],
    blockers: [],
    violations: [],
  };
}

function ok(result, rule, detail) {
  result.checks.push({ rule, ok: true, detail });
}

function block(result, rule, detail) {
  result.checks.push({ rule, ok: false, detail, severity: "blocked" });
  result.blockers.push(`${rule}: ${detail}`);
}

function violation(result, rule, detail) {
  result.checks.push({ rule, ok: false, detail, severity: "contract_violation" });
  result.violations.push(`${rule}: ${detail}`);
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validateCandidateManifest(obj, file) {
  const problems = [];
  if (!isObject(obj)) throw new InputError(`candidate-manifest at ${file} must be an object`);
  for (const key of ["candidate_id", "asset_id", "asset_profile", "current_gate"]) {
    if (typeof obj[key] !== "string" || obj[key].length < 1) problems.push(`missing/invalid '${key}'`);
  }
  if (!isObject(obj.source)) {
    problems.push("missing/invalid 'source' object");
  } else {
    for (const key of ["source_type", "license_clearance", "source_manifest_path"]) {
      if (typeof obj.source[key] !== "string" || obj.source[key].length < 1) {
        problems.push(`missing/invalid source.${key}`);
      }
    }
  }
  if (problems.length) {
    throw new InputError(`candidate-manifest at ${file} failed validation:\n  - ${problems.join("\n  - ")}`);
  }
}

function validateArtifactManifest(obj, file) {
  const problems = [];
  if (!isObject(obj)) throw new InputError(`artifact-manifest at ${file} must be an object`);
  if (typeof obj.candidate_id !== "string" || obj.candidate_id.length < 1) problems.push("missing/invalid candidate_id");
  if (!Array.isArray(obj.artifacts)) {
    problems.push("artifacts must be an array");
  } else {
    obj.artifacts.forEach((a, i) => {
      if (!isObject(a)) {
        problems.push(`artifacts[${i}] must be an object`);
        return;
      }
      for (const key of ["id", "type", "path"]) {
        if (typeof a[key] !== "string" || a[key].length < 1) problems.push(`artifacts[${i}].${key} must be a non-empty string`);
      }
      if (a.helper_overlay !== undefined && typeof a.helper_overlay !== "boolean") problems.push(`artifacts[${i}].helper_overlay must be boolean when present`);
      if (a.usable !== undefined && typeof a.usable !== "boolean") problems.push(`artifacts[${i}].usable must be boolean when present`);
    });
  }
  if (problems.length) {
    throw new InputError(`artifact-manifest at ${file} failed validation:\n  - ${problems.join("\n  - ")}`);
  }
}

function validatePromptManifest(obj, file) {
  const problems = [];
  if (!isObject(obj)) throw new InputError(`prompt-manifest at ${file} must be an object`);
  if (typeof obj.candidate_id !== "string" || obj.candidate_id.length < 1) problems.push("missing/invalid candidate_id");
  if (typeof obj.prompt_set_version !== "string" || obj.prompt_set_version.length < 1) problems.push("missing/invalid prompt_set_version");
  if (!Array.isArray(obj.prompts)) {
    problems.push("prompts must be an array");
  } else {
    obj.prompts.forEach((p, i) => {
      if (!isObject(p)) {
        problems.push(`prompts[${i}] must be an object`);
        return;
      }
      for (const key of ["id", "version", "path", "purpose"]) {
        if (typeof p[key] !== "string" || p[key].length < 1) problems.push(`prompts[${i}].${key} must be a non-empty string`);
      }
      if (p.used_by_roles !== undefined) {
        if (!Array.isArray(p.used_by_roles) || !p.used_by_roles.every((r) => typeof r === "string" && r.length >= 1)) {
          problems.push(`prompts[${i}].used_by_roles must be an array of non-empty strings when present`);
        }
      }
    });
  }
  if (problems.length) {
    throw new InputError(`prompt-manifest at ${file} failed validation:\n  - ${problems.join("\n  - ")}`);
  }
}

function loadProfileRequirements(profiles, profileName, gate) {
  const commonGate = profiles.common_gates?.[gate];
  const profile = profiles.profiles?.[profileName];
  if (!commonGate) throw new InputError(`unknown gate '${gate}' in asset profiles`);
  if (!profile) throw new InputError(`unknown asset_profile '${profileName}' in asset profiles`);
  const profileGate = profile.gates?.[gate] || {};
  return {
    requiredArtifacts: [
      ...(commonGate.required_artifacts || []),
      ...(profileGate.required_artifacts || []),
    ],
    noHelperArtifacts: new Set([
      ...(commonGate.no_helper_artifacts || []),
      ...(profileGate.no_helper_artifacts || []),
    ]),
    requiredReviewRoles: [
      ...(commonGate.required_review_roles || []),
      ...(profileGate.required_review_roles || []),
    ],
    requiredPromptIds: [
      ...(commonGate.required_prompt_ids || []),
      ...(profileGate.required_prompt_ids || []),
    ],
    hardRejects: profile.hard_rejects || [],
  };
}

function relExists(candidateDir, relPath) {
  const abs = path.resolve(candidateDir, relPath);
  const root = path.resolve(candidateDir);
  if (!abs.startsWith(root + path.sep) && abs !== root) {
    return { exists: false, abs, escaped: true };
  }
  return { exists: fs.existsSync(abs), abs, escaped: false };
}

function packageRelExists(relPath) {
  const abs = path.resolve(PKG_ROOT, relPath);
  if (!abs.startsWith(PKG_ROOT + path.sep) && abs !== PKG_ROOT) {
    return { exists: false, abs, escaped: true };
  }
  return { exists: fs.existsSync(abs), abs, escaped: false };
}

function main() {
  const args = process.argv.slice(2);
  const json = args.includes("--json");
  const gateIndex = args.indexOf("--gate");
  const gateArg = gateIndex >= 0 ? args[gateIndex + 1] : null;
  const skipValueIndexes = new Set();
  if (gateIndex >= 0) skipValueIndexes.add(gateIndex + 1);
  const candidateArg = args.find((a, i) => !a.startsWith("--") && !skipValueIndexes.has(i));
  if (!candidateArg) {
    console.error("usage: node src/check-artifacts.mjs <candidate-dir> [--gate <gate>] [--json]");
    process.exit(2);
  }

  const candidateDir = path.resolve(candidateArg);
  const result = makeResult(candidateDir, gateArg);

  try {
    const profiles = readJson(PROFILES_FILE, "asset profiles");
    const candidateFile = path.join(candidateDir, "candidate-manifest.json");
    const artifactFile = path.join(candidateDir, "artifact-manifest.json");
    const promptFile = path.join(candidateDir, "prompt-manifest.json");
    const candidate = readJson(candidateFile, "candidate-manifest");
    const artifactManifest = readJson(artifactFile, "artifact-manifest");
    const promptManifest = readJson(promptFile, "prompt-manifest");
    validateCandidateManifest(candidate, candidateFile);
    validateArtifactManifest(artifactManifest, artifactFile);
    validatePromptManifest(promptManifest, promptFile);

    result.candidate_id = candidate.candidate_id;
    result.asset_id = candidate.asset_id;
    result.asset_profile = candidate.asset_profile;
    result.gate = gateArg || candidate.current_gate;

    if (candidate.candidate_id !== artifactManifest.candidate_id) {
      violation(result, "candidate_id_match", `candidate-manifest has ${candidate.candidate_id}, artifact-manifest has ${artifactManifest.candidate_id}`);
    } else {
      ok(result, "candidate_id_match", candidate.candidate_id);
    }

    if (candidate.candidate_id !== promptManifest.candidate_id) {
      violation(result, "prompt_candidate_id_match", `candidate-manifest has ${candidate.candidate_id}, prompt-manifest has ${promptManifest.candidate_id}`);
    } else {
      ok(result, "prompt_candidate_id_match", candidate.candidate_id);
    }

    if (candidate.source.license_clearance === "blocked" || candidate.source.license_clearance === "unknown") {
      block(result, "source_license_clearance", `source license clearance is '${candidate.source.license_clearance}'`);
    } else {
      ok(result, "source_license_clearance", `source license clearance is '${candidate.source.license_clearance}'`);
    }

    const sourceManifest = relExists(candidateDir, candidate.source.source_manifest_path);
    if (sourceManifest.escaped) {
      violation(result, "source_manifest_path", `source manifest escapes candidate dir: ${candidate.source.source_manifest_path}`);
    } else if (!sourceManifest.exists) {
      block(result, "source_manifest_exists", `missing source manifest ${candidate.source.source_manifest_path}`);
    } else {
      ok(result, "source_manifest_exists", candidate.source.source_manifest_path);
    }

    const req = loadProfileRequirements(profiles, candidate.asset_profile, result.gate);
    ok(result, "profile_gate_loaded", `${candidate.asset_profile}/${result.gate}: ${req.requiredArtifacts.length} required artifact(s)`);

    const byId = new Map();
    for (const artifact of artifactManifest.artifacts) {
      if (byId.has(artifact.id)) {
        violation(result, "artifact_unique_id", `duplicate artifact id '${artifact.id}'`);
      }
      byId.set(artifact.id, artifact);
    }

    for (const id of req.requiredArtifacts) {
      const artifact = byId.get(id);
      if (!artifact) {
        block(result, "required_artifact_present", `missing required artifact '${id}'`);
        continue;
      }
      const fileCheck = relExists(candidateDir, artifact.path);
      if (fileCheck.escaped) {
        violation(result, "artifact_path_within_candidate", `${id} path escapes candidate dir: ${artifact.path}`);
      } else if (!fileCheck.exists) {
        block(result, "required_artifact_file_exists", `${id} points to missing file ${artifact.path}`);
      } else {
        ok(result, "required_artifact_file_exists", `${id} -> ${artifact.path}`);
      }
      if (req.noHelperArtifacts.has(id) && artifact.helper_overlay === true) {
        block(result, "no_helper_artifact_clean", `${id} is marked helper_overlay=true`);
      } else if (req.noHelperArtifacts.has(id)) {
        ok(result, "no_helper_artifact_clean", `${id} helper_overlay=false/omitted`);
      }
      if (artifact.usable === false) {
        block(result, "artifact_marked_usable", `${id} is marked usable=false`);
      }
    }

    const promptById = new Map();
    for (const prompt of promptManifest.prompts) {
      if (promptById.has(prompt.id)) {
        violation(result, "prompt_unique_id", `duplicate prompt id '${prompt.id}'`);
      }
      promptById.set(prompt.id, prompt);
    }

    for (const id of req.requiredPromptIds) {
      const prompt = promptById.get(id);
      if (!prompt) {
        block(result, "required_prompt_present", `missing required prompt '${id}'`);
        continue;
      }
      const fileCheck = packageRelExists(prompt.path);
      if (fileCheck.escaped) {
        violation(result, "prompt_path_within_package", `${id} path escapes tools/blender-harness: ${prompt.path}`);
      } else if (!fileCheck.exists) {
        block(result, "required_prompt_file_exists", `${id} points to missing file ${prompt.path}`);
      } else {
        ok(result, "required_prompt_file_exists", `${id} -> ${prompt.path}`);
      }
    }

    if (result.violations.length) {
      result.outcome = "contract_violation";
      result.exit_code = 2;
    } else if (result.blockers.length) {
      result.outcome = "blocked";
      result.exit_code = 1;
    } else {
      result.outcome = "complete";
      result.exit_code = 0;
    }
  } catch (err) {
    if (err instanceof InputError) {
      violation(result, "input", err.message);
      result.outcome = "contract_violation";
      result.exit_code = 2;
    } else {
      violation(result, "unexpected", err.stack || err.message);
      result.outcome = "contract_violation";
      result.exit_code = 2;
    }
  }

  if (json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(`candidate: ${result.candidate_id || candidateDir}`);
    console.log(`profile/gate: ${result.asset_profile || "?"}/${result.gate || "?"}`);
    console.log(`outcome: ${result.outcome} (exit ${result.exit_code})`);
    for (const b of result.blockers) console.log(`BLOCKED: ${b}`);
    for (const v of result.violations) console.log(`VIOLATION: ${v}`);
  }
  process.exit(result.exit_code);
}

main();
