---
title: Fundamental Theorem of Calculus & Key Derivatives
slug: calculus-fundamental-theorem
subject: mathematics
chapter: calculus
excerpt: Quick summary of differentiation rules, integration relations, and the Fundamental
  Theorem linking them.
tags:
- calculus
- derivatives
- integration
- fundamental theorem
date: '2026-10-17'
last_modified: '2026-10-21'
---

## 1. Overview & Statement

The **Fundamental Theorem of Calculus (FTC)** bridges differential calculus and integral calculus, showing that differentiation and integration are inverse operations.

### Part 1: Derivative of an Integral
If $f$ is continuous on $[a, b]$, then the function $g$ defined by:
$$g(x) = \int_{a}^{x} f(t) \, dt \quad \text{for } a \le x \le b$$
is continuous on $[a, b]$, differentiable on $(a, b)$, and its derivative is:
$$g'(x) = f(x)$$

### Part 2: Evaluation Theorem
If $f$ is continuous on $[a, b]$ and $F$ is any antiderivative of $f$ ($F' = f$), then:
$$\int_{a}^{b} f(x) \, dx = F(b) - F(a)$$

---

## 2. High-Yield Derivative Rules Table

| Function $f(x)$ | Derivative $f'(x)$ | Condition / Note |
| :--- | :--- | :--- |
| $x^n$ | $n x^{n-1}$ | Power Rule |
| $e^{kx}$ | $k e^{kx}$ | Exponential |
| $\ln(x)$ | $\frac{1}{x}$ | $x > 0$ |
| $\sin(x)$ | $\cos(x)$ | Trigonometric |
| $\cos(x)$ | $-\sin(x)$ | Note the negative sign |
| $\tan(x)$ | $\sec^2(x)$ | Standard identity |
| $u(x) \cdot v(x)$ | $u'v + uv'$ | Product Rule |
| $\frac{u(x)}{v(x)}$ | $\frac{u'v - uv'}{v^2}$ | Quotient Rule ($v \ne 0$) |

---

## 3. The Chain Rule

When dealing with composite functions $y = f(g(x))$:
$$\frac{dy}{dx} = f'(g(x)) \cdot g'(x)$$

### Quick Example:
For $y = \sin(3x^2 + 1)$:
1. Outer function: $\sin(u) \implies \cos(u)$
2. Inner function: $u = 3x^2 + 1 \implies \frac{du}{dx} = 6x$
3. Combined result:
$$\frac{dy}{dx} = 6x \cos(3x^2 + 1)$$

---

## 4. Key Exam Pitfalls to Avoid
* **Constant of Integration**: Never forget $+ C$ for indefinite integrals.
* **Quotient Rule Ordering**: Remember that $u'v - uv'$ has the numerator's derivative first.
* **Logarithmic Derivatives**: $\frac{d}{dx} \ln(f(x)) = \frac{f'(x)}{f(x)}$ via chain rule.
