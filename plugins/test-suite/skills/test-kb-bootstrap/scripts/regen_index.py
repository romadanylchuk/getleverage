#!/usr/bin/env python3
"""
Regenerate kb/index.json from kb/*.md files.

Walks every .md file under the kb directory, parses HTML-comment metadata
blocks under each level-2-or-deeper heading, and emits kb/index.json with one
entry per section.

Also surfaces, as non-blocking warnings on stderr:
  - Sections missing required metadata fields.
  - Duplicate section_ids across the kb.
  - Broken references — section_ids cited in kb-gaps.md or briefs/*.md that
    no longer exist in the kb.

Usage:
    python regen_index.py <kb-path> [--project-root <root>]

If --project-root is not supplied, the parent of <kb-path> is used to find
kb-gaps.md and briefs/.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HTML_META_RE = re.compile(r"<!--\s*\n(?P<body>.*?)\n\s*-->", re.DOTALL)
HEADING_RE = re.compile(r"^(#{2,})\s+(.+?)\s*$", re.MULTILINE)
META_FIELD_RE = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.*?)\s*$")
SECTION_ID_RE = re.compile(r"\b([a-z][a-z0-9-]*\.[a-z0-9.\-]+)\b")

REQUIRED_FIELDS = {"section_id", "tags", "summary", "source", "last_updated"}


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def parse_meta_block(raw: str) -> dict:
    """Parse the body of an HTML metadata comment into a dict."""
    out: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = META_FIELD_RE.match(line)
        if not m:
            continue
        key = m.group("key")
        value = m.group("value")
        if key == "tags" and value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            value = [t.strip() for t in inner.split(",") if t.strip()] if inner else []
        out[key] = value
    return out


def parse_kb_file(path: Path, layer: str) -> list[dict]:
    """Extract section entries from one kb markdown file."""
    text = path.read_text(encoding="utf-8")
    entries: list[dict] = []

    headings = list(HEADING_RE.finditer(text))
    for idx, h in enumerate(headings):
        title = h.group(2).strip()
        next_pos = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        section_text = text[h.end():next_pos]

        m = HTML_META_RE.search(section_text)
        # The metadata block must be the first non-empty thing after the heading;
        # otherwise this isn't a structured section.
        if not m or section_text[: m.start()].strip():
            continue

        meta = parse_meta_block(m.group("body"))
        missing = REQUIRED_FIELDS - meta.keys()
        if missing:
            print(
                f"warning: {path}: section '{title}' missing fields: {sorted(missing)}",
                file=sys.stderr,
            )
            continue

        entries.append(
            {
                "layer": layer,
                "section_id": meta["section_id"],
                "title": title,
                "summary": meta["summary"],
                "tags": meta.get("tags", []),
                "file": path.name,
                "anchor": slugify(title),
                "source": meta["source"],
                "last_updated": meta["last_updated"],
            }
        )

    return entries


def find_referenced_ids(project_root: Path) -> set[str]:
    """Collect plausible section_ids referenced in kb-gaps.md and briefs/*.md."""
    refs: set[str] = set()
    candidates: list[Path] = []
    gaps = project_root / "kb-gaps.md"
    if gaps.exists():
        candidates.append(gaps)
    briefs_dir = project_root / "briefs"
    if briefs_dir.exists():
        candidates.extend(briefs_dir.glob("*.md"))

    for f in candidates:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in SECTION_ID_RE.finditer(text):
            refs.add(m.group(1))
    return refs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kb_path", type=Path, help="Path to the kb/ directory.")
    ap.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root for finding kb-gaps.md and briefs/. Defaults to the parent of kb_path.",
    )
    args = ap.parse_args()

    kb = args.kb_path
    if not kb.is_dir():
        print(f"error: kb path is not a directory: {kb}", file=sys.stderr)
        return 1
    root = args.project_root or kb.parent

    all_entries: list[dict] = []
    for md in sorted(kb.glob("*.md")):
        all_entries.extend(parse_kb_file(md, layer=md.stem))

    seen: dict[str, str] = {}
    for e in all_entries:
        sid = e["section_id"]
        if sid in seen:
            print(
                f"warning: duplicate section_id '{sid}' in {e['file']} (also in {seen[sid]})",
                file=sys.stderr,
            )
        else:
            seen[sid] = e["file"]

    # Allow-list of known kb file stems — a dotted string in markdown only
    # gets treated as a section_id if its prefix matches one of these. Random
    # prose like "node.js", "version 1.2.0", or "foo.bar.baz" is ignored.
    known_stems = {p.stem for p in kb.glob("*.md")}

    referenced = find_referenced_ids(root)
    existing = {e["section_id"] for e in all_entries}
    for sid in sorted(referenced - existing):
        prefix = sid.split(".", 1)[0]
        if prefix in known_stems:
            print(
                f"warning: broken reference: section_id '{sid}' not found in kb",
                file=sys.stderr,
            )

    out_path = kb / "index.json"
    out_path.write_text(
        json.dumps(all_entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out_path} ({len(all_entries)} sections)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
