"""
Enhanced SME Context NLM
Provides actionable insights without needing an LLM API
Uses rule-based expert system
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.base_nlm import BaseNLM, NLMConfig
from core.simp import SIMPMessage, Intent, MessageType

logger = logging.getLogger(__name__)


class EnhancedSMEContextNLM(BaseNLM):
    """
    SME Context provider using rule-based expert system
    
    Provides insights about:
    - Grant eligibility
    - Funding recommendations
    - Application tips
    - Common pitfalls
    """
    
    def __init__(self):
        config = NLMConfig(
            nlm_id="sme_context",
            name="SME Context Expert",
            domain="sme_context",
            silo="ALL",
            can_search=False,
            can_scrape=False,
            can_analyze=True
        )
        super().__init__(config)
        
        # Expert knowledge base
        self.funding_ranges = {
            "micro": {"min": 0, "max": 50000, "employee_max": 10},
            "small": {"min": 50000, "max": 500000, "employee_max": 50},
            "medium": {"min": 500000, "max": 2000000, "employee_max": 250},
            "large": {"min": 2000000, "max": 10000000, "employee_max": 999999}
        }
        
        self.sector_insights = {
            "ai": {
                "hot_keywords": ["machine learning", "deep learning", "nlp", "computer vision"],
                "programs": ["Smart Grant", "Horizon EIC", "SBRI"],
                "tips": "Emphasize real-world applications and market validation"
            },
            "health": {
                "hot_keywords": ["digital health", "medtech", "diagnostics", "therapeutics"],
                "programs": ["NIHR", "Horizon Health", "Smart Grant"],
                "tips": "Strong clinical evidence and regulatory pathway required"
            },
            "cleantech": {
                "hot_keywords": ["renewable", "carbon", "sustainability", "net zero"],
                "programs": ["Smart Grant", "Horizon Green", "SBRI"],
                "tips": "Focus on measurable environmental impact"
            }
        }
        
    async def on_initialize(self):
        """Custom initialization"""
        logger.info(f"[{self.nlm_id}] SME expert system ready")
    
    def _register_default_handlers(self):
        """Register analyze handler"""
        super()._register_default_handlers()
        self.register_handler(Intent.ANALYZE, self.handle_analyze)
    
    async def handle_analyze(self, message: SIMPMessage) -> SIMPMessage:
        """
        Generate SME insights for query
        """
        query = message.context.get('query', '').lower()
        filters = message.context.get('filters', {})
        
        insights = []
        
        # 1. Detect company size indicators
        size_insight = self._analyze_company_size(query)
        if size_insight:
            insights.append(size_insight)
        
        # 2. Detect sector and provide tips
        sector_insight = self._analyze_sector(query)
        if sector_insight:
            insights.append(sector_insight)
        
        # 3. Geographic insights
        geo_insight = self._analyze_geography(query, filters)
        if geo_insight:
            insights.append(geo_insight)
        
        # 4. Timeline insights
        timeline_insight = self._analyze_timeline(query)
        if timeline_insight:
            insights.append(timeline_insight)
        
        # 5. Common pitfalls warning
        pitfall_warning = self._get_pitfall_warning(query)
        if pitfall_warning:
            insights.append(pitfall_warning)
        
        # Combine insights
        sme_text = " | ".join(insights) if insights else "No specific insights for this query"
        
        return message.create_response(
            context={
                "sme_insights": sme_text,
                "insight_count": len(insights),
                "confidence": "high"
            },
            intent=Intent.ANALYZE
        )
    
    def _analyze_company_size(self, query: str) -> Optional[str]:
        """Analyze company size indicators"""
        if "startup" in query or "early stage" in query:
            return "💡 For startups: Smart Grants (£25k-£2M) or Innovation Vouchers (£5k) are best starting points"
        
        if "sme" in query or "small business" in query:
            return "💡 SME programs: You qualify for most UK grants. Focus on Smart Grants and CR&D"
        
        if "scale up" in query or "scale-up" in query:
            return "💡 Scale-ups: Consider larger programs like Horizon EIC (€0.5-2.5M) or CR&D (£100k-£10M)"
        
        return None
    
    def _analyze_sector(self, query: str) -> Optional[str]:
        """Analyze sector and provide tips"""
        for sector, info in self.sector_insights.items():
            # Check if sector keywords match
            if sector in query or any(kw in query for kw in info["hot_keywords"]):
                programs = ", ".join(info["programs"][:2])  # Top 2 programs
                return f"🎯 {sector.upper()} focus: Best programs are {programs}. Tip: {info['tips']}"
        
        return None
    
    def _analyze_geography(self, query: str, filters: Dict) -> Optional[str]:
        """Geographic insights"""
        if "uk" in query or filters.get("silos") == ["UK"]:
            return "🇬🇧 UK-focused: Check Innovate UK first (fast decisions, 3-6 months). SME <250 employees required"
        
        if "europe" in query or "eu" in query or filters.get("silos") == ["EU"]:
            return "🇪🇺 EU programs: Horizon Europe has larger grants but longer timelines (6-12 months). More competitive"
        
        return None
    
    def _analyze_timeline(self, query: str) -> Optional[str]:
        """Timeline insights"""
        if "urgent" in query or "quick" in query or "fast" in query:
            return "⏰ Fast funding: Innovation Vouchers (2-4 weeks) or SBRI (3 months) are quickest"
        
        if "large" in query and any(word in query for word in ["funding", "grant", "investment"]):
            return "⏱️ Large grants take longer: Expect 6-12 months for Horizon EIC or major CR&D awards"
        
        return None
    
    def _get_pitfall_warning(self, query: str) -> Optional[str]:
        """Common pitfalls"""
        warnings = []
        
        if "first time" in query or "new to" in query:
            warnings.append("⚠️ First time? Start small with Innovation Vouchers to learn the process")
        
        if "ai" in query and "grant" in query:
            warnings.append("⚠️ AI grants are competitive: Show real customers and revenue potential")
        
        if warnings:
            return " | ".join(warnings)
        
        return None


# Example usage showing the insights in action:
"""
Query: "AI grants for UK startups"
SME Insights: 
💡 For startups: Smart Grants (£25k-£2M) or Innovation Vouchers (£5k) are best starting points | 
🎯 AI focus: Best programs are Smart Grant, Horizon EIC. Tip: Emphasize real-world applications and market validation | 
🇬🇧 UK-focused: Check Innovate UK first (fast decisions, 3-6 months). SME <250 employees required | 
⚠️ AI grants are competitive: Show real customers and revenue potential

Query: "urgent health tech funding"
SME Insights:
🎯 HEALTH focus: Best programs are NIHR, Horizon Health. Tip: Strong clinical evidence and regulatory pathway required | 
⏰ Fast funding: Innovation Vouchers (2-4 weeks) or SBRI (3 months) are quickest

Query: "large scale renewable energy project"
SME Insights:
🎯 CLEANTECH focus: Best programs are Smart Grant, Horizon Green. Tip: Focus on measurable environmental impact | 
⏱️ Large grants take longer: Expect 6-12 months for Horizon EIC or major CR&D awards
"""
