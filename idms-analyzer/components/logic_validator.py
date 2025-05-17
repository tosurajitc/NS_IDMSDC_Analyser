import os
import requests
import streamlit as st
import json
import re
from typing import Optional, Dict, Any
from docx import Document

from models.business_logic import BusinessLogic
from utils.llm_utils import LLMUtils  # Imported at the top


class LogicValidator:
    """
    LLM-powered validation of extracted business logic 
    with direct Word document generation
    """
    
    def __init__(self, llm_utils):
        """
        Initialize the logic validator with LLM utilities.
        
        Args:
            llm_utils: The LLM utilities for making API calls
        """
        self.llm_utils = llm_utils
        self.status_placeholder = None
        self.progress_bar = None
    
    def _create_validation_prompt(self, business_logic: BusinessLogic) -> Dict[str, str]:
        """
        Create a comprehensive validation prompt for the business logic.
        
        Args:
            business_logic: The business logic to validate
            
        Returns:
            Dict containing system and user prompts
        """
        system_prompt = """
        You are an expert IDMS/COBOL program business logic validation specialist.

        Validation Objectives:
        1. Thoroughly review the extracted business logic
        2. Identify potential inconsistencies or gaps
        3. Provide comprehensive validation insights
        4. Ensure logic completeness and accuracy

        Validation Criteria:
        - Verify logical consistency across all components
        - Check comprehensiveness of business rules
        - Validate integration point descriptions
        - Ensure special case handling is robust
        """

        # Add program-type specific validation guidance
        if business_logic.program_type in ["DC", "Online"]:
            system_prompt += """
            For Online/Interactive Programs:
            - Validate screen interaction logic
            - Verify user flow completeness
            - Check input validation mechanisms
            - Ensure comprehensive error handling
            """
        else:
            system_prompt += """
            For Batch/Database Programs:
            - Validate data processing workflows
            - Check record handling logic
            - Verify batch processing rules
            - Ensure comprehensive error and exception handling
            """

        user_prompt = f"""
        Validate the following business logic extraction:

        Program Name: {business_logic.program_name}
        Program Type: {business_logic.program_type}
        Program Purpose: {business_logic.program_purpose}

        Core Business Rules: {len(business_logic.core_rules)}
        Validations: {len(business_logic.validations)}
        Special Cases: {len(business_logic.special_cases)}
        Integration Points: {len(business_logic.integration_points)}

        Provide a comprehensive validation that:
        1. Verifies the completeness of each logic component
        2. Identifies potential improvements
        3. Ensures logical consistency
        4. Validates alignment with program type and purpose
        """
        
        return {"system": system_prompt, "user": user_prompt}
    
    def validate_logic(self, 
                       business_logic: BusinessLogic, 
                       model: str = "llama3-8b-8192",
                       temperature: float = 0.2,
                       max_tokens: int = 4000,
                       timeout: int = 120) -> Optional[Document]:
        """
        Validate business logic and generate a Word document.
        
        Args:
            business_logic: The business logic to validate
            model: The LLM model to use
            temperature: The temperature parameter for generation
            max_tokens: The maximum tokens to generate
            timeout: Timeout in seconds for API call
            
        Returns:
            Optional[Document]: Validated business logic as a Word document
        """
        st.subheader("Business Logic Validation")
        
        # Initialize progress tracking
        self.status_placeholder = st.empty()
        self.progress_bar = st.progress(0)
        
        if not business_logic:
            st.warning("Please extract business logic first.")
            return None
        
        try:
            # Prepare validation prompt
            self.status_placeholder.info("Preparing validation prompt...")
            self.progress_bar.progress(0.1)
            prompts = self._create_validation_prompt(business_logic)
            
            # Call LLM for validation insights
            self.status_placeholder.info("Performing cross-validation...")
            self.progress_bar.progress(0.5)
            
            validation_insights = self.llm_utils.call_groq(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            # Generate Word document
            self.status_placeholder.info("Generating validation document...")
            self.progress_bar.progress(0.8)
            
            # Add validation insights to additional notes
            if business_logic.additional_notes:
                business_logic.additional_notes += f"\n\nValidation Insights:\n{validation_insights}"
            else:
                business_logic.additional_notes = f"Validation Insights:\n{validation_insights}"
            
            # Generate Word document
            word_doc = business_logic.generate_word_document()
            
            # Create download button
            st.download_button(
                label="📥 Download Validated Business Logic",
                data=_save_document_to_bytes(word_doc),
                file_name=f"{business_logic.program_name}_Validated_Business_Logic.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # Show success message
            self.status_placeholder.success("Business logic validated successfully!")
            self.progress_bar.progress(1.0)
            
            return word_doc
        
        except Exception as e:
            self.status_placeholder.error(f"Validation error: {str(e)}")
            self.progress_bar.progress(0)
            return None
    
    def render(self, business_logic: BusinessLogic) -> Optional[Document]:
        """
        Render the validation component.
        
        Args:
            business_logic: The business logic to validate
            
        Returns:
            Optional[Document]: Validated business logic document
        """
        st.markdown("## Validate Business Logic")
        st.write("Using LLM to cross-verify and validate extracted business logic.")
        
        if not business_logic:
            st.warning("Please extract business logic first.")
            return None
        
        # Direct validation button
        if st.button("Validate Business Logic", type="primary"):
            # Get model settings from session state
            model = st.session_state.get("model", "llama3-8b-8192")
            temperature = st.session_state.get("temperature", 0.2)
            max_tokens = st.session_state.get("max_tokens", 4000)
            timeout = st.session_state.get("timeout", 120)
            
            return self.validate_logic(
                business_logic=business_logic,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
        
        return None

def _save_document_to_bytes(doc: Document) -> bytes:
    """
    Save Word document to bytes for download.
    
    Args:
        doc: The Word document to save
        
    Returns:
        bytes: Document content as bytes
    """
    import io
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()