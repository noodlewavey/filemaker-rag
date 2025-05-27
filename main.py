import argparse
import logging
from rag_system import FileMakerRAG, FileMakerRAGError
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='FileMaker Database RAG Analysis Tool')
    parser.add_argument('xml_path', help='Path to the FileMaker DDR XML file')
    parser.add_argument('--table', help='Specific table name to focus on', default=None)
    parser.add_argument('--property', help='Specific property name to focus on', default=None)
    parser.add_argument('--question', help='Question about the database', required=True)
    parser.add_argument('--debug', help='Enable debug logging', action='store_true')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Validate input file
        xml_path = Path(args.xml_path)
        if not xml_path.exists():
            raise FileMakerRAGError(f"XML file not found: {xml_path}")
        
        # Initialize the RAG system
        rag = FileMakerRAG()
        
        # Load the database
        logger.info(f"Loading database from {xml_path}...")
        rag.load_database(str(xml_path))
        
        # Query the system
        logger.info("Analyzing the database...")
        response = rag.query(
            question=args.question,
            table_name=args.table,
            property_name=args.property
        )
        
        print("\nAnalysis Result:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        
    except FileMakerRAGError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main() 