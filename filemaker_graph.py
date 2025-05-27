from lxml import etree
import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
import json
import logging
from pathlib import Path

#this file parses xml into graph representation
#provides dfs and bfs to navigate the graph 


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileMakerGraphError(Exception):
    """Base exception for FileMakerGraph errors"""

    #customize myself
    pass

class FileMakerGraph:
    def __init__(self):
        self.graph = nx.DiGraph() #directed graph - allows explicit up/down traversal
        self.node_attributes = {}
        
    def parse_xml(self, xml_path: str):
        """Parse the FileMaker DDR XML and create a graph structure."""
        try:
            xml_path = Path(xml_path)
            #converts string path into path object 
            if not xml_path.exists():
                #check if specified path exists on the disk 
                raise FileMakerGraphError(f"XML file not found: {xml_path}")
                
            logger.info(f"Parsing XML file: {xml_path}")
            #prefix 
            tree = etree.parse(str(xml_path))
            #serializes the xml file into tree objrect 
            #this is abstracted away
            root = tree.getroot()
            #returns the root element of the xml file 

            #two pass algorithm is slower maybe opitmize in the future 
            
            # First pass: Create nodes for all elements
            node_count = 0
            for element in root.iter(): #iterates through all elements in the xml file 
                #this performs dfs on the xml file 
                node_id = element.get('id')#gets the id of the element 
                if node_id: 
                    #we only buid graph of uniquely identifiable entites 
                    self.graph.add_node(node_id)
                    # Store all attributes
                    attrs = dict(element.attrib)
                    attrs['tag'] = element.tag
                    attrs['text'] = element.text.strip() if element.text else ''
                    self.node_attributes[node_id] = attrs
                    node_count += 1
                    #black boxed here.....might debug later 
            
            logger.info(f"Created {node_count} nodes from XML")
                    
            # Second pass: Create parent-child relationships
            # deterministic 
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
            #wrong xml 
            raise FileMakerGraphError(f"Invalid XML file: {e}")
        except Exception as e:
            #other exceptions
            #add more detailed exception handling later 
            raise FileMakerGraphError(f"Error parsing XML: {e}")
    
    def bfs_search(self, start_node: str, max_hops: int = 4) -> List[str]:
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
                
                # Log the current node and its neighbors with relationship types
                logger.debug(f"At node: {node} ({self.node_attributes[node].get('tag', '')})")
                for neighbor in self.graph.neighbors(node):
                    edge = self.graph[node][neighbor]
                    rel_type = edge['relationship']
                    neighbor_type = self.node_attributes[neighbor].get('tag', '')
                    if rel_type == 'parent_of':
                        logger.debug(f"  ↓ Down to child: {neighbor} ({neighbor_type})")
                    else:  # child_of
                        logger.debug(f"  ↑ Up to parent: {neighbor} ({neighbor_type})")
                    
                    if neighbor not in visited:
                        queue.append((neighbor, path + [neighbor], hops + 1))
        
        return paths
    
    def dfs_search(self, start_node: str, max_hops: int = 4) -> List[str]:
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
            
            # Log the current node and its neighbors with relationship types
            logger.debug(f"At node: {node} ({self.node_attributes[node].get('tag', '')})")
            for neighbor in self.graph.neighbors(node):
                edge = self.graph[node][neighbor]
                rel_type = edge['relationship']
                neighbor_type = self.node_attributes[neighbor].get('tag', '')
                if rel_type == 'parent_of':
                    logger.debug(f"  ↓ Down to child: {neighbor} ({neighbor_type})")
                else:  # child_of
                    logger.debug(f"  ↑ Up to parent: {neighbor} ({neighbor_type})")
                
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