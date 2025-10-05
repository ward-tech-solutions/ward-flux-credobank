"""
WARD TECH SOLUTIONS - Automated Bug Finder
Scans codebase for common issues and potential bugs
"""
import logging
import os
import re
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

class BugFinder:
    def __init__(self):
        self.issues = defaultdict(list)
        self.file_count = 0
        self.line_count = 0

    def scan_directory(self, directory="."):
        """Scan all Python files in directory"""
        for root, dirs, files in os.walk(directory):
            # Skip virtual env and caches
            if 'venv' in root or '__pycache__' in root or 'node_modules' in root:
                continue

            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    self.scan_file(filepath)

    def scan_file(self, filepath):
        """Scan a single file for issues"""
        self.file_count += 1

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.line_count += len(lines)

                for i, line in enumerate(lines, 1):
                    self.check_line(filepath, i, line, lines)

        except Exception as e:
            self.issues['File Read Errors'].append(f"{filepath}: {e}")

    def check_line(self, filepath, line_num, line, all_lines):
        """Check a single line for issues"""

        # 1. SQL Injection Risk
        if re.search(r'execute\([^)]*%s|execute\([^)]*\+|execute\([^)]*f"', line):
            if 'text(' not in line and 'sqlalchemy' not in line:
                self.issues['SQL Injection Risk'].append(
                    f"{filepath}:{line_num} - Potential SQL injection: {line.strip()}"
                )

        # 2. Hardcoded Credentials
        if re.search(r'password\s*=\s*["\'][^"\']{3,}["\']', line, re.IGNORECASE):
            if 'example' not in filepath.lower() and '.env' not in filepath:
                self.issues['Hardcoded Credentials'].append(
                    f"{filepath}:{line_num} - Hardcoded password: {line.strip()}"
                )

        # 3. Debug Mode Enabled
        if re.search(r'DEBUG\s*=\s*True', line, re.IGNORECASE):
            self.issues['Debug Mode'].append(
                f"{filepath}:{line_num} - Debug mode enabled: {line.strip()}"
                )

        # 4. Bare Except Clauses
        if re.search(r'except\s*:', line):
            self.issues['Bare Except'].append(
                f"{filepath}:{line_num} - Bare except clause (catches everything): {line.strip()}"
            )

        # 5. Print Statements (should use logging)
        if re.search(r'^\s*print\(', line):
            if 'test' not in filepath.lower():
                self.issues['Print Statements'].append(
                    f"{filepath}:{line_num} - Using print() instead of logging: {line.strip()}"
                )

        # 6. Unused Imports
        if re.search(r'^import |^from .* import', line):
            # This is complex, just flag for manual review
            pass

        # 7. TODO/FIXME Comments
        if re.search(r'#.*TODO|#.*FIXME|#.*HACK|#.*XXX', line, re.IGNORECASE):
            self.issues['TODO/FIXME Comments'].append(
                f"{filepath}:{line_num} - {line.strip()}"
            )

        # 8. Missing Error Handling
        if '.get(' in line or '.pop(' in line:
            if '[' in line and ']' in line:
                # Check if there's error handling nearby
                context = all_lines[max(0, line_num-3):min(len(all_lines), line_num+3)]
                if not any('try:' in l or 'except' in l for l in context):
                    self.issues['Missing Error Handling'].append(
                        f"{filepath}:{line_num} - Dictionary access without error handling: {line.strip()}"
                    )

        # 9. eval() or exec() usage (dangerous)
        if re.search(r'\beval\(|\bexec\(', line):
            self.issues['Dangerous Functions'].append(
                f"{filepath}:{line_num} - Using eval() or exec(): {line.strip()}"
            )

        # 10. Weak Cryptography
        if re.search(r'md5|sha1|DES', line, re.IGNORECASE):
            self.issues['Weak Cryptography'].append(
                f"{filepath}:{line_num} - Weak crypto algorithm: {line.strip()}"
            )

        # 11. Missing Input Validation
        if 'request.' in line and ('json()' in line or 'form' in line or 'args' in line):
            if '[' in line and ']' in line:
                self.issues['Potential Input Validation'].append(
                    f"{filepath}:{line_num} - Check input validation: {line.strip()}"
                )

        # 12. Insecure Randomness
        if 'random.random' in line or 'random.choice' in line:
            if 'secret' in line.lower() or 'token' in line.lower() or 'password' in line.lower():
                self.issues['Insecure Random'].append(
                    f"{filepath}:{line_num} - Use secrets module for crypto: {line.strip()}"
                )

        # 13. Race Conditions
        if re.search(r'if\s+os\.path\.exists.*:.*open\(', ' '.join(all_lines[line_num:line_num+2])):
            self.issues['Race Condition'].append(
                f"{filepath}:{line_num} - TOCTOU race condition: {line.strip()}"
            )

        # 14. Resource Leaks
        if 'open(' in line and 'with' not in line:
            if 'close()' not in ' '.join(all_lines[line_num:line_num+5]):
                self.issues['Resource Leak'].append(
                    f"{filepath}:{line_num} - File not closed properly: {line.strip()}"
                )

        # 15. Long Lines
        if len(line) > 120:
            self.issues['Code Style'].append(
                f"{filepath}:{line_num} - Line too long ({len(line)} chars)"
            )

    def generate_report(self):
        """Generate bug report"""
        logger.info(f"{str("\n" + "="*80)}")
        logger.info("🔍 WARD TECH SOLUTIONS - AUTOMATED BUG FINDER REPORT")
        logger.info(f"{str("="*80)}")

        logger.info(f"\n📊 Scan Statistics:")
        logger.info(f"   Files Scanned: {self.file_count}")
        logger.info(f"   Lines Scanned: {self.line_count}")
        logger.info(f"   Issue Categories: {len(self.issues)}")
        logger.info(f"   Total Issues: {sum(len(v) for v in self.issues.values())}")

        if not self.issues:
            logger.info("\n✅ NO ISSUES FOUND! Code looks clean.")
            return

        logger.info(f"{str("\n" + "="*80)}")
        logger.info("🐛 ISSUES FOUND (sorted by severity):")
        logger.info(f"{str("="*80)}")

        # Sort by severity
        severity_order = [
            'SQL Injection Risk',
            'Dangerous Functions',
            'Hardcoded Credentials',
            'Weak Cryptography',
            'Insecure Random',
            'Race Condition',
            'Resource Leak',
            'Missing Error Handling',
            'Debug Mode',
            'Bare Except',
            'Potential Input Validation',
            'Print Statements',
            'TODO/FIXME Comments',
            'Code Style'
        ]

        for category in severity_order:
            if category in self.issues:
                issues = self.issues[category]
                logger.info(f"\n🔴 {category} ({len(issues)} issues):")
                logger.info(f"{str("-" * 80)}")

                for issue in issues[:10]:  # Show max 10 per category
                    logger.info(f"   • {issue}")

                if len(issues) > 10:
                    logger.info(f"   ... and {len(issues) - 10} more")

        # Show other categories
        for category, issues in self.issues.items():
            if category not in severity_order:
                logger.info(f"\n⚠️  {category} ({len(issues)} issues):")
                logger.info(f"{str("-" * 80)}")
                for issue in issues[:5]:
                    logger.info(f"   • {issue}")
                if len(issues) > 5:
                    logger.info(f"   ... and {len(issues) - 5} more")

    def save_report(self, filename="BUG_REPORT.md"):
        """Save report to markdown file"""
        with open(filename, 'w') as f:
            f.write("# 🐛 WARD Tech Solutions - Automated Bug Report\n\n")
            f.write(f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 📊 Scan Statistics\n\n")
            f.write(f"- Files Scanned: **{self.file_count}**\n")
            f.write(f"- Lines Scanned: **{self.line_count}**\n")
            f.write(f"- Issue Categories: **{len(self.issues)}**\n")
            f.write(f"- Total Issues: **{sum(len(v) for v in self.issues.values())}**\n\n")

            if not self.issues:
                f.write("## ✅ NO ISSUES FOUND!\n\n")
                return

            f.write("## 🐛 Issues Found\n\n")

            for category, issues in sorted(self.issues.items()):
                f.write(f"### {category} ({len(issues)})\n\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                f.write("\n")

        logger.info(f"\n📄 Full report saved to: {filename}")


if __name__ == "__main__":
    scanner = BugFinder()

    logger.info("🔍 Scanning codebase for potential bugs...")
    scanner.scan_directory(".")

    scanner.generate_report()
    scanner.save_report("BUG_REPORT.md")

    logger.info(f"{str("\n" + "="*80)}")
    logger.info("✅ Scan complete!")
    logger.info(f"{str("="*80)}")
