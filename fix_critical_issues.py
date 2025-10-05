#!/usr/bin/env python3
"""
WARD Tech Solutions - Automated Critical Bug Fixes
Fixes all critical issues identified in QA
"""
import re
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class BugFixer:
    def __init__(self):
        self.fixes_applied = 0
        self.files_modified = []

    def fix_bare_except(self, filepath):
        """Fix bare except clauses"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            original_content = content

        # Add logging import if not present
        if "import logging" not in content and "except Exception" in content:
            # Find first import statement
            import_match = re.search(r"^(from|import) ", content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.start()
                content = content[:insert_pos] + "import logging\n" + content[insert_pos:]

        # Pattern 1: except: with single line
        pattern1 = re.compile(r"(\s+)except:\s*\n(\s+)(\w+)", re.MULTILINE)
        content = pattern1.sub(
            r'\1except Exception as e:\n\1    logging.getLogger(__name__).error(f"Error: {e}")\n\2\3', content
        )

        # Pattern 2: except: with pass
        pattern2 = re.compile(r"(\s+)except:\s*\n(\s+)pass", re.MULTILINE)
        content = pattern2.sub(
            r'\1except Exception as e:\n\2logging.getLogger(__name__).error(f"Error: {e}")\n\2pass', content
        )

        # Pattern 3: except: with return
        pattern3 = re.compile(r"(\s+)except:\s*\n(\s+)return", re.MULTILINE)
        content = pattern3.sub(
            r'\1except Exception as e:\n\2logging.getLogger(__name__).error(f"Error: {e}")\n\2return', content
        )

        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            self.files_modified.append(filepath)
            logger.info(f"✓ Fixed bare except in {filepath}")
            return True
        return False

    def fix_main_database(self):
        """Fix hardcoded database in main.py"""
        filepath = "main.py"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Find and replace the hardcoded database function
        old_function = '''def get_monitored_groupids():
    """Get list of monitored group IDs from database"""
    import sqlite3
    conn = sqlite3.connect('data/ward_ops.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT groupid FROM monitored_hostgroups WHERE is_active = 1
    """)
    groupids = [row['groupid'] for row in cursor.fetchall()]
    conn.close()
    return groupids if groupids else None'''

        new_function = '''def get_monitored_groupids():
    """Get list of monitored group IDs from database"""
    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT groupid FROM monitored_hostgroups WHERE is_active = 1")
        )
        groupids = [row[0] for row in result.fetchall()]
        return groupids if groupids else None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting monitored groups: {e}")
        return None
    finally:
        db.close()'''

        if old_function in content:
            content = content.replace(old_function, new_function)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            self.files_modified.append(filepath)
            logger.info(f"✓ Fixed hardcoded database in {filepath}")
            return True
        else:
            logger.warning("Could not find exact match for database function")
            return False

    def replace_print_with_logging(self, filepath):
        """Replace print statements with logging"""
        # Skip test files
        if "test" in filepath.lower() or "fix_" in filepath:
            return False

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            original_content = content

        # Add logging import if not present
        if "import logging" not in content:
            import_match = re.search(r"^(from|import) ", content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.start()
                content = content[:insert_pos] + "import logging\n" + content[insert_pos:]

        # Add logger if not present
        if "logger = logging.getLogger" not in content and "logging.getLogger" not in content:
            # Add after imports
            last_import = list(re.finditer(r"^(from|import) .+$", content, re.MULTILINE))
            if last_import:
                insert_pos = last_import[-1].end() + 1
                content = content[:insert_pos] + "\nlogger = logging.getLogger(__name__)\n" + content[insert_pos:]

        # Replace print statements
        # Pattern: print("message") or print('message') or print(f"message")
        content = re.sub(r'\bprint\((f?["\'].*?["\'])\)', r"logger.info(\1)", content)

        # Pattern: print(variable)
        content = re.sub(r"\bprint\(([^)]+)\)", r'logger.info(f"{str(\1)}")', content)

        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            logger.info(f"✓ Replaced print with logging in {filepath}")
            return True
        return False

    def fix_long_lines(self, filepath):
        """Break long lines (basic formatting)"""
        # This is complex - just flag for now
        # Use black formatter instead
        pass

    def run_all_fixes(self):
        """Run all fixes"""
        logger.info("=" * 60)
        logger.info("🔧 WARD Tech Solutions - Automated Bug Fixes")
        logger.info("=" * 60)

        # Fix 1: Bare except clauses
        logger.info("\n📋 Fix 1: Bare Except Clauses")
        logger.info("-" * 60)
        for root, dirs, files in os.walk("."):
            if "venv" in root or "__pycache__" in root or "node_modules" in root:
                continue
            for file in files:
                if file.endswith(".py") and not file.startswith("fix_"):
                    filepath = os.path.join(root, file)
                    self.fix_bare_except(filepath)

        # Fix 2: Hardcoded database
        logger.info("\n📋 Fix 2: Hardcoded Database")
        logger.info("-" * 60)
        self.fix_main_database()

        # Fix 3: Print statements
        logger.info("\n📋 Fix 3: Print Statements → Logging")
        logger.info("-" * 60)
        for root, dirs, files in os.walk("."):
            if "venv" in root or "__pycache__" in root or "node_modules" in root:
                continue
            for file in files:
                if file.endswith(".py") and not file.startswith("fix_"):
                    filepath = os.path.join(root, file)
                    self.replace_print_with_logging(filepath)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ FIXES COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Total fixes applied: {self.fixes_applied}")
        logger.info(f"Files modified: {len(set(self.files_modified))}")
        logger.info("\nModified files:")
        for f in sorted(set(self.files_modified)):
            logger.info(f"  • {f}")

        logger.info("\n📝 Next Steps:")
        logger.info("1. Review changes: git diff")
        logger.info("2. Test the application")
        logger.info("3. Run: black . (for code formatting)")
        logger.info("4. Run: python3 -m pytest tests/ -v")
        logger.info("5. Commit changes")


if __name__ == "__main__":
    fixer = BugFixer()
    fixer.run_all_fixes()
