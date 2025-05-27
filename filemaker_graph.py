from lxml import etree
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileMakerGraphError(Exception):
    """Base exception for FileMakerGraph errors"""
    pass

class FileMakerGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_attributes = {}
        
    def parse_xml(self, xml_path: str):
        """Parse the FileMaker DDR XML and create a graph structure."""
        try:
            xml_path = Path(xml_path)
            if not xml_path.exists():
                raise FileMakerGraphError(f"XML file not found: {xml_path}")
                
            logger.info(f"Parsing XML file: {xml_path}")
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
            
            # First pass: Create nodes for all elements
            node_count = 0
            for element in root.iter():
                node_id = element.get('id')
                if node_id:
                    self.graph.add_node(node_id)
                    # Store all attributes
                    attrs = dict(element.attrib)
                    attrs['tag'] = element.tag
                    attrs['text'] = element.text.strip() if element.text else ''
                    self.node_attributes[node_id] = attrs
                    node_count += 1
            
            logger.info(f"Created {node_count} nodes from XML")
                    
            # Second pass: Create parent-child relationships
            edge_count = 0
            for element in root.iter():
                parent_id = element.get('id')
                if parent_id:
                    for child in element:
                        child_id = child.get('id')
                        if child_id:
                            self.graph.add_edge(parent_id, child_id, relationship='parent_of')
                            self.graph.add_edge(child_id, parent_id, relationship='child_of')
                            edge_count += 2
                            
            logger.info(f"Created {edge_count} edges from XML")
            
        except etree.XMLSyntaxError as e:
            raise FileMakerGraphError(f"Invalid XML file: {e}")
        except Exception as e:
            raise FileMakerGraphError(f"Error parsing XML: {e}")
    
    def bfs_search(self, start_node: str, max_hops: int = 3) -> List[str]:
        """Perform BFS from start node with hop limit."""
        if start_node not in self.graph:
            raise FileMakerGraphError(f"Start node not found: {start_node}")
            
        visited = set()
        paths = []
        queue = [(start_node, [start_node], 0)]
        
        while queue:
            node, path, hops = queue.pop(0)
            if hops > max_hops:
                continue
                
            if node not in visited:
                visited.add(node)
                paths.append(path)
                
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        queue.append((neighbor, path + [neighbor], hops + 1))
        
        return paths
    
    def dfs_search(self, start_node: str, max_hops: int = 3) -> List[str]:
        """Perform DFS from start node with hop limit."""
        if start_node not in self.graph:
            raise FileMakerGraphError(f"Start node not found: {start_node}")
            
        visited = set()
        paths = []
        
        def dfs_recursive(node: str, path: List[str], hops: int):
            if hops > max_hops or node in visited:
                return
            
            visited.add(node)
            paths.append(path)
            
            for neighbor in self.graph.neighbors(node):
                if neighbor not in visited:
                    dfs_recursive(neighbor, path + [neighbor], hops + 1)
        
        dfs_recursive(start_node, [start_node], 0)
        return paths
    
    def get_node_context(self, node_id: str) -> Dict:
        """Get the context (attributes and relationships) for a node."""
        if node_id not in self.node_attributes:
            raise FileMakerGraphError(f"Node not found: {node_id}")
            
        context = {
            'attributes': self.node_attributes[node_id],
            'parents': [],
            'children': []
        }
        
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph[node_id][neighbor]
            if edge_data['relationship'] == 'parent_of':
                context['children'].append({
                    'id': neighbor,
                    'attributes': self.node_attributes[neighbor]
                })
            elif edge_data['relationship'] == 'child_of':
                context['parents'].append({
                    'id': neighbor,
                    'attributes': self.node_attributes[neighbor]
                })
                
        return context
    
    def get_path_context(self, path: List[str]) -> List[Dict]:
        """Get context for an entire path."""
        return [self.get_node_context(node_id) for node_id in path] 