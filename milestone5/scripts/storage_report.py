import argparse
import re
import sys
from collections import defaultdict

from sqlalchemy import select

from app.db import SessionLocal
from app.models import StoredFile
from app.ports.storage import ObjectStore


KEY_PATTERN = re.compile(
    r"^(uploads|direct)/"
    r"\d{4}/\d{2}/\d{2}/"
    r"[0-9a-fA-F-]{36}\.[A-Za-z0-9]+$"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()

    try:
        store = ObjectStore()

        # ObjectStore.list() already handles pagination.
        items = list(store.list(prefix=args.prefix))

        unstamped = []
        off_scheme = []
        bytes_by_prefix = defaultdict(int)
        grand_total = 0

        object_keys = set()

        for item in items:
            key = item.key
            size = item.size

            object_keys.add(key)

            # Count bytes by the first part of the key.
            top_prefix = key.split("/", 1)[0]
            bytes_by_prefix[top_prefix] += size
            grand_total += size

            # Check if the key follows the correct format.
            if not KEY_PATTERN.match(key):
                off_scheme.append(key)

            # Normal API uploads should have original-name metadata.
            info = store.head(key)

            if info is None:
                unstamped.append(key)
            else:
                metadata = info.get("Metadata", {})

                if not metadata.get("original-name"):
                    unstamped.append(key)

        # Compare object storage against the relational database index.
        db = SessionLocal()

        try:
            rows = db.scalars(
                select(StoredFile)
            ).all()

            database_keys = {
                row.key
                for row in rows
            }

        finally:
            db.close()

        object_without_row = sorted(
            object_keys - database_keys
        )

        row_without_object = sorted(
            database_keys - object_keys
        )

        print("Storage Report")
        print("==============")
        print(f"Objects checked: {len(items)}")
        print(f"Database rows checked: {len(database_keys)}")
        print()

        print("Unstamped objects:")
        if unstamped:
            for key in unstamped:
                print(f"  {key}")
        else:
            print("  None")

        print()

        print("Off-scheme keys:")
        if off_scheme:
            for key in off_scheme:
                print(f"  {key}")
        else:
            print("  None")

        print()

        print("Objects with no database row:")
        if object_without_row:
            for key in object_without_row:
                print(f"  {key}")
        else:
            print("  None")

        print()

        print("Database rows with no object:")
        if row_without_object:
            for key in row_without_object:
                print(f"  {key}")
        else:
            print("  None")

        print()

        print("Bytes by prefix:")
        if bytes_by_prefix:
            for prefix in sorted(bytes_by_prefix):
                print(
                    f"  {prefix}: "
                    f"{bytes_by_prefix[prefix]} bytes"
                )
        else:
            print("  None")

        print(
            f"Grand total: {grand_total} bytes"
        )

        dirty = (
            unstamped
            or off_scheme
            or object_without_row
            or row_without_object
        )

        if dirty:
            return 1

        return 0

    except Exception as error:
        print(
            f"Error: {error}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())