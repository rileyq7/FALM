"""
AI Grant Analyst Agent

Provides intelligent grant analysis, summarization, and advisory capabilities
using LLMs. Acts as an omniscient grant expert that can:
- Answer natural language questions
- Summarize and compare grants
- Analyze eligibility and fit
- Provide strategic funding advice
- Help write proposals
- Fetch and parse external documents
"""

import os
import asyncio
from typing import Dict, List, Optional
import anthropic
from openai import AsyncOpenAI
import aiohttp
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO


class GrantAnalystAgent:
    """Intelligent AI agent for grant analysis and advisory"""

    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

        # Initialize clients
        self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key) if self.anthropic_key else None
        self.openai_client = AsyncOpenAI(api_key=self.openai_key) if self.openai_key else None

        # System prompt
        self.system_prompt = """You are an expert grant analyst and funding advisor with deep knowledge of UK and EU funding bodies including:
- Innovate UK (Smart Grants, CR&D, SBRI, Innovation Vouchers)
- Horizon Europe (EIC Accelerator, Marie Curie, ERC)
- NIHR (Research for Patient Benefit, i4i, HTA)
- UKRI Research Councils (EPSRC, ESRC, NERC, etc.)

Your capabilities:
1. **Analysis**: Assess grant eligibility, fit, and competitiveness
2. **Summarization**: Distill complex funding calls into key points
3. **Comparison**: Compare multiple funding options
4. **Strategy**: Provide strategic funding advice
5. **Writing**: Help draft proposals, summaries, and justifications
6. **Research**: Interpret funding guidelines and requirements

Communication style:
- Clear, professional, and actionable
- Use specific examples and evidence
- Highlight risks and opportunities
- Provide step-by-step guidance when appropriate
- Be honest about limitations and requirements

Always consider:
- Eligibility criteria (legal, geographic, sector, TRL, etc.)
- Funding amounts and rates
- Match funding requirements
- Application complexity and timeline
- Success rates and competitiveness
- Strategic fit and alternatives
"""

    async def analyze_query(self, query: str, grants: List[Dict], context: Optional[str] = None) -> str:
        """
        Analyze a natural language query about grants

        Returns intelligent response using LLM
        """

        if not self.anthropic_client and not self.openai_client:
            return self._fallback_response(query, grants)

        # Build context from grants
        grants_context = self._build_grants_context(grants)

        # Build user message
        user_message = f"""User Query: {query}

Available Grants:
{grants_context}

{f'Additional Context: {context}' if context else ''}

Please provide a comprehensive, actionable response to the user's query. Consider their specific needs and recommend the best funding options."""

        try:
            if self.anthropic_client:
                response = await self._call_anthropic(user_message)
            else:
                response = await self._call_openai(user_message)

            return response

        except Exception as e:
            return f"I encountered an error analyzing your query: {str(e)}\n\nHere's what I found: {self._fallback_response(query, grants)}"

    async def summarize_grant(self, grant: Dict) -> str:
        """Generate intelligent summary of a grant"""

        if not self.anthropic_client and not self.openai_client:
            return self._fallback_summary(grant)

        prompt = f"""Summarize this grant opportunity concisely but comprehensively:

Title: {grant.get('title', 'Unknown')}
Description: {grant.get('description', 'No description')}
Eligibility: {grant.get('eligibility', 'Not specified')}
Scope: {grant.get('scope', 'Not specified')}
Funding: {grant.get('amount_min', '?')} - {grant.get('amount_max', '?')} {grant.get('currency', 'GBP')}
Deadline: {grant.get('deadline', 'Not specified')}

Provide:
1. One-sentence overview
2. Key eligibility requirements (3-5 points)
3. What projects are fundable
4. Critical dates and amounts
5. One strategic tip for applicants
"""

        try:
            if self.anthropic_client:
                response = await self._call_anthropic(prompt)
            else:
                response = await self._call_openai(prompt)

            return response

        except Exception as e:
            return self._fallback_summary(grant)

    async def compare_grants(self, grants: List[Dict]) -> str:
        """Compare multiple grants and provide recommendations"""

        if not self.anthropic_client and not self.openai_client:
            return self._fallback_comparison(grants)

        grants_info = "\n\n".join([
            f"""Grant {i+1}: {g.get('title', 'Unknown')}
- Funding: {g.get('amount_min', '?')} - {g.get('amount_max', '?')} {g.get('currency', 'GBP')}
- Deadline: {g.get('deadline', 'Not specified')}
- Eligibility: {g.get('eligibility', 'Not specified')[:200]}...
- Match funding: {'Required' if g.get('match_funding_required') else 'Not required'}
"""
            for i, g in enumerate(grants)
        ])

        prompt = f"""Compare these grant opportunities and provide strategic recommendations:

{grants_info}

Provide:
1. Quick comparison table (funding amounts, deadlines, key requirements)
2. Best for different scenarios (e.g., "Best for early-stage startups", "Best for large projects")
3. Strategic recommendations on which to pursue
4. Key differences in eligibility or requirements
5. Application difficulty assessment
"""

        try:
            if self.anthropic_client:
                response = await self._call_anthropic(prompt)
            else:
                response = await self._call_openai(prompt)

            return response

        except Exception as e:
            return self._fallback_comparison(grants)

    async def fetch_and_analyze_document(self, url: str) -> str:
        """Fetch external document (PDF, webpage) and analyze it"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    content_type = response.headers.get('content-type', '')

                    if 'pdf' in content_type:
                        content = await self._parse_pdf(await response.read())
                    else:
                        html = await response.text()
                        content = self._parse_html(html)

            # Analyze with LLM
            if self.anthropic_client or self.openai_client:
                prompt = f"""Analyze this funding document and extract key information:

{content[:4000]}  # Limit to avoid token limits

Provide:
1. Summary (2-3 sentences)
2. Eligibility criteria
3. Funding amounts and rates
4. Key deadlines
5. Important requirements or restrictions
6. Strategic tips for applicants
"""

                if self.anthropic_client:
                    return await self._call_anthropic(prompt)
                else:
                    return await self._call_openai(prompt)
            else:
                return f"Document content extracted ({len(content)} chars). Add API key for AI analysis."

        except Exception as e:
            return f"Error fetching document: {str(e)}"

    async def help_write_proposal(self, project_desc: str, grant: Dict) -> str:
        """Help write a grant proposal section"""

        if not self.anthropic_client and not self.openai_client:
            return "Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env for proposal writing assistance."

        prompt = f"""Help write a compelling grant proposal section.

Project Description: {project_desc}

Grant: {grant.get('title', 'Unknown')}
Scope: {grant.get('scope', 'Not specified')}
Eligibility: {grant.get('eligibility', 'Not specified')}

Write:
1. A compelling project summary (150 words)
2. Key innovation points to highlight
3. How the project fits grant scope
4. Expected outcomes and impact
5. Risk mitigation strategies

Make it specific, evidence-based, and aligned with funder priorities.
"""

        try:
            if self.anthropic_client:
                response = await self._call_anthropic(prompt)
            else:
                response = await self._call_openai(prompt)

            return response

        except Exception as e:
            return f"Error generating proposal: {str(e)}"

    # Internal methods

    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API"""

        message = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI GPT API"""

        response = await self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000
        )

        return response.choices[0].message.content

    def _build_grants_context(self, grants: List[Dict], max_grants: int = 5) -> str:
        """Build context string from grants"""

        context_parts = []

        for i, grant in enumerate(grants[:max_grants], 1):
            context_parts.append(f"""
Grant {i}: {grant.get('title', 'Unknown')}
- Description: {grant.get('description', 'No description')[:200]}...
- Funding: {grant.get('amount_min', '?')} - {grant.get('amount_max', '?')} {grant.get('currency', 'GBP')}
- Deadline: {grant.get('deadline', 'Not specified')}
- Eligibility: {grant.get('eligibility', 'Not specified')[:150]}...
- URL: {grant.get('source_url', 'Not provided')}
""")

        if len(grants) > max_grants:
            context_parts.append(f"\n... and {len(grants) - max_grants} more grants")

        return "\n".join(context_parts)

    def _fallback_response(self, query: str, grants: List[Dict]) -> str:
        """Simple fallback when no LLM is available"""

        return f"""Found {len(grants)} grants matching your query.

Top Results:
{self._build_grants_context(grants, 3)}

💡 Add ANTHROPIC_API_KEY or OPENAI_API_KEY to your .env file for intelligent analysis, summarization, and advisory capabilities.

With AI enabled, I can:
- Provide strategic funding advice
- Summarize complex guidelines
- Compare grant options
- Help write proposals
- Analyze eligibility and fit
- Fetch and parse external documents
"""

    def _fallback_summary(self, grant: Dict) -> str:
        """Simple summary without LLM"""

        return f"""**{grant.get('title', 'Unknown Grant')}**

{grant.get('description', 'No description available')[:300]}...

💰 Funding: {grant.get('amount_min', '?')} - {grant.get('amount_max', '?')} {grant.get('currency', 'GBP')}
📅 Deadline: {grant.get('deadline', 'Not specified')}
🔗 More info: {grant.get('source_url', 'Not provided')}

Add API key for detailed AI analysis.
"""

    def _fallback_comparison(self, grants: List[Dict]) -> str:
        """Simple comparison without LLM"""

        comparisons = []
        for i, g in enumerate(grants, 1):
            comparisons.append(f"{i}. {g.get('title', 'Unknown')} - {g.get('amount_max', '?')} {g.get('currency', 'GBP')}")

        return f"""Grant Comparison:

{chr(10).join(comparisons)}

Add API key for detailed comparative analysis.
"""

    async def _parse_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF"""

        try:
            pdf_file = BytesIO(pdf_bytes)
            reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in reader.pages:
                text += page.extract_text()

            return text

        except Exception as e:
            return f"Error parsing PDF: {str(e)}"

    def _parse_html(self, html: str) -> str:
        """Extract text from HTML"""

        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text
