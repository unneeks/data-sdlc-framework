import yaml
import json
import glob
import os
from datetime import date, datetime

def default_converter(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

source_dir = '/Users/ranjitpillai/apps/2026/code/agent-demo-de/agentic-data-engineering/metamodel-registry'
dest_dir = '/Users/ranjitpillai/data-sdlc-framework/apps/web/src/data'

os.makedirs(dest_dir, exist_ok=True)

metamodel = {}

# Process all YAML files in the root registry
for filepath in glob.glob(f"{source_dir}/*.yaml"):
    filename = os.path.basename(filepath)
    key = filename.replace('.yaml', '')
    
    with open(filepath, 'r') as f:
        try:
            data = yaml.safe_load(f)
            metamodel[key] = data
        except Exception as e:
            print(f"Error parsing {filename}: {e}")

# Save the full metamodel
with open(f"{dest_dir}/metamodel.json", 'w') as f:
    json.dump(metamodel, f, indent=2, default=default_converter)

print("Conversion complete.")
