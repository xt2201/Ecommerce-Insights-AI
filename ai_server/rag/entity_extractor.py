"""LLM-powered entity and relationship extraction for Knowledge Graph."""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from ai_server.llm.llm_factory import get_llm
from ai_server.utils.prompt_loader import load_prompts_as_dict
from ai_server.schemas.knowledge_graph_models import (
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """LLM-powered entity and relationship extraction from text."""
    
    _instance: Optional["EntityExtractor"] = None
    
    def __new__(cls):
        """Singleton pattern for EntityExtractor."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the entity extractor."""
        if self._initialized:
            return
        
        self.llm = get_llm(agent_name="manager")
        self._load_prompts()
        self._initialized = True
        
        logger.info("EntityExtractor initialized")
    
    def _load_prompts(self) -> None:
        """Load prompts from YAML file."""
        try:
            self.prompts = load_prompts_as_dict("entity_extraction_prompts")
            logger.debug("Loaded entity extraction prompts")
        except Exception as e:
            logger.warning(f"Failed to load prompts, using defaults: {e}")
            self.prompts = {}
    
    def extract(
        self,
        text: str,
        doc_id: Optional[str] = None,
        doc_type: str = "unknown",
        category: str = "general",
        language: str = "en",
        context: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract entities and relationships from text.
        
        Args:
            text: Text to extract from.
            doc_id: Optional document ID for reference.
            doc_type: Type of document (policy, faq, etc.).
            category: Category of the document.
            language: Language hint (en, vi).
            context: Additional context for extraction.
            
        Returns:
            ExtractionResult with entities and relationships.
        """
        if not text or not text.strip():
            return ExtractionResult(source_text=text)
        
        # Build user prompt
        user_prompt = self._build_extraction_prompt(
            text=text,
            doc_id=doc_id or "unknown",
            doc_type=doc_type,
            category=category,
            language=language,
            context=context or "",
        )
        
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=user_prompt),
            ]
            
            response = self.llm.invoke(messages)
            content = self._clean_response(response.content)
            parsed = json.loads(content)
            
            # Parse entities
            entities = []
            for e_data in parsed.get("entities", []):
                try:
                    entity = ExtractedEntity(
                        name=e_data.get("name", "").lower().strip(),
                        entity_type=e_data.get("entity_type", "unknown"),
                        confidence=float(e_data.get("confidence", 0.8)),
                        aliases=[a.lower().strip() for a in e_data.get("aliases", [])],
                        properties=e_data.get("properties", {}),
                        language=e_data.get("language", language),
                    )
                    if entity.name:  # Only add if name is not empty
                        entities.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to parse entity: {e}")
            
            # Parse relationships
            relationships = []
            for r_data in parsed.get("relationships", []):
                try:
                    rel = ExtractedRelationship(
                        source_entity=r_data.get("source_entity", "").lower().strip(),
                        target_entity=r_data.get("target_entity", "").lower().strip(),
                        relationship_type=r_data.get("relationship_type", "related_to"),
                        confidence=float(r_data.get("confidence", 0.8)),
                        properties=r_data.get("properties", {}),
                        bidirectional=r_data.get("bidirectional", False),
                    )
                    if rel.source_entity and rel.target_entity:
                        relationships.append(rel)
                except Exception as e:
                    logger.warning(f"Failed to parse relationship: {e}")
            
            result = ExtractionResult(
                entities=entities,
                relationships=relationships,
                reasoning=parsed.get("reasoning", ""),
                source_text=text,
                language_detected=parsed.get("language_detected", language),
            )
            
            logger.info(
                f"Extracted {len(entities)} entities, {len(relationships)} relationships "
                f"from text ({len(text)} chars)"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return ExtractionResult(source_text=text, reasoning=f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult(source_text=text, reasoning=f"Extraction error: {e}")
    
    def extract_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> List[ExtractionResult]:
        """Extract entities from multiple documents.
        
        Args:
            documents: List of dicts with 'text', 'doc_id', 'doc_type', etc.
            
        Returns:
            List of ExtractionResult, one per document.
        """
        results = []
        
        for doc in documents:
            result = self.extract(
                text=doc.get("text", ""),
                doc_id=doc.get("id") or doc.get("doc_id"),
                doc_type=doc.get("type") or doc.get("doc_type", "unknown"),
                category=doc.get("category", "general"),
                language=doc.get("language", "en"),
                context=doc.get("context"),
            )
            results.append(result)
        
        total_entities = sum(r.entity_count for r in results)
        total_rels = sum(r.relationship_count for r in results)
        logger.info(
            f"Batch extraction: {len(documents)} docs, "
            f"{total_entities} entities, {total_rels} relationships"
        )
        
        return results
    
    def detect_language(self, text: str) -> str:
        """Detect language of text (simple heuristic).
        
        Args:
            text: Text to analyze.
            
        Returns:
            Language code ('en' or 'vi').
        """
        # Vietnamese-specific characters and patterns
        vietnamese_patterns = [
            r'[àáạảãâầấậẩẫăằắặẳẵ]',
            r'[èéẹẻẽêềếệểễ]',
            r'[ìíịỉĩ]',
            r'[òóọỏõôồốộổỗơờớợởỡ]',
            r'[ùúụủũưừứựửữ]',
            r'[ỳýỵỷỹ]',
            r'[đĐ]',
        ]
        
        for pattern in vietnamese_patterns:
            if re.search(pattern, text):
                return "vi"
        
        # Vietnamese keywords
        vietnamese_keywords = [
            'của', 'và', 'là', 'được', 'cho', 'trong', 'này', 'có',
            'đến', 'không', 'với', 'từ', 'một', 'như', 'hoặc', 'nếu',
            'bạn', 'chúng tôi', 'sản phẩm', 'đơn hàng', 'vận chuyển',
        ]
        
        text_lower = text.lower()
        for keyword in vietnamese_keywords:
            if keyword in text_lower:
                return "vi"
        
        return "en"
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for extraction."""
        if self.prompts and "system_prompt" in self.prompts:
            return self.prompts["system_prompt"]
        return self._default_system_prompt()
    
    def _build_extraction_prompt(
        self,
        text: str,
        doc_id: str,
        doc_type: str,
        category: str,
        language: str,
        context: str,
    ) -> str:
        """Build the user prompt for extraction."""
        template = self.prompts.get("extraction_template")
        
        if template:
            return template.format(
                text=text,
                doc_id=doc_id,
                doc_type=doc_type,
                category=category,
                language=language,
                context=context,
            )
        
        # Default template
        return f"""## Text to Analyze
{text}

## Document Context
- Document ID: {doc_id}
- Document Type: {doc_type}
- Category: {category}
- Language Hint: {language}

## Additional Context
{context}

Extract all entities and relationships from the text above.
Output valid JSON only, no additional text."""
    
    def _clean_response(self, content: str) -> str:
        """Clean LLM response for JSON parsing."""
        # Remove thinking tags (for models like Qwen)
        if "<think>" in content:
            parts = content.split("</think>")
            content = parts[-1].strip() if len(parts) > 1 else content
        
        # Extract JSON from markdown code blocks
        if "```json" in content:
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)
        elif "```" in content:
            match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)
        
        # Try to find JSON object
        content = content.strip()
        
        # Find first { and last }
        start = content.find('{')
        end = content.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
        
        return content
    
    def _default_system_prompt(self) -> str:
        """Default system prompt if YAML not loaded."""
        return """You are an expert knowledge graph builder for e-commerce customer service.
Extract entities and relationships from text about store policies and FAQs.

Entity types: policy, faq, product, brand, category, feature, price_point, time_period, condition, action, attribute

Relationship types: has_condition, has_time_limit, allows_action, applies_to, requires, results_in, is_brand_of, belongs_to_category, has_feature, related_to, see_also

Output JSON only:
{
  "entities": [{"name": "...", "entity_type": "...", "confidence": 0.9, "aliases": [], "properties": {}, "language": "en"}],
  "relationships": [{"source_entity": "...", "target_entity": "...", "relationship_type": "...", "confidence": 0.9, "bidirectional": false}],
  "reasoning": "...",
  "language_detected": "en"
}"""


# Convenience function
def get_entity_extractor() -> EntityExtractor:
    """Get the singleton EntityExtractor instance."""
    return EntityExtractor()
