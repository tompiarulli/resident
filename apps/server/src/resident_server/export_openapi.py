"""Write the OpenAPI spec to a file: ``python -m resident_server.export_openapi out.json``."""

import json
import sys
from pathlib import Path

from resident_server.main import app

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {out}")
