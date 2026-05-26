"""
Mapping Engine — Uses RAG retrieval + LLM to propose field mappings
between API response payloads and CMSD schema entities.
Enhanced: multi-endpoint support, raw/converted values, smart reanalysis.
"""

import json
import logging
from typing import Any

from .llm import llm_client
from .rag.retriever import retriever

logger = logging.getLogger("ai-agent.mapping-engine")

# Known CMSD entities and their key fields (for validation)
CMSD_ENTITY_FIELDS: dict[str, list[str]] = {
    "Resource": ["identifier", "name", "description", "resource_type", "capacity",
                 "availability", "mttr", "mtbf", "mcbf", "reliability",
                 "cycle_time", "size", "decision_rule", "routing_rule",
                 "transport_capacity", "worker_count", "current_status"],
    "ResourceClass": ["identifier", "name", "description", "resource_type"],
    "PartType": ["identifier", "name", "description", "size", "weight"],
    "Part": ["identifier", "production_status", "size"],
    "BillOfMaterials": ["identifier", "name", "description", "components"],
    "BOMComponent": ["identifier", "quantity"],
    "ProcessPlan": ["identifier", "name", "description", "processes"],
    "Process": ["identifier", "name", "description", "duration",
                "setup_time", "load_time", "unload_time"],
    "Order": ["identifier", "status", "due_date", "release_date", "order_lines"],
    "OrderLine": ["identifier", "status", "due_date", "release_date",
                  "quantity", "part_description"],
    "Calendar": ["identifier", "name", "description", "production_days_per_year",
                 "shifts", "holidays"],
    "Shift": ["identifier", "day_of_week", "start_time", "end_time", "breaks"],
    "Break": ["identifier", "start_time", "end_time"],
    "Holiday": ["identifier", "holiday_date"],
    "Connection": ["identifier", "from_resource_id", "to_resource_id", "connection_type"],
    "Job": ["identifier", "status", "priority", "start_time", "planned_effort"],
    "InventoryItem": ["identifier", "quantity"],
    "MaintenancePlan": ["identifier", "name", "description"],
}


class MappingEngine:
    """Proposes field mappings between API payloads and CMSD schema entities."""

    async def propose_mapping(
        self,
        data_point_name: str,
        cmsd_entity: str,
        api_endpoint: str,
        payload_analysis: dict[str, Any],
        rag_context: str,
    ) -> dict[str, Any]:
        """
        Use LLM + RAG context to propose a field mapping.
        Returns a structured mapping dict.
        Supports both single payload_analysis and list of analyses.
        """
        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            data_point_name, cmsd_entity, api_endpoint,
            payload_analysis, rag_context,
        )

        try:
            result = llm_client.chat_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
            # Validate the mapping
            validated = self._validate_mapping(result, cmsd_entity)
            return validated
        except Exception as e:
            logger.error(f"Mapping proposal failed: {e}")
            # Return a fallback structure that the user can edit
            return {
                "data_point": data_point_name,
                "cmsd_entity": cmsd_entity,
                "api_endpoint": api_endpoint,
                "mapping": {},
                "error": str(e),
                "requires_manual_review": True,
            }

    async def propose_mapping_multi(
        self,
        data_point_name: str,
        cmsd_entity: str,
        endpoint_labels: list[str],
        payload_analyses: list[dict[str, Any]],
        rag_context: str,
    ) -> dict[str, Any]:
        """
        Propose a mapping using data from MULTIPLE API endpoints.
        Each payload_analysis is a dict from api_explorer.analyze_payload().
        endpoint_labels are human-readable labels like "SAP /resources".
        """
        system_prompt = self._build_system_prompt_multi()
        user_prompt = self._build_user_prompt_multi(
            data_point_name, cmsd_entity, endpoint_labels,
            payload_analyses, rag_context,
        )

        try:
            result = llm_client.chat_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
            validated = self._validate_mapping(result, cmsd_entity)
            return validated
        except Exception as e:
            logger.error(f"Multi-endpoint mapping proposal failed: {e}")
            return {
                "data_point": data_point_name,
                "cmsd_entity": cmsd_entity,
                "api_endpoint": ", ".join(endpoint_labels),
                "mapping": {},
                "error": str(e),
                "requires_manual_review": True,
            }

    async def chat_about_mapping(
        self,
        data_point_name: str,
        current_mapping: dict[str, Any],
        user_question: str,
        rag_context: str | None = None,
    ) -> str:
        """
        Chat with the agent about a specific mapping.
        User can ask questions, request adjustments, etc.
        """
        context = rag_context or ""

        system_prompt = (
            "You are an expert CMSD (Core Manufacturing Simulation Data) mapping assistant. "
            "Your job is to help the user understand and refine field mappings between "
            "API response payloads and CMSD schema entities.\n\n"
            "Be specific about field paths, data types, and transformations. "
            "If the user asks for a change, explain how it would affect the mapping. "
            "Keep responses concise and technical."
        )

        user_prompt = (
            f"The user is working on mapping '{data_point_name}' to CMSD entity.\n\n"
            f"Current mapping: {json.dumps(current_mapping, indent=2)}\n\n"
            f"Relevant context: {context[:1000]}\n\n"
            f"User's question: {user_question}"
        )

        return llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

    async def smart_reanalyze(
        self,
        data_point_name: str,
        cmsd_entity: str,
        current_mapping: dict[str, Any],
        user_guidance: str,
        payload_analyses: list[dict[str, Any]] | None = None,
        endpoint_labels: list[str] | None = None,
        rag_context: str | None = None,
    ) -> dict[str, Any]:
        """
        Re-analyze a mapping with user guidance from chat.
        The LLM receives the current mapping + user's instructions and
        produces a refined mapping proposal, only changing what the user asked.
        """
        context = rag_context or ""
        cmsd_fields = CMSD_ENTITY_FIELDS.get(cmsd_entity, [])
        fields_str = "\n".join(f"  - {f}" for f in cmsd_fields)

        system_prompt = (
            "You are an expert manufacturing data mapping engine. "
            "Your task is to REFINE an existing field mapping based on specific user guidance.\n\n"
            "RULES:\n"
            "1. ONLY change fields the user explicitly mentions in their guidance.\n"
            "2. PRESERVE all other fields exactly as they are in the current mapping.\n"
            "3. Follow the user's instructions precisely (which API to use, which path, which conversion).\n"
            "4. Include raw_value (exact value from API payload) and converted_value (after type_conversion) for changed fields.\n"
            "5. Set confidence to 'manual' for fields changed per user guidance.\n\n"
            "Output format: JSON with this structure:\n"
            '{\n'
            '  "data_point": "string",\n'
            '  "cmsd_entity": "string",\n'
            '  "mapping": {\n'
            '    "cmsd_field_name": {\n'
            '      "api_path": "dot.path.to.field",\n'
            '      "type_conversion": "none|to_decimal|to_duration|to_weight|to_dimensions",\n'
            '      "raw_value": "value from API payload",\n'
            '      "converted_value": "value after type conversion",\n'
            '      "sample_value": "value from payload (legacy)",\n'
            '      "confidence": "manual|high|medium|low"\n'
            '    }\n'
            '  },\n'
            '  "notes": "what was changed"\n'
            '}\n\n'
            "IMPORTANT: Output ONLY the JSON object. No markdown, no explanation."
        )

        endpoints_info = ""
        if endpoint_labels and payload_analyses:
            for label, analysis in zip(endpoint_labels, payload_analyses):
                endpoints_info += (
                    f"\n## Endpoint: {label}\n"
                    f"{json.dumps(analysis, indent=2, default=str)[:1500]}\n"
                )

        user_prompt = (
            f"## Data Point: {data_point_name}\n"
            f"## Target CMSD Entity: {cmsd_entity}\n"
            f"## Required CMSD Fields:\n{fields_str}\n\n"
            f"## Current Mapping (preserve unless user says otherwise):\n"
            f"{json.dumps(current_mapping, indent=2)}\n\n"
            f"## Available API Payloads:{endpoints_info}\n\n"
            f"## RAG Context:\n{context[:1500]}\n\n"
            f"## USER GUIDANCE (follow these instructions):\n{user_guidance}\n\n"
            f"Refine the mapping per the user's guidance. Only change what they asked."
        )

        try:
            result = llm_client.chat_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
            # Merge refined fields into current mapping
            refined = self._merge_refinements(current_mapping, result, cmsd_entity)
            return refined
        except Exception as e:
            logger.error(f"Smart reanalyze failed: {e}")
            return {
                **current_mapping,
                "error": str(e),
                "requires_manual_review": True,
            }

    def _merge_refinements(
        self,
        current_mapping: dict[str, Any],
        llm_result: dict[str, Any],
        cmsd_entity: str,
    ) -> dict[str, Any]:
        """Merge LLM-refined fields into the current mapping, preserving untouched fields."""
        merged = dict(current_mapping)
        merged_mapping = dict(merged.get("mapping", {}))

        llm_mapping = llm_result.get("mapping", {})
        for field, info in llm_mapping.items():
            if isinstance(info, dict):
                merged_mapping[field] = {
                    "api_path": info.get("api_path", merged_mapping.get(field, {}).get("api_path", "")),
                    "type_conversion": info.get("type_conversion", "none"),
                    "raw_value": info.get("raw_value", ""),
                    "converted_value": info.get("converted_value", ""),
                    "sample_value": info.get("sample_value", info.get("raw_value", "")),
                    "confidence": info.get("confidence", "manual"),
                }

        merged["mapping"] = merged_mapping
        merged["notes"] = llm_result.get("notes", merged.get("notes", ""))
        merged["unmapped_fields"] = [
            f for f in CMSD_ENTITY_FIELDS.get(cmsd_entity, [])
            if f not in merged_mapping
        ]
        merged["requires_manual_review"] = len(merged["unmapped_fields"]) > 0
        return merged

    async def analyze_rag(
        self,
        data_point_name: str,
        cmsd_entity: str,
        api_endpoint: str | None = None,
        payload_sample: str | None = None,
    ) -> str:
        """
        Retrieve RAG context for a specific data point mapping.
        Returns the assembled context string for use in prompts.
        """
        return retriever.retrieve_for_mapping(
            data_point_name=data_point_name,
            cmsd_entity=cmsd_entity,
            api_endpoint=api_endpoint,
            api_payload_sample=payload_sample,
        )

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert manufacturing data mapping engine. "
            "Your task is to analyze an API response payload and propose a mapping "
            "to CMSD (Core Manufacturing Simulation Data) schema entities.\n\n"
            "Rules:\n"
            "1. Map API field paths (dot-notation like 'bom_header.bom_id') to CMSD fields.\n"
            "2. For nested structures, use JSONPath-like notation: 'items[*].field'.\n"
            "3. Include type conversion hints when needed (e.g., string→Decimal, seconds→Duration).\n"
            "4. If a CMSD field appears to have no match in the payload, set it to null.\n"
            "5. Be thorough — attempt to map EVERY CMSD field that has a matching field in the payload, "
            "even if the match is approximate. Only leave a field unmapped if it truly has no counterpart.\n"
            "6. Include 'raw_value' (exact value from the API payload at the field path) AND "
            "'converted_value' (value after applying type_conversion) for each mapping.\n"
            "7. Identify the array of entity instances in the payload: find the JSONPath to the array "
            "(e.g., $.resources[*]) and the field used as unique identifier within each item.\n\n"
            "Output format: JSON with this structure:\n"
            '{\n'
            '  "data_point": "string",\n'
            '  "cmsd_entity": "string",\n'
            '  "api_endpoint": "string",\n'
            '  "mapping": {\n'
            '    "cmsd_field_name": {\n'
            '      "api_path": "dot.path.to.field",\n'
            '      "type_conversion": "none|to_decimal|to_duration|to_weight|to_dimensions|string→enum",\n'
            '      "raw_value": "exact value from API payload at that path",\n'
            '      "converted_value": "value after type conversion",\n'
            '      "sample_value": "value from payload (legacy)",\n'
            '      "confidence": "high|medium|low"\n'
            '    },\n'
            '    ...\n'
            '  },\n'
            '  "root_array_path": "path.to.array[*] if payload is list under a key",\n'
            '  "instances": {\n'
            '    "count_path": "JSONPath to the array of instances (e.g. $.machines[*])",\n'
            '    "key_field": "field name used as unique identifier within each array item"\n'
            '  },\n'
            '  "notes": "any observations about the mapping"\n'
            '}\n\n'
            "IMPORTANT: Output ONLY the JSON object. No markdown, no explanation."
        )

    def _build_system_prompt_multi(self) -> str:
        return (
            "You are an expert manufacturing data mapping engine. "
            "Your task is to analyze MULTIPLE API response payloads and propose a mapping "
            "to CMSD (Core Manufacturing Simulation Data) schema entities.\n\n"
            "Rules:\n"
            "1. Map API field paths (dot-notation like 'bom_header.bom_id') to CMSD fields.\n"
            "2. For nested structures, use JSONPath-like notation: 'items[*].field'.\n"
            "3. Include type conversion hints when needed (e.g., string→Decimal, seconds→Duration).\n"
            "4. A CMSD field can come from ANY of the provided endpoints — pick the best source.\n"
            "5. If a CMSD field appears to have no match in ANY payload, leave it unmapped.\n"
            "6. Be thorough — attempt to map EVERY CMSD field that has a matching field in ANY payload, "
            "even if the match is approximate. Only leave a field unmapped if it truly has no counterpart.\n"
            "7. Include 'raw_value' (exact value from the API payload at the field path) AND "
            "'converted_value' (value after applying type_conversion) for each mapping.\n"
            "8. In 'notes', mention which endpoint each field came from if relevant.\n"
            "9. Identify the array of entity instances across payloads: find the JSONPath to the array "
            "(e.g., $.resources[*]) and the field used as unique identifier within each item.\n\n"
            "Output format: JSON with this structure:\n"
            '{\n'
            '  "data_point": "string",\n'
            '  "cmsd_entity": "string",\n'
            '  "api_endpoint": "comma-separated endpoints",\n'
            '  "mapping": {\n'
            '    "cmsd_field_name": {\n'
            '      "api_path": "dot.path.to.field",\n'
            '      "type_conversion": "none|to_decimal|to_duration|to_weight|to_dimensions|string→enum",\n'
            '      "raw_value": "exact value from API payload at that path",\n'
            '      "converted_value": "value after type conversion",\n'
            '      "sample_value": "value from payload (legacy)",\n'
            '      "source_endpoint": "which endpoint this came from",\n'
            '      "confidence": "high|medium|low"\n'
            '    },\n'
            '    ...\n'
            '  },\n'
            '  "root_array_path": "path.to.array[*] if payload is list under a key",\n'
            '  "instances": {\n'
            '    "count_path": "JSONPath to the array of instances (e.g. $.machines[*])",\n'
            '    "key_field": "field name used as unique identifier within each array item"\n'
            '  },\n'
            '  "notes": "any observations about the mapping"\n'
            '}\n\n'
            "IMPORTANT: Output ONLY the JSON object. No markdown, no explanation."
        )

    def _build_user_prompt(
        self,
        data_point_name: str,
        cmsd_entity: str,
        api_endpoint: str,
        payload_analysis: dict,
        rag_context: str,
    ) -> str:
        cmsd_fields = CMSD_ENTITY_FIELDS.get(cmsd_entity, [])
        fields_str = "\n".join(f"  - {f}" for f in cmsd_fields)

        return (
            f"## Data Point: {data_point_name}\n"
            f"## Target CMSD Entity: {cmsd_entity}\n"
            f"## Required CMSD Fields:\n{fields_str}\n\n"
            f"## API Endpoint: {api_endpoint}\n\n"
            f"## RAG Context (from knowledge base):\n{rag_context[:2000]}\n\n"
            f"## Live API Payload Analysis:\n"
            f"{json.dumps(payload_analysis, indent=2, default=str)[:3000]}\n\n"
            f"Propose a mapping from the API payload to the CMSD fields above."
        )

    def _build_user_prompt_multi(
        self,
        data_point_name: str,
        cmsd_entity: str,
        endpoint_labels: list[str],
        payload_analyses: list[dict[str, Any]],
        rag_context: str,
    ) -> str:
        cmsd_fields = CMSD_ENTITY_FIELDS.get(cmsd_entity, [])
        fields_str = "\n".join(f"  - {f}" for f in cmsd_fields)

        parts = [
            f"## Data Point: {data_point_name}",
            f"## Target CMSD Entity: {cmsd_entity}",
            f"## Required CMSD Fields:\n{fields_str}\n",
            f"## RAG Context (from knowledge base):\n{rag_context[:2000]}\n",
        ]

        for i, (label, analysis) in enumerate(zip(endpoint_labels, payload_analyses)):
            parts.append(
                f"## API Endpoint {i+1}: {label}\n"
                f"{json.dumps(analysis, indent=2, default=str)[:2000]}\n"
            )

        parts.append("Propose a mapping from ALL the API payloads above to the CMSD fields.")
        return "\n".join(parts)

    def _validate_mapping(self, proposed: dict, cmsd_entity: str) -> dict:
        """
        Validate the proposed mapping against known CMSD fields.
        Adds confidence flags and marks unmapped required fields.
        Extracts instances block (count_path, key_field) from LLM response.
        """
        known_fields = CMSD_ENTITY_FIELDS.get(cmsd_entity, [])
        mapping = proposed.get("mapping", {})

        instances_raw = proposed.get("instances", {})
        instances = {
            "count_path": instances_raw.get("count_path", "") if isinstance(instances_raw, dict) else "",
            "key_field": instances_raw.get("key_field", "") if isinstance(instances_raw, dict) else "",
        }

        validated = {
            "data_point": proposed.get("data_point", ""),
            "cmsd_entity": cmsd_entity,
            "api_endpoint": proposed.get("api_endpoint", ""),
            "root_array_path": proposed.get("root_array_path", "$"),
            "mapping": {},
            "unmapped_fields": [],
            "instances": instances,
            "notes": proposed.get("notes", ""),
            "requires_manual_review": False,
        }

        # Validate each mapped field
        for cmsd_field, map_info in mapping.items():
            if isinstance(map_info, dict):
                validated["mapping"][cmsd_field] = {
                    "api_path": map_info.get("api_path", ""),
                    "type_conversion": map_info.get("type_conversion", "none"),
                    "raw_value": map_info.get("raw_value", map_info.get("sample_value", "")),
                    "converted_value": map_info.get("converted_value", ""),
                    "sample_value": map_info.get("sample_value", map_info.get("raw_value", "")),
                    "confidence": map_info.get("confidence", "medium"),
                    "source_endpoint": map_info.get("source_endpoint", ""),
                }
            elif isinstance(map_info, str):
                validated["mapping"][cmsd_field] = {
                    "api_path": map_info,
                    "type_conversion": "none",
                    "raw_value": "",
                    "converted_value": "",
                    "sample_value": "",
                    "confidence": "medium",
                    "source_endpoint": "",
                }

        # Find unmapped known fields
        for field in known_fields:
            if field not in validated["mapping"]:
                validated["unmapped_fields"].append(field)
                validated["requires_manual_review"] = True

        # Flag low-confidence mappings
        for field, info in validated["mapping"].items():
            if info.get("confidence") == "low":
                validated["requires_manual_review"] = True
                break

        return validated

    def apply_user_edits(
        self,
        current_mapping: dict[str, Any],
        edits: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply user edits to a mapping.
        edits is {cmsd_field: {api_path, type_conversion, ...} | null}
        null means remove the field from mapping.
        """
        updated = dict(current_mapping)
        mapping = dict(updated.get("mapping", {}))

        for field, edit in edits.items():
            if edit is None:
                mapping.pop(field, None)
                if field in updated.get("unmapped_fields", []):
                    updated["unmapped_fields"].remove(field)
            else:
                mapping[field] = {
                    "api_path": edit.get("api_path", mapping.get(field, {}).get("api_path", "")),
                    "type_conversion": edit.get("type_conversion", "none"),
                    "raw_value": edit.get("raw_value", mapping.get(field, {}).get("raw_value", "")),
                    "converted_value": edit.get("converted_value", mapping.get(field, {}).get("converted_value", "")),
                    "sample_value": edit.get("sample_value", edit.get("raw_value", mapping.get(field, {}).get("sample_value", ""))),
                    "confidence": "manual",
                    "source_endpoint": edit.get("source_endpoint", mapping.get(field, {}).get("source_endpoint", "")),
                }

        updated["mapping"] = mapping
        updated["unmapped_fields"] = [
            f for f in CMSD_ENTITY_FIELDS.get(updated.get("cmsd_entity", ""), [])
            if f not in mapping
        ]
        updated["requires_manual_review"] = len(updated["unmapped_fields"]) > 0
        return updated


# Singleton
mapping_engine = MappingEngine()