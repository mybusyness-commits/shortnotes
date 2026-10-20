---
title: 'Matrix Multiplication & Inverses: Formulas, Properties & Step-by-Step Guide'
slug: matrix-multiplication-inverses
subject: mathematics
chapter: linear-algebra
excerpt: Comprehensive high-yield notes on matrix multiplication conditions, algebraic
  properties, 2x2 and 3x3 matrix inverses, and singular matrix criteria.
tags:
- linear algebra
- matrices
- matrix inverse
- determinants
- matrix multiplication
date: '2026-10-18'
last_modified: '2026-10-21'
---

## 1. Matrix Multiplication Fundamentals

Matrix multiplication is a row-by-column binary operation. Two matrices $A$ and $B$ can only be multiplied if the number of columns in $A$ equals the number of rows in $B$.

* If $A$ has dimension $m \times k$ and $B$ has dimension $k \times n$, then the product $C = AB$ has dimension $m \times n$.
* Each entry $c_{ij}$ in product matrix $C$ is computed as the dot product of the $i$-th row of $A$ and the $j$-th column of $B$:
  $$c_{ij} = \sum_{r=1}^{k} a_{ir} b_{rj} = a_{i1}b_{1j} + a_{i2}b_{2j} + \dots + a_{ik}b_{kj}$$

### Key Algebraic Properties
* **Non-Commutative**: In general, $AB \ne BA$. Changing the order can either change the result or render the multiplication undefined.
* **Associative**: $A(BC) = (AB)C$.
* **Distributive**: $A(B + C) = AB + AC$ and $(A + B)C = AC + BC$.
* **Identity Element**: For any $m \times n$ matrix $A$, $I_m A = A I_n = A$, where $I$ is the identity matrix.
* **Transpose of Product**: $(AB)^T = B^T A^T$ (note the reversed order).

---

## 2. Invertible Matrices & Inverses

An $n \times n$ square matrix $A$ is **invertible** (or **non-singular**) if and only if there exists an $n \times n$ matrix $B$ such that:
$$AB = BA = I_n$$
If such a matrix exists, it is unique and denoted by $A^{-1}$.

### Essential Invertibility Criteria
A square matrix $A$ has an inverse if and only if:
1. $\det(A) \ne 0$ (Determinant is non-zero).
2. Rank of $A$ is $n$ (Full rank, columns are linearly independent).
3. The null space of $A$ contains only the zero vector: $\text{Null}(A) = \{0\}$.
4. $\lambda = 0$ is not an eigenvalue of $A$.

---

## 3. Finding the Inverse of a $2 \times 2$ Matrix

For a general $2 \times 2$ matrix:
$$A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}$$

1. **Calculate the Determinant**:
   $$\det(A) = ad - bc$$
   If $ad - bc = 0$, the matrix is singular and has **no inverse**.

2. **Apply the Inversion Formula**:
   Swap the main diagonal elements ($a \leftrightarrow d$), negate the off-diagonal elements ($-b, -c$), and divide by the determinant:
   $$A^{-1} = \frac{1}{ad - bc} \begin{pmatrix} d & -b \\ -c & a \end{pmatrix}$$

### Worked Example:
Find the inverse of $A = \begin{pmatrix} 4 & 7 \\ 2 & 6 \end{pmatrix}$.

1. $\det(A) = (4)(6) - (7)(2) = 24 - 14 = 10 \ne 0$.
2. Swap and negate:
   $$A^{-1} = \frac{1}{10} \begin{pmatrix} 6 & -7 \\ -2 & 4 \end{pmatrix} = \begin{pmatrix} 0.6 & -0.7 \\ -0.2 & 0.4 \end{pmatrix}$$
3. Verification:
   $$A A^{-1} = \begin{pmatrix} 4 & 7 \\ 2 & 6 \end{pmatrix} \begin{pmatrix} 0.6 & -0.7 \\ -0.2 & 0.4 \end{pmatrix} = \begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix} = I_2$$

---

## 4. Higher-Order Inverses ($3 \times 3$ and Beyond)

For $3 \times 3$ matrices, two standard methods are utilized:

### Method A: Adjugate (Cofactor) Method
$$A^{-1} = \frac{1}{\det(A)} \text{adj}(A) = \frac{1}{\det(A)} C^T$$
Where $C$ is the cofactor matrix with entries $C_{ij} = (-1)^{i+j} M_{ij}$, and $M_{ij}$ is the minor determinant formed by deleting row $i$ and column $j$.

### Method B: Gauss-Jordan Elimination
1. Set up the augmented matrix $[A \mid I_n]$.
2. Perform elementary row operations (row swapping, scalar multiplication, row addition) until the left half becomes the identity matrix:
   $$[A \mid I_n] \xrightarrow{\text{Row Operations}} [I_n \mid A^{-1}]$$
3. The right half is then your inverse matrix $A^{-1}$.

---

## 5. Properties of Matrix Inverses Summary Table

| Operation / Property | Formula | Important Condition |
| :--- | :--- | :--- |
| **Inverse of Inverse** | $(A^{-1})^{-1} = A$ | $A$ must be non-singular |
| **Inverse of Product** | $(AB)^{-1} = B^{-1} A^{-1}$ | Both $A$ and $B$ non-singular |
| **Inverse of Transpose** | $(A^T)^{-1} = (A^{-1})^T$ | Reversible operation |
| **Scalar Multiplication** | $(kA)^{-1} = \frac{1}{k} A^{-1}$ | $k \ne 0$ |
| **Determinant of Inverse** | $\det(A^{-1}) = \frac{1}{\det(A)}$ | $\det(A) \ne 0$ |

---

## 6. Common Examination Pitfalls
* **$(AB)^{-1} \ne A^{-1} B^{-1}$**: The order must always reverse to $B^{-1} A^{-1}$.
* **Dividing by Zero Determinant**: Always verify $\det(A) \ne 0$ before beginning inversion algebra.
* **Non-Square Matrices**: Inverses $A^{-1}$ are strictly defined only for square ($n \times n$) matrices. Rectangular matrices do not have standard two-sided inverses.
