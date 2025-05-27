import argparse
from rag_system import FileMakerRAG

def main():
    parser = argparse.ArgumentParser(description='FileMaker Database RAG Analysis Tool')
    parser.add_argument('xml_path', help='Path to the FileMaker DDR XML file')
    parser.add_argument('--table', help='Specific table name to focus on', default=None)
    parser.add_argument('--property', help='Specific property name to focus on', default=None)
    parser.add_argument('--question', help='Question about the database', required=True)
    
    args = parser.parse_args()
    
    # Initialize the RAG system
    rag = FileMakerRAG()
    
    # Load the database
    print(f"Loading database from {args.xml_path}...")
    rag.load_database(args.xml_path)
    
    # Query the system
    print("\nAnalyzing the database...")
    response = rag.query(
        question=args.question,
        table_name=args.table,
        property_name=args.property
    )
    
    print("\nAnalysis Result:")
    print("-" * 80)
    print(response)
    print("-" * 80)

if __name__ == "__main__":
    main() 