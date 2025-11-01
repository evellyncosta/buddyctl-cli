# Error Recovery Instructions

How to handle and recover from common tool errors.

## SEARCH Content Not Found Error

**Error Message**:
```
❌ Error: SEARCH content not found in file.py. Make sure text matches EXACTLY.
```

**What This Means**:
The text you specified in the `search` parameter doesn't exist in the file, or doesn't match exactly.

**How to Fix**:

### Step 1: Read the file again
```python
read_file(file_path="the_file.py")
```

### Step 2: Identify the exact text
- Find the section you want to modify
- Copy the EXACT text (including all whitespace)
- Include 5-10 lines of surrounding context

### Step 3: Verify whitespace
- Check if the file uses tabs or spaces for indentation
- Count the number of spaces/tabs
- Copy exactly as shown

### Step 4: Try again with exact match
```python
search_replace_in_file(
    file_path="the_file.py",
    search="<exact text copied from file>",
    replace="<your new text>"
)
```

## Common Causes

### 1. Whitespace Mismatch
```python
# ❌ WRONG (missing indentation)
search="def calculate():\nreturn 42"

# ✅ CORRECT (includes 4 spaces)
search="def calculate():\n    return 42"
```

### 2. Not Enough Context
```python
# ❌ WRONG (ambiguous - might match multiple places)
search="return result"

# ✅ CORRECT (unique match with context)
search="""    total = sum(values)
    result = total * 2
    return result"""
```

### 3. File Changed Since Last Read
```python
# ❌ WRONG (using outdated text)
# You read file 5 minutes ago, file may have changed

# ✅ CORRECT (read again before modifying)
read_file(file_path="file.py")  # Get current content
search_replace_in_file(...)     # Use fresh text
```

## File Already Exists Error

**Error Message**:
```
❌ Error: File 'helper.py' already exists. Use search_replace_in_file to modify it.
```

**How to Fix**:

### Option 1: Modify the existing file
```python
# Read first to see current content
read_file(file_path="helper.py")

# Then modify using search_replace
search_replace_in_file(
    file_path="helper.py",
    search="<exact text to replace>",
    replace="<new text>"
)
```

### Option 2: Choose a different name
```python
create_new_file(
    file_path="helper_v2.py",  # Different name
    content="..."
)
```

## Path Traversal Security Error

**Error Message**:
```
❌ Error: Path '../../../etc/passwd' is outside project boundaries
```

**What This Means**:
You're trying to access/modify files outside the current project directory (security protection).

**How to Fix**:
- Use paths relative to the project root
- Don't use `..` to go up directories outside the project
- Stick to files within the project

## Permission Denied Error

**Error Message**:
```
❌ Error: Permission denied writing: file.py
```

**Possible Causes**:
1. File is read-only
2. File is open in another program
3. Insufficient system permissions

**How to Fix**:
- Close the file if it's open in an editor
- Check file permissions
- Try a different file

## Recovery Strategy

When you encounter an error:

1. **Read the error message carefully** - It tells you exactly what's wrong
2. **Read the file again** - Get current, accurate content
3. **Copy exact text** - Include all whitespace and context
4. **Try again** - Use the corrected information

**Example Recovery Flow**:
```
User: "Add logging to calculate() function"

[Attempt 1]
search_replace_in_file(...)
❌ Error: SEARCH content not found

[Recovery]
read_file(file_path="calculator.py")  # Read again
# Identify exact text with correct whitespace
# Include more context (10 lines instead of 3)

[Attempt 2]
search_replace_in_file(...)
✅ Success!
```

## Prevention Tips

1. **Always read first** - Don't guess file contents
2. **Include context** - 5-10 lines minimum
3. **Copy exactly** - All whitespace matters
4. **Verify unique** - Search text should match only once
5. **Check twice** - Review your search text before submitting
