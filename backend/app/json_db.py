import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime
import threading

DB_FILE = Path(__file__).parent.parent / "data.json"
_lock = threading.Lock()

def _read_db():
    default_data = {"uploads": [], "chunks": [], "outputs": [], "output_chunks": []}
    
    if not DB_FILE.exists():
        return default_data
    
    try:
        with open(DB_FILE, "r") as f:
            content = f.read().strip()
            
            # Handle empty file
            if not content:
                print(f"Warning: {DB_FILE} is empty. Using default data structure.")
                return default_data
            
            # Parse JSON
            data = json.loads(content)
            
            # Handle non-dict JSON (e.g., array, null, string)
            if not isinstance(data, dict):
                print(f"Warning: {DB_FILE} contains non-object data. Using default data structure.")
                return default_data
            
            # Ensure all required tables exist
            for table in ["uploads", "chunks", "outputs", "output_chunks"]:
                if table not in data:
                    data[table] = []
            
            return data
            
    except json.JSONDecodeError as e:
        print(f"Error: {DB_FILE} contains invalid JSON: {e}. Using default data structure.")
        return default_data
    except Exception as e:
        print(f"Error reading {DB_FILE}: {e}. Using default data structure.")
        return default_data

def _write_db(data):
    temp_file = DB_FILE.with_suffix('.tmp')
    try:
        # Ensure the directory exists
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Write atomically by writing to a temp file first
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Rename to actual file (atomic on most systems)
        temp_file.replace(DB_FILE)
        
    except Exception as e:
        print(f"Error writing to {DB_FILE}: {e}")
        # Clean up temp file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise

class MockResponse:
    def __init__(self, data):
        self.data = data

class Table:
    def __init__(self, name):
        self.name = name
        self._filters = []
        self._order_field = None
        self._insert_record = None
    
    def insert(self, record):
        self._insert_record = record
        return self
    
    def execute(self):
        if self._insert_record is not None:
            with _lock:
                db = _read_db()
                if "created_at" not in self._insert_record:
                    self._insert_record["created_at"] = datetime.utcnow().isoformat()
                db[self.name].append(self._insert_record)
                _write_db(db)
            return MockResponse([self._insert_record])
        return MockResponse([])
    
    def update(self, updates):
        return TableUpdate(self.name, self._filters, updates)
    
    def select(self, fields="*"):
        return TableSelect(self.name, fields, self._filters, self._order_field)
    
    def eq(self, field, value):
        new_table = Table(self.name)
        new_table._filters = self._filters + [(field, value)]
        return new_table
    
    def order(self, field):
        new_table = Table(self.name)
        new_table._filters = self._filters
        new_table._order_field = field
        return new_table

class TableUpdate:
    def __init__(self, table_name, filters, updates):
        self.table_name = table_name
        self.filters = filters
        self.updates = updates
    
    def eq(self, field, value):
        self.filters.append((field, value))
        return self
    
    def execute(self):
        with _lock:
            db = _read_db()
            for record in db[self.table_name]:
                if all(record.get(k) == v for k, v in self.filters):
                    record.update(self.updates)
            _write_db(db)
        return MockResponse([])

class TableSelect:
    def __init__(self, table_name, fields, filters, order_field):
        self.table_name = table_name
        self.fields = fields
        self.filters = filters
        self.order_field = order_field
    
    def eq(self, field, value):
        self.filters.append((field, value))
        return self
    
    def order(self, field):
        self.order_field = field
        return self
    
    def execute(self):
        with _lock:
            db = _read_db()
            results = db[self.table_name]
            
            # Apply filters
            for field, value in self.filters:
                results = [r for r in results if r.get(field) == value]
            
            # Apply ordering
            if self.order_field:
                results = sorted(results, key=lambda x: x.get(self.order_field, ""))
            
            return MockResponse(results)

class JsonDB:
    def table(self, name):
        return Table(name)

json_db = JsonDB()

