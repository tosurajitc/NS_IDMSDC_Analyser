"""
prompt_templates.py - Contains prompt templates for LLM interactions.
This module provides structured prompts for business logic extraction,
test script generation, and other LLM-based operations.
"""

from typing import Dict, Any, Optional, List, Tuple
from string import Template
import re

class PromptTemplates:
    """Class containing prompt templates for different LLM operations"""
    
    # Maximum tokens for different operations
    # These are conservative estimates to ensure we stay within model limits
    MAX_TOKENS = {
        "business_logic": 6000,  # For business logic extraction
        "test_script": 6000,     # For test script generation
        "detection": 2000        # For program type detection
    }
    
    # Estimated tokens per line of code
    TOKENS_PER_LINE = 7  # Average tokens per line of COBOL/IDMS code
    
    @staticmethod
    def business_logic_extraction(program_type: str, program_id: Optional[str] = None) -> str:
        """
        Get the prompt template for business logic extraction.
        
        Args:
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            Prompt template as a string
        """
        program_id_text = f" program {program_id}" if program_id else ""
        
        # Base template that works for both DB and DC programs
        base_template = f"""
You are an expert in IDMS and COBOL programming tasked with extracting business logic from an {program_type}{program_id_text}.

I will provide you with an IDMS program, and I need you to analyze it and extract the business logic in a structured format.

Please organize your response as a markdown document with the following sections:
1. Program Purpose - A clear statement of what the program does
2. Core Business Rules - The main business rules implemented in the program
3. Data Validation Rules - All validation logic for input data
4. Special Processing Rules - Any special cases or exception handling
5. Integration Points - How this program interfaces with other systems or programs

Focus on business functionality, not technical implementation. Identify meaningful business rules, not just code structure.
"""

        # Add specific guidance based on program type
        if program_type == "IDMS-DC":
            dc_specific = """
For this IDMS-DC program, pay special attention to:
- Screen mapping and user interactions
- PF key functions and screen flow
- Error handling and messages
- Validation rules for user input
- Session state management
- Add a "Screen Flow Logic" section that explains the user interaction flow
"""
            base_template += dc_specific
        else:  # IDMS-DB
            db_specific = """
For this IDMS-DB program, focus on:
- Database access patterns
- Record relationships and join conditions
- Business transformations and calculations
- Processing order and logic branches
- Batch processing rules
"""
            base_template += db_specific

        # Add final instructions
        base_template += """
Here is the IDMS program code:
Provide only the extracted business logic in a clear, structured markdown format. Do not include technical code explanations or implementation details unless they directly relate to business rules.

Take a methodical approach:
1. First, understand the overall program structure and purpose
2. Identify key data structures and their business meaning
3. Analyze the procedures to extract business rules
4. Document validation and special case handling
5. Note integration points with other systems

Make your output comprehensive but focused on business meaning, not technical details.
"""
        
        return base_template
    
    @staticmethod
    def test_script_generation(program_type: str, program_id: Optional[str] = None) -> str:
        """
        Get the prompt template for test script generation.
        
        Args:
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            Prompt template as a string
        """
        program_id_text = f" program {program_id}" if program_id else ""
        
        # Base template that works for both DB and DC programs
        base_template = f"""
You are an expert in IDMS testing tasked with creating a comprehensive test script for an {program_type}{program_id_text}.

Based on the extracted business logic below, create a detailed test script that covers all functional aspects of the program. The test script should be organized as a markdown document with the following sections:

1. Test Environment Setup - Required environment and prerequisites
2. Test Data Requirements - Specific test data needed
3. Test Cases - Detailed test cases including:
   - Test case ID and objective
   - Preconditions
   - Test steps with specific inputs
   - Expected results
   - Any special considerations

Ensure that your test cases cover:
- Normal successful paths
- Validation errors and edge cases
- Special processing rules
- Integration with other systems
"""

        # Add specific guidance based on program type
        if program_type == "IDMS-DC":
            dc_specific = """
For this IDMS-DC online program, include test cases for:
- All screen navigation paths (PF key functions)
- All validation error scenarios
- Session state persistence
- User interface elements and feedback
- Error message validation
- Performance considerations for online usage
"""
            base_template += dc_specific
        else:  # IDMS-DB
            db_specific = """
For this IDMS-DB batch program, include test cases for:
- Database interaction (retrieval, update, store, erase)
- Edge cases in data processing
- Error handling paths
- Performance with different data volumes
- Integration with downstream systems
"""
            base_template += db_specific

        # Add final instructions
        base_template += """
Here is the extracted business logic:
Provide a comprehensive, practical test script that could be used by a tester to verify all aspects of the program's functionality. 
Each test case should be detailed enough that someone with basic IDMS knowledge could execute it.

Number each test case (TC01, TC02, etc.) and ensure coverage of all business rules identified in the business logic.
Focus on functional validation rather than technical implementation.

Include separate test cases for each major business rule and validation rule.
"""
        
        return base_template
    
    @staticmethod
    def program_type_detection() -> str:
        """
        Get the prompt for detecting program type (DB or DC).
        
        Returns:
            Prompt as a string
        """
        return """
Analyze the IDMS program code below and determine if this is an IDMS-DC program (online/interactive) or an IDMS-DB program (batch/database).

IDMS-DC indicators include:
- PROTOCOL MODE IS IDMS-DC
- MAP SECTION definitions
- MAP IN/MAP OUT/MODIFY MAP statements
- DC RETURN statements
- TRANSFER CONTROL statements
- DC-AID-CONDITION-NAMES (for PF keys)
- GET/PUT SCRATCH operations

IDMS-DB indicators include:
- Database operations without user interface
- Batch processing logic
- READY/FINISH usage without DC components
- No MAP or screen handling

Respond with just "IDMS-DC" or "IDMS-DB" based on your analysis, and nothing else.
"""
    
    @staticmethod
    def code_summary() -> str:
        """
        Get the prompt for generating a quick code summary.
        
        Returns:
            Prompt as a string
        """
        return """
Provide a very brief summary of what this IDMS program does in 3-5 sentences. Focus only on the business purpose, not technical details.
"""
    
    @staticmethod
    def fill_template(template: str, variables: Dict[str, Any]) -> str:
        """
        Fill in a template with the provided variables.
        
        Args:
            template: Template string
            variables: Dictionary of variables to substitute
            
        Returns:
            Filled template as a string
        """
        return Template(template).safe_substitute(variables)
    
    @classmethod
    def prepare_code_for_prompt(cls, code_content: str, operation: str = "business_logic") -> str:
        """
        Prepare code content for inclusion in a prompt, handling large code bases.
        
        Args:
            code_content: Full program code
            operation: Type of operation ("business_logic", "test_script", "detection")
            
        Returns:
            Processed code content ready for prompt
        """
        # Estimate token count
        lines = code_content.split('\n')
        estimated_tokens = len(lines) * cls.TOKENS_PER_LINE
        
        # If code is small enough, return as is
        if estimated_tokens <= cls.MAX_TOKENS[operation]:
            return code_content
        
        # For large code, extract important sections
        important_sections = cls._extract_important_sections(code_content)
        
        # Limit to maximum tokens
        max_tokens = cls.MAX_TOKENS[operation]
        tokens_used = 0
        final_content = []
        
        # First add the program header (identification, remarks, etc.)
        header_end = code_content.find("PROCEDURE DIVISION")
        if header_end > 0:
            header = code_content[:header_end]
            header_tokens = len(header.split('\n')) * cls.TOKENS_PER_LINE
            if header_tokens < max_tokens * 0.4:  # Use up to 40% for header
                final_content.append(header)
                tokens_used += header_tokens
        
        # Then add important sections until we reach token limit
        for section in important_sections:
            section_tokens = len(section.split('\n')) * cls.TOKENS_PER_LINE
            if tokens_used + section_tokens <= max_tokens * 0.9:  # Leave 10% buffer
                final_content.append(section)
                tokens_used += section_tokens
            else:
                # If we can't fit the whole section, add a summary comment
                summary = f"\n* SECTION SUMMARY: This section contains additional code that was truncated due to size.\n"
                final_content.append(summary)
                break
        
        # Combine and return
        result = "\n".join(final_content)
        
        # Add a note about truncation
        if estimated_tokens > max_tokens:
            truncation_note = f"\n\n/* NOTE: This code has been truncated from {len(lines)} lines to fit token limits. Key sections have been preserved. */\n"
            result += truncation_note
        
        return result
    
    @classmethod
    def prepare_business_logic_for_prompt(cls, business_logic: str) -> str:
        """
        Prepare business logic content for inclusion in test script generation prompt.
        
        Args:
            business_logic: Business logic markdown content
            
        Returns:
            Processed business logic ready for prompt
        """
        # Split into sections based on markdown headings
        sections = re.split(r'(#+ [^\n]+)', business_logic)
        if sections and not sections[0].strip().startswith('#'):
            # Handle case where first section doesn't start with a heading
            intro = sections.pop(0)
            if sections:
                sections[0] = intro + sections[0]
        
        # Estimate tokens for each section
        section_tokens = [(s, len(s.split()) * 1.5) for s in sections]  # Rough estimate: 1.5 tokens per word
        
        # Calculate total tokens
        total_tokens = sum(tokens for _, tokens in section_tokens)
        
        # If within limits, return as is
        if total_tokens <= cls.MAX_TOKENS["test_script"]:
            return business_logic
        
        # Otherwise, prioritize sections
        priority_keywords = [
            "purpose", "business rules", "validation", "special", 
            "integration", "screen flow", "error handling"
        ]
        
        # Score sections by priority
        scored_sections = []
        for i in range(0, len(section_tokens), 2):
            if i+1 < len(section_tokens):
                heading = section_tokens[i][0].lower()
                content = section_tokens[i+1][0]
                tokens = section_tokens[i][1] + section_tokens[i+1][1]
                
                # Calculate priority score based on keywords
                score = 1
                for keyword in priority_keywords:
                    if keyword in heading:
                        score += 3
                
                # Purpose and core business rules get highest priority
                if "purpose" in heading:
                    score += 5
                if "business rules" in heading:
                    score += 4
                
                scored_sections.append((heading + content, tokens, score))
        
        # Sort by priority score (descending)
        scored_sections.sort(key=lambda x: x[2], reverse=True)
        
        # Build result while staying within token limit
        result = []
        tokens_used = 0
        max_tokens = cls.MAX_TOKENS["test_script"] * 0.9  # Leave 10% buffer
        
        for content, tokens, _ in scored_sections:
            if tokens_used + tokens <= max_tokens:
                result.append(content)
                tokens_used += tokens
            else:
                break
        
        # Add a note about truncation
        truncation_note = "\n\n> Note: Some sections of the business logic have been omitted due to length constraints. Focus on the key sections provided."
        result.append(truncation_note)
        
        return "".join(result)
    
    @staticmethod
    def _extract_important_sections(code_content: str) -> List[str]:
        """
        Extract important sections from IDMS code.
        
        Args:
            code_content: Full program code
            
        Returns:
            List of important code sections
        """
        important_sections = []
        
        # Extract PROCEDURE DIVISION
        procedure_start = code_content.find("PROCEDURE DIVISION")
        if procedure_start > 0:
            important_sections.append(code_content[procedure_start:])
        
        # Extract validation logic (commonly contains business rules)
        validation_patterns = [
            r"PERFORM \d+-[A-Z0-9-]+-VERIFY THRU \d+-[A-Z0-9-]+-EXIT",
            r"\d+-[A-Z0-9-]+-VERIFY\.",
            r"\d+-PANEL-VERIFY\."
        ]
        
        for pattern in validation_patterns:
            matches = re.finditer(pattern, code_content)
            for match in matches:
                # Extract the paragraph and following code
                para_name = match.group(0).rstrip('.')
                para_start = code_content.find(para_name)
                if para_start > 0:
                    para_end = code_content.find("EXIT.", para_start)
                    if para_end > 0:
                        important_sections.append(code_content[para_start:para_end+5])
        
        # Extract error handling
        error_patterns = [
            r"\d+-ERR-",
            r"ON ERROR",
            r"ERROR-SWITCH"
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, code_content)
            for match in matches:
                # Extract surrounding paragraph
                pos = match.start()
                para_start = code_content.rfind(".", 0, pos)
                para_end = code_content.find(".", pos)
                if para_start >= 0 and para_end > para_start:
                    important_sections.append(code_content[para_start+1:para_end+1])
        
        return important_sections


class BusinessLogicExtractionPrompt:
    """Class for business logic extraction prompts with system and user components"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt for business logic extraction.
        
        Returns:
            System prompt as a string
        """
        return """
You are an expert in IDMS and COBOL programming who specializes in extracting business logic from legacy code.
You focus on business rules, not technical implementation details.
You provide clear, structured responses organized with markdown headings and bullet points.
You understand both IDMS-DC (online) and IDMS-DB (batch) programs and their unique characteristics.
"""
    
    @staticmethod
    def get_user_prompt(program_type: str, program_id: Optional[str] = None) -> str:
        """
        Get the user prompt for business logic extraction.
        
        Args:
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            User prompt template as a string
        """
        return PromptTemplates.business_logic_extraction(program_type, program_id)
    
    @classmethod
    def create_messages(cls, code_content: str, program_type: str, program_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Create complete messages for business logic extraction.
        
        Args:
            code_content: Program code content
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            List of message dictionaries (system and user messages)
        """
        # Prepare code content
        prepared_code = PromptTemplates.prepare_code_for_prompt(code_content, "business_logic")
        
        # Get user prompt and fill in code content
        user_prompt = cls.get_user_prompt(program_type, program_id)
        filled_prompt = PromptTemplates.fill_template(user_prompt, {"code_content": prepared_code})
        
        # Create messages
        messages = [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": filled_prompt}
        ]
        
        return messages


class TestScriptGenerationPrompt:
    """Class for test script generation prompts with system and user components"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt for test script generation.
        
        Returns:
            System prompt as a string
        """
        return """
You are an expert in IDMS testing who specializes in creating comprehensive test scripts for IDMS applications.
You create detailed, practical test cases that cover all aspects of functionality.
You understand both IDMS-DC (online) and IDMS-DB (batch) programs and their unique testing requirements.
You focus on functional validation rather than technical implementation details.
You provide well-structured test scripts with clear steps and expected results.
"""
    
    @staticmethod
    def get_user_prompt(program_type: str, program_id: Optional[str] = None) -> str:
        """
        Get the user prompt for test script generation.
        
        Args:
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            User prompt template as a string
        """
        return PromptTemplates.test_script_generation(program_type, program_id)
    
    @classmethod
    def create_messages(cls, business_logic: str, program_type: str, program_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Create complete messages for test script generation.
        
        Args:
            business_logic: Extracted business logic content
            program_type: "IDMS-DC" or "IDMS-DB"
            program_id: Optional program ID
            
        Returns:
            List of message dictionaries (system and user messages)
        """
        # Prepare business logic content
        prepared_logic = PromptTemplates.prepare_business_logic_for_prompt(business_logic)
        
        # Get user prompt and fill in business logic
        user_prompt = cls.get_user_prompt(program_type, program_id)
        filled_prompt = PromptTemplates.fill_template(user_prompt, {"business_logic": prepared_logic})
        
        # Create messages
        messages = [
            {"role": "system", "content": cls.get_system_prompt()},
            {"role": "user", "content": filled_prompt}
        ]
        
        return messages


class DetectionPrompt:
    """Class for program type detection prompts"""
    
    @classmethod
    def create_messages(cls, code_content: str) -> List[Dict[str, str]]:
        """
        Create complete messages for program type detection.
        
        Args:
            code_content: Program code content
            
        Returns:
            List of message dictionaries
        """
        # Prepare code content (use just the first part for detection)
        lines = code_content.split('\n')
        # Use first 200 lines or first 20% of code, whichever is smaller
        detection_lines = lines[:min(200, max(100, len(lines) // 5))]
        prepared_code = '\n'.join(detection_lines)
        
        # Get detection prompt and fill in code content
        detection_prompt = PromptTemplates.program_type_detection()
        filled_prompt = PromptTemplates.fill_template(detection_prompt, {"code_content": prepared_code})
        
        # Create messages
        messages = [
            {"role": "user", "content": filled_prompt}
        ]
        
        return messages