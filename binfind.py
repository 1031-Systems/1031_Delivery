#!/usr/bin/env python3
"""Search a binary file for an ASCII string. Exit 0 if found, 1 if not."""

import sys


def search_binary(filepath: str, needle: str) -> bool:
    pattern = needle.encode("ascii")
    with open(filepath, "rb") as f:
        data = f.read()
    return pattern in data


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file> <string>", file=sys.stderr)
        sys.exit(2)

    filepath, needle = sys.argv[1], sys.argv[2]

    try:
        needle.encode("ascii")
    except UnicodeEncodeError:
        print("Error: search string contains non-ASCII characters.", file=sys.stderr)
        sys.exit(2)

    try:
        found = search_binary(filepath, needle)
    except FileNotFoundError:
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f"Error: permission denied: {filepath}", file=sys.stderr)
        sys.exit(2)

    if found:
        print(f"Found: {needle!r}")
        sys.exit(0)
    else:
        print(f"Not found: {needle!r}")
        sys.exit(1)


if __name__ == "__main__":
    main()

