# IDMS Program Analyzer

A Streamlit-based application that helps legacy COBOL/IDMS developers extract business logic from their programs and generate test scripts using LLM technology.

## Overview

The IDMS Program Analyzer is designed to address a common challenge in legacy system maintenance: understanding and testing complex IDMS programs written decades ago. The application leverages Llama models via the Groq API to analyze COBOL/IDMS programs, extract structured business logic, and generate comprehensive test scripts.

## Features

1. **Intelligent Code Analysis**: Automatically distinguishes between IDMS-DC (online) and IDMS-DB (batch) programs
2. **Structured Business Logic Extraction**: Produces a markdown document with program purpose, core rules, validations, special cases, and integration points
3. **User Validation**: Allows users to review and edit the extracted business logic
4. **Comprehensive Test Scripts**: Creates detailed test cases with environment setup, test data, preconditions, steps, and expected results
5. **Professional Document Export**: Converts the outputs to well-formatted Word (.docx) documents
6. **Handling Large Programs**: Smart chunking and summarization to process programs of any size within token limits

## Project Structure

```
idms-program-analyzer/
│
├── app.py                    # Main Streamlit application
│
├── components/               # UI Components
│   ├── file_uploader.py      # File upload and validation
│   ├── logic_extractor.py    # Extract business logic using LLM
│   ├── logic_validator.py    # Validate and edit business logic
│   ├── test_generator.py     # Generate test scripts
│   └── doc_exporter.py       # Export to Word documents
│
├── models/                   # Data Models
│   └── business_logic.py     # Business logic data structures
│
├── utils/                    # Utilities
│   └── llm_utils.py          # Groq API integration
│
├── .env                      # Environment variables (not in git)
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/idms-program-analyzer.git
cd idms-program-analyzer
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Follow the application workflow:
   - Upload your IDMS/COBOL program file (supported formats: .cob, .cbl, .cobol, .cpy, .txt)
   - Extract business logic
   - Review and validate the extracted logic
   - Generate test scripts
   - Download the results as Word documents

## Requirements

- Python 3.8+
- Groq API access (get an API key at https://console.groq.com)
- Internet connection for API calls

## Technologies Used

- **Frontend**: Streamlit for the web interface
- **LLM Integration**: Groq API with Llama models for AI analysis
- **Document Generation**: python-docx for creating Word documents
- **Data Validation**: Pydantic for structured data handling

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Special thanks to the Groq team for providing access to powerful language models
- Streamlit for making it easy to build data applications in Python
