Standards
=========

This section outlines the coding standards and style guidelines for the project. Agents and contributors are expected to follow these guidelines.

Docstrings
----------

We use **Google-style docstrings** via the ``sphinx.ext.napoleon`` extension.

*   **Type Hints**: Type hints are mandatory and serve as the primary documentation for argument and return types.
*   **Minimalism**:
    *   Do not document arguments if their purpose is obvious from the name and type hint.
    *   Only document arguments that require explanation (e.g., specific constraints, non-obvious behavior).
*   **Descriptions**: A description is nice, but only include it if it adds value to a well-named function. Avoid stating the obvious.

Example
~~~~~~~

.. code-block:: python

   def calculate_velocity(distance: float, time: float) -> float:
       """
       Calculate velocity.

       Args:
           time: Must be non-zero.
       """
       return distance / time
