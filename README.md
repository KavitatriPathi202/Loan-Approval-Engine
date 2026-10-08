LOAN APPROVAL ENGINE: EMI CALCULATOR AND CREDIT RISK SCORER
============================================================

ABOUT
-----
A menu-driven Python project that models how a bank decides whether to
approve a loan. It calculates EMIs, scores applicants from 300 to 900,
assigns risk-based interest rates, and compares lending policies using
synthetic applicant data. It is written in core Python only, with no
external libraries.

FEATURES
--------
* EMI calculator and month-by-month repayment schedule
* Credit risk scorer (300-900) with risk bands and risk-based rates
* Assessment of a single applicant from user input
* Synthetic applicant generator using a custom random generator
* Policy comparison: cutoff score vs approval rate, defaults and profit
* Factor analysis: which applicant groups default most
* Top-K riskiest applicants using partition-based selection
* Efficiency study: naive vs fast exponentiation (O(n) vs O(log n))
* Built-in verification with known EMI test cases

HOW IT WORKS
------------
EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
  P = loan amount, r = monthly rate, n = months

Credit score = 300 + points from five factors:
  FOIR (EMI burden)      up to 250
  Past defaults          up to 150
  Credit history         up to 100
  Age stability          up to 50
  Loan size vs income    up to 50

Risk bands and rates:
  750 and above  Low risk       9.5%
  650 to 749     Medium risk    12.0%
  550 to 649     High risk      15.5%
  Below 550      Rejected

A loan is rejected if FOIR is above 60%, the applicant has 3 or more
past defaults, or the score is below the cutoff.

HOW TO RUN
----------
1. Install Python 3.
2. Run:  python loan_engine.py
3. Choose option 5 first to create a dataset, then options 6, 7 and 8.

CONCEPTS USED
-------------
Functions, conditionals, loops, lists, tuples, dictionaries,
pseudo-random numbers, large power computation, Kth smallest element,
counting, summation, max/min and algorithm efficiency analysis.

KEY FINDINGS
------------
* Raising the cutoff score lowers defaults but also lowers approvals.
* Profit is highest at a moderate cutoff, not the strictest one.
* Past defaults, age outside 25-55 and very large loans showed the
  highest default rates.

LIMITATIONS
-----------
All data is synthetic and the scoring rules are simplified. This is an
educational project and must not be used for real lending decisions.
