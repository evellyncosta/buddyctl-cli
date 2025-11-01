# Tool Usage Instructions

Detailed instructions for using each tool effectively.

## read_file

**Purpose**: Read the complete contents of a file.

**When to use**:
- Before making any modifications to a file
- To understand current code structure
- To verify file contents before applying changes

**Parameters**:
- `file_path` (str): Path to the file to read (relative or absolute)

**Returns**: File contents as string

**Example**:
```python
read_file(file_path="src/calculator.py")
```

**Best Practices**:
- Always read files before modifying them
- Use this to get exact text for search/replace operations
- Check file structure to understand context

---

## search_replace_in_file

**Purpose**: Replace exact text in a file (first occurrence only).

**When to use**:
- Modifying existing code in a file
- Adding new code at specific locations
- Fixing bugs or refactoring code

**Parameters**:
- `file_path` (str): Path to the file to modify
- `search` (str): Exact text to find (must match character-by-character)
- `replace` (str): New text to replace with

**Returns**: Success message or detailed error

**CRITICAL RULES**:
1. `search` text must match EXACTLY (including all whitespace)
2. Include 5-10 lines of context to make match unique
3. Only first occurrence is replaced
4. If search text not found, operation fails with helpful error

**Example**:
```python
search_replace_in_file(
    file_path="calculator.py",
    search="""def add(a, b):
    return a + b""",
    replace="""def add(a, b):
    # Add two numbers
    return a + b"""
)
```

**Common Mistakes to Avoid**:
- ❌ Guessing at whitespace (tabs vs spaces)
- ❌ Using partial text (not enough context)
- ❌ Forgetting to include indentation
- ❌ Not reading file first to verify exact text

**Error Handling**:
If you get "SEARCH content not found" error:
1. Read the file again to see current content
2. Copy the exact text (including whitespace)
3. Include more context to make match unique

---

## create_new_file

**Purpose**: Create a new file with specified content.

**When to use**:
- Creating new modules, classes, or scripts
- Adding new configuration files
- Creating test files

**Parameters**:
- `file_path` (str): Path for the new file
- `content` (str): Complete file content

**Returns**: Success message with file size

**CRITICAL RULES**:
1. Only for NEW files (not existing files)
2. Parent directories are created automatically
3. If file already exists, operation fails
4. Use search_replace_in_file for existing files

**Example**:
```python
create_new_file(
    file_path="src/utils/helper.py",
    content="""# Helper utilities

def format_output(data):
    \"\"\"Format data for output.\"\"\"
    return str(data)
"""
)
```

**Best Practices**:
- Include proper file headers (docstrings, imports)
- Use consistent indentation
- Follow project's code style
- Add necessary imports at the top

**Error Handling**:
If file already exists:
- Use `search_replace_in_file` to modify it instead
- Or read the file first to understand its contents
