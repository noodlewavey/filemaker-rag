# FileMaker RAG Analysis Tool

This tool helps debug FileMaker database issues by analyzing the Database Design Report (DDR) XML using a Tree-based RAG (Retrieval Augmented Generation) approach. It's particularly useful for identifying problematic scripts that might be causing duplicate entries or other data integrity issues.

## Features

- Parse FileMaker DDR XML files into a graph structure
- Use both BFS and DFS to traverse the database structure
- Combine structural analysis with LLM-based reasoning
- Focus searches on specific tables or properties
- Identify potential problematic scripts and their effects on tables

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/filemaker-rag.git
cd filemaker-rag
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your OpenAI API key:
Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

The tool can be used from the command line:

```bash
python main.py path/to/ddr.xml --question "Which scripts might be creating duplicate entries?" --table "MyTable"
```

### Arguments

- `xml_path`: Path to the FileMaker DDR XML file (required)
- `--question`: Your question about the database (required)
- `--table`: Specific table name to focus on (optional)
- `--property`: Specific property name to focus on (optional)

### Example Questions

1. Find scripts creating duplicate entries:
```bash
python main.py ddr.xml --question "Which scripts might be creating duplicate entries in the Customers table?" --table "Customers"
```

2. Analyze table modifications:
```bash
python main.py ddr.xml --question "What scripts modify the email field?" --property "email"
```

## How It Works

1. **XML Parsing**: The tool parses the FileMaker DDR XML into a graph structure where nodes represent database elements (tables, scripts, fields, etc.) and edges represent relationships.

2. **Graph Traversal**: 
   - Uses BFS to explore immediate context (neighboring elements)
   - Uses DFS to explore execution chains and nested dependencies
   - Implements hop limits to prevent runaway traversal

3. **Context Collection**: Gathers relevant context about database elements by traversing the graph from important starting points.

4. **LLM Analysis**: Feeds the collected context to GPT-4 for analysis and recommendations about potential issues.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 