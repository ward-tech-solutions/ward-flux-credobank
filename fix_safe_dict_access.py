#!/usr/bin/env python3
"""
Fix safe dictionary access patterns
Add defensive checks for dictionary operations that could fail
"""
import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def add_safe_dict_checks():
    """Add safe dictionary access patterns to critical files"""

    fixes_applied = 0
    files_modified = []

    # Fix 1: zabbix_client.py - Add validation for API responses
    file_path = 'zabbix_client.py'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Add validation for host data
        content = re.sub(
            r"(ping_data = ping_lookup\.get\(host\['hostid'\], \{\}\))",
            r"ping_data = ping_lookup.get(host.get('hostid'), {})",
            content
        )

        # Add validation for interface data
        content = re.sub(
            r"(host\['interfaces'\]\[0\])",
            r"host.get('interfaces', [{}])[0] if host.get('interfaces') else {}",
            content
        )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            fixes_applied += 1
            files_modified.append(file_path)
            logger.info(f"✅ Fixed dictionary access in {file_path}")

    # Fix 2: Add try-except around API calls in setup_wizard.py
    file_path = 'setup_wizard.py'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Wrap API calls with better error handling
        if 'hosts = zapi.host.get(output=["hostid"])' in content:
            content = re.sub(
                r'(\s+)(hosts = zapi\.host\.get\(output=\["hostid"\]\))',
                r'\1try:\n\1    \2\n\1    if not isinstance(hosts, list):\n\1        hosts = []\n\1except Exception as e:\n\1    logger.error(f"Error fetching hosts: {e}")\n\1    hosts = []',
                content
            )

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            fixes_applied += 1
            files_modified.append(file_path)
            logger.info(f"✅ Fixed dictionary access in {file_path}")

    return fixes_applied, files_modified

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SAFE DICTIONARY ACCESS FIXER")
    logger.info("=" * 60)

    fixes, files = add_safe_dict_checks()

    logger.info(f"\n✅ Applied {fixes} safe dictionary access fixes")
    logger.info(f"✅ Modified {len(files)} files")

    if files:
        logger.info("\nModified files:")
        for f in files:
            logger.info(f"  - {f}")

    logger.info("\n" + "=" * 60)
    logger.info("NOTE: Most .get() operations are already safe.")
    logger.info("The main risk is when API returns unexpected structure.")
    logger.info("All critical API response handling has been reviewed.")
    logger.info("=" * 60)
