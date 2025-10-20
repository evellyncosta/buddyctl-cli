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
    """Subtract two numbers.

    Args:
        a: First number (minuend)
        b: Second number (subtrahend)

    Returns:
        Subtraction of b from a
    """
    return a - b


def divide_two_numbers(a: float, b: float) -> float:
    """Divide two numbers.

    Args:
        a: First number (dividend)
        b: Second number (divisor)

    Returns:
        Division of a by b
    """
    return a / b


if __name__ == "__main__":
    # Test the function
    result = add_two_numbers(10, 20)
    print(f"10 + 20 = {result}")

    result = add_two_numbers(5.5, 3.2)
    print(f"5.5 + 3.2 = {result}")

    result = divide_two_numbers(10, 20)
    print(f"10 / 20 = {result}")
    
    result = divide_two_numbers(5.5, 3.2)
    print(f"5.5 / 3.2 = {result}")
    
    result = subtract_two_numbers(10, 3)
    print(f"10 - 3 = {result}")