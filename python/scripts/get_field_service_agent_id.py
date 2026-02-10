"""Print Field Service Assistant agent UUID (for test_generate_stream)."""
import sys
sys.path.insert(0, ".")
from app.db import session_scope
from app.models import Agent

with session_scope() as s:
    a = s.query(Agent).filter(Agent.name == "Field Service Assistant", Agent.is_deleted.is_(False)).first()
    if a:
        print(str(a.id))
    else:
        print("", file=sys.stderr)
        sys.exit(1)
