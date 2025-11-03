"""
Add this method to BaseNLM to enable hybrid search
Replace the existing search() method
"""

async def search(self, query: str, max_results: int = 10, filters: Dict = None) -> List[Dict]:
    """
    Hybrid search: semantic + keyword matching
    
    Combines:
    - Semantic similarity (70% weight)
    - Keyword overlap (30% weight)
    """
    import json
    
    # Generate query embedding
    query_embedding = self.embedder.encode(query).tolist()
    query_terms = set(query.lower().split())
    
    # Get more results for re-ranking
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=max_results * 3,  # Get 3x for re-ranking
        where=filters
    )
    
    # Parse and score results
    grants = []
    if results['metadatas'] and results['metadatas'][0]:
        for i, metadata in enumerate(results['metadatas'][0]):
            grant = {}
            for key, value in metadata.items():
                # Deserialize JSON strings
                if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                    try:
                        grant[key] = json.loads(value)
                    except json.JSONDecodeError:
                        grant[key] = value
                else:
                    grant[key] = value
            
            # Calculate keyword overlap score
            grant_text = f"{grant.get('title', '')} {grant.get('description', '')}".lower()
            grant_terms = set(grant_text.split())
            keyword_overlap = len(query_terms.intersection(grant_terms))
            keyword_score = keyword_overlap / max(len(query_terms), 1)
            
            # Semantic distance from ChromaDB (lower = better)
            semantic_distance = results['distances'][0][i]
            semantic_score = 1 - semantic_distance  # Convert to similarity
            
            # Combined score (weighted)
            combined_score = (
                0.7 * semantic_score +
                0.3 * keyword_score
            )
            
            grant['relevance_score'] = float(combined_score)
            grant['semantic_score'] = float(semantic_score)
            grant['keyword_score'] = float(keyword_score)
            
            grants.append(grant)
    
    # Sort by combined score
    grants.sort(key=lambda g: g['relevance_score'], reverse=True)
    
    # Return top N
    top_grants = grants[:max_results]
    
    logger.info(f"[{self.nlm_id}] Hybrid search '{query}': {len(top_grants)} results "
               f"(avg semantic: {sum(g['semantic_score'] for g in top_grants)/len(top_grants):.3f}, "
               f"avg keyword: {sum(g['keyword_score'] for g in top_grants)/len(top_grants):.3f})")
    
    return top_grants
