from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from openai import OpenAI
from filemaker_graph import FileMakerGraph, FileMakerGraphError
import logging
from sentence_transformers import SentenceTransformer
#sentence transformer is used to embed the text of the nodes into a vector space
#this allows us to find similar nodes based on the text of the nodes
import numpy as np
from pathlib import Path

#Uses filemaker_graaph to build the graph
#gathers relevant context
#sends to llm for analysis....

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileMakerRAGError(Exception):
    """Base exception for FileMakerRAG errors"""
    pass

class FileMakerRAG:
    def __init__(self):
        self.graph = FileMakerGraph()
        
        # Load environment variables
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise FileMakerRAGError("OpenAI API key not found in environment variables")
            
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            raise FileMakerRAGError(f"Error initializing OpenAI client: {e}")
            
        # Initialize sentence transformer for embedding-based search
        try:
            logger.info("Loading sentence transformer model...")
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            raise FileMakerRAGError(f"Error loading sentence transformer: {e}")
            
        self.node_embeddings = {}
        
    def load_database(self, xml_path: str):
        """Load and parse the FileMaker database XML."""
        try:
            self.graph.parse_xml(xml_path)
            logger.info("Computing embeddings for nodes...")
            self._compute_node_embeddings()
        except FileMakerGraphError as e:
            raise FileMakerRAGError(f"Error loading database: {e}")
            
    def _compute_node_embeddings(self):
        """Compute embeddings for all nodes in the graph."""
        for node_id, attrs in self.graph.node_attributes.items():
            #we look up the dictionary to get the attributes of the node
            # Create a text representation of the node
            text = f"{attrs.get('tag', '')} {attrs.get('name', '')} {attrs.get('text', '')}"
            #example of the format of the text:
            #<Table name="Table1">
            #<Field name="Field1" type="text">
            #<Field name="Field2" type="number">
            #</Table>
            #</Field>
            #</Field>

            #example of the text:
            #Table Table1
            #Field Field1 text
            #Field Field2 number
            
            
            self.node_embeddings[node_id] = self.encoder.encode(text)
            
    def _find_similar_nodes(self, query: str, top_k: int = 5) -> List[str]:
        """Find nodes most similar to the query using embeddings."""
        query_embedding = self.encoder.encode(query)
        
        # Compute similarities
        similarities = {}
        for node_id, embedding in self.node_embeddings.items():
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
            similarities[node_id] = similarity
            #similarity is a number between 0 and 1 that represents how similar the query is to the node
            #we feed in query_embedding and embedding and get a similarity score
            
        # Get top-k similar nodes
        sorted_nodes = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in sorted_nodes[:top_k]]
        
    def format_context(self, contexts: List[Dict]) -> str:
        """Format the context information for the LLM prompt."""
        formatted = []
        seen = set()  # For deduplication
        
        for ctx in contexts:
            if 'attributes' not in ctx:
                continue
                
            # Create a unique key for deduplication
            attrs = ctx['attributes']
            key = f"{attrs.get('tag', '')}_{attrs.get('name', '')}_{attrs.get('text', '')}"
            
            if key in seen:
                continue
                
            seen.add(key)
            node_info = []
            
            node_info.append(f"Type: {attrs.get('tag', 'unknown')}")
            if 'name' in attrs:
                node_info.append(f"Name: {attrs['name']}")
            if 'text' in attrs and attrs['text']:
                node_info.append(f"Content: {attrs['text']}")
                    
            if ctx.get('parents'):
                parents = [p['attributes'].get('name', p['id']) for p in ctx['parents']]
                node_info.append(f"Parents: {', '.join(parents)}")
                
            if ctx.get('children'):
                children = [c['attributes'].get('name', c['id']) for c in ctx['children']]
                node_info.append(f"Children: {', '.join(children)}")
                
            formatted.append(" | ".join(node_info))
            
        return "\n".join(formatted)
        
    def query(self, question: str, property_name: str = None, table_name: str = None) -> str:
        """
        Query the FileMaker database using RAG approach.
        
        Args:
            question: The question about the database
            property_name: Optional property to focus the search on
            table_name: Optional table name to focus the search on
        """
        try:
            # First, find relevant starting nodes based on the query
            relevant_nodes = set()
            
            if table_name:
                # Search for table nodes
                for node_id, attrs in self.graph.node_attributes.items():
                    if attrs['tag'] == 'Table' and attrs.get('name') == table_name:
                        relevant_nodes.add(node_id)
                        
            if property_name:
                # Search for property nodes
                for node_id, attrs in self.graph.node_attributes.items():
                    if attrs.get('name') == property_name:
                        relevant_nodes.add(node_id)
            
            if not relevant_nodes:
                # Use embedding-based search
                logger.info("No exact matches found, using embedding-based search...")
                search_query = f"{table_name or ''} {property_name or ''} {question}"
                relevant_nodes = set(self._find_similar_nodes(search_query))
                
            # Collect contexts by traversing both up and down from each node
            all_contexts = []
            for start_node in relevant_nodes:
                logger.info(f"Gathering context for node: {start_node}")
                
                # First get paths going up and down with BFS
                bfs_paths = self.graph.bfs_search(start_node, max_hops=4)
                
                # Then get paths going up and down with DFS
                dfs_paths = self.graph.dfs_search(start_node, max_hops=4)
                
                # Combine all unique paths
                all_paths = set(tuple(path) for path in bfs_paths + dfs_paths)
                
                # Get context for each path
                for path in all_paths:
                    context = self.graph.get_path_context(list(path))
                    all_contexts.extend(context)
                    
            # Format the context for the LLM
            formatted_context = self.format_context(all_contexts)
            
            if not formatted_context:
                return "No relevant information found in the database."
            
            # Prepare the prompt for the LLM
            prompt = f"""You are analyzing a FileMaker database structure. Given the following context about the database structure and relationships, please answer this question: {question}

Context:
{formatted_context}

Please analyze the context and provide a detailed answer about which scripts might be causing issues, particularly focusing on any scripts that modify tables or create entries. If you find potential problematic scripts, explain why they might be causing issues."""

            try:
                # Query the LLM
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a FileMaker database expert helping to debug issues with scripts and data modifications."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                raise FileMakerRAGError(f"Error querying OpenAI API: {e}")
                
        except Exception as e:
            raise FileMakerRAGError(f"Error processing query: {e}") 