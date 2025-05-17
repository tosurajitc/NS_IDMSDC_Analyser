"""
LLM utilities for interacting with the Groq API.
This module handles all interactions with the LLM model for extracting
business logic and generating test scripts.
"""

import os
import time
import json
import requests
import logging
import backoff
from typing import Dict, Any, Optional, List, Tuple
import traceback
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMUtils:
    """Utility class for interacting with Groq LLM API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM utilities."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided and not found in environment variables")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.default_model = "llama3-8b-8192"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def call_groq(self, 
                 system_prompt: str, 
                 user_prompt: str, 
                 model: Optional[str] = None,
                 temperature: float = 0.1,
                 max_tokens: int = 4000,
                 timeout: int = 120) -> str:
        """
        Call the Groq API with the given prompts.
        
        Args:
            system_prompt: The system prompt
            user_prompt: The user prompt
            model: The model to use (defaults to self.default_model)
            temperature: The temperature parameter (0.0 to 1.0)
            max_tokens: The maximum number of tokens to generate
            timeout: Request timeout in seconds
            
        Returns:
            str: The LLM response text
        """
        if not model:
            model = self.default_model
        
        url = f"{self.base_url}/chat/completions"
        
        # Debug info
        st.write(f"Calling API with model: {model}, temperature: {temperature}, max_tokens: {max_tokens}")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            # Log request details
            logger.info(f"Making request to {url} with model {model}")
            
            # Make the request with timeout
            start_time = time.time()
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload,
                timeout=timeout  # Set timeout in seconds
            )
            elapsed = time.time() - start_time
            
            # Log response details
            logger.info(f"Request completed in {elapsed:.2f} seconds with status {response.status_code}")
            
            response.raise_for_status()  # Raise an error for bad status codes
            
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {timeout} seconds"
            logger.error(error_msg)
            st.error(error_msg)
            raise TimeoutError(error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Groq API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            st.error(error_msg)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            st.error(error_msg)
            raise
    
    def extract_business_logic(self, code_content: str, model: str = "llama3-8b-8192") -> str:
        """
        Extract business logic from IDMS program code using Groq's LLM.
        
        Args:
            code_content: The IDMS program code as a string
            model: The model to use for extraction
            
        Returns:
            Extracted business logic as a markdown-formatted string
        """
        prompt = self._create_business_logic_prompt(code_content)
        
        system_prompt = "You are an expert in IDMS and COBOL programming who specializes in extracting business logic from legacy code."
        
        try:
            business_logic = self.call_groq(
                system_prompt=system_prompt,
                user_prompt=prompt,
                model=model,
                temperature=0.2,
                max_tokens=4000
            )
            return business_logic
        except Exception as e:
            logger.error(f"Error extracting business logic: {str(e)}")
            raise
    
    def generate_test_script(self, business_logic: str, model: str = "llama3-8b-8192") -> str:
        """
        Generate a test script based on extracted business logic using Groq's LLM.
        
        Args:
            business_logic: The extracted business logic
            model: The model to use for test script generation
            
        Returns:
            Generated test script as a markdown-formatted string
        """
        prompt = self._create_test_script_prompt(business_logic)
        
        system_prompt = "You are an expert in IDMS testing who specializes in creating comprehensive test scripts for IDMS applications."
        
        try:
            test_script = self.call_groq(
                system_prompt=system_prompt,
                user_prompt=prompt,
                model=model,
                temperature=0.3,
                max_tokens=4000
            )
            return test_script
        except Exception as e:
            logger.error(f"Error generating test script: {str(e)}")
            raise
    
    def _create_business_logic_prompt(self, code_content: str) -> str:
        """Create a prompt for extracting business logic from code"""
        return f"""
You are an expert in IDMS and COBOL programming tasked with extracting business logic from an IDMS program.

I will provide you with an IDMS program, and I need you to analyze it and extract the business logic in a structured format.

Please organize your response as a markdown document with the following sections:
1. Program Purpose - A clear statement of what the program does
2. Core Business Rules - The main business rules implemented in the program
3. Data Validation Rules - All validation logic for input data
4. Special Processing Rules - Any special cases or exception handling
5. Integration Points - How this program interfaces with other systems or programs
6. Screen Flow Logic - How users interact with the program (if applicable)

Focus on business functionality, not technical implementation. Identify meaningful business rules, not just code structure.

For IDMS-DC programs, pay special attention to:
- Screen mapping and user interactions
- PF key functions
- Error handling and messages
- Validation rules

For IDMS-DB programs, focus on:
- Database access patterns
- Record relationships
- Business transformations

Here is the IDMS program code:

```
{code_content}
```

Please provide your analysis in a well-structured markdown format.
"""
    
    def _create_test_script_prompt(self, business_logic: str) -> str:
        """Create a prompt for generating test scripts based on business logic"""
        return f"""
Based on the extracted business logic below, create a comprehensive test script for this IDMS program.

The test script should include:
1. A test plan overview
2. Test case categories
3. Individual test cases with:
   - Test case ID
   - Description
   - Prerequisites
   - Test data
   - Steps to execute
   - Expected results
   - Pass/Fail criteria

For each business rule, validation rule, and special processing rule, create at least one test case.
Include both positive tests (expected behavior) and negative tests (error handling).

For IDMS-DC programs, include screen navigation testing.
For IDMS-DB programs, include database access pattern testing.

Here is the extracted business logic:

{business_logic}

Please provide the test script in a well-structured markdown format.
"""
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text.
        This is a rough estimate based on the average token length.
        
        Args:
            text: The text to estimate
            
        Returns:
            int: Estimated token count
        """
        # A simple approximation: average token is about 4 characters
        return len(text) // 4
