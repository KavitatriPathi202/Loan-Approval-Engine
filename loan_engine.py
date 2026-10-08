

# ---------------------------------------------------------------
# 1. PSEUDO-RANDOM NUMBER GENERATOR (Linear Congruential Generator)
# ---------------------------------------------------------------
class RNG:
    def __init__(self, seed):
        self.state = seed

    def next(self):
        # LCG constants from Numerical Recipes
        self.state = (1664525 * self.state + 1013904223) % 4294967296
        return self.state

    def random(self):
        # float in [0, 1)
        return self.next() / 4294967296

    def randint(self, low, high):
        # use the high bits: low bits of an LCG repeat in short cycles
        return low + (self.next() >> 8) % (high - low + 1)

    def choice(self, items):
        return items[self.randint(0, len(items) - 1)]


# ---------------------------------------------------------------
# 2. MATH HELPERS (own power function: naive and fast)
# ---------------------------------------------------------------
def power_naive(base, n):
    """O(n) multiplications. Returns (result, multiplications)."""
    result = 1
    count = 0
    for _ in range(n):
        result *= base
        count += 1
    return result, count


def power_fast(base, n):
    """O(log n) multiplications (exponentiation by squaring)."""
    result = 1
    count = 0
    while n > 0:
        if n % 2 == 1:
            result *= base
            count += 1
        base *= base
        count += 1
        n //= 2
    return result, count


def emi_amount(principal, annual_rate, months):
    """EMI = P*r*(1+r)^n / ((1+r)^n - 1), r = monthly rate."""
    r = annual_rate / (12 * 100)
    if r == 0:
        return principal / months
    factor, _ = power_fast(1 + r, months)
    return principal * r * factor / (factor - 1)


def repayment_schedule(principal, annual_rate, months):
    """Returns a list of tuples: (month, emi, interest, principal_paid, balance)."""
    r = annual_rate / (12 * 100)
    emi = emi_amount(principal, annual_rate, months)
    balance = principal
    schedule = []
    for m in range(1, months + 1):
        interest = balance * r
        principal_paid = emi - interest
        balance = balance - principal_paid
        if balance < 0.005:
            balance = 0.0
        schedule.append((m, emi, interest, principal_paid, balance))
    return schedule


# ---------------------------------------------------------------
# 3. CREDIT RISK SCORER (score range 300 - 900, like CIBIL)
# ---------------------------------------------------------------
def foir_ratio(applicant, new_emi):
    """Fixed Obligation to Income Ratio."""
    return (applicant["existing_emi"] + new_emi) / applicant["income"]


def score_breakdown(applicant, new_emi):
    """Returns (total_score, dictionary of factor points)."""
    points = {}

    # Factor 1: FOIR (max 250)
    foir = foir_ratio(applicant, new_emi)
    if foir <= 0.30:
        points["FOIR"] = 250
    elif foir <= 0.40:
        points["FOIR"] = 200
    elif foir <= 0.50:
        points["FOIR"] = 120
    elif foir <= 0.60:
        points["FOIR"] = 50
    else:
        points["FOIR"] = 0

    # Factor 2: past defaults (max 150)
    d = applicant["past_defaults"]
    if d == 0:
        points["Defaults"] = 150
    elif d == 1:
        points["Defaults"] = 60
    else:
        points["Defaults"] = 0

    # Factor 3: credit history length in years (max 100)
    years = applicant["history_years"]
    if years > 10:
        years = 10
    points["History"] = years * 10

    # Factor 4: age stability (max 50)
    if 25 <= applicant["age"] <= 55:
        points["Age"] = 50
    else:
        points["Age"] = 25

    # Factor 5: loan to annual income ratio (max 50)
    lti = applicant["loan_amount"] / (applicant["income"] * 12)
    if lti <= 1:
        points["LoanSize"] = 50
    elif lti <= 3:
        points["LoanSize"] = 30
    else:
        points["LoanSize"] = 0

    total = 300 + sum(points.values())
    return total, points


def risk_band(score):
    if score >= 750:
        return "LOW RISK"
    elif score >= 650:
        return "MEDIUM RISK"
    elif score >= 550:
        return "HIGH RISK"
    return "VERY HIGH RISK"


def risk_based_rate(score):
    """Interest rate depends on risk band. Returns None if not eligible."""
    if score >= 750:
        return 9.5
    elif score >= 650:
        return 12.0
    elif score >= 550:
        return 15.5
    return None


# ---------------------------------------------------------------
# 4. DECISION ENGINE
# ---------------------------------------------------------------
def assess(applicant, cutoff=550, risk_based=True, flat_rate=12.0):
    """Returns a dictionary with the full decision."""
    # EMI is needed for FOIR, so first compute it at the flat rate
    trial_emi = emi_amount(applicant["loan_amount"], flat_rate, applicant["tenure"])
    score, points = score_breakdown(applicant, trial_emi)
    foir = foir_ratio(applicant, trial_emi)

    result = {
        "score": score,
        "points": points,
        "band": risk_band(score),
        "foir": foir,
        "approved": False,
        "rate": None,
        "emi": None,
        "reason": "",
    }

    if foir > 0.60:
        result["reason"] = "FOIR above 60% (EMI burden too high)"
        return result
    if applicant["past_defaults"] >= 3:
        result["reason"] = "Three or more past defaults"
        return result
    if score < cutoff:
        result["reason"] = "Score " + str(score) + " is below cutoff " + str(cutoff)
        return result

    if risk_based:
        rate = risk_based_rate(score)
        if rate is None:
            # cutoff was set lower than the lowest band: charge the top rate
            rate = 15.5
    else:
        rate = flat_rate

    result["approved"] = True
    result["rate"] = rate
    result["emi"] = emi_amount(applicant["loan_amount"], rate, applicant["tenure"])
    result["reason"] = "Meets policy"
    return result


# ---------------------------------------------------------------
# 5. SYNTHETIC DATA GENERATOR
# ---------------------------------------------------------------
def generate_applicants(n, seed):
    rng = RNG(seed)
    applicants = []
    tenures = [12, 24, 36, 48, 60]
    for i in range(1, n + 1):
        income = rng.randint(15000, 150000)
        age = rng.randint(21, 60)
        history = rng.randint(0, 15)
        # most people have 0 defaults
        roll = rng.random()
        if roll < 0.70:
            defaults = 0
        elif roll < 0.88:
            defaults = 1
        elif roll < 0.96:
            defaults = 2
        else:
            defaults = 3
        existing = int(income * rng.random() * 0.4)
        loan = rng.randint(1, 20) * income  # 1x to 20x monthly income
        loan = (loan // 1000) * 1000
        if loan < 10000:
            loan = 10000
        tenure = rng.choice(tenures)

        a = {
            "id": i,
            "income": income,
            "age": age,
            "history_years": history,
            "past_defaults": defaults,
            "existing_emi": existing,
            "loan_amount": loan,
            "tenure": tenure,
        }
        # hidden truth: did this person actually default on this loan?
        trial_emi = emi_amount(loan, 12.0, tenure)
        s, _ = score_breakdown(a, trial_emi)
        weakness = (900 - s) / 600  # 0 = best, 1 = worst
        p_default = 0.02 + 0.45 * weakness * weakness
        a["will_default"] = rng.random() < p_default
        applicants.append(a)
    return applicants


# ---------------------------------------------------------------
# 6. ANALYSIS (RESEARCH PART)
# ---------------------------------------------------------------
LOSS_GIVEN_DEFAULT = 0.5  # bank loses 50% of principal on a default


def run_policy(applicants, cutoff, risk_based):
    """Returns a dictionary of statistics for one policy."""
    total = len(applicants)
    approved = 0
    defaults = 0
    profit = 0.0
    for a in applicants:
        d = assess(a, cutoff, risk_based)
        if d["approved"]:
            approved += 1
            interest_income = d["emi"] * a["tenure"] - a["loan_amount"]
            if a["will_default"]:
                defaults += 1
                profit -= a["loan_amount"] * LOSS_GIVEN_DEFAULT
            else:
                profit += interest_income
    stats = {
        "cutoff": cutoff,
        "approved": approved,
        "approval_rate": 100.0 * approved / total,
        "defaults": defaults,
        "default_rate": 100.0 * defaults / approved if approved > 0 else 0.0,
        "profit": profit,
    }
    return stats


def kth_smallest(values, k):
    """Selection using partitioning (quickselect style). k starts at 1."""
    items = list(values)
    target = k - 1
    while True:
        pivot = items[len(items) // 2]
        smaller = []
        equal = []
        larger = []
        for x in items:
            if x < pivot:
                smaller.append(x)
            elif x == pivot:
                equal.append(x)
            else:
                larger.append(x)
        if target < len(smaller):
            items = smaller
        elif target < len(smaller) + len(equal):
            return pivot
        else:
            target = target - len(smaller) - len(equal)
            items = larger


# ---------------------------------------------------------------
# 7. INPUT HELPERS (safe input, no crashes on bad entry)
# ---------------------------------------------------------------
def ask_float(prompt, minimum=None, maximum=None):
    while True:
        text = input(prompt).strip()
        try:
            value = float(text)
        except ValueError:
            print("  Please enter a number.")
            continue
        if minimum is not None and value < minimum:
            print("  Value must be at least " + str(minimum))
            continue
        if maximum is not None and value > maximum:
            print("  Value must be at most " + str(maximum))
            continue
        return value


def ask_int(prompt, minimum=None, maximum=None):
    while True:
        text = input(prompt).strip()
        try:
            value = int(text)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print("  Value must be at least " + str(minimum))
            continue
        if maximum is not None and value > maximum:
            print("  Value must be at most " + str(maximum))
            continue
        return value


def money(x):
    return "Rs " + format(x, ",.2f")


# Dataset kept in memory so menu options can reuse it
DATASET = []


def need_dataset():
    if len(DATASET) == 0:
        print("\nNo dataset yet. Use option 5 first to generate applicants.")
        return False
    return True


# ---------------------------------------------------------------
# 8. MENU OPTIONS
# ---------------------------------------------------------------
def option_emi():
    print("\n--- EMI CALCULATOR ---")
    p = ask_float("Loan amount (Rs): ", 1)
    rate = ask_float("Annual interest rate (%): ", 0, 100)
    months = ask_int("Tenure (months): ", 1, 600)
    emi = emi_amount(p, rate, months)
    total = emi * months
    print("\nMonthly EMI      :", money(emi))
    print("Total payment    :", money(total))
    print("Total interest   :", money(total - p))
    print("Interest / loan  :", format(100 * (total - p) / p, ".1f") + "%")


def option_schedule():
    print("\n--- REPAYMENT SCHEDULE ---")
    p = ask_float("Loan amount (Rs): ", 1)
    rate = ask_float("Annual interest rate (%): ", 0, 100)
    months = ask_int("Tenure (months): ", 1, 600)
    sched = repayment_schedule(p, rate, months)
    print("\n Month |      EMI |  Interest |  Principal |     Balance")
    print("-------+----------+-----------+------------+------------")
    total_interest = 0.0
    for row in sched:
        m, e, i, pp, b = row
        total_interest += i
        print(format(m, "6d") + " |" + format(e, "9.2f") + " |" +
              format(i, "10.2f") + " |" + format(pp, "11.2f") + " |" +
              format(b, "12.2f"))
    print("\nTotal interest paid:", money(total_interest))


def option_assess():
    print("\n--- ASSESS ONE APPLICANT ---")
    a = {
        "id": 0,
        "income": ask_float("Monthly income (Rs): ", 1),
        "age": ask_int("Age: ", 18, 80),
        "history_years": ask_int("Years of credit history: ", 0, 60),
        "past_defaults": ask_int("Number of past defaults: ", 0, 20),
        "existing_emi": ask_float("Existing monthly EMIs (Rs): ", 0),
        "loan_amount": ask_float("Loan amount wanted (Rs): ", 1),
        "tenure": ask_int("Tenure (months): ", 1, 600),
    }
    d = assess(a)
    print("\n========== DECISION ==========")
    print("Credit score  :", d["score"], "(300-900)")
    print("Risk band     :", d["band"])
    print("FOIR          :", format(d["foir"] * 100, ".1f") + "%")
    print("Score breakdown:")
    for factor in d["points"]:
        print("   " + format(factor, "10s") + " :", d["points"][factor])
    if d["approved"]:
        print("\nDECISION      : APPROVED")
        print("Interest rate :", d["rate"], "% per year")
        print("Monthly EMI   :", money(d["emi"]))
        total = d["emi"] * a["tenure"]
        print("Total interest:", money(total - a["loan_amount"]))
    else:
        print("\nDECISION      : REJECTED")
        print("Reason        :", d["reason"])


def option_generate():
    global DATASET
    print("\n--- GENERATE SYNTHETIC APPLICANTS ---")
    n = ask_int("How many applicants (50 to 5000): ", 50, 5000)
    seed = ask_int("Random seed (any number, same seed = same data): ", 1, 999999)
    DATASET = generate_applicants(n, seed)
    defaulters = 0
    for a in DATASET:
        if a["will_default"]:
            defaulters += 1
    print("\nGenerated", n, "applicants.")
    print("If everyone were approved, defaults would be", defaulters,
          "(" + format(100 * defaulters / n, ".1f") + "%)")


def option_policy_compare():
    if not need_dataset():
        return
    print("\n--- POLICY COMPARISON (cutoff score vs outcome) ---")
    print("Policies: risk-based interest rate vs one flat 12% rate")
    cutoffs = [300, 450, 550, 600, 650, 700, 750]
    for mode in (True, False):
        if mode:
            print("\n[RISK-BASED RATE: 9.5% / 12% / 15.5% by band]")
        else:
            print("\n[FLAT RATE: 12% for everyone]")
        print(" Cutoff | Approved | Approval% | Defaults | Default% |      Bank profit")
        print("--------+----------+-----------+----------+----------+------------------")
        best = None
        for c in cutoffs:
            s = run_policy(DATASET, c, mode)
            print(format(s["cutoff"], "7d") + " |" + format(s["approved"], "9d") +
                  " |" + format(s["approval_rate"], "9.1f") + "% |" +
                  format(s["defaults"], "9d") + " |" +
                  format(s["default_rate"], "7.1f") + "% |" +
                  format(s["profit"], "17,.0f"))
            if best is None or s["profit"] > best["profit"]:
                best = s
        print(">> Most profitable cutoff:", best["cutoff"],
              "with profit", money(best["profit"]))


def option_factor_analysis():
    if not need_dataset():
        return
    print("\n--- WHICH FACTOR PREDICTS DEFAULT BEST? ---")
    print("Default rate inside each group of applicants (all applicants, no policy)\n")

    groups = {
        "Past defaults = 0": lambda a: a["past_defaults"] == 0,
        "Past defaults >= 1": lambda a: a["past_defaults"] >= 1,
        "History < 3 years": lambda a: a["history_years"] < 3,
        "History >= 3 years": lambda a: a["history_years"] >= 3,
        "Age 25-55": lambda a: 25 <= a["age"] <= 55,
        "Age outside 25-55": lambda a: not (25 <= a["age"] <= 55),
        "Income < 40000": lambda a: a["income"] < 40000,
        "Income >= 40000": lambda a: a["income"] >= 40000,
        "Loan > 12x income": lambda a: a["loan_amount"] > 12 * a["income"],
        "Loan <= 12x income": lambda a: a["loan_amount"] <= 12 * a["income"],
    }
    results = []
    for name in groups:
        count = 0
        bad = 0
        for a in DATASET:
            if groups[name](a):
                count += 1
                if a["will_default"]:
                    bad += 1
        rate = 100.0 * bad / count if count > 0 else 0.0
        results.append((rate, name, count))
        print(format(name, "22s") + " : " + format(rate, "5.1f") + "% default  (" +
              str(count) + " applicants)")
    # largest default rate group
    worst = max(results)
    print("\nHighest-risk group:", worst[1], "->", format(worst[0], ".1f") + "%")


def option_topk():
    if not need_dataset():
        return
    print("\n--- TOP-K RISKIEST APPLICANTS ---")
    k = ask_int("Show how many (K): ", 1, len(DATASET))
    scores = []
    for a in DATASET:
        d = assess(a)
        scores.append(d["score"])
    kth = kth_smallest(scores, k)
    print("\nThe", k, "th lowest credit score is", kth)
    print("Applicants with score <= " + str(kth) + ":\n")
    print("    ID | Score | Defaults |   Income |   Loan amount | Band")
    print("-------+-------+----------+----------+---------------+----------------")
    shown = 0
    for a in DATASET:
        d = assess(a)
        if d["score"] <= kth and shown < k:
            print(format(a["id"], "6d") + " |" + format(d["score"], "6d") + " |" +
                  format(a["past_defaults"], "9d") + " |" +
                  format(a["income"], "9,d") + " |" +
                  format(int(a["loan_amount"]), "14,d") + " | " + d["band"])
            shown += 1


def option_efficiency():
    print("\n--- EFFICIENCY: NAIVE POWER vs FAST POWER ---")
    print("Counting multiplications needed for (1+r)^n\n")
    print("  Tenure n | Naive mults | Fast mults | Same answer?")
    print("-----------+-------------+------------+-------------")
    r = 0.01
    for n in [12, 24, 60, 120, 240, 360, 600]:
        a, ca = power_naive(1 + r, n)
        b, cb = power_fast(1 + r, n)
        same = abs(a - b) < 1e-9 * a
        print(format(n, "10d") + " |" + format(ca, "12d") + " |" +
              format(cb, "11d") + " | " + str(same))
    print("\nNaive grows like O(n); fast grows like O(log n).")


def option_verify():
    print("\n--- VERIFICATION: KNOWN TEST CASES ---")
    tests = [
        (500000, 10, 60, 10623.52),
        (100000, 12, 12, 8884.88),
        (1000000, 8, 120, 12132.76),
        (250000, 9, 36, 7949.93),
    ]
    print("  Principal | Rate | Months |  Expected |   Computed | Result")
    print("-----------+------+--------+-----------+------------+-------")
    passed = 0
    for p, r, n, expected in tests:
        got = emi_amount(p, r, n)
        ok = abs(got - expected) < 0.02
        if ok:
            passed += 1
        print(format(p, "10,d") + " |" + format(r, "5d") + " |" +
              format(n, "7d") + " |" + format(expected, "10.2f") + " |" +
              format(got, "11.2f") + " | " + ("PASS" if ok else "FAIL"))
    print("\nPassed", passed, "of", len(tests))


# ---------------------------------------------------------------
# 9. MAIN MENU (top-down design)
# ---------------------------------------------------------------
def main():
    print("=" * 56)
    print("   LOAN APPROVAL ENGINE: EMI + CREDIT RISK SCORER")
    print("=" * 56)
    while True:
        print("\nMAIN MENU")
        print(" 1. EMI calculator")
        print(" 2. Repayment schedule")
        print(" 3. Assess one applicant (enter details)")
        print(" 4. Verification with known test cases")
        print(" 5. Generate synthetic applicants (dataset)")
        print(" 6. Policy comparison: cutoff score vs profit")
        print(" 7. Factor analysis: what predicts default?")
        print(" 8. Top-K riskiest applicants")
        print(" 9. Efficiency: naive vs fast power")
        print(" 0. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            option_emi()
        elif choice == "2":
            option_schedule()
        elif choice == "3":
            option_assess()
        elif choice == "4":
            option_verify()
        elif choice == "5":
            option_generate()
        elif choice == "6":
            option_policy_compare()
        elif choice == "7":
            option_factor_analysis()
        elif choice == "8":
            option_topk()
        elif choice == "9":
            option_efficiency()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Enter a number from 0 to 9.")


if __name__ == "__main__":
    main()
