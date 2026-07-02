from typing import Dict
from .models import ApplicationRecord

# In-memory database of applications
applications: Dict[str, ApplicationRecord] = {}
