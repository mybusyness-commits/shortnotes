---
title: Attributes
slug: attributes
subject: mathematics
chapter: statistics
excerpt: Attributes
tags:
- statistics
- attributes
- graph
- histogram
date: '2026-10-18'
last_modified: '2026-10-18'
---

$$\text{\bf CORE PRINCIPLE: THEORY OF ATTRIBUTES}$$

$$\text{Frequencies are organized into a } 2 \times 2 \text{ Contingency Table:}$$

$$\begin{array}{|c|c|c|c|}
\hline
& B \text{ (Present)} & \beta \text{ (Absent)} & \text{\bf Total} \\ \hline
A \text{ (Present)} & (AB) & (A\beta) & \mathbf{(A)} \\ \hline
\alpha \text{ (Absent)} & (\alpha B) & (\alpha\beta) & \mathbf{(\alpha)} \\ \hline
\text{\bf Total} & \mathbf{(B)} & \mathbf{(\beta)} & \mathbf{N \text{ (Grand Total)}} \\ \hline
\end{array}$$

$$\text{Under the Null Hypothesis } (H_0) \text{ of independence, the Expected Frequency } (E) \text; is:}$$
$$E = \frac{\text{Row Total} \times \text{Column Total}}{N}$$

$$\text{\bf EXAMPLE PROBLEM}$$
$$\text{Given Data: } N = 200, \quad (A) = 80, \quad (B) = 60, \quad (AB) = 35$$
$$\text{Critical Value: } \chi^2_{0.05} \text{ for } 1 \text{ d.f.} = 3.84$$

$$\text{\bf STEP 1: Complete the Contingency Table (Observed Frequencies } O\text{)}$$
$$\begin{array}{l}
(A\beta) = (A) - (AB) = 80 - 35 = 45 \\
(\alpha B) = (B) - (AB) = 60 - 35 = 25 \\
(\alpha) = N - (A) = 200 - 80 = 120 \\
(\alpha\beta) = (\alpha) - (\alpha B) = 120 - 25 = 95
\end{array}$$

$$\begin{array}{|c|c|c|c|}
\hline
& B & \beta & \text{\bf Total} \\ \hline
A & 35 & 45 & \mathbf{80} \\ \hline
\alpha & 25 & 95 & \mathbf{120} \\ \hline
\text{\bf Total} & \mathbf{60} & \mathbf{140} & \mathbf{200} \\ \hline
\end{array}$$

$$\text{\bf STEP 2: Compute Expected Frequencies } (E)$$
$$\begin{array}{ll}
E_{(AB)} = \frac{80 \times 60}{200} = 24 & E_{(A\beta)} = \frac{80 \times 140}{200} = 56 \\
E_{(\alpha B)} = \frac{120 \times 60}{200} = 36 & E_{(\alpha\beta)} = \frac{120 \times 140}{200} = 84
\end{array}$$

$$\text{\bf STEP 3: Calculate Chi-Square Statistic } (\chi^2)$$
$$\chi^2 = \sum \frac{(O - E)^2}{E}$$
$$\chi^2 = \frac{(35 - 24)^2}{24} + \frac{(45 - 56)^2}{56} + \frac{(25 - 36)^2}{36} + \frac{(95 - 84)^2}{84}$$
$$\chi^2 = \frac{121}{24} + \frac{121}{56} + \frac{121}{36} + \frac{121}{84}$$
$$\chi^2 \approx 5.04 + 2.16 + 3.36 + 1.44 = \mathbf{12.00}$$

$$\text{\bf STEP 4: Decision}$$
$$\text{Since } \chi^2_{\text{calculated}} (12.00) > \chi^2_{\text{critical}} (3.84)\text{, reject } H_0\text{.}$$
$$\text{\bf Conclusion: The attributes are significantly associated.}$$
