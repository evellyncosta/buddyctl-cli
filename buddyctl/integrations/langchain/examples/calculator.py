# Copyright 2024 Evellyn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simple calculator module."""


def add_two_numbers(a: float, b: float) -> float:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def subtract_two_numbers(a: float, b: float) -> float:
    """Subtract second number from first number.

    Args:
        a: First number (minuend)
        b: Second number (subtrahend)

    Returns:
        Difference of a and b
    """
    return a - b


def multiply_two_numbers(a: float, b: float) -> float:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Product of a and b
    """
    return a * b


def divide_two_numbers(a: float, b: float) -> float:
    """Divide first number by second number.

    Args:
        a: First number (dividend)
        b: Second number (divisor)

    Returns:
        Quotient of a and b

    Raises:
        ValueError: If divisor is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


if __name__ == "__main__":
    # Test all four operations with two numbers
    num1, num2 = 10, 20
    
    # Addition
    result = add_two_numbers(num1, num2)
    print(f"{num1} + {num2} = {result}")
    
    # Subtraction
    result = subtract_two_numbers(num1, num2)
    print(f"{num1} - {num2} = {result}")
    
    # Multiplication
    result = multiply_two_numbers(num1, num2)
    print(f"{num1} * {num2} = {result}")
    
    # Division
    result = divide_two_numbers(num1, num2)
    print(f"{num1} / {num2} = {result}")
    
    print()  # Empty line for separation
    
    # Test with decimal numbers
    num1, num2 = 5.5, 2.2
    
    print(f"Testing with decimal numbers: {num1} and {num2}")
    print(f"{num1} + {num2} = {add_two_numbers(num1, num2)}")
    print(f"{num1} - {num2} = {subtract_two_numbers(num1, num2)}")
    print(f"{num1} * {num2} = {multiply_two_numbers(num1, num2)}")
    print(f"{num1} / {num2} = {divide_two_numbers(num1, num2)}")
    
    # Test division by zero handling
    print()
    try:
        result = divide_two_numbers(10, 0)
        print(f"10 / 0 = {result}")
    except ValueError as e:
        print(f"Error: {e}")