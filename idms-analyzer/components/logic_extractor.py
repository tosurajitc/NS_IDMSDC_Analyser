import streamlit as st
import json
import time
import re
import backoff
from typing import Dict, Any, Optional, List, Tuple

# Import the model
from models.business_logic import BusinessLogic

class LogicExtractor:
    """Component for extracting business logic from IDMS programs using LLM."""
    
    def __init__(self, llm_utils):
        """
        Initialize the logic extractor.
        
        Args:
            llm_utils: The LLM utilities module for making API calls to Groq
        """
        self.llm_utils = llm_utils
        self.extraction_progress = 0
        self.max_chunk_size = 8000  # Maximum characters per chunk (adjust based on token limits)
        self.status_placeholder = None
        self.progress_bar = None
    
    def _create_extraction_prompt(self, program_content: str, program_type: str) -> Dict[str, str]:
        """
        Create a comprehensive prompt for extracting detailed business logic.
        """
        system_prompt = """
        You are an expert IDMS/COBOL program business logic extraction specialist. 
        Your task is to provide an extremely detailed, comprehensive business logic 
        extraction that covers all critical aspects of the program.

        Extraction Guidelines:
        1. Provide a clear, concise program purpose statement, with minimum 150 words
        2. Extract core business rules with deep, actionable details
        3. Capture comprehensive data validation rules
        4. Identify all special processing rules
        5. Outline all integration points
        6. Describe screen flow logic (for online programs)

        Extraction Depth Requirements:
        - Each section must be richly detailed
        - Provide context and rationale behind rules
        - Include specific conditions and exceptions
        - Capture business logic nuances
        - Ensure at least 2 pages of comprehensive documentation

        Specific Focus Areas:
        - Business intent behind each rule
        - Validation constraints and their purposes
        - Exceptional handling scenarios
        - Interdependencies between different program components
        """

        # Add program-type specific guidance
        if program_type == "DC":
            system_prompt += """
            For Online/Interactive Programs:
            - Detailed screen navigation logic
            - User interaction workflows
            - Input validation mechanisms
            - Error handling and user guidance
            - Screen-to-database interaction patterns
            """
        else:
            system_prompt += """
            For Batch/Database Programs:
            - Comprehensive data processing workflows
            - Batch processing rules and logic
            - Data transformation mechanisms
            - Error handling and logging
            - Database interaction patterns
            """

        system_prompt += """
        Extraction Output Requirements:
        - Structured, readable format
        - Minimum 2 pages of detailed documentation
        - Clear, professional language
        - Technical yet business-focused description
        - Include all significant program logic components
        """

        user_prompt = f"""
        Extract comprehensive business logic from the following IDMS program:

        Program Content:
        ```
        {program_content}
        ```

        Please provide a detailed, structured business logic extraction 
        covering all critical aspects of the program. Ensure the extraction 
        is comprehensive, covering at least 2 pages of detailed documentation.
        """

        return {"system": system_prompt, "user": user_prompt}
    
    def _chunk_program(self, program_content: str) -> List[str]:
        """
        Split large programs into manageable chunks for LLM processing.
        
        Strategy:
        1. Keep complete sections together when possible
        2. Split at logical boundaries (sections, paragraphs)
        3. Ensure the IDENTIFICATION DIVISION appears in the first chunk
        
        Args:
            program_content: The full program content
            
        Returns:
            List[str]: List of program chunks
        """
        # First, try to identify major divisions
        divisions = {
            "IDENTIFICATION": re.search(r'IDENTIFICATION\s+DIVISION', program_content, re.IGNORECASE),
            "ENVIRONMENT": re.search(r'ENVIRONMENT\s+DIVISION', program_content, re.IGNORECASE),
            "DATA": re.search(r'DATA\s+DIVISION', program_content, re.IGNORECASE),
            "PROCEDURE": re.search(r'PROCEDURE\s+DIVISION', program_content, re.IGNORECASE)
        }
        
        # If the program is small enough, return it as a single chunk
        if len(program_content) <= self.max_chunk_size:
            return [program_content]
        
        chunks = []
        
        # Extract the IDENTIFICATION DIVISION for the first chunk
        # This ensures the program name and other key info is in the first chunk
        id_div_match = divisions["IDENTIFICATION"]
        env_div_match = divisions["ENVIRONMENT"]
        
        if id_div_match:
            id_div_start = id_div_match.start()
            id_div_end = env_div_match.start() if env_div_match else self.max_chunk_size
            
            # If the ID division plus a bit more fits in one chunk, include more
            if id_div_end - id_div_start > self.max_chunk_size:
                id_div_end = id_div_start + self.max_chunk_size
            
            # First chunk with ID division and as much as will fit
            first_chunk = program_content[id_div_start:id_div_end]
            chunks.append(first_chunk)
            
            # Process the rest of the program
            remaining = program_content[id_div_end:]
        else:
            # If no ID division is found, just start from the beginning
            first_chunk = program_content[:self.max_chunk_size]
            chunks.append(first_chunk)
            remaining = program_content[self.max_chunk_size:]
        
        # Process the remaining content, trying to split at logical boundaries
        while remaining:
            # Look for section or paragraph boundaries to split at
            boundary_matches = list(re.finditer(r'^\s+[A-Z0-9-]+\s+SECTION\s*\.|^\s+[A-Z0-9-]+\s*\.', 
                                               remaining[:self.max_chunk_size * 2], 
                                               re.MULTILINE | re.IGNORECASE))
            
            # Find the last boundary that fits within max_chunk_size
            split_pos = self.max_chunk_size
            for match in reversed(boundary_matches):
                if match.start() <= self.max_chunk_size:
                    split_pos = match.start()
                    break
            
            # If no suitable boundary found, just split at max_chunk_size
            if split_pos >= self.max_chunk_size or not boundary_matches:
                split_pos = min(self.max_chunk_size, len(remaining))
            
            # Add the chunk
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:]
        
        return chunks
    
    def _merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple chunks into a single coherent result.
        
        Args:
            chunk_results: List of results from individual chunks
            
        Returns:
            Dict[str, Any]: Merged results
        """
        if not chunk_results:
            return {}
        
        # Start with the first chunk's results
        merged = chunk_results[0].copy()
        
        # Lists to combine across chunks
        list_fields = ["core_rules", "validations", "special_cases", "integration_points"]
        
        # Combine subsequent chunks
        for result in chunk_results[1:]:
            # Merge list fields, avoiding duplicates
            for field in list_fields:
                if field in result and field in merged:
                    # Get existing items for deduplication
                    existing_items = merged[field]
                    
                    # For each field type, implement custom deduplication logic
                    if field == "core_rules":
                        # Deduplicate based on rule description similarity
                        for new_rule in result[field]:
                            # Check if this rule is already present (based on description similarity)
                            if not any(self._text_similarity(new_rule.get("description", ""), 
                                                          existing.get("description", "")) > 0.7 
                                    for existing in existing_items):
                                existing_items.append(new_rule)
                    
                    elif field == "validations":
                        # Deduplicate based on field name
                        for new_validation in result[field]:
                            if not any(new_validation.get("field", "") == existing.get("field", "")
                                    for existing in existing_items):
                                existing_items.append(new_validation)
                    
                    elif field == "special_cases":
                        # Deduplicate based on condition similarity
                        for new_case in result[field]:
                            if not any(self._text_similarity(new_case.get("condition", ""), 
                                                          existing.get("condition", "")) > 0.7
                                    for existing in existing_items):
                                existing_items.append(new_case)
                    
                    elif field == "integration_points":
                        # Deduplicate based on name
                        for new_point in result[field]:
                            if not any(new_point.get("name", "") == existing.get("name", "")
                                    for existing in existing_items):
                                existing_items.append(new_point)
            
            # For additional_notes, append unique information
            if "additional_notes" in result and result["additional_notes"]:
                if "additional_notes" not in merged or not merged["additional_notes"]:
                    merged["additional_notes"] = result["additional_notes"]
                else:
                    merged["additional_notes"] += "\n\n" + result["additional_notes"]
        
        return merged
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity between two strings.
        Simple implementation using word overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0
        
        # Convert to sets of words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0
    
    def extract_logic(self, 
                    program_content: str, 
                    program_type: str,
                    model: str = "llama3-8b-8192",
                    temperature: float = 0.1,
                    max_tokens: int = 4000,
                    timeout: int = 120) -> Optional[BusinessLogic]:
        """
        Extract business logic from the program using the LLM.
        
        Args:
            program_content: The IDMS program content
            program_type: The program type (DC or DB)
            model: The LLM model to use
            temperature: The temperature parameter for generation
            max_tokens: The maximum tokens to generate
            timeout: Timeout in seconds for API call
            
        Returns:
            Optional[BusinessLogic]: Extracted business logic model or None if extraction failed
        """
        # Initialize progress display
        st.subheader("Extracting Business Logic")
        
        self.status_placeholder = st.empty()
        self.status_placeholder.info("Analyzing program structure...")
        
        self.progress_bar = st.progress(0)
        self.raw_response = ""  # Initialize raw response attribute
        
        try:
            # Split program into manageable chunks if needed
            chunks = self._chunk_program(program_content)
            total_chunks = len(chunks)
            
            # Update status
            self.status_placeholder.info(f"Program split into {total_chunks} chunks for analysis")
            
            # Process each chunk
            chunk_responses = []  # Store raw responses from each chunk
            for i, chunk in enumerate(chunks):
                self.status_placeholder.info(f"Processing chunk {i+1} of {total_chunks}...")
                
                # Create the prompt for this chunk
                prompts = self._create_extraction_prompt(chunk, program_type)
                
                # Call the LLM with backoff for rate limiting/errors
                @backoff.on_exception(backoff.expo, Exception, max_tries=3)
                def call_llm():
                    return self.llm_utils.call_groq(
                        system_prompt=prompts["system"],
                        user_prompt=prompts["user"],
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout
                    )
                
                try:
                    response = call_llm()
                    chunk_responses.append(response)  # Save the raw response
                except Exception as e:
                    self.status_placeholder.error(f"Error calling LLM API: {str(e)}")
                    return None
                
                # Update progress
                progress = (i + 1) / total_chunks
                self.progress_bar.progress(progress)
            
            # Combine all raw responses
            self.raw_response = "\n\n==== CHUNK SEPARATOR ====\n\n".join(chunk_responses)
            # Save to session state for later access
            st.session_state['last_raw_response'] = self.raw_response
            
            # Extract business logic using only the structured text method
            self.status_placeholder.info("Extracting business logic from structured text...")
            
            # Use only the new structured text extraction method
            structured_extract = self._extract_data_from_structured_text(self.raw_response, program_type)
            
            # Debug message to confirm method is being used
            self.status_placeholder.info("Using _extract_data_from_structured_text method")
            
            # Create BusinessLogic model
            try:
                business_logic = BusinessLogic(
                    program_name=structured_extract.get("program_name", "Unknown Program"),
                    program_type=program_type,
                    program_purpose=structured_extract.get("program_purpose", "Purpose not identified"),
                    core_rules=structured_extract.get("core_rules", []),
                    validations=structured_extract.get("validations", []),
                    special_cases=structured_extract.get("special_cases", []),
                    integration_points=structured_extract.get("integration_points", []),
                    additional_notes=structured_extract.get("additional_notes", "")
                )
                
                # Show success message
                self.status_placeholder.success("Business logic extraction completed successfully!")
                self.progress_bar.progress(1.0)
                
                return business_logic
                
            except Exception as e:
                self.status_placeholder.error(f"Failed to create BusinessLogic model: {str(e)}")
                self.status_placeholder.error("Cannot extract structured business logic from the LLM response.")
                self.progress_bar.progress(0)
                return None
                
        except Exception as e:
            self.status_placeholder.error(f"Error during extraction: {str(e)}")
            self.progress_bar.progress(0)
            return None
        



        
    def _extract_data_from_structured_text(self, text: str, program_type: str) -> Dict[str, Any]:
        """
        Extract structured data from LLM response with a flexible approach.
        
        Args:
            text: The raw text response from LLM
            program_type: The program type (DC or DB)
            
        Returns:
            Dict with extracted data structured for BusinessLogic model
        """
        # Initialize the result structure based on BusinessLogic requirements
        result = {
            "program_name": "Unnamed Program",  # Required field with a default
            "program_type": program_type,       # Use the provided program type
            "program_purpose": "Purpose not explicitly specified in the extracted text.",  # Required field with a default
            "core_rules": [],
            "validations": [],
            "special_cases": [], 
            "integration_points": [],
            "additional_notes": ""
        }
        
        # Log the text being processed
        st.write("Processing LLM response to extract structured data...")
        
        # Extract program name - look for patterns like "The X800DN program" or similar
        program_name_patterns = [
            r'(?:The\s+|Program\s+|)([A-Z0-9_-]+)(?:\s+program|\s+is\s+designed|\s+allows)',
            r'Program\s+Name:\s*([A-Z0-9_-]+)',
            r'program\s+name\s+is\s+([A-Z0-9_-]+)',
            r'([A-Z0-9_-]+)\s+(?:is\s+a|is\s+an|provides)'
        ]
        
        for pattern in program_name_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                result["program_name"] = matches.group(1).strip()
                break
        
        # Extract program purpose
        purpose_patterns = [
            r'(?:Program\s+Purpose\s*(?:Statement)?:?)(?:\s*\*\*)?(?:\s*\n)?(.*?)(?:\n\s*\n|\n\s*\*\*)',
            r'(?:The\s+[A-Z0-9_-]+\s+program\s+is\s+designed\s+to\s+)(.*?)(?:\n\s*\n)',
            r'(?:Purpose:|Program Purpose:)(.*?)(?:\n\s*\n|\n\s*\*\*)'
        ]
        
        for pattern in purpose_patterns:
            matches = re.search(pattern, text, re.DOTALL)
            if matches:
                purpose_text = matches.group(1).strip()
                # Clean up the purpose text (remove asterisks, extra spaces, etc.)
                purpose_text = re.sub(r'\*\*', '', purpose_text)
                purpose_text = re.sub(r'\n\s*', ' ', purpose_text)
                result["program_purpose"] = purpose_text
                break
        
        # Extract core business rules
        core_rules_section = None
        core_rules_patterns = [
            r'(?:\*\*Core\s+Business\s+Rules:\*\*|\*\*Core\s+Business\s+Rules\*\*|Core\s+Business\s+Rules:)(.*?)(?:\*\*Data\s+Validation\s+Rules:|Data\s+Validation\s+Rules:|Special\s+Processing\s+Rules:|Integration\s+Points:|\Z)',
            r'(?:Core\s+Business\s+Rules\s*(?::|-))(.*?)(?:Data\s+Validation\s+Rules|Special\s+Processing\s+Rules|Integration\s+Points|\Z)'
        ]
        
        for pattern in core_rules_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                core_rules_section = matches.group(1).strip()
                break
        
        if core_rules_section:
            # Look for numbered rules (1. Rule description)
            rule_pattern = r'(?:^|\n)\s*(\d+\.\s*\*\*([^:]+):\*\*|\d+\.\s*([^:]+):)(.*?)(?=(?:^|\n)\s*\d+\.|Business\s+Intent:|Validation\s+Constraints:|$)'
            rule_matches = re.finditer(rule_pattern, core_rules_section, re.DOTALL | re.MULTILINE)
            
            for i, match in enumerate(rule_matches):
                rule_title = match.group(2) or match.group(3)
                rule_text = match.group(4).strip()
                
                # Extract more detailed information if available
                impl_match = re.search(r'(?:Implementation:|Business\s+Intent:)(.*?)(?:Validation\s+Constraints:|Exceptional\s+Handling\s+Scenarios:|$)', rule_text, re.DOTALL)
                implementation = impl_match.group(1).strip() if impl_match else rule_text
                
                result["core_rules"].append({
                    "rule_id": f"RULE_{i+1}",
                    "description": rule_title.strip(),
                    "implementation": implementation
                })
        
        # Extract validations
        validations_section = None
        validation_patterns = [
            r'(?:\*\*Data\s+Validation\s+Rules:\*\*|\*\*Data\s+Validation\s+Rules\*\*|Data\s+Validation\s+Rules:)(.*?)(?:\*\*Special\s+Processing\s+Rules:|Special\s+Processing\s+Rules:|\*\*Integration\s+Points:|\Z)',
            r'(?:Data\s+Validation\s+Rules\s*(?::|-))(.*?)(?:Special\s+Processing\s+Rules|Integration\s+Points|\Z)'
        ]
        
        for pattern in validation_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                validations_section = matches.group(1).strip()
                break
        
        if validations_section:
            # Look for numbered validations (1. Validation description)
            validation_pattern = r'(?:^|\n)\s*(\d+\.\s*\*\*([^:]+):\*\*|\d+\.\s*([^:]+):)(.*?)(?=(?:^|\n)\s*\d+\.|Validation\s+Constraints:|Exceptional\s+Handling\s+Scenarios:|$)'
            validation_matches = re.finditer(validation_pattern, validations_section, re.DOTALL | re.MULTILINE)
            
            for match in validation_matches:
                field = match.group(2) or match.group(3)
                validation_text = match.group(4).strip()
                
                # Extract error handling if available
                error_match = re.search(r'(?:Exceptional\s+Handling\s+Scenarios:)(.*?)(?:$)', validation_text, re.DOTALL)
                error_handling = error_match.group(1).strip() if error_match else None
                
                # Extract rule from the validation text
                rule_match = re.search(r'(?:Validation\s+Constraints:)(.*?)(?:Exceptional\s+Handling\s+Scenarios:|$)', validation_text, re.DOTALL)
                rule = rule_match.group(1).strip() if rule_match else validation_text
                
                result["validations"].append({
                    "field": field.strip(),
                    "rule": rule,
                    "error_handling": error_handling
                })
        
        # Extract special cases
        special_cases_section = None
        special_cases_patterns = [
            r'(?:\*\*Special\s+Processing\s+Rules:\*\*|\*\*Special\s+Processing\s+Rules\*\*|Special\s+Processing\s+Rules:)(.*?)(?:\*\*Integration\s+Points:|\*\*Screen\s+Flow\s+Logic|Integration\s+Points:|\Z)',
            r'(?:Special\s+Processing\s+Rules\s*(?::|-))(.*?)(?:Integration\s+Points|Screen\s+Flow\s+Logic|\Z)'
        ]
        
        for pattern in special_cases_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                special_cases_section = matches.group(1).strip()
                break
        
        if special_cases_section:
            # Look for numbered special cases (1. Special case description)
            case_pattern = r'(?:^|\n)\s*(\d+\.\s*\*\*([^:]+):\*\*|\d+\.\s*([^:]+):)(.*?)(?=(?:^|\n)\s*\d+\.|Business\s+Intent:|Validation\s+Constraints:|$)'
            case_matches = re.finditer(case_pattern, special_cases_section, re.DOTALL | re.MULTILINE)
            
            for match in case_matches:
                condition = match.group(2) or match.group(3)
                case_text = match.group(4).strip()
                
                # Extract handling from the case text
                handling_match = re.search(r'(?:Business\s+Intent:)(.*?)(?:Validation\s+Constraints:|Exceptional\s+Handling\s+Scenarios:|$)', case_text, re.DOTALL)
                handling = handling_match.group(1).strip() if handling_match else case_text
                
                # Extract notes if available
                notes_match = re.search(r'(?:Exceptional\s+Handling\s+Scenarios:)(.*?)(?:$)', case_text, re.DOTALL)
                notes = notes_match.group(1).strip() if notes_match else None
                
                result["special_cases"].append({
                    "condition": condition.strip(),
                    "handling": handling,
                    "notes": notes
                })
        
        # Extract integration points
        integration_points_section = None
        integration_points_patterns = [
            r'(?:\*\*Integration\s+Points:\*\*|\*\*Integration\s+Points\*\*|Integration\s+Points:)(.*?)(?:\*\*Screen\s+Flow\s+Logic|\*\*Error\s+Handling|Screen\s+Flow\s+Logic:|Error\s+Handling:|\Z)',
            r'(?:Integration\s+Points\s*(?::|-))(.*?)(?:Screen\s+Flow\s+Logic|Error\s+Handling|\Z)'
        ]
        
        for pattern in integration_points_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                integration_points_section = matches.group(1).strip()
                break
        
        if integration_points_section:
            # Look for numbered integration points (1. Integration point description)
            point_pattern = r'(?:^|\n)\s*(\d+\.\s*\*\*([^:]+):\*\*|\d+\.\s*([^:]+):)(.*?)(?=(?:^|\n)\s*\d+\.|Business\s+Intent:|Validation\s+Constraints:|$)'
            point_matches = re.finditer(point_pattern, integration_points_section, re.DOTALL | re.MULTILINE)
            
            for match in point_matches:
                name = match.group(2) or match.group(3)
                point_text = match.group(4).strip()
                
                # Default values
                description = point_text
                point_type = "Database"  # Default type
                direction = "Both"       # Default direction
                
                # Extract description from the integration point text
                desc_match = re.search(r'(?:Business\s+Intent:)(.*?)(?:Validation\s+Constraints:|Exceptional\s+Handling\s+Scenarios:|$)', point_text, re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip()
                
                # Try to determine type and direction from the name and description
                if 'input' in point_text.lower() or 'read' in point_text.lower():
                    direction = 'Input'
                elif 'output' in point_text.lower() or 'write' in point_text.lower():
                    direction = 'Output'
                
                if 'api' in point_text.lower() or 'service' in point_text.lower():
                    point_type = 'API'
                elif 'file' in point_text.lower():
                    point_type = 'File'
                
                result["integration_points"].append({
                    "name": name.strip(),
                    "description": description,
                    "type": point_type,
                    "direction": direction
                })
        
        # Extract additional information
        additional_sections = []
        
        # Look for Screen Flow Logic section
        screen_flow_section = None
        if program_type == "DC":
            screen_flow_patterns = [
                r'(?:\*\*Screen\s+Flow\s+Logic[^:]*:\*\*|\*\*Screen\s+Flow\s+Logic[^:]*\*\*|Screen\s+Flow\s+Logic[^:]*:)(.*?)(?:\*\*Error\s+Handling|Error\s+Handling:|\*\*Conclusion|\Z)',
                r'(?:Screen\s+Flow\s+Logic[^:]*\s*(?::|-))(.*?)(?:Error\s+Handling|Conclusion|\Z)'
            ]
            
            for pattern in screen_flow_patterns:
                matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if matches:
                    screen_flow_section = matches.group(1).strip()
                    additional_sections.append("Screen Flow Logic:\n" + screen_flow_section)
                    break
        
        # Look for Error Handling section
        error_handling_section = None
        error_handling_patterns = [
            r'(?:\*\*Error\s+Handling[^:]*:\*\*|\*\*Error\s+Handling[^:]*\*\*|Error\s+Handling[^:]*:)(.*?)(?:\*\*Conclusion|Conclusion:|\Z)',
            r'(?:Error\s+Handling[^:]*\s*(?::|-))(.*?)(?:Conclusion|\Z)'
        ]
        
        for pattern in error_handling_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                error_handling_section = matches.group(1).strip()
                additional_sections.append("Error Handling:\n" + error_handling_section)
                break
        
        # Look for Conclusion section
        conclusion_section = None
        conclusion_patterns = [
            r'(?:\*\*Conclusion:\*\*|\*\*Conclusion\*\*|Conclusion:)(.*?)(?:\Z)',
            r'(?:Conclusion\s*(?::|-))(.*?)(?:\Z)'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                conclusion_section = matches.group(1).strip()
                additional_sections.append("Conclusion:\n" + conclusion_section)
                break
        
        # Combine additional sections
        if additional_sections:
            result["additional_notes"] = "\n\n".join(additional_sections)
        
        # Ensure all required fields are present for the nested models
        
        # Ensure BusinessRule structure
        for i, rule in enumerate(result["core_rules"]):
            if "rule_id" not in rule or not rule["rule_id"]:
                rule["rule_id"] = f"RULE_{i+1}"
            if "description" not in rule or not rule["description"]:
                rule["description"] = "Description not specified"
            if "implementation" not in rule or not rule["implementation"]:
                rule["implementation"] = "Implementation details not specified"
        
        # Ensure Validation structure
        for validation in result["validations"]:
            if "field" not in validation or not validation["field"]:
                validation["field"] = "Unspecified Field"
            if "rule" not in validation or not validation["rule"]:
                validation["rule"] = "Validation rule not specified"
            # error_handling is optional, so it's okay if it's missing
        
        # Ensure SpecialCase structure
        for case in result["special_cases"]:
            if "condition" not in case or not case["condition"]:
                case["condition"] = "Unspecified Condition"
            if "handling" not in case or not case["handling"]:
                case["handling"] = "Handling not specified"
            # notes is optional, so it's okay if it's missing
        
        # Ensure IntegrationPoint structure
        for point in result["integration_points"]:
            if "name" not in point or not point["name"]:
                point["name"] = "Unnamed Integration Point"
            if "description" not in point or not point["description"]:
                point["description"] = "Description not specified"
            if "type" not in point or not point["type"]:
                point["type"] = "Database"  # Default type
            if "direction" not in point or not point["direction"]:
                point["direction"] = "Both"  # Default direction
        
        # Only include additional_notes if we have content
        if not result.get("additional_notes"):
            result["additional_notes"] = None
        
        # Log extraction results
        st.write(f"Extracted program name: {result['program_name']}")
        st.write(f"Extracted {len(result['core_rules'])} core rules")
        st.write(f"Extracted {len(result['validations'])} validations")
        st.write(f"Extracted {len(result['special_cases'])} special cases")
        st.write(f"Extracted {len(result['integration_points'])} integration points")
        
        return result

    
    def render(self, file_info: Dict[str, Any]) -> Optional[BusinessLogic]:
        """
        Render the logic extraction component and process the program.
        
        Args:
            file_info: Information about the uploaded file
            
        Returns:
            Optional[BusinessLogic]: Extracted business logic model or None if extraction failed
        """
        if not file_info or not file_info.get("valid"):
            st.warning("Please upload a valid IDMS program file first.")
            return None
        
        program_content = file_info["content"]
        program_type = file_info["type"]
        
        # Sample size for processing (from session state if available)
        if "sample_size" in st.session_state and st.session_state.sample_size:
            if len(program_content) > st.session_state.sample_size:
                st.info(f"Processing first {st.session_state.sample_size} characters (of {len(program_content)} total)")
                program_content = program_content[:st.session_state.sample_size]
        
        # Timeout for API call (from session state if available)
        timeout = 120  # default timeout
        if "timeout" in st.session_state:
            timeout = st.session_state.timeout
        
        col1, col2 = st.columns(2)
        with col1:
            extract_button = st.button("Extract Business Logic", type="primary", use_container_width=True)
        
        with col2:
            st.button("Cancel", type="secondary", use_container_width=True, disabled=True)
        
        if extract_button:
            # Get model settings from session state if available
            model = st.session_state.get("model", "llama3-8b-8192")
            temperature = st.session_state.get("temperature", 0.1)
            max_tokens = st.session_state.get("max_tokens", 4000)
            
            return self.extract_logic(
                program_content=program_content,
                program_type=program_type,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
        
        return None