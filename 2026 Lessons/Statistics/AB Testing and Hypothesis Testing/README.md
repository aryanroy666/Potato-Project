# A/B Testing & Hypothesis Testing

**Tools:** Python, NumPy, SciPy

**File:** [`AB Testing & Hypothesis Testing.py`](./AB%20Testing%20&%20Hypothesis%20Testing.py)

## What I Learned

An A/B test answers one business question: **"Did my change really work, or was I just lucky?"** Hypothesis testing is the maths that separates a real effect from random noise.

The scenario: an e-commerce site tests a new "Buy Now" button (Variant B) against the current one (Control A). The script simulates the experiment data, runs the tests, and ends with a business recommendation.

## The Core Idea: A Court Trial

| Trial | Hypothesis test |
|-------|-----------------|
| "Innocent until proven guilty" | **Null hypothesis (H0):** the new button has no effect |
| The prosecution's claim | **Alternative hypothesis (H1):** the new button changes conversion |
| Strength of the evidence | **p-value** |
| Level of proof required ("beyond reasonable doubt") | **Significance level (alpha), usually 0.05** |
| Verdict | Reject H0 or fail to reject H0 |

Note the wording: we **fail to reject** H0, we never "prove" it. A court says "not guilty", not "innocent".

## What the Script Does

| Step | Method | Purpose |
|------|--------|---------|
| 1 | State H0 and H1 | Decide the question **before** seeing results |
| 2 | Two-proportion z-test (by hand, cross-checked with chi-square) | Test a yes/no metric like conversion rate |
| 3 | 95% confidence interval | Estimate **how big** the lift could be |
| 4 | Welch's t-test and Cohen's d | Test a numeric metric like revenue per user, and measure effect size |
| 5 | Sample size calculation | Plan how many users are needed **before** the test |
| 6 | Peeking simulation | Show why stopping a test early inflates false alarms |
| 7 | Business summary | Turn statistics into a recommendation |

## Results From the Simulated Data (seed 42)

| Metric | Control A | Variant B | Result |
|--------|-----------|-----------|--------|
| Conversion rate | 9.86% | 11.80% | z = 3.12, p = 0.0018, significant |
| 95% CI for the difference | | | 0.72 to 3.16 percentage points |
| Revenue per user | 49.45 | 52.66 | p < 0.0001, but Cohen's d = 0.14 (small) |
| False alarm rate, one look at the end | | | 5.8% (about the expected 5%) |
| False alarm rate, peeking 10 times | | | 19.6% |

The data is simulated, so these numbers describe the exercise only, not a real business.

## Key Concepts and Interview Points

**What a p-value really means.** It is the probability of seeing a difference at least this large **if H0 were true**. It is **not** the probability that H0 is true, and not the probability that the result is a fluke. This is the most common misunderstanding, and interviewers love to test it.

**Statistically significant is not the same as practically important.** The revenue test has a tiny p-value, but Cohen's d is only 0.14, a small effect. With enough users, almost any tiny difference becomes "significant". Always report effect size and a confidence interval, then ask whether the lift is worth the cost of the change.

**Confidence interval beats p-value for decisions.** The p-value says *whether* there is an effect. The interval says *how big* it could be. A good answer in an interview: *"I'd roll out B only if the lower end of the interval is still worth the engineering cost."*

**Type I and Type II errors.**

| Error | Meaning | Analogy |
|-------|---------|---------|
| Type I (false positive), probability = alpha | Declaring an effect that is not real | Convicting an innocent person |
| Type II (false negative), probability = 1 − power | Missing an effect that is real | Letting a guilty person go free |

**Power and sample size.** Power is the chance of detecting a real effect (80% is the common target). The smaller the lift you want to detect, the more users you need: in the script, detecting +1 percentage point needs about 14 times more users than detecting +4. You cannot judge a coin's fairness from 10 flips.

**The peeking problem.** Checking results every day and stopping at the first p < 0.05 is like re-rolling a die until you get a six. In the simulation, with no real difference at all, peeking 10 times pushed the false alarm rate from about 5% to nearly 20%. The fix: fix the sample size in advance and do not stop early (or use sequential testing methods designed for early stopping).

**Which test to use.**

| Metric type | Example | Test |
|-------------|---------|------|
| Yes/no (proportion) | Converted or not | Two-proportion z-test or chi-square |
| Numeric, two groups | Revenue per user | Welch's t-test |

Welch's version is the safer default because it does not assume equal variance in both groups.

**Pooled vs unpooled standard error.** The z-test pools both groups because it assumes H0 is true (one shared rate). The confidence interval does not pool, because it estimates the actual difference without that assumption.

## How to Run

```bash
pip install numpy scipy
python "AB Testing & Hypothesis Testing.py"
```

The random seed is fixed, so your output matches the table above.

## Next Steps

- Add a plot of the two conversion rates with confidence interval error bars
- Try a one-sided test and discuss when it is appropriate
- Explore multiple testing (testing many variants) and the Bonferroni correction
- Re-run the same analysis in SQL to compute conversion rates by group
