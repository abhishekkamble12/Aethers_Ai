"""
CSV Timetable Loader with row-level validation
"""

import csv
from io import StringIO
from typing import List, Dict, Any, Tuple

REQUIRED_COLUMNS = [
    "class", "day", "period", "start", "end", "subject", "teacher_code", "venue", "outdoor", "locked"
]

def load_timetable_csv(file_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses a CSV timetable string and returns (records, errors).
    Errors are row-level human-readable error messages.
    """
    reader = csv.DictReader(StringIO(file_content.strip()))
    records = []
    errors = []
    
    # Check headers
    if not reader.fieldnames:
        return [], ["Empty CSV file or missing header line."]
        
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing_cols:
        return [], [f"Missing required columns in CSV header: {', '.join(missing_cols)}"]
        
    for row_idx, row in enumerate(reader, start=2): # 1-indexed, header is row 1
        row_errors = []
        
        # Check required fields not empty
        for col in ["class", "day", "period", "start", "end", "subject", "teacher_code"]:
            if not row.get(col, "").strip():
                row_errors.append(f"Row {row_idx}: '{col}' cannot be empty.")
                
        # Boolean conversions
        outdoor_raw = row.get("outdoor", "").strip().lower()
        if outdoor_raw in ("true", "1", "yes"):
            outdoor = True
        elif outdoor_raw in ("false", "0", "no"):
            outdoor = False
        else:
            row_errors.append(f"Row {row_idx}: invalid boolean value for 'outdoor': '{outdoor_raw}'")
            outdoor = False
            
        locked_raw = row.get("locked", "").strip().lower()
        if locked_raw in ("true", "1", "yes"):
            locked = True
        elif locked_raw in ("false", "0", "no"):
            locked = False
        else:
            row_errors.append(f"Row {row_idx}: invalid boolean value for 'locked': '{locked_raw}'")
            locked = False
            
        if row_errors:
            errors.extend(row_errors)
        else:
            records.append({
                "class": row["class"].strip(),
                "day": row["day"].strip(),
                "period": row["period"].strip(),
                "start": row["start"].strip(),
                "end": row["end"].strip(),
                "subject": row["subject"].strip(),
                "teacher_code": row["teacher_code"].strip(),
                "venue": row.get("venue", "").strip(),
                "outdoor": outdoor,
                "locked": locked
            })
            
    return records, errors
