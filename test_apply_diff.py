#!/usr/bin/env python3
"""Test script to verify the apply_diff functionality works correctly."""

from buddyctl.integrations.langchain.tools import apply_diff

# Sample diff that adds a comment to a Python function
test_diff = """--- a/test_file.py
+++ b/test_file.py
@@ -1,5 +1,6 @@
 def hello():
+    # This is a new comment
     print("Hello World")

 if __name__ == "__main__":
     hello()
"""

print("Testing apply_diff tool...")
print("=" * 60)
print("Sample diff:")
print(test_diff)
print("=" * 60)

# Note: This will fail with "File not found" since test_file.py doesn't exist
# But it demonstrates that the tool is properly imported and callable
result = apply_diff.invoke({"diff_content": test_diff})
print("\nResult:")
print(result)
