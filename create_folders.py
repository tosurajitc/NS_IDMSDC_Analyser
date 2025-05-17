import os
import re
import argparse
import sys



# RUn this program: python create_folders.py --file "C:\@Official\Automation\2025 Planning\Agentic AI Handson\NS_IDMSDC_Analyser\folder_structure.txt"


def create_structure(file_path, output_dir="."):
    """
    Create a folder structure based on a text file with tree formatting.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Process lines to extract clean names and levels
    structure = []
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Extract the actual content after tree characters
        # Look for patterns like ├── or └── or │   ├──
        match = re.search(r'([│├└─\s]*)([^│├└─\s].+)$', line.rstrip())
        if not match:
            continue
        
        prefix = match.group(1)
        content = match.group(2).strip()
        
        # Skip comment lines
        if content.startswith('#'):
            continue
        
        # Calculate level based on tree characters or spaces
        level = 0
        if '├──' in prefix or '└──' in prefix:
            # Count tree branches (│) before the actual branch indicator
            level = prefix.count('│') + 1
        
        # Clean up any comments at the end of the line
        if '#' in content:
            content = content.split('#', 1)[0].strip()
        
        structure.append((level, content))
    
    # Process the structure to create directories and files
    path_stack = []
    for level, content in structure:
        # Adjust path stack based on level
        path_stack = path_stack[:level]
        
        # Determine if it's a file or directory
        is_file = '.' in os.path.basename(content) and not content.endswith('/')
        if content.endswith('/'):
            content = content[:-1]  # Remove trailing slash
        
        # Add to path
        path_stack.append(content)
        
        # Create full path (using relative paths)
        full_path = os.path.join(output_dir, *path_stack)
        
        # Create directory or file
        if is_file:
            create_file(full_path)
            path_stack.pop()  # Remove file from path
        else:
            create_directory(full_path)


def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")


def create_file(path):
    """Create a file with appropriate placeholder content based on extension."""
    # Create parent directory if needed
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
        print(f"Created directory: {parent_dir}")
    
    # Create file if it doesn't exist
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            filename = os.path.basename(path)
            extension = os.path.splitext(filename)[1].lower()
            
            if extension in ['.py']:
                f.write(f'"""\n{filename}\n\nDescription: \nAuthor: \nDate: \n"""\n\n\n')
            elif extension in ['.js', '.jsx', '.ts', '.tsx']:
                f.write(f'/**\n * {filename}\n *\n * Description: \n * Author: \n * Date: \n */\n\n\n')
            elif extension in ['.html']:
                f.write(f'<!-- \n  {filename}\n  \n  Description: \n  Author: \n  Date: \n-->\n\n')
            elif extension in ['.css', '.scss']:
                f.write(f'/*\n * {filename}\n *\n * Description: \n * Author: \n * Date: \n */\n\n')
            elif extension in ['.md']:
                f.write(f'# {os.path.splitext(filename)[0]}\n\n## Description\n\n\n')
            elif extension in ['.json']:
                f.write(f'{{\n  "name": "{os.path.splitext(filename)[0]}",\n  "description": ""\n}}\n')
            else:
                f.write(f'# {filename}\n# \n# Description: \n# Author: \n# Date: \n\n')
        
        print(f"Created file: {path}")
    else:
        print(f"File already exists: {path}")


def main():
    parser = argparse.ArgumentParser(description='Create folder structure from a text file.')
    parser.add_argument('--file', '-f', type=str, default='folder_structure.txt',
                        help='Path to the structure file (default: folder_structure.txt)')
    parser.add_argument('--output', '-o', type=str, default='.',
                        help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
    # Make sure the output directory is interpreted relative to the current directory
    output_dir = args.output
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)
    
    # Create the folder structure
    create_structure(args.file, output_dir)
    print("\nFolder structure creation completed!")


if __name__ == "__main__":
    main()