import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
import logging

T = TypeVar('T', bound=BaseModel)

class Parser:
    @staticmethod
    def parse_json(json_str: str, schema: Type[T]) -> T:
        """Parses a JSON string into a Pydantic model. Handles common LLM errors like wrapping in 'properties'."""
        cleaned = json_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Try direct pydantic validation first
        try:
            return schema.model_validate_json(cleaned)
        except ValidationError as e:
            # Try to load as dict and unwrap common LLM wrapping issues
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    # If LLM wrapped it under a top-level "properties" key (common Gemma/Llama schema confusion)
                    if "properties" in data and "properties" not in schema.model_fields:
                        data = data["properties"]
                    # If it's wrapped in another common way, e.g. a single-key dict where the value has the fields
                    elif len(data) == 1 and list(data.keys())[0].lower() == schema.__name__.lower() and isinstance(list(data.values())[0], dict):
                        data = list(data.values())[0]
                    
                    # If any field in the schema is a list, but the model returned a dict with 'items' or similar
                    for field_name, field_info in schema.model_fields.items():
                        if field_name in data and isinstance(data[field_name], dict):
                            val = data[field_name]
                            for k in ["items", "values", "list", "array"]:
                                if k in val and isinstance(val[k], list):
                                    data[field_name] = val[k]
                                    break
                                    
                return schema.model_validate(data)
            except Exception as inner_e:
                logging.error(f"Failed to parse LLM output against {schema.__name__}: {e}\nRaw output: {json_str}")
                raise e


