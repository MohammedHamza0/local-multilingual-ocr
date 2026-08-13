#!/usr/bin/env python3
"""
arabic_pdf_triage.py (Archived Standalone Pre-OCR Gate Script)
------------------------------------------------------------
Superseded by app/services/triage_service.py in the main web application.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from pypdf import PdfReader

# See app/services/triage_service.py for the active production engine.
