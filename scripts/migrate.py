#!/usr/bin/env python3
"""Apply SQL migrations. Equivalent to: python -m app.db.migrate"""

from __future__ import annotations

from app.db.migrate import main

if __name__ == "__main__":
    raise SystemExit(main())
