"""
FALM Grant Analyst - Production API Server
Complete implementation with data ingestion, scraping, and multi-silo architecture
"""

import os
import json
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Data processing
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import aiohttp
import requests

# PDF processing
import PyPDF2
import pdfplumber

# Vector DB
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Scheduling
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# MongoDB for metadata
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

# LLM Integration (Claude/OpenAI)
import anthropic
from openai import AsyncOpenAI

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Production configuration"""
    # API Keys (set via environment variables)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Database
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB = "falm_grants"
    
    # ChromaDB
    CHROMA_PERSIST_DIR = "./chroma_db"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    # Data directories
    DATA_DIR = Path("./data")
    SCRAPED_DATA_DIR = DATA_DIR / "scraped"
    PDF_CACHE_DIR = DATA_DIR / "pdfs"
    SILO_DATA_DIR = DATA_DIR / "silos"
    
    # Scraping
    MAX_CONCURRENT_SCRAPES = 5
    SCRAPE_TIMEOUT = 30
    USER_AGENT = "Mozilla/5.0 (FALM Grant Analyst Bot)"
    
    # SIMP Protocol
    SIMP_VERSION = "1.0"
    MESSAGE_TIMEOUT = 5.0
    
    # Create directories
    for dir in [DATA_DIR, SCRAPED_DATA_DIR, PDF_CACHE_DIR, SILO_DATA_DIR]:
        dir.mkdir(parents=True, exist_ok=True)

config = Config()

# ============================================================================
# DATA MODELS
# ============================================================================

class MessageType(str, Enum):
    QUERY = "query"
    RESPONSE = "response"
    CONTEXT_SHARE = "context_share"
    ERROR = "error"

class SIMPMessage(BaseModel):
    """Structured Inter-Model Protocol Message"""
    version: str = config.SIMP_VERSION
    msg_type: MessageType
    sender: str
    receiver: str
    intent: str
    context: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

class Grant(BaseModel):
    """Grant data model"""
    grant_id: str
    title: str
    provider: str
    silo: str  # UK, EU, US
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    currency: str = "GBP"
    deadline: Optional[datetime] = None
    eligibility: Dict[str, Any] = {}
    sectors: List[str] = []
    description: str = ""
    application_url: str = ""
    supplementary_urls: List[str] = []
    pdf_documents: List[str] = []
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}

class DataIngestionRequest(BaseModel):
    """Request to ingest data from a source"""
    source_url: str
    source_type: str = "web"  # web, pdf, api
    silo: str = "UK"  # UK, EU, US
    follow_links: bool = True
    max_depth: int = 2
    metadata: Dict[str, Any] = {}

class QueryRequest(BaseModel):
    """User query request"""
    query: str
    user_id: Optional[str] = "anonymous"
    silos: List[str] = ["UK", "EU", "US"]
    filters: Dict[str, Any] = {}
    max_results: int = 10

# ============================================================================
# SCRAPING ENGINE
# ============================================================================

class ScrapingEngine:
    """Advanced web scraping with link following and PDF extraction"""
    
    def __init__(self):
        self.session = None
        self.visited_urls: Set[str] = set()
        self.pdf_cache: Dict[str, str] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": config.USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=config.SCRAPE_TIMEOUT)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_grant_source(self, url: str, silo: str, follow_links: bool = True, max_depth: int = 2) -> Grant:
        """Scrape a grant source and extract all relevant data"""
        logger.info(f"Scraping {url} for {silo} silo")
        
        # Get main page content
        content = await self._fetch_url(url)
        if not content:
            raise ValueError(f"Failed to fetch {url}")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract grant information
        grant_data = await self._extract_grant_info(soup, url, silo)
        
        # Follow supplementary links
        if follow_links and max_depth > 0:
            supplementary_data = await self._follow_links(soup, url, max_depth)
            grant_data.supplementary_urls = supplementary_data['urls']
            grant_data.pdf_documents = supplementary_data['pdfs']
            
            # Merge extracted context
            if 'context' in supplementary_data:
                grant_data.metadata.update(supplementary_data['context'])
        
        # Extract PDFs
        for pdf_url in grant_data.pdf_documents[:5]:  # Limit PDFs for performance
            pdf_text = await self._extract_pdf_text(pdf_url)
            if pdf_text:
                grant_data.metadata[f"pdf_{hashlib.md5(pdf_url.encode()).hexdigest()[:8]}"] = pdf_text[:5000]
        
        return grant_data
    
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with caching"""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        
        return None
    
    async def _extract_grant_info(self, soup: BeautifulSoup, url: str, silo: str) -> Grant:
        """Extract grant information from page"""
        # Generic extraction - customize per source
        grant = Grant(
            grant_id=hashlib.md5(url.encode()).hexdigest()[:12],
            title=soup.find('h1', text=True).text.strip() if soup.find('h1') else "Unknown Grant",
            provider=self._extract_provider(soup, silo),
            silo=silo,
            application_url=url
        )
        
        # Extract amounts
        amount_patterns = ['£', '€', '$']
        for pattern in amount_patterns:
            amounts = soup.find_all(text=lambda text: pattern in text if text else False)
            if amounts:
                grant.currency = {'£': 'GBP', '€': 'EUR', '$': 'USD'}[pattern]
                # Parse amounts (simplified - enhance with regex)
                break
        
        # Extract deadline
        deadline_keywords = ['deadline', 'closes', 'due date', 'submission']
        for keyword in deadline_keywords:
            deadline_elem = soup.find(text=lambda text: keyword.lower() in text.lower() if text else False)
            if deadline_elem:
                # Parse date (simplified - use dateutil in production)
                grant.metadata['deadline_text'] = deadline_elem.strip()
                break
        
        # Extract eligibility
        eligibility_section = soup.find(['div', 'section'], class_=lambda x: x and 'eligib' in x.lower() if x else False)
        if eligibility_section:
            grant.eligibility = {
                'text': eligibility_section.get_text(strip=True)[:1000],
                'requirements': self._parse_requirements(eligibility_section)
            }
        
        # Extract sectors
        sectors_keywords = ['technology', 'AI', 'health', 'energy', 'manufacturing', 'digital', 'green']
        page_text = soup.get_text().lower()
        grant.sectors = [kw for kw in sectors_keywords if kw.lower() in page_text]
        
        return grant
    
    def _extract_provider(self, soup: BeautifulSoup, silo: str) -> str:
        """Extract grant provider based on silo"""
        providers = {
            'UK': ['Innovate UK', 'UKRI', 'British Council'],
            'EU': ['Horizon Europe', 'EIC', 'EIT'],
            'US': ['NSF', 'SBIR', 'DOE', 'NIH']
        }
        
        page_text = soup.get_text()
        for provider in providers.get(silo, []):
            if provider.lower() in page_text.lower():
                return provider
        
        return "Unknown Provider"
    
    def _parse_requirements(self, elem) -> List[str]:
        """Parse requirements from eligibility section"""
        requirements = []
        
        # Look for lists
        for li in elem.find_all('li'):
            req_text = li.get_text(strip=True)
            if req_text:
                requirements.append(req_text[:200])
        
        # Look for key phrases
        key_phrases = ['must be', 'required', 'need to', 'should have']
        text = elem.get_text()
        for phrase in key_phrases:
            if phrase in text.lower():
                # Extract sentence containing phrase
                sentences = text.split('.')
                for sent in sentences:
                    if phrase in sent.lower():
                        requirements.append(sent.strip()[:200])
        
        return requirements[:10]  # Limit requirements
    
    async def _follow_links(self, soup: BeautifulSoup, base_url: str, max_depth: int) -> Dict:
        """Follow relevant links and extract supplementary information"""
        result = {
            'urls': [],
            'pdfs': [],
            'context': {}
        }
        
        # Find relevant links
        relevant_keywords = ['guidance', 'eligibility', 'scope', 'application', 'form', 'template', 'FAQ']
        links = soup.find_all('a', href=True)
        
        tasks = []
        for link in links[:20]:  # Limit links
            href = link['href']
            link_text = link.get_text(strip=True).lower()
            
            # Make absolute URL
            if not href.startswith('http'):
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            
            # Check if PDF
            if href.endswith('.pdf'):
                result['pdfs'].append(href)
                continue
            
            # Check if relevant
            if any(kw.lower() in link_text for kw in relevant_keywords):
                result['urls'].append(href)
                
                if max_depth > 1 and len(tasks) < config.MAX_CONCURRENT_SCRAPES:
                    tasks.append(self._fetch_supplementary(href, max_depth - 1))
        
        # Fetch supplementary pages concurrently
        if tasks:
            supplementary_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, supp in enumerate(supplementary_results):
                if isinstance(supp, dict):
                    result['context'][f'supplementary_{i}'] = supp
        
        return result
    
    async def _fetch_supplementary(self, url: str, depth: int) -> Dict:
        """Fetch and extract key information from supplementary page"""
        content = await self._fetch_url(url)
        if not content:
            return {}
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract key information
        info = {
            'url': url,
            'title': soup.find('title').text if soup.find('title') else '',
            'headings': [h.text.strip() for h in soup.find_all(['h1', 'h2', 'h3'])[:5]],
            'key_points': []
        }
        
        # Extract key points (paragraphs after important headings)
        important_headings = ['eligibility', 'scope', 'assessment', 'criteria', 'requirements']
        for heading in soup.find_all(['h2', 'h3']):
            if any(kw in heading.text.lower() for kw in important_headings):
                next_elem = heading.find_next_sibling()
                if next_elem and next_elem.name in ['p', 'ul', 'ol']:
                    info['key_points'].append({
                        'heading': heading.text.strip(),
                        'content': next_elem.get_text(strip=True)[:500]
                    })
        
        return info
    
    async def _extract_pdf_text(self, pdf_url: str) -> Optional[str]:
        """Extract text from PDF"""
        if pdf_url in self.pdf_cache:
            return self.pdf_cache[pdf_url]
        
        try:
            # Download PDF
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    pdf_content = await response.read()
                    
                    # Save to cache
                    pdf_path = config.PDF_CACHE_DIR / hashlib.md5(pdf_url.encode()).hexdigest()
                    pdf_path.write_bytes(pdf_content)
                    
                    # Extract text using pdfplumber
                    text_parts = []
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages[:10]:  # Limit pages
                            text = page.extract_text()
                            if text:
                                text_parts.append(text)
                    
                    full_text = '\n'.join(text_parts)
                    self.pdf_cache[pdf_url] = full_text
                    return full_text
                    
        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_url}: {e}")
        
        return None

# ============================================================================
# VECTOR DATABASE
# ============================================================================

class VectorDB:
    """ChromaDB vector database for semantic search"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        self.embedder = SentenceTransformer(config.EMBEDDING_MODEL)
        self.collections = {}
        
    def get_or_create_collection(self, silo: str):
        """Get or create a collection for a silo"""
        collection_name = f"grants_{silo.lower()}"
        
        if collection_name not in self.collections:
            self.collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"silo": silo}
            )
        
        return self.collections[collection_name]
    
    async def add_grant(self, grant: Grant):
        """Add grant to vector database"""
        collection = self.get_or_create_collection(grant.silo)
        
        # Prepare document
        document = f"""
        Title: {grant.title}
        Provider: {grant.provider}
        Amount: {grant.currency} {grant.amount_min}-{grant.amount_max}
        Deadline: {grant.deadline}
        Sectors: {', '.join(grant.sectors)}
        Description: {grant.description}
        Eligibility: {json.dumps(grant.eligibility)}
        """
        
        # Add metadata context
        for key, value in grant.metadata.items():
            if isinstance(value, str):
                document += f"\n{key}: {value[:500]}"
        
        # Generate embedding
        embedding = self.embedder.encode(document).tolist()
        
        # Add to ChromaDB
        collection.add(
            ids=[grant.grant_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[{
                "title": grant.title,
                "provider": grant.provider,
                "silo": grant.silo,
                "deadline": grant.deadline.isoformat() if grant.deadline else "",
                "url": grant.application_url,
                "sectors": json.dumps(grant.sectors)
            }]
        )
        
        logger.info(f"Added grant {grant.grant_id} to {grant.silo} vector DB")
    
    async def search(self, query: str, silos: List[str], n_results: int = 10) -> List[Dict]:
        """Search across silos for relevant grants"""
        all_results = []
        
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        # Search each silo
        for silo in silos:
            collection = self.get_or_create_collection(silo)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            if results['ids'][0]:
                for i, grant_id in enumerate(results['ids'][0]):
                    all_results.append({
                        'grant_id': grant_id,
                        'silo': silo,
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'metadata': results['metadatas'][0][i],
                        'document': results['documents'][0][i]
                    })
        
        # Sort by score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return all_results[:n_results]

# ============================================================================
# DOMAIN NLMs
# ============================================================================

class DomainNLM:
    """Base class for domain-specialized NLMs"""
    
    def __init__(self, name: str, domain: str, vector_db: VectorDB):
        self.name = name
        self.domain = domain
        self.vector_db = vector_db
        self.llm_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None
        
    async def process_message(self, message: SIMPMessage) -> SIMPMessage:
        """Process incoming SIMP message"""
        try:
            # Route based on intent
            if message.intent == "search":
                result = await self.search(message.context)
            elif message.intent == "analyze":
                result = await self.analyze(message.context)
            elif message.intent == "validate":
                result = await self.validate(message.context)
            else:
                result = {"error": f"Unknown intent: {message.intent}"}
            
            # Create response
            response = SIMPMessage(
                msg_type=MessageType.RESPONSE,
                sender=self.name,
                receiver=message.sender,
                intent=f"{message.intent}_response",
                context=result,
                correlation_id=message.correlation_id
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return SIMPMessage(
                msg_type=MessageType.ERROR,
                sender=self.name,
                receiver=message.sender,
                intent="error",
                context={"error": str(e)},
                correlation_id=message.correlation_id
            )
    
    async def search(self, context: Dict) -> Dict:
        """Search for relevant information"""
        query = context.get('query', '')
        silos = context.get('silos', ['UK'])
        
        results = await self.vector_db.search(query, silos)
        
        return {
            'results': results,
            'count': len(results)
        }
    
    async def analyze(self, context: Dict) -> Dict:
        """Analyze data with LLM if available"""
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        prompt = f"""
        Analyze the following grant information for the query: {context.get('query')}
        
        Data: {json.dumps(context.get('data', {}))}
        
        Provide key insights and recommendations.
        """
        
        response = self.llm_client.messages.create(
            model="claude-3-sonnet-20240229",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return {
            'analysis': response.content[0].text,
            'model': 'claude-3-sonnet'
        }
    
    async def validate(self, context: Dict) -> Dict:
        """Validate eligibility or requirements"""
        # Implement validation logic
        return {
            'valid': True,
            'checks': context.get('requirements', [])
        }

class GrantsNLM(DomainNLM):
    """Specialized for grant discovery"""
    
    async def search(self, context: Dict) -> Dict:
        """Enhanced grant search"""
        query = context.get('query', '')
        filters = context.get('filters', {})
        silos = context.get('silos', ['UK'])
        
        # Add sector filtering
        if 'sectors' in filters:
            query += f" {' '.join(filters['sectors'])}"
        
        results = await self.vector_db.search(query, silos, n_results=20)
        
        # Filter by deadline if specified
        if 'deadline_after' in filters:
            deadline_filter = datetime.fromisoformat(filters['deadline_after'])
            results = [
                r for r in results
                if r['metadata'].get('deadline') and 
                datetime.fromisoformat(r['metadata']['deadline']) > deadline_filter
            ]
        
        return {
            'grants': results[:10],
            'total_found': len(results),
            'silos_searched': silos
        }

class EligibilityNLM(DomainNLM):
    """Specialized for eligibility checking"""
    
    async def validate(self, context: Dict) -> Dict:
        """Check eligibility against requirements"""
        user_profile = context.get('user_profile', {})
        grant_requirements = context.get('requirements', {})
        
        checks = []
        eligible = True
        
        # Check company type
        if 'company_type' in grant_requirements:
            check = {
                'requirement': 'Company Type',
                'needed': grant_requirements['company_type'],
                'user_has': user_profile.get('company_type', 'Unknown'),
                'passed': user_profile.get('company_type') == grant_requirements['company_type']
            }
            checks.append(check)
            eligible = eligible and check['passed']
        
        # Check location
        if 'location' in grant_requirements:
            check = {
                'requirement': 'Location',
                'needed': grant_requirements['location'],
                'user_has': user_profile.get('location', 'Unknown'),
                'passed': user_profile.get('location') in grant_requirements['location']
            }
            checks.append(check)
            eligible = eligible and check['passed']
        
        # Check company size
        if 'min_employees' in grant_requirements:
            check = {
                'requirement': 'Minimum Employees',
                'needed': grant_requirements['min_employees'],
                'user_has': user_profile.get('employees', 0),
                'passed': user_profile.get('employees', 0) >= grant_requirements['min_employees']
            }
            checks.append(check)
            eligible = eligible and check['passed']
        
        return {
            'eligible': eligible,
            'checks': checks,
            'recommendation': 'You are eligible for this grant!' if eligible else 'Some requirements not met.'
        }

# ============================================================================
# ORCHESTRATOR
# ============================================================================

class Orchestrator:
    """Central orchestrator that routes messages between NLMs"""
    
    def __init__(self, vector_db: VectorDB):
        self.vector_db = vector_db
        self.nlms = {
            'grants': GrantsNLM('grants', 'grant_discovery', vector_db),
            'eligibility': EligibilityNLM('eligibility', 'eligibility_checking', vector_db)
        }
        self.message_history = []
        self.llm_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None
    
    async def process_query(self, request: QueryRequest) -> Dict:
        """Process user query through FALM mesh"""
        start_time = datetime.utcnow()
        correlation_id = hashlib.md5(f"{request.query}{start_time}".encode()).hexdigest()[:8]
        
        # Extract intents from query
        intents = self._extract_intents(request.query)
        
        # Create SIMP messages for relevant NLMs
        messages = []
        for intent in intents:
            if intent['nlm'] in self.nlms:
                message = SIMPMessage(
                    msg_type=MessageType.QUERY,
                    sender='orchestrator',
                    receiver=intent['nlm'],
                    intent=intent['action'],
                    context={
                        'query': request.query,
                        'silos': request.silos,
                        'filters': request.filters,
                        'user_id': request.user_id
                    },
                    correlation_id=correlation_id
                )
                messages.append(message)
        
        # Send messages to NLMs concurrently
        tasks = [self.nlms[msg.receiver].process_message(msg) for msg in messages]
        responses = await asyncio.gather(*tasks)
        
        # Store message history
        self.message_history.extend(messages)
        self.message_history.extend(responses)
        
        # Aggregate responses
        aggregated = self._aggregate_responses(responses)
        
        # Synthesize final answer
        if self.llm_client and aggregated:
            final_answer = await self._synthesize_answer(request.query, aggregated)
        else:
            final_answer = self._format_basic_answer(aggregated)
        
        # Calculate metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            'answer': final_answer,
            'sources': aggregated,
            'correlation_id': correlation_id,
            'processing_time': processing_time,
            'nlms_queried': [msg.receiver for msg in messages],
            'simp_messages': len(messages) + len(responses)
        }
    
    def _extract_intents(self, query: str) -> List[Dict]:
        """Extract intents and determine which NLMs to query"""
        intents = []
        query_lower = query.lower()
        
        # Grant search patterns
        grant_patterns = ['grant', 'funding', 'fund', 'money', 'finance', 'support', 'scheme']
        if any(pattern in query_lower for pattern in grant_patterns):
            intents.append({'nlm': 'grants', 'action': 'search'})
        
        # Eligibility patterns
        eligibility_patterns = ['eligible', 'qualify', 'can i apply', 'requirements', 'criteria']
        if any(pattern in query_lower for pattern in eligibility_patterns):
            intents.append({'nlm': 'eligibility', 'action': 'validate'})
        
        # Default to grant search if no clear intent
        if not intents:
            intents.append({'nlm': 'grants', 'action': 'search'})
        
        return intents
    
    def _aggregate_responses(self, responses: List[SIMPMessage]) -> Dict:
        """Aggregate responses from multiple NLMs"""
        aggregated = {
            'grants': [],
            'eligibility': {},
            'errors': []
        }
        
        for response in responses:
            if response.msg_type == MessageType.ERROR:
                aggregated['errors'].append(response.context)
            elif response.sender == 'grants':
                aggregated['grants'] = response.context.get('grants', [])
            elif response.sender == 'eligibility':
                aggregated['eligibility'] = response.context
        
        return aggregated
    
    async def _synthesize_answer(self, query: str, aggregated: Dict) -> str:
        """Use Claude to synthesize natural language answer"""
        prompt = f"""
        User Query: {query}
        
        Grant Search Results: {json.dumps(aggregated.get('grants', [])[:3], indent=2)}
        
        Eligibility Results: {json.dumps(aggregated.get('eligibility', {}), indent=2)}
        
        Please provide a helpful, conversational response to the user's query based on this data.
        Focus on the most relevant grants and key eligibility points.
        """
        
        response = self.llm_client.messages.create(
            model="claude-3-sonnet-20240229",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return response.content[0].text
    
    def _format_basic_answer(self, aggregated: Dict) -> str:
        """Format basic answer without LLM"""
        answer_parts = []
        
        # Add grants
        grants = aggregated.get('grants', [])
        if grants:
            answer_parts.append(f"Found {len(grants)} relevant grants:\n")
            for grant in grants[:3]:
                metadata = grant.get('metadata', {})
                answer_parts.append(f"- {metadata.get('title', 'Unknown Grant')}")
                answer_parts.append(f"  Provider: {metadata.get('provider', 'Unknown')}")
                answer_parts.append(f"  Deadline: {metadata.get('deadline', 'Not specified')}")
                answer_parts.append(f"  Link: {metadata.get('url', '')}\n")
        
        # Add eligibility
        eligibility = aggregated.get('eligibility', {})
        if eligibility:
            answer_parts.append(f"\nEligibility: {eligibility.get('recommendation', 'Check requirements')}")
            for check in eligibility.get('checks', []):
                status = '✓' if check['passed'] else '✗'
                answer_parts.append(f"  {status} {check['requirement']}: {check['user_has']}")
        
        return '\n'.join(answer_parts) if answer_parts else "No relevant results found."

# ============================================================================
# DATA MANAGEMENT
# ============================================================================

class DataManager:
    """Manage data ingestion, storage, and updates"""
    
    def __init__(self, vector_db: VectorDB):
        self.vector_db = vector_db
        self.mongo_client = AsyncIOMotorClient(config.MONGODB_URL)
        self.db = self.mongo_client[config.MONGODB_DB]
        self.grants_collection = self.db.grants
        self.sources_collection = self.db.sources
        
        # Create indexes
        asyncio.create_task(self._create_indexes())
    
    async def _create_indexes(self):
        """Create MongoDB indexes"""
        await self.grants_collection.create_index([("grant_id", ASCENDING)])
        await self.grants_collection.create_index([("silo", ASCENDING)])
        await self.grants_collection.create_index([("deadline", DESCENDING)])
        await self.sources_collection.create_index([("url", ASCENDING)])
    
    async def ingest_source(self, request: DataIngestionRequest) -> Dict:
        """Ingest data from a source"""
        logger.info(f"Ingesting {request.source_url} into {request.silo} silo")
        
        # Check if already processed
        existing = await self.sources_collection.find_one({"url": request.source_url})
        if existing and (datetime.utcnow() - existing['last_updated']).days < 7:
            return {"status": "already_processed", "grant_id": existing.get('grant_id')}
        
        # Scrape data
        async with ScrapingEngine() as scraper:
            try:
                grant = await scraper.scrape_grant_source(
                    request.source_url,
                    request.silo,
                    request.follow_links,
                    request.max_depth
                )
                
                # Add metadata from request
                grant.metadata.update(request.metadata)
                
                # Save to MongoDB
                await self.grants_collection.replace_one(
                    {"grant_id": grant.grant_id},
                    grant.dict(),
                    upsert=True
                )
                
                # Add to vector DB
                await self.vector_db.add_grant(grant)
                
                # Update sources collection
                await self.sources_collection.replace_one(
                    {"url": request.source_url},
                    {
                        "url": request.source_url,
                        "silo": request.silo,
                        "grant_id": grant.grant_id,
                        "last_updated": datetime.utcnow()
                    },
                    upsert=True
                )
                
                return {
                    "status": "success",
                    "grant_id": grant.grant_id,
                    "title": grant.title,
                    "supplementary_urls": len(grant.supplementary_urls),
                    "pdfs": len(grant.pdf_documents)
                }
                
            except Exception as e:
                logger.error(f"Error ingesting {request.source_url}: {e}")
                return {"status": "error", "error": str(e)}
    
    async def add_manual_grant(self, grant_data: Dict) -> Dict:
        """Add grant data manually"""
        grant = Grant(**grant_data)
        
        # Save to MongoDB
        await self.grants_collection.replace_one(
            {"grant_id": grant.grant_id},
            grant.dict(),
            upsert=True
        )
        
        # Add to vector DB
        await self.vector_db.add_grant(grant)
        
        return {"status": "success", "grant_id": grant.grant_id}
    
    async def bulk_import(self, file_path: Path, silo: str) -> Dict:
        """Bulk import grants from JSON or CSV"""
        if file_path.suffix == '.json':
            with open(file_path) as f:
                grants_data = json.load(f)
        elif file_path.suffix == '.csv':
            df = pd.read_csv(file_path)
            grants_data = df.to_dict('records')
        else:
            return {"status": "error", "error": "Unsupported file format"}
        
        results = []
        for grant_data in grants_data:
            grant_data['silo'] = silo
            result = await self.add_manual_grant(grant_data)
            results.append(result)
        
        return {
            "status": "success",
            "imported": len(results),
            "results": results
        }

# ============================================================================
# SCHEDULER
# ============================================================================

class UpdateScheduler:
    """Schedule automatic data updates"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.scheduler = AsyncIOScheduler()
        self.update_sources = []
        
    def start(self):
        """Start scheduler"""
        # Add daily update job
        self.scheduler.add_job(
            self.update_all_sources,
            IntervalTrigger(days=1),
            id='daily_update',
            name='Daily grant data update'
        )
        
        self.scheduler.start()
        logger.info("Update scheduler started")
    
    async def update_all_sources(self):
        """Update all registered sources"""
        logger.info("Running scheduled update")
        
        for source in self.update_sources:
            request = DataIngestionRequest(**source)
            await self.data_manager.ingest_source(request)
        
        logger.info(f"Updated {len(self.update_sources)} sources")
    
    def add_source(self, source: Dict):
        """Add source for automatic updates"""
        self.update_sources.append(source)

# ============================================================================
# API APPLICATION
# ============================================================================

app = FastAPI(
    title="FALM Grant Analyst API",
    description="Production-ready Federated Agentic LLM Mesh for grant discovery",
    version="2.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
vector_db = VectorDB()
data_manager = DataManager(vector_db)
orchestrator = Orchestrator(vector_db)
scheduler = UpdateScheduler(data_manager)

# Start scheduler on startup
@app.on_event("startup")
async def startup():
    scheduler.start()
    logger.info("FALM Production API started")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "running",
        "service": "FALM Grant Analyst",
        "version": "2.0.0",
        "silos": ["UK", "EU", "US"]
    }

@app.post("/api/query")
async def query(request: QueryRequest) -> Dict:
    """Process user query through FALM mesh"""
    result = await orchestrator.process_query(request)
    return result

@app.post("/api/ingest/url")
async def ingest_url(request: DataIngestionRequest) -> Dict:
    """Ingest data from URL"""
    result = await data_manager.ingest_source(request)
    return result

@app.post("/api/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    silo: str = "UK"
) -> Dict:
    """Ingest grants from uploaded file"""
    # Save uploaded file
    file_path = config.DATA_DIR / file.filename
    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # Import
    result = await data_manager.bulk_import(file_path, silo)
    
    # Clean up
    file_path.unlink()
    
    return result

@app.post("/api/grants")
async def add_grant(grant: Grant) -> Dict:
    """Add grant manually"""
    result = await data_manager.add_manual_grant(grant.dict())
    return result

@app.get("/api/grants/{grant_id}")
async def get_grant(grant_id: str) -> Dict:
    """Get grant details"""
    grant = await data_manager.db.grants.find_one({"grant_id": grant_id})
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    return grant

@app.post("/api/schedule/source")
async def schedule_source(source: DataIngestionRequest) -> Dict:
    """Add source for automatic updates"""
    scheduler.add_source(source.dict())
    return {"status": "scheduled", "sources": len(scheduler.update_sources)}

@app.get("/api/stats")
async def get_stats() -> Dict:
    """Get system statistics"""
    stats = {
        "total_grants": await data_manager.db.grants.count_documents({}),
        "grants_by_silo": {},
        "total_sources": await data_manager.db.sources.count_documents({}),
        "scheduled_sources": len(scheduler.update_sources),
        "message_history": len(orchestrator.message_history)
    }
    
    for silo in ["UK", "EU", "US"]:
        stats["grants_by_silo"][silo] = await data_manager.db.grants.count_documents({"silo": silo})
    
    return stats

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "falm_production_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
