Math
====

.. meta::
    :description: Examples of MathJax equations.
    :keywords: mathjax, equations, latex, math

MathJax Equations
-----------------

You can include beautiful mathematical equations using LaTeX syntax, rendered by MathJax.

Inline Math
~~~~~~~~~~~

The Pythagorean theorem is :math:`a^2 + b^2 = c^2`.

Block Math
~~~~~~~~~~

.. math::

   \int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}

Maxwell's Equations
~~~~~~~~~~~~~~~~~~~

.. math::
   :label: maxwell

   \begin{align}
     \nabla \cdot \mathbf{E} &= \frac{\rho}{\varepsilon_0} \\
     \nabla \cdot \mathbf{B} &= 0 \\
     \nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \\
     \nabla \times \mathbf{B} &= \mu_0\mathbf{J} + \mu_0\varepsilon_0\frac{\partial \mathbf{E}}{\partial t}
   \end{align}
