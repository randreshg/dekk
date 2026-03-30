"""Flow template generation for acpx workflows.

Generates starter ``.flow.ts`` files customized for the project based on
discovered skills, project name, and detected build system.

Three templates are available:
  - **review**: PR code review flow (6 nodes)
  - **triage**: Multi-step PR triage flow (9 nodes)
  - **echo**: Simple agent echo test flow (4 nodes)
"""

from __future__ import annotations

from pathlib import Path

from dekk.agents.constants import (
    DEKK_TOML,
    DEFAULT_FLOWS_DIR,
    DEFAULT_SOURCE_DIR,
    SKILLS_DIR_NAME,
    TOML_NAME_KEY,
    TOML_PROJECT_KEY,
)
from dekk.agents.discovery import discover_skills

# Available flow templates
FLOW_TEMPLATES: dict[str, str] = {
    "review": "PR code review — fetches diff, reviews with agent, posts verdict",
    "triage": "Multi-step PR triage — extract intent, test changes, final review",
    "echo": "Simple echo test — verifies agent spawning works",
}


def _discover_project_skills(project_root: Path, source_dir: str) -> list[str]:
    """Return skill names available in the project."""
    source = project_root / source_dir
    skills = discover_skills(source)
    return [s.name for s in skills]


def _render_utils_ts() -> str:
    """Render the shared lib/utils.ts helper."""
    return '''\
/**
 * Shared utilities for acpx flows.
 */
import { readFileSync, existsSync } from "fs";
import { join } from "path";

const AGENTS_DIR = ".agents";
const SKILLS_DIR = "skills";
const SKILL_FILENAME = "SKILL.md";

/**
 * Read a skill's SKILL.md content from the project's .agents/ directory.
 * Returns the full file content (frontmatter + body).
 */
export function readSkill(projectRoot: string, skillName: string): string {
  const skillPath = join(projectRoot, AGENTS_DIR, SKILLS_DIR, skillName, SKILL_FILENAME);
  if (!existsSync(skillPath)) {
    return `[Skill '${skillName}' not found at ${skillPath}]`;
  }
  return readFileSync(skillPath, "utf-8");
}

/**
 * Build a prompt section embedding one or more skills.
 */
export function embedSkills(projectRoot: string, skillNames: string[]): string {
  const sections = skillNames
    .map((name) => {
      const content = readSkill(projectRoot, name);
      return `### Skill: ${name}\\n\\n${content}`;
    })
    .join("\\n\\n");

  return `## Available Skills\\n\\n${sections}`;
}
'''


def _render_review_flow(project_name: str, skills: list[str]) -> str:
    """Render the PR code review flow template."""
    review_skills = []
    for s in ("review", "lint"):
        if s in skills:
            review_skills.append(s)
    if not review_skills:
        review_skills = ["review"]

    skills_json = ", ".join(f'"{s}"' for s in review_skills)

    return f'''\
/**
 * PR Code Review Flow — {project_name}
 *
 * A 6-node acpx workflow that reviews a pull request:
 *   1. load_pr (compute) — Parse input
 *   2. fetch_diff (action/shell) — Get PR diff via gh CLI
 *   3. review_code (acp) — Agent reviews the diff
 *   4. judge_verdict (compute) — Route based on review verdict
 *   5. post_approval (action/shell) — Approve the PR
 *   6. post_changes (action/shell) — Request changes on the PR
 *
 * Usage:
 *   acpx flow run ./review.flow.ts \\
 *     --input-json '{{"repo":"owner/repo","prNumber":42}}' \\
 *     --approve-all
 */
import {{ defineFlow, acp, compute, shell, extractJsonObject }} from "acpx/flows";
import {{ embedSkills }} from "./lib/utils.js";

type ReviewInput = {{
  repo: string;
  prNumber: number;
  projectRoot?: string;
}};

type ReviewOutput = {{
  verdict: "approve" | "request_changes";
  summary: string;
  comments: string[];
}};

const SESSION_HANDLE = "review";

export default defineFlow({{
  name: "pr-review",
  startAt: "load_pr",

  permissions: {{
    requiredMode: "approve-all",
    reason: "Flow executes shell commands and agent actions autonomously",
  }},

  nodes: {{
    load_pr: compute({{
      run: ({{ input }}) => {{
        const {{ repo, prNumber, projectRoot }} = input as ReviewInput;
        return {{
          repo,
          prNumber,
          projectRoot: projectRoot || process.cwd(),
        }};
      }},
    }}),

    fetch_diff: shell({{
      statusDetail: "Fetching PR diff...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        return {{
          command: "gh",
          args: ["pr", "diff", String(pr.prNumber), "--repo", pr.repo],
          shell: false,
        }};
      }},
      parse: (result) => ({{
        diff: result.stdout,
        linesChanged: result.stdout.split("\\n").length,
      }}),
    }}),

    review_code: acp({{
      session: {{ handle: SESSION_HANDLE }},
      statusDetail: "Agent reviewing code...",
      timeoutMs: 5 * 60_000,
      cwd: ({{ outputs }}) => (outputs.load_pr as {{ projectRoot: string }}).projectRoot,

      prompt: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number; projectRoot: string }};
        const diff = outputs.fetch_diff as {{ diff: string; linesChanged: number }};

        const skills = embedSkills(pr.projectRoot, [{skills_json}]);

        return [
          skills,
          "",
          "## Task",
          "",
          `Review the following PR diff (${{diff.linesChanged}} lines) from ${{pr.repo}}#${{pr.prNumber}}.`,
          "",
          "Analyze for:",
          "1. Correctness — does the code do what it intends?",
          "2. Security — buffer overflows, injection, unsafe operations",
          "3. Style — does it follow project conventions?",
          "4. Performance — any obvious regressions?",
          "",
          "Output your review as JSON:",
          "```json",
          '{{',
          '  "verdict": "approve" | "request_changes",',
          '  "summary": "one-line summary",',
          '  "comments": ["comment 1", "comment 2"]',
          '}}',
          "```",
          "",
          "## Diff",
          "",
          "```diff",
          diff.diff.slice(0, 50_000),
          "```",
        ].join("\\n");
      }},

      parse: (text) => {{
        const parsed = extractJsonObject(text) as ReviewOutput;
        return {{
          verdict: parsed.verdict || "request_changes",
          summary: parsed.summary || "No summary provided",
          comments: parsed.comments || [],
        }};
      }},
    }}),

    judge_verdict: compute({{
      run: ({{ outputs }}) => {{
        const review = outputs.review_code as ReviewOutput;
        return {{ route: review.verdict }};
      }},
    }}),

    post_approval: shell({{
      statusDetail: "Approving PR...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        const review = outputs.review_code as ReviewOutput;
        return {{
          command: "gh",
          args: [
            "pr", "review", String(pr.prNumber),
            "--repo", pr.repo,
            "--approve",
            "--body", review.summary,
          ],
          shell: false,
        }};
      }},
    }}),

    post_changes: shell({{
      statusDetail: "Requesting changes...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        const review = outputs.review_code as ReviewOutput;
        const body = [
          review.summary,
          "",
          ...review.comments.map((c: string) => `- ${{c}}`),
        ].join("\\n");
        return {{
          command: "gh",
          args: [
            "pr", "review", String(pr.prNumber),
            "--repo", pr.repo,
            "--request-changes",
            "--body", body,
          ],
          shell: false,
        }};
      }},
    }}),
  }},

  edges: [
    {{ from: "load_pr", to: "fetch_diff" }},
    {{ from: "fetch_diff", to: "review_code" }},
    {{ from: "review_code", to: "judge_verdict" }},
    {{
      from: "judge_verdict",
      switch: {{
        on: "$output.route",
        cases: {{
          approve: "post_approval",
          request_changes: "post_changes",
        }},
      }},
    }},
  ],
}});
'''


def _render_triage_flow(project_name: str, skills: list[str]) -> str:
    """Render the multi-step PR triage flow template."""
    review_skills = [s for s in ("review",) if s in skills] or ["review"]
    build_test_skills = [s for s in ("build", "test") if s in skills] or ["build", "test"]

    review_json = ", ".join(f'"{s}"' for s in review_skills)
    bt_json = ", ".join(f'"{s}"' for s in build_test_skills)

    return f'''\
/**
 * PR Triage Flow — {project_name}
 *
 * A multi-step agent pipeline that triages PRs:
 *   1. load_pr (compute) — Parse input
 *   2. fetch_context (action/shell) — Get PR metadata
 *   3. fetch_diff (action/shell) — Get PR diff
 *   4. extract_intent (acp) — Agent extracts PR intent
 *   5. classify (compute) — Route: verify or close
 *   6. test_changes (acp) — Agent verifies changes
 *   7. final_review (acp) — Agent does final review
 *   8. post_result (compute) — Prepare final output
 *   9. comment_and_close (action/shell) — Close low-quality PR
 *
 * Usage:
 *   acpx flow run ./triage.flow.ts \\
 *     --input-json '{{"repo":"owner/repo","prNumber":42}}' \\
 *     --approve-all
 */
import {{ defineFlow, acp, compute, shell, extractJsonObject }} from "acpx/flows";
import {{ embedSkills }} from "./lib/utils.js";

type TriageInput = {{
  repo: string;
  prNumber: number;
  projectRoot?: string;
}};

const SESSION_HANDLE = "triage";

export default defineFlow({{
  name: "pr-triage",
  startAt: "load_pr",

  permissions: {{
    requiredMode: "approve-all",
    reason: "Flow executes shell commands and agent actions autonomously",
  }},

  nodes: {{
    load_pr: compute({{
      run: ({{ input }}) => {{
        const {{ repo, prNumber, projectRoot }} = input as TriageInput;
        return {{
          repo,
          prNumber,
          projectRoot: projectRoot || process.cwd(),
        }};
      }},
    }}),

    fetch_context: shell({{
      statusDetail: "Fetching PR context...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        return {{
          command: "gh",
          args: [
            "pr", "view", String(pr.prNumber),
            "--repo", pr.repo,
            "--json", "title,body,labels,files,additions,deletions,changedFiles",
          ],
          shell: false,
        }};
      }},
      parse: (result) => {{
        const metadata = JSON.parse(result.stdout);
        return {{ metadata }};
      }},
    }}),

    fetch_diff: shell({{
      statusDetail: "Fetching PR diff...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        return {{
          command: "gh",
          args: ["pr", "diff", String(pr.prNumber), "--repo", pr.repo],
          shell: false,
        }};
      }},
      parse: (result) => ({{
        diff: result.stdout,
      }}),
    }}),

    extract_intent: acp({{
      session: {{ handle: SESSION_HANDLE }},
      statusDetail: "Extracting PR intent...",
      timeoutMs: 3 * 60_000,
      cwd: ({{ outputs }}) => (outputs.load_pr as {{ projectRoot: string }}).projectRoot,

      prompt: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number; projectRoot: string }};
        const ctx = outputs.fetch_context as {{ metadata: Record<string, unknown> }};
        const diff = outputs.fetch_diff as {{ diff: string }};

        return [
          `## Task: Extract Intent for PR #${{pr.prNumber}}`,
          "",
          "Analyze this PR and determine its intent.",
          "",
          "### PR Metadata",
          "```json",
          JSON.stringify(ctx.metadata, null, 2).slice(0, 5000),
          "```",
          "",
          "### Diff (first 30k chars)",
          "```diff",
          diff.diff.slice(0, 30_000),
          "```",
          "",
          "Output JSON:",
          "```json",
          '{{',
          '  "intent": "one-line description of what this PR does",',
          '  "category": "bug_fix" | "feature" | "docs" | "refactor" | "low_quality",',
          '  "risk": "low" | "medium" | "high",',
          '  "reason": "why you classified it this way"',
          '}}',
          "```",
        ].join("\\n");
      }},

      parse: (text) => {{
        const parsed = extractJsonObject(text) as Record<string, unknown>;
        return {{
          intent: parsed.intent || "unknown",
          category: parsed.category || "feature",
          risk: parsed.risk || "medium",
          reason: parsed.reason || "",
        }};
      }},
    }}),

    classify: compute({{
      run: ({{ outputs }}) => {{
        const intent = outputs.extract_intent as {{ category: string }};
        if (intent.category === "low_quality") {{
          return {{ route: "close" }};
        }}
        return {{ route: "verify" }};
      }},
    }}),

    test_changes: acp({{
      session: {{ handle: SESSION_HANDLE }},
      statusDetail: "Verifying changes...",
      timeoutMs: 5 * 60_000,
      cwd: ({{ outputs }}) => (outputs.load_pr as {{ projectRoot: string }}).projectRoot,

      prompt: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ projectRoot: string }};
        const intent = outputs.extract_intent as {{
          intent: string;
          category: string;
          risk: string;
        }};

        const skills = embedSkills(pr.projectRoot, [{bt_json}]);

        return [
          skills,
          "",
          "## Task: Verify Changes",
          "",
          `This PR is a **${{intent.category}}** (risk: ${{intent.risk}}).`,
          `Intent: ${{intent.intent}}`,
          "",
          "Please:",
          "1. Build the project to check for compilation errors",
          "2. Run the test suite",
          "3. Check if the changes match the stated intent",
          "",
          "Output JSON:",
          "```json",
          '{{',
          '  "builds": true | false,',
          '  "tests_pass": true | false,',
          '  "matches_intent": true | false,',
          '  "issues": ["issue 1", "issue 2"]',
          '}}',
          "```",
        ].join("\\n");
      }},

      parse: (text) => {{
        const parsed = extractJsonObject(text) as Record<string, unknown>;
        return {{
          builds: parsed.builds ?? true,
          tests_pass: parsed.tests_pass ?? true,
          matches_intent: parsed.matches_intent ?? true,
          issues: (parsed.issues as string[]) || [],
        }};
      }},
    }}),

    final_review: acp({{
      session: {{ handle: SESSION_HANDLE }},
      statusDetail: "Final review...",
      timeoutMs: 3 * 60_000,
      cwd: ({{ outputs }}) => (outputs.load_pr as {{ projectRoot: string }}).projectRoot,

      prompt: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ projectRoot: string }};
        const intent = outputs.extract_intent as {{
          intent: string;
          category: string;
          risk: string;
        }};
        const verification = outputs.test_changes as {{
          builds: boolean;
          tests_pass: boolean;
          matches_intent: boolean;
          issues: string[];
        }};

        const skills = embedSkills(pr.projectRoot, [{review_json}]);

        return [
          skills,
          "",
          "## Task: Final Review",
          "",
          `PR category: **${{intent.category}}** (risk: ${{intent.risk}})`,
          `Intent: ${{intent.intent}}`,
          "",
          "### Verification Results",
          `- Builds: ${{verification.builds ? "PASS" : "FAIL"}}`,
          `- Tests: ${{verification.tests_pass ? "PASS" : "FAIL"}}`,
          `- Matches intent: ${{verification.matches_intent ? "YES" : "NO"}}`,
          verification.issues.length > 0
            ? `- Issues: ${{verification.issues.join(", ")}}`
            : "- No issues found",
          "",
          "Based on the verification results, provide your final verdict.",
          "",
          "Output JSON:",
          "```json",
          '{{',
          '  "verdict": "approve" | "request_changes" | "escalate",',
          '  "summary": "one-line summary for the PR comment",',
          '  "comments": ["detailed comment 1", ...]',
          '}}',
          "```",
        ].join("\\n");
      }},

      parse: (text) => {{
        const parsed = extractJsonObject(text) as Record<string, unknown>;
        return {{
          verdict: parsed.verdict || "escalate",
          summary: parsed.summary || "",
          comments: (parsed.comments as string[]) || [],
        }};
      }},
    }}),

    post_result: compute({{
      run: ({{ outputs }}) => {{
        const intent = outputs.extract_intent as {{ intent: string; category: string }};
        const review = outputs.final_review as {{
          verdict: string;
          summary: string;
          comments: string[];
        }};
        return {{
          intent: intent.intent,
          category: intent.category,
          verdict: review.verdict,
          summary: review.summary,
          comments: review.comments,
        }};
      }},
    }}),

    comment_and_close: shell({{
      statusDetail: "Closing PR...",
      exec: ({{ outputs }}) => {{
        const pr = outputs.load_pr as {{ repo: string; prNumber: number }};
        const intent = outputs.extract_intent as {{ reason: string }};
        return {{
          command: "gh",
          args: [
            "pr", "close", String(pr.prNumber),
            "--repo", pr.repo,
            "--comment", `Closing: ${{intent.reason}}`,
          ],
          shell: false,
        }};
      }},
    }}),
  }},

  edges: [
    {{ from: "load_pr", to: "fetch_context" }},
    {{ from: "fetch_context", to: "fetch_diff" }},
    {{ from: "fetch_diff", to: "extract_intent" }},
    {{ from: "extract_intent", to: "classify" }},
    {{
      from: "classify",
      switch: {{
        on: "$output.route",
        cases: {{
          verify: "test_changes",
          close: "comment_and_close",
        }},
      }},
    }},
    {{ from: "test_changes", to: "final_review" }},
    {{ from: "final_review", to: "post_result" }},
  ],
}});
'''


def _render_echo_flow(project_name: str) -> str:
    """Render the echo test flow template."""
    return f'''\
/**
 * Echo Flow — {project_name}
 *
 * Simple test to verify agent spawning works.
 * Two sequential ACP nodes: one with codex, one with claude,
 * both answering the same question to compare outputs.
 *
 * Usage:
 *   acpx flow run ./echo.flow.ts \\
 *     --input-json '{{"question":"What is 2+2?"}}' \\
 *     --approve-all
 */
import {{ defineFlow, acp, compute }} from "acpx/flows";

type EchoInput = {{
  question: string;
}};

export default defineFlow({{
  name: "echo-test",
  startAt: "load_input",

  permissions: {{
    requiredMode: "approve-all",
  }},

  nodes: {{
    load_input: compute({{
      run: ({{ input }}) => {{
        const {{ question }} = input as EchoInput;
        return {{ question }};
      }},
    }}),

    ask_codex: acp({{
      profile: "codex",
      session: {{ handle: "codex-echo", isolated: true }},
      statusDetail: "Asking Codex...",
      timeoutMs: 2 * 60_000,

      prompt: ({{ outputs }}) => {{
        const {{ question }} = outputs.load_input as {{ question: string }};
        return `Answer this concisely in one line: ${{question}}`;
      }},

      parse: (text) => ({{ answer: text.trim() }}),
    }}),

    ask_claude: acp({{
      profile: "claude",
      session: {{ handle: "claude-echo", isolated: true }},
      statusDetail: "Asking Claude...",
      timeoutMs: 2 * 60_000,

      prompt: ({{ outputs }}) => {{
        const {{ question }} = outputs.load_input as {{ question: string }};
        return `Answer this concisely in one line: ${{question}}`;
      }},

      parse: (text) => ({{ answer: text.trim() }}),
    }}),

    compare: compute({{
      run: ({{ outputs }}) => {{
        const codex = outputs.ask_codex as {{ answer: string }};
        const claude = outputs.ask_claude as {{ answer: string }};
        return {{
          codex_answer: codex.answer,
          claude_answer: claude.answer,
          match: codex.answer.toLowerCase() === claude.answer.toLowerCase(),
        }};
      }},
    }}),
  }},

  edges: [
    {{ from: "load_input", to: "ask_codex" }},
    {{ from: "ask_codex", to: "ask_claude" }},
    {{ from: "ask_claude", to: "compare" }},
  ],
}});
'''


def _render_package_json() -> str:
    """Render a minimal package.json for the flows directory."""
    return '''\
{
  "private": true,
  "type": "module",
  "dependencies": {
    "acpx": "^0.4.0"
  },
  "devDependencies": {
    "@types/node": "^25.5.0"
  }
}
'''


def _render_tsconfig() -> str:
    """Render tsconfig.json for the flows directory."""
    return '''\
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist"
  },
  "include": ["./**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
'''


def generate_flow(
    project_root: Path,
    template: str,
    source_dir: str = DEFAULT_SOURCE_DIR,
    flows_dir: str = DEFAULT_FLOWS_DIR,
    force: bool = False,
) -> list[Path]:
    """Generate an acpx flow template customized for the project.

    Args:
        project_root: Root directory of the project.
        template: Template name ("review", "triage", "echo").
        source_dir: Source-of-truth directory name.
        flows_dir: Directory to write flows into.
        force: Overwrite existing flow files.

    Returns:
        List of created file paths.
    """
    if template not in FLOW_TEMPLATES:
        msg = f"Unknown template '{template}'. Available: {', '.join(FLOW_TEMPLATES)}"
        raise ValueError(msg)

    target = project_root / flows_dir
    target.mkdir(parents=True, exist_ok=True)

    # Discover project info
    project_name = project_root.name
    dekk_toml = project_root / DEKK_TOML
    if dekk_toml.is_file():
        from dekk._compat import tomllib

        with open(dekk_toml, "rb") as f:
            data = tomllib.load(f)
        project_name = data.get(TOML_PROJECT_KEY, {}).get(TOML_NAME_KEY, project_name)

    skills = _discover_project_skills(project_root, source_dir)

    created: list[Path] = []

    # Generate the flow file
    flow_file = target / f"{template}.flow.ts"
    if flow_file.exists() and not force:
        return created

    if template == "review":
        content = _render_review_flow(project_name, skills)
    elif template == "triage":
        content = _render_triage_flow(project_name, skills)
    elif template == "echo":
        content = _render_echo_flow(project_name)
    else:
        return created

    flow_file.write_text(content, encoding="utf-8")
    created.append(flow_file)

    # Generate lib/utils.ts if not present
    lib_dir = target / "lib"
    utils_file = lib_dir / "utils.ts"
    if not utils_file.exists():
        lib_dir.mkdir(parents=True, exist_ok=True)
        utils_file.write_text(_render_utils_ts(), encoding="utf-8")
        created.append(utils_file)

    # Generate package.json if not present
    pkg_file = target / "package.json"
    if not pkg_file.exists():
        pkg_file.write_text(_render_package_json(), encoding="utf-8")
        created.append(pkg_file)

    # Generate tsconfig.json if not present
    tsconfig_file = target / "tsconfig.json"
    if not tsconfig_file.exists():
        tsconfig_file.write_text(_render_tsconfig(), encoding="utf-8")
        created.append(tsconfig_file)

    return created
