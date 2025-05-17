import streamlit as st
from typing import Optional, Dict, List

from models.business_logic import BusinessLogic, TestScript, TestCase

class TestGenerator:
    """
    Component for generating test scripts based on extracted business logic
    using LLM reasoning
    """
    
    def __init__(self, llm_utils):
        """
        Initialize the test script generator.
        
        Args:
            llm_utils: The LLM utilities for making API calls
        """
        self.llm_utils = llm_utils
    
    def _create_test_script_prompt(self, business_logic: BusinessLogic) -> Dict[str, str]:
        """
        Create a simplified, concise prompt for generating test scripts.
        
        Args:
            business_logic: The business logic to base test scripts on
            
        Returns:
            Dict with system and user prompts
        """
        system_prompt = """
        You are a test engineer creating comprehensive test scripts for an IDMS/COBOL program.
        
        Generate at least 5 detailed test cases with the following format for EACH test case:
        
        Test ID: PROGRAM-TC-001
        Test Objective: Brief description of what's being tested
        Preconditions: 
        1. First precondition
        2. Second precondition
        
        Test Steps:
        1. First step
        2. Second step
        3. Third step
        
        Expected Results:
        - First expected result
        - Second expected result
        
        IMPORTANT: Follow this exact format for each test case to ensure proper parsing.
        Make sure each test case has a unique Test ID, clear steps, and expected results.
        """

        user_prompt = f"""
        Create a comprehensive test script for this program:
        
        Program Name: {business_logic.program_name}
        Program Type: {business_logic.program_type}
        Purpose: {business_logic.program_purpose}
        
        Key business rules: 
        """
        
        # Add a brief summary of business rules
        if business_logic.core_rules:
            for i, rule in enumerate(business_logic.core_rules[:3]):  # Limit to first 3 rules
                user_prompt += f"- {rule.rule_id}: {rule.description}\n"
            if len(business_logic.core_rules) > 3:
                user_prompt += f"- Plus {len(business_logic.core_rules) - 3} more rules\n"
        else:
            user_prompt += "- No specific core rules identified\n"
        
        user_prompt += """
        Include test cases for:
        1. Basic functionality
        2. Data validation
        3. Error handling
        4. Integration points
        5. Special processing conditions
        
        IMPORTANT: Format each test case exactly as shown in the system prompt with:
        - Test ID
        - Test Objective
        - Preconditions (numbered list)
        - Test Steps (numbered list)
        - Expected Results (bulleted list)
        """
        
        return {"system": system_prompt, "user": user_prompt}
    

    
    
    def generate_test_script(self, 
                            business_logic: BusinessLogic, 
                            model: str = "llama3-8b-8192",
                            temperature: float = 0.3,
                            max_tokens: int = 4000,
                            timeout: int = 120) -> Optional[TestScript]:
        """
        Generate test scripts based on business logic.
        
        Args:
            business_logic: The business logic to base test scripts on
            model: The LLM model to use
            temperature: The temperature parameter for generation
            max_tokens: The maximum tokens to generate
            timeout: Timeout in seconds for API call
            
        Returns:
            Optional[TestScript]: Generated test script
        """
        st.subheader("Generating Test Scripts")
        
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # Prepare test script generation prompt
            status_placeholder.info("Preparing test script generation prompt...")
            progress_bar.progress(0.1)
            
            prompts = self._create_test_script_prompt(business_logic)
            
            # Call LLM for test script generation
            status_placeholder.info("Generating test scripts...")
            progress_bar.progress(0.5)
            
            try:
                test_script_response = self.llm_utils.call_groq(
                    system_prompt=prompts["system"],
                    user_prompt=prompts["user"],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                # Process and create test script
                status_placeholder.info("Processing test script...")
                progress_bar.progress(0.8)
                
                # Create TestScript with generated test cases
                test_cases = self._parse_test_script_response(test_script_response)
                
                if not test_cases or len(test_cases) < 3:
                    status_placeholder.warning("Initial test case generation produced too few test cases. Trying again with more explicit instructions...")
                    
                    # Try again with a more structured prompt
                    simplified_prompt = {
                        "system": """
                        Generate exactly 5 test cases for an IDMS program using this precise format:
                        
                        Test ID: PROG-TC-001
                        Test Objective: What the test verifies
                        Preconditions: 
                        1. Condition one
                        2. Condition two
                        
                        Test Steps:
                        1. Step one
                        2. Step two
                        3. Step three
                        
                        Expected Results:
                        - Result one
                        - Result two
                        
                        REPEAT this pattern exactly 5 times with different test scenarios.
                        """,
                        "user": f"""
                        Program: {business_logic.program_name}
                        Type: {business_logic.program_type}
                        Purpose: {business_logic.program_purpose}
                        
                        Create 5 different test cases covering:
                        1. Basic functionality
                        2. Validation
                        3. Error handling
                        4. Edge cases
                        5. Integration
                        
                        Use the EXACT format specified.
                        """
                    }
                    
                    retry_response = self.llm_utils.call_groq(
                        system_prompt=simplified_prompt["system"],
                        user_prompt=simplified_prompt["user"],
                        model=model,
                        temperature=temperature + 0.1,  # Slightly higher for variety
                        max_tokens=max_tokens,
                        timeout=timeout
                    )
                    
                    # Try to parse the retry response
                    retry_cases = self._parse_test_script_response(retry_response)
                    
                    # If we got valid test cases from the retry, use those
                    if retry_cases and len(retry_cases) >= 3:
                        test_cases = retry_cases
                    else:
                        # If retry failed too, create some basic test cases manually
                        if not test_cases or len(test_cases) == 0:
                            test_cases = [
                                TestCase(
                                    test_id=f"{business_logic.program_name}-TC-001",
                                    title="Basic Functionality Test",
                                    description="Verify the basic functionality of the program",
                                    prerequisites=["Test environment is available"],
                                    test_data={"input": "test value"},
                                    steps=[
                                        "Start the program",
                                        "Enter valid test data",
                                        "Submit the transaction"
                                    ],
                                    expected_results=[
                                        "Transaction processes successfully",
                                        "Data is stored correctly"
                                    ],
                                    related_rules=[]
                                ),
                                TestCase(
                                    test_id=f"{business_logic.program_name}-TC-002",
                                    title="Validation Test",
                                    description="Verify input validation functionality",
                                    prerequisites=["Test environment is available"],
                                    test_data={"invalid_input": "invalid value"},
                                    steps=[
                                        "Start the program",
                                        "Enter invalid test data",
                                        "Submit the transaction"
                                    ],
                                    expected_results=[
                                        "System rejects the transaction",
                                        "Appropriate error message is displayed"
                                    ],
                                    related_rules=[]
                                ),
                                TestCase(
                                    test_id=f"{business_logic.program_name}-TC-003",
                                    title="Integration Test",
                                    description="Verify integration with external systems",
                                    prerequisites=[
                                        "Test environment is available",
                                        "External systems are accessible"
                                    ],
                                    test_data={"integration_data": "test value"},
                                    steps=[
                                        "Start the program",
                                        "Enter data that triggers external system integration",
                                        "Submit the transaction"
                                    ],
                                    expected_results=[
                                        "System correctly integrates with external systems",
                                        "Data is exchanged properly"
                                    ],
                                    related_rules=[]
                                )
                            ]
                
                test_script = TestScript(
                    program_name=business_logic.program_name,
                    test_cases=test_cases
                )
                
                # Show success message
                status_placeholder.success(f"Successfully generated {len(test_script.test_cases)} test cases!")
                progress_bar.progress(1.0)
                
                return test_script
                
            except Exception as api_e:
                status_placeholder.error(f"API Error: {str(api_e)}")
                progress_bar.progress(0)
                
                # Create a default test script with basic test cases
                default_test_script = TestScript(
                    program_name=business_logic.program_name,
                    test_cases=[
                        TestCase(
                            test_id=f"{business_logic.program_name}-TC-001",
                            title="Basic Functionality Test",
                            description="Verify the basic functionality of the program",
                            prerequisites=["Test environment is available"],
                            test_data={"input": "test value"},
                            steps=["Start the program", "Enter valid test data", "Submit the transaction"],
                            expected_results=["Transaction processes successfully", "Data is stored correctly"],
                            related_rules=[]
                        ),
                        TestCase(
                            test_id=f"{business_logic.program_name}-TC-002",
                            title="Validation Test",
                            description="Verify input validation functionality",
                            prerequisites=["Test environment is available"],
                            test_data={"invalid_input": "invalid value"},
                            steps=["Start the program", "Enter invalid test data", "Submit the transaction"],
                            expected_results=["System rejects the transaction", "Appropriate error message is displayed"],
                            related_rules=[]
                        )
                    ]
                )
                
                return default_test_script
            
        except Exception as e:
            status_placeholder.error(f"Test script generation error: {str(e)}")
            progress_bar.progress(0)
            return None
        


        
    def _parse_test_script_response(self, response: str) -> List[TestCase]:
        """
        Parse the LLM response and convert to TestCase instances.
        Uses a simpler pattern-based approach to extract test cases.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            List of generated TestCase instances
        """
        import re
        
        st.write("Parsing test script response...")
        
        # Debug - show the response to help understand the format
        st.text_area("Raw LLM Response (first 1000 chars)", response[:1000], height=200)
        
        # If response is empty or None
        if not response:
            st.error("Empty response from LLM")
            return []
        
        test_cases = []
        
        try:
            # Try to find test cases based on common patterns
            # First, look for "Test ID:" or "Test Case:" sections
            test_sections = re.split(r'(?:\n|^)(?:Test ID:|Test Case:)\s*([A-Z0-9][A-Z0-9-]*)', response)
            
            # If we found test sections
            if len(test_sections) > 1:
                # The first element is text before the first Test ID
                pre_text = test_sections[0]
                
                # Process each test case
                for i in range(1, len(test_sections), 2):
                    if i+1 < len(test_sections):
                        test_id = test_sections[i].strip()
                        content = test_sections[i+1].strip()
                        
                        # Extract title/objective
                        title = "Untitled Test Case"
                        title_match = re.search(r'Test Objective:?\s*([^\n]+)|Objective:?\s*([^\n]+)', content)
                        if title_match:
                            title = (title_match.group(1) or title_match.group(2)).strip()
                        
                        # Extract description (same as title if not found)
                        description = title
                        
                        # Extract prerequisites
                        prerequisites = []
                        prereq_section = re.search(r'Preconditions:?\s*(.*?)(?=\n\s*(?:Test Steps:|Steps:|Expected Results:)|$)', 
                                                content, re.DOTALL)
                        if prereq_section:
                            prereq_text = prereq_section.group(1).strip()
                            # Look for numbered or bulleted items
                            prereq_items = re.findall(r'(?:^|\n)\s*(?:\d+\.\s*|\*\s*|-\s*)([^\n]+)', prereq_text)
                            if prereq_items:
                                prerequisites = [item.strip() for item in prereq_items]
                            else:
                                # If no bullets/numbers, split by lines
                                prerequisites = [line.strip() for line in prereq_text.split('\n') if line.strip()]
                        
                        # Extract steps
                        steps = []
                        steps_section = re.search(r'(?:Test Steps:|Steps:)\s*(.*?)(?=\n\s*(?:Expected Results:|Results:)|$)', 
                                                content, re.DOTALL)
                        if steps_section:
                            steps_text = steps_section.group(1).strip()
                            # Look for numbered items
                            steps_items = re.findall(r'(?:^|\n)\s*(?:\d+\.\s*)([^\n]+)', steps_text)
                            if steps_items:
                                steps = [item.strip() for item in steps_items]
                            else:
                                # If no numbers, try bulleted items
                                steps_items = re.findall(r'(?:^|\n)\s*(?:\*\s*|-\s*)([^\n]+)', steps_text)
                                if steps_items:
                                    steps = [item.strip() for item in steps_items]
                                else:
                                    # If no formatting, split by lines
                                    steps = [line.strip() for line in steps_text.split('\n') if line.strip()]
                        
                        # Extract expected results
                        expected_results = []
                        results_section = re.search(r'(?:Expected Results:|Results:)\s*(.*?)(?=$)', 
                                                content, re.DOTALL)
                        if results_section:
                            results_text = results_section.group(1).strip()
                            # Look for bulleted or numbered items
                            result_items = re.findall(r'(?:^|\n)\s*(?:\d+\.\s*|\*\s*|-\s*)([^\n]+)', results_text)
                            if result_items:
                                expected_results = [item.strip() for item in result_items]
                            else:
                                # If no formatting, split by lines
                                expected_results = [line.strip() for line in results_text.split('\n') if line.strip()]
                        
                        # Create test case
                        test_case = TestCase(
                            test_id=test_id,
                            title=title,
                            description=description,
                            prerequisites=prerequisites,
                            test_data={},  # Difficult to extract structured test data automatically
                            steps=steps,
                            expected_results=expected_results,
                            related_rules=[]
                        )
                        
                        test_cases.append(test_case)
            
            # If we couldn't find test cases with the first pattern, try an alternative approach
            if not test_cases:
                # Try numbered test cases (1. Test Case: X800DN-TC-001)
                numbered_sections = re.split(r'(?:\n|^)(?:\d+\.\s*Test Case:?\s*|\d+\.\s*)([A-Z0-9][A-Z0-9-]*)', response)
                
                if len(numbered_sections) > 1:
                    # Process each section
                    for i in range(1, len(numbered_sections), 2):
                        if i+1 < len(numbered_sections):
                            test_id = numbered_sections[i].strip()
                            content = numbered_sections[i+1].strip()
                            
                            # Process similarly to above
                            title = "Untitled Test Case"
                            title_match = re.search(r'(?:^|\n)([^\n]+)', content)
                            if title_match:
                                title = title_match.group(1).strip()
                            
                            # Create a basic test case with what we can extract
                            # Use similar extraction patterns as above for other fields
                            test_case = TestCase(
                                test_id=test_id,
                                title=title,
                                description=title,
                                prerequisites=[],
                                test_data={},
                                steps=[],
                                expected_results=[],
                                related_rules=[]
                            )
                            
                            test_cases.append(test_case)
            
            # If we still couldn't find test cases, try looking for headings
            if not test_cases:
                # Try heading patterns (# Test Case 1: Basic Functionality)
                heading_matches = re.finditer(r'(?:^|\n)#+\s*(?:Test Case|TC)[:\s-]+(\d+)[:\s-]+([^\n]+)', response)
                for match in heading_matches:
                    test_id = f"TC-{match.group(1)}"
                    title = match.group(2).strip()
                    
                    # Create a minimal test case
                    test_case = TestCase(
                        test_id=test_id,
                        title=title,
                        description=title,
                        prerequisites=[],
                        test_data={},
                        steps=[],
                        expected_results=[],
                        related_rules=[]
                    )
                    
                    test_cases.append(test_case)
            
            # If we still couldn't extract test cases, create a default set
            if not test_cases:
                st.warning("Could not parse test cases from the response. Creating default test cases.")
                
                # Extract any useful information from the response
                program_name = "Unknown"
                name_match = re.search(r'Program(?:\s+Name)?:?\s+([A-Za-z0-9_-]+)', response)
                if name_match:
                    program_name = name_match.group(1)
                
                # Create generic test cases
                test_cases = [
                    TestCase(
                        test_id=f"{program_name}-TC-001",
                        title="Basic Functionality Test",
                        description="Verify the basic functionality of the program",
                        prerequisites=["Test environment is available"],
                        test_data={"input": "test value"},
                        steps=["Start the program", "Enter valid test data", "Submit the transaction"],
                        expected_results=["Transaction processes successfully", "Data is stored correctly"],
                        related_rules=[]
                    ),
                    TestCase(
                        test_id=f"{program_name}-TC-002",
                        title="Validation Test",
                        description="Verify input validation functionality",
                        prerequisites=["Test environment is available"],
                        test_data={"invalid_input": "invalid value"},
                        steps=["Start the program", "Enter invalid test data", "Submit the transaction"],
                        expected_results=["System rejects the transaction", "Appropriate error message is displayed"],
                        related_rules=[]
                    ),
                    TestCase(
                        test_id=f"{program_name}-TC-003",
                        title="Integration Test",
                        description="Verify integration with external systems",
                        prerequisites=["Test environment is available", "External systems are accessible"],
                        test_data={"integration_data": "test value"},
                        steps=["Start the program", "Enter data that triggers external system integration", "Submit the transaction"],
                        expected_results=["System correctly integrates with external systems", "Data is exchanged properly"],
                        related_rules=[]
                    )
                ]
        
        except Exception as e:
            st.error(f"Error parsing test script response: {str(e)}")
            
            # Return a default test case indicating the error
            test_cases = [
                TestCase(
                    test_id="ERROR-TC-001",
                    title="Parser Error - Manual Review Required",
                    description=f"Failed to parse LLM response: {str(e)}. Please review the raw response.",
                    prerequisites=["Manual review required"],
                    test_data={},
                    steps=["Review raw LLM response", "Extract test cases manually"],
                    expected_results=["Test cases correctly extracted"],
                    related_rules=[]
                )
            ]
        
        st.success(f"Extracted {len(test_cases)} test cases from response")
        return test_cases
        


    def render(self, business_logic: BusinessLogic) -> Optional[TestScript]:
        """
        Render the test script generation component.
        
        Args:
            business_logic: The business logic to base test scripts on
            
        Returns:
            Optional[TestScript]: Generated test script
        """
        st.markdown("## Generate Test Scripts")
        st.write("Generate comprehensive test scripts based on business logic.")
        
        if st.button("Generate Test Scripts", type="primary"):
            # Get model settings
            model = st.session_state.get("model", "llama3-8b-8192")
            temperature = st.session_state.get("temperature", 0.3)
            max_tokens = st.session_state.get("max_tokens", 4000)
            timeout = st.session_state.get("timeout", 120)
            
            return self.generate_test_script(
                business_logic=business_logic,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
        
        return None
    
    def render(self, business_logic: BusinessLogic) -> Optional[TestScript]:
        """
        Render the test script generation component.
        
        Args:
            business_logic: The business logic to base test scripts on
            
        Returns:
            Optional[TestScript]: Generated test script
        """
        st.markdown("## Generate Test Scripts")
        st.write("Generate comprehensive test scripts based on business logic.")
        
        try:
            # Log start of generation process
            st.info("Starting test script generation...")
            
            # Get model settings
            model = st.session_state.get("model", "llama3-8b-8192")
            temperature = st.session_state.get("temperature", 0.3)
            max_tokens = st.session_state.get("max_tokens", 4000)
            timeout = st.session_state.get("timeout", 120)
            
            # Log model settings
            st.write(f"Using model: {model}, temperature: {temperature}, max_tokens: {max_tokens}")
            
            # Generate test script
            test_script = self.generate_test_script(
                business_logic=business_logic,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            # Check if generation was successful
            if test_script:
                st.success(f"Generated test script with {len(test_script.test_cases)} test cases")
                return test_script
            else:
                st.error("Failed to generate test script (generate_test_script returned None)")
                return None
        
        except Exception as e:
            st.error(f"Error in render method: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None