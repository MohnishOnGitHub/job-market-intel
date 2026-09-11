#!/usr/bin/env python3
"""Apply SQL migrations. Equivalent to: python -m app.db.migrate"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.migrate import main

if __name__ == "__main__":
    raise SystemExit(main())
