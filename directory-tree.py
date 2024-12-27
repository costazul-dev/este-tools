#!/usr/bin/env python3

"""
Directory Tree Generator

A script that generates a visual tree-like representation of a directory structure.
Given a directory path as input, it recursively maps all subdirectories and files,
displaying them in a hierarchical format similar to the Unix 'tree' command.

Features:
- Recursive directory traversal
- Shell-like tree formatting with branch connectors (├── and └──)
- Option to either print to console or save to a text file
- File output named after the root directory (directory_name_structure.txt)
- Cross-platform compatibility
- No external dependencies

Usage:
    ./directory_tree.py <directory_path>

Example output:
my_project/
├── src/
│   ├── main.py
│   └── utils/
│       ├── helper.py
│       └── config.py
└── README.md
"""

import os
import sys
from pathlib import Path

def print_tree(dir_path, prefix="", output_file=None):
    entries = sorted(os.scandir(dir_path), key=lambda e: e.name)
    total = len(entries)
    
    for idx, entry in enumerate(entries):
        connector = "└── " if idx == total - 1 else "├── "
        line = f"{prefix}{connector}{entry.name}"
        
        if output_file:
            output_file.write(line + "\n")
        else:
            print(line)
            
        if entry.is_dir():
            new_prefix = prefix + ("    " if idx == total - 1 else "│   ")
            print_tree(entry.path, new_prefix, output_file)

def main():
    if len(sys.argv) != 2:
        print("Usage: ./directory-tree.py <directory_path>")
        sys.exit(1)
        
    dir_path = Path(sys.argv[1])
    if not dir_path.is_dir():
        print(f"Error: {dir_path} is not a directory")
        sys.exit(1)
        
    print(f"\n{dir_path.name}/")
    output_path = f"{dir_path.name}_structure.txt"
    
    try:
        if input("Save to file? (y/n): ").lower().startswith('y'):
            with open(output_path, 'w') as f:
                f.write(f"{dir_path.name}/\n")
                print_tree(dir_path, output_file=f)
            print(f"Structure saved to {output_path}")
        else:
            print_tree(dir_path)
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(0)

if __name__ == "__main__":
    main()