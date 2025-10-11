"""
Clean up branch names - remove trailing underscores and IPs
"""
import sqlite3
import re

DB_PATH = "data/ward_ops.db"

def clean_branch_name(name):
    """Clean branch name"""
    if not name:
        return name

    # Remove trailing underscores
    name = name.rstrip('_')

    # Remove IP addresses at the end
    name = re.sub(r'\s+\d+\.\d+\.\d+.*$', '', name)
    name = re.sub(r'\s+\d+\.\d+.*$', '', name)

    # Clean up extra spaces
    name = ' '.join(name.split())

    return name.strip()

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all branches
    cursor.execute("SELECT id, name, display_name, device_count FROM branches ORDER BY device_count DESC")
    branches = cursor.fetchall()

    # Track which clean names we've seen
    seen_names = {}
    updated = 0
    merged = 0

    for branch_id, name, display_name, device_count in branches:
        clean_name = clean_branch_name(name)
        clean_display = clean_branch_name(display_name)

        if clean_name in seen_names:
            # Merge this branch into the existing one
            existing_id = seen_names[clean_name]
            print(f"Merging: '{name}' ({branch_id}) -> '{clean_name}' ({existing_id})")

            # Update devices to point to the existing branch
            cursor.execute(
                "UPDATE standalone_devices SET branch_id = ? WHERE branch_id = ?",
                (existing_id, branch_id)
            )

            # Delete this duplicate branch
            cursor.execute("DELETE FROM branches WHERE id = ?", (branch_id,))
            merged += 1
        else:
            # Update this branch's name if needed
            if clean_name != name or clean_display != display_name:
                cursor.execute(
                    "UPDATE branches SET name = ?, display_name = ? WHERE id = ?",
                    (clean_name, clean_display, branch_id)
                )
                print(f"Updated: '{name}' -> '{clean_name}'")
                updated += 1

            seen_names[clean_name] = branch_id

    # Update device counts
    cursor.execute("""
        UPDATE branches
        SET device_count = (
            SELECT COUNT(*) FROM standalone_devices WHERE branch_id = branches.id
        )
    """)

    conn.commit()
    conn.close()

    print(f"\n✓ Updated {updated} branch names")
    print(f"✓ Merged {merged} duplicate branches")

if __name__ == "__main__":
    main()
