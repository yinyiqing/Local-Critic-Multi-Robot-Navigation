#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


CASE_RE = re.compile(
    r"^\s*(?P<case>[^|]+?)\s+\|\s+episodes=(?P<episodes>\d+)\s+\|\s+"
    r"success_rate=(?P<success>[0-9.]+)\s+\|\s+collision_rate=(?P<collision>[0-9.]+)\s+\|\s+"
    r"unresolved_rate=(?P<unresolved>[0-9.]+)\s+\|\s+full_success_rate=(?P<full>[0-9.]+)"
)


def parse_case_summary(log_path):
    rows = {}
    for line in Path(log_path).read_text(encoding="utf-8").splitlines():
        match = CASE_RE.match(line)
        if not match:
            continue
        case_name = match.group("case").strip()
        rows[case_name] = {
            "episodes": int(match.group("episodes")),
            "success_rate": float(match.group("success")),
            "collision_rate": float(match.group("collision")),
            "unresolved_rate": float(match.group("unresolved")),
            "full_success_rate": float(match.group("full")),
        }
    if not rows:
        raise ValueError(f"No case summary rows found in {log_path}")
    return rows


def better_actor(left_stats, right_stats):
    left_key = (
        left_stats["full_success_rate"],
        left_stats["success_rate"],
        -left_stats["collision_rate"],
        -left_stats["unresolved_rate"],
    )
    right_key = (
        right_stats["full_success_rate"],
        right_stats["success_rate"],
        -right_stats["collision_rate"],
        -right_stats["unresolved_rate"],
    )
    return "left" if left_key >= right_key else "right"


def main():
    parser = argparse.ArgumentParser(
        description="Compare case-level test summaries and build a case_oracle map."
    )
    parser.add_argument("--left-log", required=True)
    parser.add_argument("--right-log", required=True)
    parser.add_argument("--left-mode", default="standard")
    parser.add_argument("--right-mode", default="dense")
    parser.add_argument("--default-mode", default="standard")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if args.left_mode not in ("standard", "dense"):
        raise ValueError("--left-mode must be standard or dense")
    if args.right_mode not in ("standard", "dense"):
        raise ValueError("--right-mode must be standard or dense")
    if args.default_mode not in ("standard", "dense"):
        raise ValueError("--default-mode must be standard or dense")

    left_cases = parse_case_summary(args.left_log)
    right_cases = parse_case_summary(args.right_log)
    shared_cases = sorted(set(left_cases) & set(right_cases))
    if not shared_cases:
        raise ValueError("No shared case names found between the two logs")

    result = {"default": args.default_mode}
    comparison = {}
    for case_name in shared_cases:
        chosen = better_actor(left_cases[case_name], right_cases[case_name])
        result[case_name] = args.left_mode if chosen == "left" else args.right_mode
        comparison[case_name] = {
            "chosen_mode": result[case_name],
            "left": left_cases[case_name],
            "right": right_cases[case_name],
        }

    payload = {"oracle_map": result, "comparison": comparison}
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote oracle map to {args.output}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
