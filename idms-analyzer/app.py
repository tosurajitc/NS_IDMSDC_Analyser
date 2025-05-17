import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load utilities
from utils.llm_utils import LLMUtils

# Load components
from components.file_uploader import FileUploader
from components.logic_extractor import LogicExtractor
from components.logic_validator import LogicValidator
from components.test_generator import TestGenerator
from components.doc_exporter import DocExporter
from models.business_logic import BusinessLogic


def ensure_workflow_progression():
    """Ensure session state has the necessary values to progress through the workflow."""
    # If business logic exists but validated logic doesn't, copy it to validated logic
    if 'business_logic' in st.session_state and st.session_state.business_logic is not None:
        if 'validated_logic' not in st.session_state or st.session_state.validated_logic is None:
            st.session_state.validated_logic = st.session_state.business_logic
            st.session_state['validation_bypassed'] = True

# Set page configuration
st.set_page_config(
    page_title="IDMS Program Analyzer",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'file_info' not in st.session_state:
    st.session_state.file_info = None
if 'business_logic' not in st.session_state:
    st.session_state.business_logic = None
if 'validated_logic' not in st.session_state:
    st.session_state.validated_logic = None
if 'test_script' not in st.session_state:
    st.session_state.test_script = None
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1  # 1: Upload, 2: Extract, 3: Validate, 4: Generate, 5: Export
if 'model' not in st.session_state:
    st.session_state.model = "llama3-8b-8192"
if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.1
if 'max_tokens' not in st.session_state:
    st.session_state.max_tokens = 4000
if 'timeout' not in st.session_state:
    st.session_state.timeout = 120
if 'sample_size' not in st.session_state:
    st.session_state.sample_size = 5000  # Default sample size for processing

def create_sidebar():
    """Create the application sidebar with navigation and settings."""
    with st.sidebar:
        st.title("IDMS Program Analyzer")
        
        st.subheader("Navigation")
        
        # Navigation buttons
        if st.button("📤 Upload Program", disabled=st.session_state.current_step == 1, use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()
            
        if st.button("🔍 Extract Logic", 
                    disabled=st.session_state.file_info is None or st.session_state.current_step < 2, 
                    use_container_width=True):
            st.session_state.current_step = 2
            st.rerun()
            
        if st.button("✏️ Validate Logic", 
                    disabled=st.session_state.business_logic is None or st.session_state.current_step < 3, 
                    use_container_width=True):
            st.session_state.current_step = 3
            st.rerun()
            
        if st.button("🧪 Generate Tests", 
                    disabled=st.session_state.validated_logic is None or st.session_state.current_step < 4, 
                    use_container_width=True):
            st.session_state.current_step = 4
            st.rerun()
            
        if st.button("📄 Export Documents", 
                    disabled=st.session_state.test_script is None or st.session_state.current_step < 5, 
                    use_container_width=True):
            st.session_state.current_step = 5
            st.rerun()
        
        st.divider()
        
        # Settings
        st.subheader("Settings")
        
        # LLM model selection
        st.session_state.model = st.selectbox(
            "LLM Model",
            ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"],
            index=0,
            key="model_selection"
        )
        
        # Token adjustments
        st.session_state.max_tokens = st.slider(
            "Max Tokens", 
            min_value=1000, 
            max_value=32000, 
            value=4000, 
            step=1000,
            key="max_tokens_slider"
        )
        
        # Temperature
        st.session_state.temperature = st.slider(
            "Temperature", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.1, 
            step=0.1,
            key="temperature_slider"
        )
        
        # API timeout setting
        st.session_state.timeout = st.slider(
            "API Timeout (seconds)",
            min_value=30,
            max_value=300,
            value=120,
            step=30,
            key="timeout_slider"
        )
        
        # Sample size for processing (to handle very large files)
        sample_enabled = st.checkbox("Enable sample processing (for large files)", value=True)
        
        if sample_enabled:
            file_size = len(st.session_state.file_info["content"]) if st.session_state.file_info else 10000
            st.session_state.sample_size = st.slider(
                "Process first N characters",
                min_value=1000,
                max_value=min(file_size, 20000) if st.session_state.file_info else 10000,
                value=min(5000, file_size) if st.session_state.file_info else 5000,
                step=1000
            )
        else:
            st.session_state.sample_size = None  # Process entire file
        
        st.divider()
        
        # About section
        st.subheader("About")
        st.info(
            "This application analyzes IDMS programs to extract business logic "
            "and generate test scripts using Large Language Models."
        )
        
        # Reset application
        if st.button("🔄 Reset Application", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        # Help information for file types
        st.markdown("---")
        st.markdown("#### Supported File Types")
        st.markdown("""
        - `.cob` - COBOL source files
        - `.cbl` - COBOL source files
        - `.cobol` - COBOL source files
        - `.cpy` - COBOL copybooks
        - `.txt` - Text files containing COBOL/IDMS code
        """)

def show_progress_bar():
    """Display a progress bar showing the current step."""
    steps = [
        "1. Upload Program",
        "2. Extract Logic",
        "3. Validate Logic", 
        "4. Generate Tests",
        "5. Export Documents"
    ]
    
    # Calculate progress
    progress = (st.session_state.current_step - 1) / (len(steps) - 1)
    
    # Display progress bar
    st.progress(progress)
    
    # Display steps
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        step_num = i + 1
        if step_num < st.session_state.current_step:
            col.markdown(f"✅ {step}")
        elif step_num == st.session_state.current_step:
            col.markdown(f"**→ {step}**")
        else:
            col.markdown(f"⬜ {step}")
    
    st.divider()

def upload_step():
    """Step 1: File upload interface."""
    st.title("Upload IDMS Program")
    
    # Initialize the file uploader component
    uploader = FileUploader()
    file_info = uploader.render()
    
    # Store file info in session state if valid
    if file_info["valid"]:
        st.session_state.file_info = file_info
    
        
        # Button to proceed to extraction
        if st.button("Extract Business Logic", type="primary"):
            # Set flag to auto-start extraction in the next step
            st.session_state['auto_start_extraction'] = True
            st.session_state.current_step = 2
            st.session_state['intentional_step_change'] = True
            st.rerun()

def extract_step():
    """Step 2: Business logic extraction interface."""
    # Create a row with two columns for the title and validate button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Extract Business Logic")
    with col2:
        # Only show validate button if business logic has been extracted
        if st.session_state.business_logic is not None:
            if st.button("Validate Business Logic", type="primary", key="header_validate_btn"):
                st.session_state.current_step = 3
                st.session_state['intentional_step_change'] = True
                st.rerun()
    
    # Check if file info exists
    if not st.session_state.file_info:
        st.warning("Please upload a valid IDMS program file first.")
        if st.button("Go to Upload Step"):
            st.session_state.current_step = 1
            st.rerun()
        return
    
    # Initialize LLM utilities
    llm_utils = LLMUtils()
    
    # Initialize the logic extractor component
    extractor = LogicExtractor(llm_utils)
    
    # Show file info and sample processing details
    if st.session_state.sample_size:
        total_size = len(st.session_state.file_info["content"])
        if st.session_state.sample_size < total_size:
            st.info(f"Processing the first {st.session_state.sample_size} characters of {total_size} total (to change, adjust settings in sidebar)")
    
    # Flag for auto-starting extraction
    auto_start = st.session_state.get('auto_start_extraction', False)
    
    # If business logic hasn't been extracted yet, render the extractor
    if st.session_state.business_logic is None:
        # Prepare the content for extraction
        program_content = st.session_state.file_info["content"]
        if st.session_state.sample_size and len(program_content) > st.session_state.sample_size:
            program_content = program_content[:st.session_state.sample_size]
        
        # Show the extract button (even though we might auto-start)
        extract_button = st.button("Extract Business Logic", type="primary")
        
        # If button clicked or auto-start flag is set
        if extract_button or auto_start:
            # Clear the auto-start flag to prevent re-triggering
            if 'auto_start_extraction' in st.session_state:
                del st.session_state['auto_start_extraction']
            
            # Get model settings from session state if available
            model = st.session_state.get("model", "llama3-8b-8192")
            temperature = st.session_state.get("temperature", 0.1)
            max_tokens = st.session_state.get("max_tokens", 4000)
            timeout = st.session_state.get("timeout", 120)
            
            # Display API call information
            st.info(f"Calling API with model: {model}, temperature: {temperature}, max_tokens: {max_tokens}")
            
            # Extract business logic
            business_logic = extractor.extract_logic(
                program_content=program_content,
                program_type=st.session_state.file_info["type"],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            # Display raw LLM response directly, regardless of extraction success
            if hasattr(extractor, 'raw_response') and extractor.raw_response:
                st.subheader("Raw LLM Response")
                # Fix: Add a proper label to the text_area
                st.text_area(
                    label="LLM Response Text",
                    value=extractor.raw_response,
                    height=400,
                    key="raw_llm_response_1"
                )
            elif 'last_raw_response' in st.session_state:
                st.subheader("Raw LLM Response")
                # Fix: Add a proper label to the text_area
                st.text_area(
                    label="LLM Response Text", 
                    value=st.session_state.last_raw_response,
                    height=400,
                    key="raw_llm_response_2"
                )
            
            if business_logic:
                st.session_state.business_logic = business_logic
                st.rerun()  # Refresh to show validation button in header
                
                # Add next button at bottom too
                if st.button("Validate Business Logic", type="primary"):
                    st.session_state.current_step = 3
                    st.session_state['intentional_step_change'] = True
                    st.rerun()
            else:
                st.error("Failed to parse business logic structure. Check the raw response above for details.")
                # Add a button to manually proceed to validation if needed
                if st.button("Force Proceed to Validation", type="secondary"):
                    # Create a minimal business logic instance to allow progression
                    from models.business_logic import BusinessLogic
                    basic_logic = BusinessLogic(
                        program_name=st.session_state.file_info.get("name", "Unknown Program"),
                        program_type=st.session_state.file_info.get("type", "DB"),
                        program_purpose="Manually proceeding after extraction failure",
                        core_rules=[],
                        validations=[],
                        special_cases=[],
                        integration_points=[],
                        additional_notes="Business logic extraction failed. Using manual override to proceed."
                    )
                    st.session_state.business_logic = basic_logic
                    st.session_state.current_step = 3
                    st.session_state['intentional_step_change'] = True
                    st.rerun()
    else:
        # Display the extracted business logic
        st.success("Business logic extracted successfully!")
        
        # Display raw LLM response if available
        if 'last_raw_response' in st.session_state:
            st.subheader("Raw LLM Response")
            # Fix: Add a proper label to the text_area
            st.text_area(
                label="LLM Response Text", 
                value=st.session_state.last_raw_response,
                height=400,
                key="raw_llm_response_3"
            )
        
        # Display a preview of the extracted logic
        with st.expander("Preview Business Logic", expanded=True):
            # Fixed: Accessing program_name as an attribute, not a method
            st.markdown(f"# {st.session_state.business_logic.program_name}")
            st.markdown(f"**Program Type:** {st.session_state.business_logic.program_type}")
            st.markdown(f"**Program Purpose:** {st.session_state.business_logic.program_purpose}")
            
            # Display core business rules
            st.markdown("## Core Business Rules")
            if st.session_state.business_logic.core_rules:
                for rule in st.session_state.business_logic.core_rules:
                    st.markdown(f"### {rule.rule_id}")
                    st.markdown(f"**Description:** {rule.description}")
                    st.markdown(f"**Implementation:** {rule.implementation}")
            else:
                st.markdown("*No core business rules identified.*")
                
            # Display validations
            st.markdown("## Data Validation Rules")
            if st.session_state.business_logic.validations:
                for validation in st.session_state.business_logic.validations:
                    st.markdown(f"- **{validation.field}**: {validation.rule}")
                    if validation.error_handling:
                        st.markdown(f"  - Error Handling: {validation.error_handling}")
            else:
                st.markdown("*No validation rules identified.*")
                
            # Display special cases
            st.markdown("## Special Processing Rules")
            if st.session_state.business_logic.special_cases:
                for case in st.session_state.business_logic.special_cases:
                    st.markdown(f"### {case.condition}")
                    st.markdown(f"**Handling:** {case.handling}")
                    if case.notes:
                        st.markdown(f"**Notes:** {case.notes}")
            else:
                st.markdown("*No special cases identified.*")
                
            # Display integration points
            st.markdown("## Integration Points")
            if st.session_state.business_logic.integration_points:
                for point in st.session_state.business_logic.integration_points:
                    st.markdown(f"### {point.name}")
                    st.markdown(f"**Type:** {point.type}")
                    st.markdown(f"**Direction:** {point.direction}")
                    st.markdown(f"**Description:** {point.description}")
            else:
                st.markdown("*No integration points identified.*")
        
        # Buttons for next steps
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Re-Extract Business Logic"):
                st.session_state.business_logic = None
                st.rerun()
        
        with col2:
            if st.button("Validate Business Logic", type="primary"):
                st.session_state.current_step = 3
                st.session_state['intentional_step_change'] = True
                st.rerun()



def validate_step():
    """Step 3: Business logic validation interface."""
    st.title("Validate Business Logic")
    
    # Ensure workflow can progress
    ensure_workflow_progression()
    
    # Check if business logic exists
    if not st.session_state.business_logic:
        st.warning("Please extract business logic first.")
        if st.button("Go to Extract Step"):
            st.session_state.current_step = 2
            st.rerun()
        return
    
    # Display validation state
    if st.session_state.get('validation_bypassed', False):
        st.info("Validation was automatically bypassed to ensure workflow progression.")
    
    # Initialize LLM utilities
    llm_utils = LLMUtils()
    
    # Initialize the logic validator component
    validator = LogicValidator(llm_utils)
    
    # Only call render if validation hasn't been bypassed
    if not st.session_state.get('validation_bypassed', False):
        # Render the validator and get validated logic
        try:
            validated_logic = validator.render(st.session_state.business_logic)
            if validated_logic:
                st.session_state.validated_logic = validated_logic
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
            st.session_state.validated_logic = st.session_state.business_logic
            st.session_state['validation_bypassed'] = True
            st.warning("Validation encountered an error. Using unvalidated business logic to allow workflow progression.")
    
    # Display comprehensive business logic preview
    with st.expander("Preview Business Logic", expanded=True):
        # Program information
        st.markdown(f"# {st.session_state.business_logic.program_name}")
        st.markdown(f"**Program Type:** {st.session_state.business_logic.program_type}")
        st.markdown(f"**Program Purpose:** {st.session_state.business_logic.program_purpose}")
        
        # Core business rules
        st.markdown("## Core Business Rules")
        if not st.session_state.business_logic.core_rules:
            st.markdown("*No core business rules identified.*")
        else:
            for rule in st.session_state.business_logic.core_rules:
                with st.container():
                    st.markdown(f"### {rule.rule_id}")
                    st.markdown(f"**Description:** {rule.description}")
                    st.markdown(f"**Implementation:** {rule.implementation}")
        
        # Validations
        st.markdown("## Data Validation Rules")
        if not st.session_state.business_logic.validations:
            st.markdown("*No validation rules identified.*")
        else:
            for validation in st.session_state.business_logic.validations:
                with st.container():
                    st.markdown(f"- **{validation.field}**: {validation.rule}")
                    if validation.error_handling:
                        st.markdown(f"  - Error Handling: {validation.error_handling}")
        
        # Special cases
        st.markdown("## Special Processing Rules")
        if not st.session_state.business_logic.special_cases:
            st.markdown("*No special cases identified.*")
        else:
            for case in st.session_state.business_logic.special_cases:
                with st.container():
                    st.markdown(f"### {case.condition}")
                    st.markdown(f"**Handling:** {case.handling}")
                    if case.notes:
                        st.markdown(f"**Notes:** {case.notes}")
        
        # Integration points
        st.markdown("## Integration Points")
        if not st.session_state.business_logic.integration_points:
            st.markdown("*No integration points identified.*")
        else:
            for point in st.session_state.business_logic.integration_points:
                with st.container():
                    st.markdown(f"### {point.name}")
                    st.markdown(f"**Type:** {point.type}")
                    st.markdown(f"**Direction:** {point.direction}")
                    st.markdown(f"**Description:** {point.description}")
        
        # Additional notes
        if st.session_state.business_logic.additional_notes:
            st.markdown("## Additional Notes")
            st.markdown(st.session_state.business_logic.additional_notes)
    
    # Button to proceed to test generation
    if st.button("Generate Test Scripts", type="primary"):
        # Ensure validated_logic exists before proceeding
        if st.session_state.validated_logic is None:
            st.session_state.validated_logic = st.session_state.business_logic
            st.session_state['validation_bypassed'] = True
        
        # Force set the step and rerun
        st.session_state.current_step = 4
        st.rerun()

def generate_step():
    """Step 4: Test script generation interface."""
    st.title("Generate Test Scripts")
    
    # Ensure we have validated logic
    if not st.session_state.validated_logic:
        st.warning("Please validate business logic first.")
        if st.button("Go to Validation Step"):
            st.session_state.current_step = 3
            st.rerun()
        return
    
    # If we already have a test script, show it
    if st.session_state.test_script is not None:
        st.success(f"Test script generated with {len(st.session_state.test_script.test_cases)} test cases!")
        
        # Display test script preview
        with st.expander("Preview Test Script", expanded=True):
            st.markdown(f"# Test Script for {st.session_state.test_script.program_name}")
            st.markdown(f"**Total Test Cases:** {len(st.session_state.test_script.test_cases)}")
            
            # Create a tab for each test case
            if len(st.session_state.test_script.test_cases) > 0:
                tab_labels = [f"TC{i+1}: {tc.test_id}" for i, tc in enumerate(st.session_state.test_script.test_cases)]
                tabs = st.tabs(tab_labels)
                
                for i, (tab, test_case) in enumerate(zip(tabs, st.session_state.test_script.test_cases)):
                    with tab:
                        # Test case details
                        st.markdown(f"## {test_case.title}")
                        st.markdown(f"**Description:** {test_case.description}")
                        
                        # Prerequisites
                        st.markdown("### Prerequisites")
                        for prereq in test_case.prerequisites:
                            st.markdown(f"- {prereq}")
                        
                        # Test data
                        st.markdown("### Test Data")
                        for key, value in test_case.test_data.items():
                            st.markdown(f"- **{key}:** {value}")
                        
                        # Steps
                        st.markdown("### Steps")
                        for j, step in enumerate(test_case.steps, 1):
                            st.markdown(f"{j}. {step}")
                        
                        # Expected results
                        st.markdown("### Expected Results")
                        for result in test_case.expected_results:
                            st.markdown(f"- {result}")
        
        # Button to proceed to export
        if st.button("Export Documents", type="primary"):
            st.session_state.current_step = 5
            st.rerun()
            
        # Option to regenerate
        if st.button("Regenerate Test Script", type="secondary"):
            st.session_state.test_script = None
            st.rerun()
    
    # No test script yet - show generation button
    else:
        st.info("Ready to generate comprehensive test scripts based on the extracted business logic.")
        
        # Button to generate test scripts
        if st.button("Generate Test Scripts", type="primary"):
            with st.spinner("Generating test scripts..."):
                try:
                    # Initialize LLM utilities
                    llm_utils = LLMUtils()
                    
                    # Initialize the test generator
                    test_generator = TestGenerator(llm_utils)
                    
                    # Generate test script using TestGenerator
                    test_script = test_generator.render(st.session_state.validated_logic)
                    
                    if test_script and len(test_script.test_cases) > 0:
                        st.session_state.test_script = test_script
                        st.success(f"Successfully generated {len(test_script.test_cases)} test cases!")
                        st.rerun()
                    else:
                        # Fallback if TestGenerator fails
                        st.error("Failed to generate test script using TestGenerator. Creating basic test script instead.")
                        
                        # Create a basic test script directly
                        from models.business_logic import TestScript, TestCase
                        
                        # Get program name
                        program_name = st.session_state.validated_logic.program_name
                        
                        # Create a few basic test cases
                        test_cases = [
                            TestCase(
                                test_id="TC001",
                                title="Basic Functionality Test",
                                description="Verify the basic functionality of the program",
                                prerequisites=["System is available"],
                                test_data={"input": "test value"},
                                steps=["Start the program", "Enter test data", "Submit"],
                                expected_results=["Program processes data correctly"],
                                related_rules=[]
                            ),
                            TestCase(
                                test_id="TC002",
                                title="Input Validation Test",
                                description="Verify the input validation logic",
                                prerequisites=["System is available"],
                                test_data={"invalid_input": "invalid value"},
                                steps=["Start the program", "Enter invalid data", "Submit"],
                                expected_results=["Program rejects invalid input"],
                                related_rules=[]
                            )
                        ]
                        
                        # Create test script
                        test_script = TestScript(
                            program_name=program_name,
                            test_cases=test_cases
                        )
                        
                        # Store and proceed
                        st.session_state.test_script = test_script
                        st.warning("Created basic test script with limited test cases.")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error generating test script: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())

def export_step():
    """Step 5: Document export interface."""
    st.title("Export Documents")
    
    # Check if test script exists
    if not st.session_state.test_script or not st.session_state.validated_logic:
        st.warning("Please generate test scripts first.")
        if st.button("Go to Test Generation Step"):
            st.session_state.current_step = 4
            st.rerun()
        return
    
    # Initialize the document exporter component
    exporter = DocExporter()
    
    # Render the exporter
    exporter.render(
        st.session_state.validated_logic,
        st.session_state.test_script
    )
    
    # Option to start over
    st.success("🎉 Analysis complete! You can now download your documents or start a new analysis.")
    
    if st.button("Start New Analysis", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def main():
    """Main application function."""
    try:
        # Store the current step before processing
        original_step = st.session_state.current_step
        
        # Create the sidebar
        create_sidebar()
        
        # Show progress bar
        show_progress_bar()
        
        # Show the appropriate step based on current_step
        if st.session_state.current_step == 1:
            upload_step()
        elif st.session_state.current_step == 2:
            extract_step()
        elif st.session_state.current_step == 3:
            validate_step()
        elif st.session_state.current_step == 4:
            generate_step()
        elif st.session_state.current_step == 5:
            export_step()
            
        # Debug check for unexpected step changes
        if st.session_state.current_step != original_step and not st.session_state.get('intentional_step_change', False):
            st.warning(f"Step changed unexpectedly from {original_step} to {st.session_state.current_step}")
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("If the application is stuck at 'Analyzing program structure...', try these solutions:")
        st.error("1. Check your GROQ_API_KEY in the .env file")
        st.error("2. Reduce the sample size in the sidebar settings")
        st.error("3. Try a different LLM model in the sidebar settings")
        st.error("4. Increase the timeout value in the sidebar settings")
        
        # Option to reset application
        if st.button("Reset Application", type="primary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()