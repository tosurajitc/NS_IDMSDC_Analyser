import streamlit as st
import re
import os
from typing import Optional, Tuple, Dict, Any
import pandas as pd

class FileUploader:
    """Streamlit component for uploading and validating IDMS program files."""
    
    def __init__(self):
        """Initialize the file uploader component."""
        self.valid_extensions = [".cob", ".cbl", ".txt", ".cobol", ".cpy"]
        self.min_file_size = 100  # Minimum file size in bytes to be considered valid
        self.max_file_size = 10 * 1024 * 1024  # Maximum file size (10MB)
    
    def _is_valid_extension(self, filename: str) -> bool:
        """
        Check if the file has a valid extension.
        Allow any plausible COBOL file extension, or validate content regardless of extension.
        """
        # If we're accepting all file types based on content, just return True
        return True
    
    def _is_valid_size(self, file_size: int) -> bool:
        """Check if the file size is within acceptable limits."""
        return self.min_file_size <= file_size <= self.max_file_size
    
    def _detect_program_type(self, content: str) -> str:
        """
        Detect if the program is IDMS-DC (online) or IDMS-DB (batch).
        
        Args:
            content: The content of the uploaded file
            
        Returns:
            str: "DC" for online programs, "DB" for batch programs
        """
        # Look for common IDMS-DC indicators
        dc_patterns = [
            r'PROTOCOL\s+MODE\s+IS\s+(IDMSDC|DCUF)',
            r'CALL\s+"IDMS"',
            r'MAP\s+SECTION',
            r'COPY\s+IDMS\s+SUBSCHEMA',
            r'##MAPBIND',
            r'TRANSFER\s+TO\s+PROGRAM',
            r'LINK\s+TO\s+PROGRAM',
            r'ACCEPT\s+TASK\s+CODE'
        ]
        
        # Look for common IDMS-DB batch indicators
        db_patterns = [
            r'DATABASE\s+SECTION',
            r'INVOKE\s+SUBSCHEMA',
            r'DB-STATISTICS',
            r'RUN-UNIT',
            r'COPY\s+IDMS\s+SUBSCHEMA-CTRL',
            r'PROCEDURE\s+DIVISION\s+USING\s+SUBSCHEMA-NAMES'
        ]
        
        # Count matches for each type
        dc_count = sum(1 for pattern in dc_patterns if re.search(pattern, content, re.IGNORECASE))
        db_count = sum(1 for pattern in db_patterns if re.search(pattern, content, re.IGNORECASE))
        
        # Determine the program type based on the counts
        if dc_count > db_count:
            return "DC"
        elif db_count > dc_count:
            return "DB"
        else:
            # If can't determine clearly, look for additional clues
            if any(indicator in content.upper() for indicator in ["SCREEN SECTION", "WORKING-STORAGE SECTION"]):
                return "DC"  # More likely to be online
            else:
                return "DB"  # Default to batch if unclear
    
    def _has_idms_content(self, content: str) -> bool:
        """
        Check if the file appears to contain IDMS/COBOL code.
        More lenient version that accepts almost any file with code-like content.
        
        Args:
            content: The content of the uploaded file
            
        Returns:
            bool: True if the file appears to contain code
        """
        # Look for common COBOL/IDMS indicators
        cobol_indicators = [
            r'IDENTIFICATION\s+DIVISION',
            r'PROCEDURE\s+DIVISION',
            r'PROGRAM-ID',
            r'DATA\s+DIVISION',
            r'WORKING-STORAGE\s+SECTION',
            r'ENVIRONMENT\s+DIVISION',
            r'COPY\s+IDMS',
            r'MOVE\s+',
            r'PERFORM\s+',
            r'IF\s+',
            r'END-IF',
            r'SECTION',
            r'DIVISION',
            r'COMPUTE',
            r'ACCEPT',
            r'DISPLAY',
            r'EXEC\s+SQL',
            r'CALL\s+',
            r'PIC\s+',
            r'PICTURE\s+',
            r'COBOL',
            r'IDMS'
        ]
        
        # Check if the file contains at least a few code-like indicators
        matches = sum(1 for pattern in cobol_indicators if re.search(pattern, content, re.IGNORECASE))
        
        # Debug info
        st.write(f"Debug - COBOL indicators found: {matches}")
        
        # More lenient - just needs 1 match
        return matches >= 1
    
    def _read_file_content(self, file) -> str:
        """
        Read file content with various encodings if necessary.
        
        Args:
            file: The uploaded file object
            
        Returns:
            str: The file content as a string
        """
        # Make a copy of the original file content
        file_content = file.read()
        file.seek(0)  # Reset file pointer
        
        # Try to detect if this is a binary file
        is_binary = False
        try:
            # Check for null bytes which typically indicate binary data
            if b'\x00' in file_content[:1024]:
                is_binary = True
        except:
            pass
        
        if is_binary:
            st.warning("File appears to be binary. Attempting to decode...")
            # For binary files, just use a representation that won't crash
            try:
                return file_content.decode('latin-1', errors='replace')
            except:
                return str(file_content)
        
        # First try UTF-8
        try:
            content = file_content.decode("utf-8")
            return content
        except UnicodeDecodeError:
            pass
            
        # Try other common encodings
        encodings = [
            "latin-1", "iso-8859-1", "windows-1252", "ascii", 
            "cp437", "cp850", "cp1140",  # EBCDIC-related encodings
            "utf-16", "utf-32"
        ]
        
        for encoding in encodings:
            try:
                content = file_content.decode(encoding, errors="replace")
                st.info(f"Successfully decoded using {encoding} encoding")
                return content
            except Exception as e:
                continue
        
        # If all encodings fail, convert to hex representation as last resort
        st.warning("Unable to decode the file with standard encodings. Using fallback method.")
        return f"BINARY FILE: First 100 bytes: {file_content[:100].hex()}"
    
    def render(self) -> Dict[str, Any]:
        """
        Render the file uploader in the Streamlit UI.
        
        Returns:
            Dict with file information:
            {
                "content": file content (str or None),
                "name": file name (str or None),
                "type": program type (str or None),
                "valid": whether the file is valid (bool),
                "error": error message if any (str or None)
            }
        """
        st.subheader("Upload IDMS Program")
        
        with st.expander("📋 Upload Instructions", expanded=True):
            st.markdown("""
            ### Instructions
            1. Upload a COBOL/IDMS program file (.cob, .cbl, .cobol, .cpy, .txt, or any text file containing COBOL code)
            2. The system will automatically detect if it's an IDMS-DC (online) or IDMS-DB (batch) program
            3. File size should be between 100 bytes and 10MB
            
            **Note:** 
            - Large files may take longer to analyze, but our system is optimized to handle them efficiently.
            - If you're having trouble uploading a specific file, you might need to rename it with a .txt extension.
            """)
            
            # Add information about common errors
        
        # Initialize result dictionary
        result = {
            "content": None,
            "name": None,
            "type": None,
            "valid": False,
            "error": None
        }
        
        # Create the file uploader
        uploaded_file = st.file_uploader(
            "Choose a COBOL/IDMS file", 
            type=None,  # Accept any file type
            help="Upload a COBOL or IDMS program file to analyze"
        )
        
        # Process the uploaded file
        if uploaded_file is not None:
            try:
                # Get the file name and size
                original_file_name = uploaded_file.name
                file_size = uploaded_file.size
                
                # Add file extension override option
                st.write("If you're having trouble with file type, you can override the file extension:")
                override_ext = st.selectbox(
                    "Force file type:",
                    ["Auto-detect", ".txt", ".cob", ".cbl", ".cobol", ".cpy"],
                    index=0
                )
                
                # Apply extension override if selected
                if override_ext != "Auto-detect":
                    file_name = os.path.splitext(original_file_name)[0] + override_ext
                    st.info(f"Treating file as: {file_name}")
                else:
                    file_name = original_file_name
                
                st.write(f"Debug - Uploaded file: {file_name}, Size: {file_size} bytes, Type: {uploaded_file.type}")
                
                # Check file size
                if not self._is_valid_size(file_size):
                    if file_size < self.min_file_size:
                        result["error"] = f"File is too small (minimum: {self.min_file_size} bytes)"
                    else:
                        result["error"] = f"File is too large (maximum: {self.max_file_size/1024/1024:.1f} MB)"
                    st.error(result["error"])
                    return result
                
                # Read file content
                file_content = self._read_file_content(uploaded_file)
                
                # Check for COBOL/IDMS content
                if not self._has_idms_content(file_content):
                    result["error"] = "The file doesn't appear to contain valid COBOL/IDMS code"
                    st.error(result["error"])
                    return result
                
                # Detect program type
                program_type = self._detect_program_type(file_content)
                
                # Update result with success info
                result["content"] = file_content
                result["name"] = file_name
                result["type"] = program_type
                result["valid"] = True
                
                # Show success message with detected program type
                st.success(f"Successfully uploaded {file_name} (detected as IDMS-{program_type} program)")
                
                # Display file info in an expandable section
                with st.expander("📄 File Information", expanded=False):
                    # Create a 2-column table with labels and values
                    data = [
                        ["File name", file_name],
                        ["File size", f"{file_size/1024:.1f} KB"],
                        ["Program type", f"IDMS-{program_type}"],
                        ["Line count", len(file_content.splitlines())]
                    ]

                    df = pd.DataFrame(data, columns=["Attribute", "Value"])
                    st.table(df)
                
            except Exception as e:
                result["error"] = f"Error processing file: {str(e)}"
                st.error(result["error"])
        
        return result
    

    def _extract_sections(self, content: str) -> list:
        """Extract section names from the program."""
        # Look for section names in PROCEDURE DIVISION
        procedure_match = re.search(r'PROCEDURE\s+DIVISION.*?\.(.*?)(?:PROGRAM-END|$)', 
                                   content, re.DOTALL | re.IGNORECASE)
        
        if not procedure_match:
            return []
        
        procedure_content = procedure_match.group(1)
        
        # Extract section names
        section_pattern = r'([A-Z0-9-]+)\s+SECTION\s*\.'
        sections = re.findall(section_pattern, procedure_content, re.IGNORECASE)
        
        # Also get paragraph names (entries that end with a period)
        para_pattern = r'^([A-Z0-9-]+)\s*\.$'
        paragraphs = re.findall(para_pattern, procedure_content, re.MULTILINE | re.IGNORECASE)
        
        # Combine and remove duplicates while preserving order
        all_sections = []
        for item in sections + paragraphs:
            if item and item not in all_sections:
                all_sections.append(item)
        
        return all_sections

