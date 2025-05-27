from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from openai import OpenAI
from filemaker_graph import FileMakerGraph

load_dotenv()

class FileMakerRAG:
    def __init__(self):
        self.graph = FileMakerGraph()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def load_database(self, xml_path: str):
        """Load and parse the FileMaker database XML."""
        self.graph.parse_xml(xml_path)
        
    def format_context(self, contexts: List[Dict]) -> str:
        """Format the context information for the LLM prompt."""
        formatted = []
        for ctx in contexts:
            node_info = []
            if 'attributes' in ctx:
                attrs = ctx['attributes']
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
        # First, find relevant starting nodes based on the query
        relevant_nodes = []
        
        if table_name:
            # Search for table nodes
            for node_id, attrs in self.graph.node_attributes.items():
                if attrs['tag'] == 'Table' and attrs.get('name') == table_name:
                    relevant_nodes.append(node_id)
                    
        if property_name:
            # Search for property nodes
            for node_id, attrs in self.graph.node_attributes.items():
                if attrs.get('name') == property_name:
                    relevant_nodes.append(node_id)
        
        if not relevant_nodes:
            # If no specific nodes found, we might want to do a more general search
            # This could be enhanced with embedding-based search
            pass
            
        # Collect contexts from both BFS and DFS
        all_contexts = []
        for start_node in relevant_nodes:
            # Get BFS paths
            bfs_paths = self.graph.bfs_search(start_node, max_hops=3)
            for path in bfs_paths:
                context = self.graph.get_path_context(path)
                all_contexts.extend(context)
                
            # Get DFS paths
            dfs_paths = self.graph.dfs_search(start_node, max_hops=3)
            for path in dfs_paths:
                context = self.graph.get_path_context(path)
                all_contexts.extend(context)
                
        # Format the context for the LLM
        formatted_context = self.format_context(all_contexts)
        
        # Prepare the prompt for the LLM
        prompt = f"""You are analyzing a FileMaker database structure. Given the following context about the database structure and relationships, please answer this question: {question}

Context:
{formatted_context}

Please analyze the context and provide a detailed answer about which scripts might be causing issues, particularly focusing on any scripts that modify tables or create entries. If you find potential problematic scripts, explain why they might be causing issues."""

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