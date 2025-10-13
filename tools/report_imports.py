"""Parse Python import profiling output and report slowest imports."""

import sys
import re
from typing import List, Tuple
from pathlib import Path


def parse_import_log(log_file: Path) -> List[Tuple[float, str]]:
    """Parse import log file and extract cumulative times.
    
    Args:
        log_file: Path to import log file
        
    Returns:
        List of (cumulative_time, module_name) tuples
    """
    imports = []
    
    # Pattern: import time: self [us] | cumulative | imported package
    # Example: import time:       123 |        456 | module.name
    pattern = re.compile(r'import time:\s+(\d+)\s+\|\s+(\d+)\s+\|\s+(.+)')
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                self_time = int(match.group(1))
                cumulative_time = int(match.group(2))
                module_name = match.group(3).strip()
                imports.append((cumulative_time, module_name))
    
    return imports


def format_time(microseconds: float) -> str:
    """Format microseconds to human-readable time.
    
    Args:
        microseconds: Time in microseconds
        
    Returns:
        Formatted time string
    """
    if microseconds >= 1_000_000:
        return f"{microseconds / 1_000_000:.2f}s"
    elif microseconds >= 1_000:
        return f"{microseconds / 1_000:.1f}ms"
    else:
        return f"{microseconds:.0f}μs"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python report_imports.py <import_profile.log>")
        sys.exit(1)
    
    log_file = Path(sys.argv[1])
    
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)
    
    # Parse imports
    imports = parse_import_log(log_file)
    
    if not imports:
        print("No import data found in log file.")
        sys.exit(1)
    
    # Sort by cumulative time (descending)
    imports.sort(reverse=True)
    
    # Display top 25
    print("=" * 80)
    print("TOP 25 SLOWEST IMPORTS (by cumulative time)")
    print("=" * 80)
    print(f"{'Rank':<6} {'Time':<12} {'Module':<60}")
    print("-" * 80)
    
    for i, (time_us, module) in enumerate(imports[:25], 1):
        time_str = format_time(time_us)
        # Truncate module name if too long
        module_display = module[:57] + "..." if len(module) > 60 else module
        print(f"{i:<6} {time_str:<12} {module_display:<60}")
    
    # Summary statistics
    total_time = sum(t for t, _ in imports)
    top10_time = sum(t for t, _ in imports[:10])
    
    print("-" * 80)
    print(f"Total import time: {format_time(total_time)}")
    print(f"Top 10 modules account for: {format_time(top10_time)} ({top10_time/total_time*100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()

