"""
Device Name Normalization and Branch Organization Script

This script:
1. Creates a branches table
2. Normalizes device names (removes PING-, IPs, etc.)
3. Associates devices with branches
4. Adds device_subtype for better categorization
"""

import re
import sqlite3
import uuid
from datetime import datetime
from collections import defaultdict

DB_PATH = "data/ward_ops.db"


def extract_branch_from_location(location):
    """Extract branch name from location string like 'Imereti / Kutaisi'"""
    if not location:
        return None, None

    parts = location.split(" / ")
    if len(parts) >= 2:
        region = parts[0].strip()
        branch = parts[1].strip()
        # Remove trailing IP info
        branch = re.sub(r'\s+\d+\.\d+\.\d+\.\d+.*$', '', branch)
        return region, branch
    elif len(parts) == 1:
        # Just branch name
        return None, parts[0].strip()

    return None, None


def normalize_device_name(name, hostname, device_type, location):
    """
    Normalize device names to follow pattern: BranchName-DeviceType-Identifier

    Rules:
    1. Remove PING- prefix
    2. Remove IP addresses
    3. Keep meaningful identifiers (AP, 881, NVR, ATM, etc.)
    4. Use branch name from location if name is generic
    5. Standardize separators to hyphens

    Examples:
        PING-Kutaisi1-AP -> Kutaisi1-AP
        Zugdidi3-881 -> Zugdidi3-Router
        Batumi2-1101 -> Batumi2-Switch
        Marjanishvili -> Marjanishvili-Switch
        PING-Vake-PayBox_10.159.X.X -> Vake-Paybox
    """
    if not name:
        return None

    # Extract branch name from location for context
    branch_name = None
    if location:
        parts = location.split(" / ")
        if len(parts) >= 2:
            branch_name = parts[1].strip()
            # Clean branch name from IP
            branch_name = re.sub(r'\s+\d+\.\d+\.\d+\.\d+.*$', '', branch_name)
            branch_name = re.sub(r'_\d+$', '', branch_name)  # Remove trailing numbers like Zugdidi_3

    # Start with original name
    clean_name = name

    # Remove PING- prefix
    clean_name = re.sub(r'^PING-', '', clean_name, flags=re.IGNORECASE)

    # Remove IP addresses from name (various patterns)
    clean_name = re.sub(r'_\d+\.\d+\.\d+\.\d+.*$', '', clean_name)
    clean_name = re.sub(r'\s+\d+\.\d+\.\d+\.\d+.*$', '', clean_name)

    # Remove trailing " -" which appears in some names
    clean_name = re.sub(r'\s+-\s*$', '', clean_name)

    # Standardize underscores to hyphens for consistency
    clean_name = clean_name.replace('_', '-')

    # Clean up multiple consecutive hyphens
    clean_name = re.sub(r'-+', '-', clean_name)

    # Remove trailing dashes and spaces
    clean_name = clean_name.strip(' -')

    # If name is too generic or empty, use branch name + device type
    generic_names = ['ruckusap', 'switch', 'router', 'ap', 'wifi', 'camera', 'atm', 'biostar', 'nvr']
    if clean_name.lower() in generic_names and branch_name:
        # Use branch name + device type suffix
        type_suffix = get_device_type_suffix(device_type, name)
        clean_name = f"{branch_name}-{type_suffix}"

    return clean_name


def get_device_type_suffix(device_type, original_name):
    """
    Get a standardized suffix based on device type

    Returns a short suffix like: Router, Switch, AP, ATM, NVR, Biostar, Paybox
    """
    if not device_type:
        return "Device"

    # Standardize device type names
    type_map = {
        'Router': 'Router',
        'Switch': 'Switch',
        'Access Point': 'AP',
        'ATM': 'ATM',
        'NVR': 'NVR',
        'Biostar': 'Biostar',
        'Paybox': 'Paybox',
        'Camera': 'Camera',
    }

    # Check if original name contains model numbers that should be preserved
    if original_name:
        # Preserve router model numbers
        if re.search(r'-(881|891|1111|1121|1101|ASR\d+)', original_name, re.IGNORECASE):
            model_match = re.search(r'-(881|891|1111|1121|1101|ASR\d+)', original_name, re.IGNORECASE)
            return f"Router-{model_match.group(1)}"

    return type_map.get(device_type, device_type)


def determine_device_subtype(name, device_type, hostname):
    """
    Determine device subtype for better categorization

    Returns: (subtype, floor_info, unit_number)
    """
    subtype = None
    floor_info = None
    unit_number = None

    name_lower = name.lower() if name else ''
    hostname_lower = hostname.lower() if hostname else ''

    # Extract floor information
    floor_match = re.search(r'floor[_\s]*(\d+)', name_lower + ' ' + hostname_lower, re.IGNORECASE)
    if floor_match:
        floor_info = f"Floor {floor_match.group(1)}"

    # Extract unit/instance number
    # Look for patterns like: Kutaisi1, Batumi2, Zugdidi3, etc.
    unit_match = re.search(r'(\w+?)(\d+)[-_]?(?:AP|881|1111|1101|SW|NVR|ATM|biostar)?$', name, re.IGNORECASE)
    if unit_match:
        unit_number = int(unit_match.group(2))

    # Determine subtype based on device_type and name patterns
    if device_type == 'Router':
        if '881' in name or '891' in name:
            subtype = 'Branch Router (881/891)'
        elif '1111' in name or '1121' in name or '1101' in name:
            subtype = 'Branch Router (1111/1121/1101)'
        elif 'ASR' in name.upper():
            subtype = 'Core Router (ASR)'
        else:
            subtype = 'Router'

    elif device_type == 'Switch':
        if 'Head Office' in name or 'MGMT' in name:
            subtype = 'Core Switch'
        elif 'campus' in name_lower or 'kampus' in name_lower:
            subtype = 'Campus Switch'
        else:
            subtype = 'Branch Switch'

    elif device_type == 'Access Point':
        if 'ruckusap' in name_lower and 'ruckusap' == name_lower:
            subtype = 'Generic AP (Needs Naming)'
        elif floor_info:
            subtype = f'Access Point ({floor_info})'
        else:
            subtype = 'Access Point'

    elif device_type == 'ATM':
        subtype = 'ATM Machine'

    elif device_type == 'NVR':
        subtype = 'Network Video Recorder'

    elif device_type == 'Biostar':
        subtype = 'Access Control'

    elif device_type == 'Paybox':
        subtype = 'Payment Terminal'

    elif device_type == 'Camera':
        subtype = 'IP Camera'

    return subtype, floor_info, unit_number


def create_branches_table(conn):
    """Create branches table"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            region TEXT,
            branch_code TEXT,
            address TEXT,
            is_active BOOLEAN DEFAULT 1,
            device_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_branches_name ON branches(name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_branches_region ON branches(region)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_branches_active ON branches(is_active)
    """)

    conn.commit()
    print("✓ Created branches table")


def add_device_columns(conn):
    """Add new columns to standalone_devices table"""
    cursor = conn.cursor()

    # Check which columns exist
    cursor.execute("PRAGMA table_info(standalone_devices)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("branch_id", "TEXT"),
        ("normalized_name", "TEXT"),
        ("device_subtype", "TEXT"),
        ("floor_info", "TEXT"),
        ("unit_number", "INTEGER"),
        ("original_name", "TEXT"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE standalone_devices ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise

    # Create indexes
    if "branch_id" not in existing_columns:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_branch ON standalone_devices(branch_id)")
    if "device_subtype" not in existing_columns:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_subtype ON standalone_devices(device_subtype)")

    conn.commit()
    print("✓ Updated standalone_devices table schema")


def extract_and_create_branches(conn):
    """Extract unique branches from device locations and create branch records"""
    cursor = conn.cursor()

    # Get all devices with locations
    cursor.execute("SELECT id, name, location FROM standalone_devices WHERE location IS NOT NULL AND location != ''")
    devices = cursor.fetchall()

    # Extract unique branches
    branches_data = {}  # branch_name -> {region, device_ids}

    for device_id, device_name, location in devices:
        region, branch_name = extract_branch_from_location(location)

        if branch_name:
            if branch_name not in branches_data:
                branches_data[branch_name] = {
                    'region': region,
                    'device_ids': []
                }
            branches_data[branch_name]['device_ids'].append(device_id)

    # Create branch records
    branch_count = 0
    for branch_name, data in branches_data.items():
        branch_id = str(uuid.uuid4())

        # Generate display name (capitalize properly)
        display_name = branch_name.title()

        # Generate branch code (first 3 letters + number if exists)
        code_match = re.search(r'(\w+?)(\d+)?$', branch_name)
        if code_match:
            base = code_match.group(1)[:3].upper()
            num = code_match.group(2) if code_match.group(2) else ''
            branch_code = f"{base}{num}"
        else:
            branch_code = branch_name[:3].upper()

        try:
            cursor.execute("""
                INSERT INTO branches (id, name, display_name, region, branch_code, device_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (branch_id, branch_name, display_name, data['region'], branch_code, len(data['device_ids'])))

            branch_count += 1
        except sqlite3.IntegrityError:
            # Branch already exists, get its ID
            cursor.execute("SELECT id FROM branches WHERE name = ?", (branch_name,))
            result = cursor.fetchone()
            if result:
                branch_id = result[0]

        # Update devices with branch_id
        for device_id in data['device_ids']:
            cursor.execute("UPDATE standalone_devices SET branch_id = ? WHERE id = ?", (branch_id, device_id))

    conn.commit()
    print(f"✓ Created {branch_count} branches")
    return branch_count


def normalize_all_devices(conn):
    """Normalize all device names"""
    cursor = conn.cursor()

    # Get all devices including location
    cursor.execute("SELECT id, name, hostname, device_type, location FROM standalone_devices")
    devices = cursor.fetchall()

    updated_count = 0
    for device_id, name, hostname, device_type, location in devices:
        # Store original name
        cursor.execute("UPDATE standalone_devices SET original_name = ? WHERE id = ? AND original_name IS NULL",
                      (name, device_id))

        # Normalize name with location context
        normalized = normalize_device_name(name, hostname, device_type, location)

        # Determine subtype and extract metadata
        subtype, floor_info, unit_number = determine_device_subtype(name, device_type, hostname)

        # Update device
        cursor.execute("""
            UPDATE standalone_devices
            SET normalized_name = ?,
                device_subtype = ?,
                floor_info = ?,
                unit_number = ?
            WHERE id = ?
        """, (normalized, subtype, floor_info, unit_number, device_id))

        updated_count += 1

    conn.commit()
    print(f"✓ Normalized {updated_count} device names")
    return updated_count


def generate_report(conn):
    """Generate a summary report of the migration"""
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("MIGRATION SUMMARY REPORT")
    print("="*70)

    # Total devices
    cursor.execute("SELECT COUNT(*) FROM standalone_devices")
    total_devices = cursor.fetchone()[0]
    print(f"\nTotal Devices: {total_devices}")

    # Devices by branch
    cursor.execute("""
        SELECT b.display_name, b.region, COUNT(d.id) as device_count
        FROM branches b
        LEFT JOIN standalone_devices d ON b.id = d.branch_id
        GROUP BY b.id
        ORDER BY device_count DESC
        LIMIT 10
    """)
    print("\nTop 10 Branches by Device Count:")
    print(f"{'Branch':<30} {'Region':<20} {'Devices':>10}")
    print("-" * 70)
    for row in cursor.fetchall():
        print(f"{row[0]:<30} {row[1] or 'N/A':<20} {row[2]:>10}")

    # Devices by type
    cursor.execute("""
        SELECT device_type, device_subtype, COUNT(*) as count
        FROM standalone_devices
        GROUP BY device_type, device_subtype
        ORDER BY count DESC
    """)
    print("\nDevices by Type:")
    print(f"{'Type':<20} {'Subtype':<35} {'Count':>10}")
    print("-" * 70)
    for row in cursor.fetchall():
        type_name = row[0] or 'Unknown'
        subtype_name = row[1] or 'General'
        print(f"{type_name:<20} {subtype_name:<35} {row[2]:>10}")

    # Devices without branches
    cursor.execute("SELECT COUNT(*) FROM standalone_devices WHERE branch_id IS NULL")
    no_branch_count = cursor.fetchone()[0]
    print(f"\nDevices without branch assignment: {no_branch_count}")

    # Sample normalized names
    cursor.execute("""
        SELECT original_name, normalized_name, device_type, device_subtype
        FROM standalone_devices
        WHERE original_name != normalized_name
        LIMIT 10
    """)
    print("\nSample Name Normalizations:")
    print(f"{'Original':<40} {'Normalized':<30} {'Type':<15}")
    print("-" * 90)
    for row in cursor.fetchall():
        print(f"{row[0]:<40} {row[1]:<30} {row[2]:<15}")

    print("\n" + "="*70)


def main():
    """Main migration function"""
    print("Starting Device Normalization and Branch Organization...")
    print("="*70 + "\n")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Step 1: Create branches table
        print("Step 1: Creating branches table...")
        create_branches_table(conn)

        # Step 2: Add new columns to devices table
        print("\nStep 2: Updating devices table schema...")
        add_device_columns(conn)

        # Step 3: Extract and create branch records
        print("\nStep 3: Extracting branches from device locations...")
        branch_count = extract_and_create_branches(conn)

        # Step 4: Normalize all device names
        print("\nStep 4: Normalizing device names...")
        device_count = normalize_all_devices(conn)

        # Step 5: Generate report
        generate_report(conn)

        print("\n✓ Migration completed successfully!")
        print(f"  - {branch_count} branches created")
        print(f"  - {device_count} devices normalized")

    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        conn.close()

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
