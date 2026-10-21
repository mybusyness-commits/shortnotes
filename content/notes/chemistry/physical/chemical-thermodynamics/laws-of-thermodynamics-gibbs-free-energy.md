---
title: First & Second Laws of Thermodynamics, Enthalpy & Gibbs Free Energy
slug: laws-of-thermodynamics-gibbs-free-energy
subject: chemistry
branch: physical
chapter: chemical-thermodynamics
excerpt: 'High-yield equations, sign conventions, state functions, Hess law, and spontaneity criteria with Gibbs free energy.'
tags: [physical-chemistry, thermodynamics, enthalpy, entropy, gibbs-free-energy, spontaneity]
date: '2026-10-21'
last_modified: '2026-10-21'
---

## 1. First Law of Thermodynamics

Energy cannot be created or destroyed, only transferred:

$$\Delta U = q + w$$

Where:
* $\Delta U$ = Change in internal energy ($\text{J}$)
* $q$ = Heat absorbed by system ($> 0$ endothermic, $< 0$ exothermic)
* $w$ = Work done on system: $w = -P_{\text{ext}} \Delta V$

At constant pressure ($q_p = \Delta H$):

$$\Delta H = \Delta U + \Delta n_g R T$$

Where $\Delta n_g = \sum n_{\text{gaseous products}} - \sum n_{\text{gaseous reactants}}$.

---

## 2. Gibbs Free Energy & Spontaneity

The fundamental condition for spontaneous processes at constant temperature and pressure:

$$\Delta G = \Delta H - T\Delta S$$

| $\Delta H$ | $\Delta S$ | $\Delta G = \Delta H - T\Delta S$ | Spontaneity Condition |
| :--- | :--- | :--- | :--- |
| **Negative ($-$)** | **Positive ($+$)** | Always Negative ($-$) | **Spontaneous at all temperatures** |
| **Positive ($+$)** | **Negative ($-$)** | Always Positive ($+$) | **Non-spontaneous at all temperatures** (Reverse is spontaneous) |
| **Negative ($-$)** | **Negative ($-$)** | Negative at low $T$ | **Spontaneous at low temperatures** |
| **Positive ($+$)** | **Positive ($+$)** | Negative at high $T$ | **Spontaneous at high temperatures** |

---

## 3. Equilibrium Constant Relation

$$\Delta G^\circ = -RT \ln K_{\text{eq}} = -2.303 RT \log_{10} K_{\text{eq}}$$

* If $K_{\text{eq}} > 1 \implies \Delta G^\circ < 0$ (Products favored at equilibrium)
* If $K_{\text{eq}} < 1 \implies \Delta G^\circ > 0$ (Reactants favored at equilibrium)
