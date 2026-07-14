import json
from src.cmsd_schema.cmsd_document import CMSDDocument
from rich import print
from pydantic import TypeAdapter

schema = CMSDDocument.model_json_schema()
schema_str = json.dumps(CMSDDocument.model_json_schema())

with open('output.json', 'w') as f:
    f.write(json.dumps(schema_str, indent="\t", ensure_ascii=False))