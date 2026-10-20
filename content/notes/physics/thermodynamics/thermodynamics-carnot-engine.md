---
title: Laws of Thermodynamics & Carnot Engine Efficiency
slug: thermodynamics-carnot-engine
subject: physics
chapter: thermodynamics
excerpt: Concise summary of the Zeroth, First, and Second Laws of Thermodynamics,
  state functions, and Carnot cycle equations.
tags:
- thermodynamics
- carnot engine
- physics
- entropy
date: '2026-10-17'
last_modified: '2026-10-21'
---

## 1. The Four Laws in Brief

* **Zeroth Law (Thermal Equilibrium)**: If system $A$ is in thermal equilibrium with $B$, and $B$ is with $C$, then $A$ is in thermal equilibrium with $C$. This establishes the definition of temperature.
* **First Law (Conservation of Energy)**:
  $$\Delta U = Q - W$$
  Where $\Delta U$ is the change in internal energy, $Q$ is heat added to the system, and $W$ is work done **by** the system ($W = \int P \, dV$).
* **Second Law (Entropy & Spontaneity)**: The entropy of an isolated system never decreases over time:
  $$\Delta S_{\text{universe}} \ge 0$$
  No cyclic heat engine can convert 100% of input heat into mechanical work (Kelvin-Planck statement).
* **Third Law (Absolute Zero)**: As temperature approaches absolute zero ($T \to 0\text{ K}$), the entropy of a pure crystalline substance approaches a constant minimum value (zero).

---

## 2. Work Done in Thermodynamic Processes (Ideal Gas)

| Process Type | Defining Condition | Work Done ($W$) | Internal Energy Change ($\Delta U$) |
| :--- | :--- | :--- | :--- |
| **Isochoric** | Volume constant ($dV = 0$) | $W = 0$ | $\Delta U = Q = n C_v \Delta T$ |
| **Isobaric** | Pressure constant ($dP = 0$) | $W = P(V_2 - V_1) = n R \Delta T$ | $\Delta U = n C_v \Delta T$ |
| **Isothermal** | Temperature constant ($dT = 0$) | $W = nRT \ln\left(\frac{V_2}{V_1}\right)$ | $\Delta U = 0 \implies Q = W$ |
| **Adiabatic** | No heat exchange ($Q = 0$) | $W = \frac{P_1 V_1 - P_2 V_2}{\gamma - 1}$ | $\Delta U = -W$ |

Where $\gamma = \frac{C_p}{C_v}$ is the heat capacity ratio.

---

## 3. The Carnot Cycle & Efficiency

The Carnot cycle is the theoretical upper limit on the efficiency of any heat engine operating between two temperatures $T_H$ (hot reservoir) and $T_C$ (cold reservoir):

$$\eta_{\text{Carnot}} = 1 - \frac{T_C}{T_H} = \frac{T_H - T_C}{T_H}$$

> **Critical Rule**: All temperatures in thermodynamic efficiency calculations must be converted to **Kelvin** ($T_{\text{Kelvin}} = T_{\text{Celsius}} + 273.15$).

### The 4 Stages of the Carnot Cycle:
1. **Reversible Isothermal Expansion** at $T_H$ (Heat absorbed $Q_H$)
2. **Reversible Adiabatic Expansion** ($T_H \to T_C$)
3. **Reversible Isothermal Compression** at $T_C$ (Heat rejected $Q_C$)
4. **Reversible Adiabatic Compression** ($T_C \to T_H$)
