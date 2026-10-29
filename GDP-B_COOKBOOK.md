# The GDP-B Cookbook

**A practical guide to survey design, valuation, aggregation, and GDP-B growth accounting.**

Revised October 29, 2026.

This guide brings together the economic framework, practical survey and estimation choices, historical applications, and a runnable synthetic example. Source and version notes appear in Appendix A.

### Contents

- [1. What GDP-B measures and how to use this guide](#1-what-gdp-b-measures-and-how-to-use-this-guide)
- [2. The economic framework](#2-the-economic-framework)
- [3. Survey design: Measuring the value of access](#3-survey-design-measuring-the-value-of-access)
- [4. Estimation: Estimate the distribution of WTA](#4-estimation-estimate-the-distribution-of-wta)
- [5. Aggregation: From WTA to population values and GDP-B growth](#5-aggregation-from-wta-to-population-values-and-gdp-b-growth)
- [6. Interpretation and limitations](#6-interpretation-and-limitations)
- [7. Optional extension: SurplusGPT and large-scale predictions](#7-optional-extension-surplusgpt-and-large-scale-predictions)
- [8. Implementation: A reproducible example and the `gdpb` project](#8-implementation-a-reproducible-example-and-the-gdpb-project)
- [9. Methodological checklist](#9-methodological-checklist)
- [10. References](#10-references)
- [Appendix A. Source and version notes](#appendix-a-source-and-version-notes)
- [Appendix B. Complete runnable example](#appendix-b-complete-runnable-example)

---

## 1. What GDP-B measures and how to use this guide

GDP measures economic production, but it does not capture all the benefits people receive from products and services. This is especially important for free digital products, such as search engines, maps, and messaging apps. These products generate economic activity that may be included in GDP, but the value they provide to consumers is not fully captured.

**GDP-B** is a framework for measuring these additional consumer benefits and understanding how they contribute to economic growth. The “B” stands for benefits.

The framework was developed by Brynjolfsson, Collis, Diewert, Eggers, and Fox in a [2019 NBER working paper](https://www.nber.org/papers/w25695) and published in [*American Economic Journal: Macroeconomics*](https://www.aeaweb.org/articles?id=10.1257/mac.20210319) in 2025.

GDP-B complements official GDP. It does not replace it.

### 1.1 Three things we can measure

The main method is a **willingness-to-accept (WTA) survey**. Respondents are offered money to give up access to a product for a specified period. By comparing responses to different payment amounts, we estimate how much people value access.

The results can be used in three different ways:

| Measure | What it tells us | How to calculate it |
|---|---|---|
| **Value to a typical user** | How much compensation would persuade half of users to give up access? | Median WTA |
| **Total consumer value** | How much compensation would users require in total? | Average WTA × number of users |
| **GDP-B growth adjustment** | How much does a change in product availability or value contribute to economic growth? | Apply the appropriate GDP-B calculation using valuations from the relevant periods |

**Use the median to describe a typical user and the mean to calculate total value.**

If average WTA is capped at a maximum amount, clearly label the resulting total as a capped estimate.

Importantly, a product's total consumer value is not the same as its contribution to GDP growth.

WTA also differs from willingness to pay. It measures the compensation someone would require to lose access, not how much they would spend to obtain the product.

For paid products, the survey must specify whether subscription fees or other payments continue during the period without access.

### 1.2 The main steps

The GDP-B measurement process has five steps:

1. **Define what we are measuring.** Specify the product, target population, usage period, length of access restriction, available alternatives, and treatment of existing payments.

2. **Collect survey responses.** Ask about product usage before mentioning compensation. Randomly assign one payment amount per respondent and product, then record whether the respondent accepts or rejects the offer.

3. **Estimate WTA.** Calculate median and average WTA, report uncertainty, and check whether the estimates are supported by the survey data. Clearly state any cap on average WTA.

4. **Calculate total value.** Combine average WTA with the estimated number of users. Make sure the survey, adoption rates, and population figures use consistent definitions. Explain any assumptions used to convert monthly valuations into annual estimates.

5. **Check and interpret the results.** Test how estimates change with different assumptions, survey designs, and statistical models. Account for interactions between products. Calculate GDP-B growth only when the necessary historical and economic data are available.

Sections 3–6 explain these steps in detail.

Section 7 introduces SurplusGPT, an optional extension that uses large language models to predict valuations when survey data are limited. LLMs are not required to measure GDP-B, and their predictions must be validated against human responses.

Section 8 covers implementation, and Section 9 provides a practical checklist.

### 1.3 Which valuations can be used in GDP-B?

Surveys can estimate the value of many kinds of products, but **not every estimated value can simply be added to GDP**.

Different products require different treatments:

| Product type | How to interpret its value |
|---|---|
| **Existing paid products** | WTA measures the value of access under the survey scenario. The full amount cannot automatically be added to GDP because some of the product's value is already reflected in market activity. |
| **Free products** | WTA can help measure benefits not fully captured by GDP, provided users, access restrictions, and substitutes are defined consistently. |
| **New paid products** | We need to estimate the additional benefits from introducing the product, beyond the spending already included in GDP. |
| **Product improvements** | We need to compare clearly defined versions or features and account for improvements already reflected in official economic statistics. |

This distinction matters when surveys include both digital services and essential goods, such as electricity or running water.

People may require very large payments to give up essential services. These valuations tell us how much respondents value access under the specific survey conditions, but they do not mean that an equally large amount is missing from GDP.

## 2. The economic framework

GDP-B extends conventional GDP by accounting for consumer benefits that are not fully captured by market spending, especially from new and free products.

This section explains the main calculations. We use our own equation numbers (T1–T13). The full derivations are in Brynjolfsson et al. (2019, 2025).

### 2.1 Existing products: Spending and consumer welfare

Conventional GDP measures spending on goods and services. However, spending does not necessarily capture the full benefits consumers receive.

In economic theory, the **expenditure function** measures the minimum amount someone needs to spend to reach a given level of well-being (utility):

$$
C(u,p)=\min_{q\geq0}\{p\cdot q:f(q)\geq u\}. \tag{T1}
$$

Here, \(u\) is utility, \(p\) represents prices, and \(q\) represents quantities. Assuming consumers choose their spending optimally, observed spending equals the minimum cost of reaching their observed utility.

We can measure changes in welfare by comparing the cost of reaching different utility levels while holding prices fixed.

Two standard measures are:

$$
Q_E=C(u^1,p^0)-C(u^0,p^0),
\qquad
Q_C=C(u^1,p^1)-C(u^0,p^1). \tag{T2}
$$

The first uses prices from the earlier period, while the second uses prices from the later period. They can differ because prices change over time.

Since utility cannot be observed directly, researchers often use changes in purchased quantities.

The **Laspeyres measure** values quantity changes at the earlier prices, while the **Paasche measure** uses the later prices:

$$
V_L=p^0\cdot(q^1-q^0),\qquad
V_P=p^1\cdot(q^1-q^0). \tag{T3}
$$

The **Bennet measure** takes the average of the two:

$$
V_B=\tfrac12(p^0+p^1)\cdot(q^1-q^0)
=V_L+\tfrac12(p^1-p^0)\cdot(q^1-q^0). \tag{T4}
$$

Under the particular assumptions discussed by Diewert and Mizobuchi (2009), this equals the average of the two welfare measures in equation T2. That relationship does not hold automatically under every model of consumer preferences.

An important accounting identity is:

$$
p^1\cdot q^1-p^0\cdot q^0
=V_B+\tfrac12(q^0+q^1)\cdot(p^1-p^0). \tag{T5}
$$

In plain English, **the change in total spending can be separated into a quantity component and a price component**.

When comparing different years, prices must also be adjusted to a common purchasing-power basis before interpreting quantity changes as changes in real welfare.

### 2.2 New products: Estimating the value of introduction

New products create a measurement problem because they did not exist in the earlier period.

One approach uses a **reservation price**: the hypothetical price high enough that consumers would choose not to buy the product.

Suppose a new product was unavailable in period 0 and becomes available in period 1.

Let \(r_n^0\) be its reservation price before introduction, \(p_n^1\) its actual price after introduction, and \(q_n^1\) the quantity purchased.

Let \(\gamma=CPI_1/CPI_0\) adjust earlier prices into later purchasing-power units.

The new product's contribution under the Bennet approach is:

$$
\tfrac12(\gamma r_n^0+p_n^1)q_n^1
=p_n^1q_n^1+\tfrac12(\gamma r_n^0-p_n^1)q_n^1. \tag{T6}
$$

This separates two components:

- **Market spending:** What consumers actually pay, already captured in conventional GDP.
- **Additional consumer value:** The estimated benefit from having access to the new product, beyond market spending.

The GDP-B framework uses this adjustment to construct an expanded growth index.

Let \(Q^F\) be the conventional Fisher quantity index, \(Y_0\) baseline nominal GDP, \(P^F\) the Fisher price-index ratio, and \(\mathcal P^F=P^F/\gamma\). Then:

$$
G_N=Q^F+
\frac{(\gamma r_n^0-p_n^1)q_n^1}
{\gamma Y_0(1+\mathcal P^F)}. \tag{T7}
$$

This is a **growth index**, where 1 means no growth. To express it as a growth rate, subtract 1.

The calculation requires consistent information about prices, quantities, product definitions, and what is already included in GDP. It does not mean that all estimated consumer benefits can simply be added to GDP.

**The main challenge is estimating the reservation price.** Surveys usually observe responses to a limited range of compensation amounts, so estimating the price at which demand disappears requires extrapolation.

Researchers should report the model used, the observed payment range, uncertainty, and how sensitive the results are to different assumptions. Valid responses should not be removed simply because they produce inconvenient estimates.

There is also an important historical limitation. The value of a product today reflects its current features and user network. Converting today's valuation into earlier-year dollars does not tell us what the product was worth when it first launched.

### 2.3 Free products: Measuring benefits without market prices

Free products, such as free search engines or messaging services, can provide substantial consumer value even when users pay nothing.

To measure this value, we consider how much compensation people would need to lose access.

Let \(z\) represent access to free products. The conditional expenditure function is:

$$
c(u,p,z)=\min_{q\geq0}\{p\cdot q:f(q,z)\geq u\}. \tag{T8}
$$

This measures the minimum spending needed to reach utility \(u\), given access to free products \(z\).

The compensation required to lose access to the entire specified bundle is:

$$
W_A(u,p,z)=c(u,p,0)-c(u,p,z). \tag{T9}
$$

This is the **willingness to accept (WTA)** for losing access while maintaining the original level of well-being.

If the experiment removes only some products, the calculation should reflect the access that remains available.

WTA is different from willingness to pay (WTP) for gaining access. The two use different starting situations and need not produce the same valuation.

We can also define the **marginal value** of free-product access:

$$
w(u,p,z)=-\nabla_z c(u,p,z). \tag{T10}
$$

This measures the value of a small change in access. For a sufficiently small reduction \(\Delta z\), compensation is approximately \(w\cdot\Delta z\).

However, giving up an entire service for one month is not necessarily a small change. We therefore should not automatically calculate its value by multiplying the marginal value by the amount of access lost.

The [later manuscript hosted by the Australian Bureau of Statistics](https://www.abs.gov.au/system/files/documents/9d03e643ba44abb61eefe972765b3c67/Fox%20-%20The%20digital%20economy%2C%20welfare%20and%20productivity%20growth.pdf) also distinguishes the value of losing an entire product from its marginal value.

The broader GDP-B framework can account for both existing and newly introduced free products. However, the combined equation 31 in the 2019 working paper contains an inflation adjustment that differs from an earlier expression.

For that reason, we do not use that equation directly in this cookbook. A full implementation would need to resolve the difference using the original derivation.

Instead, we use the simpler total-income approach below.

### 2.4 The total-income approach

The total-income approach adds the estimated consumer value of free products to conventional GDP.

Let:

- \(Y_t\) be nominal GDP in period \(t\).
- \(M_t\) be the estimated annual compensation required to give up the specified free products, expressed in the same currency as GDP.
- \(T_t\) be total income, including those benefits.

Then:

$$
T_t=Y_t+M_t. \tag{T11}
$$

The products and population included in \(M_t\) must be defined consistently across periods.

Importantly, the value of several products together is not necessarily the sum of their individual values. Products may be substitutes or complements. When estimating the value of a bundle, we need to account for these relationships.

**Calculating real growth**

To compare total income across periods, adjust for inflation.

Let \(D=P_1/P_0\) be the ratio of GDP deflators. Then:

$$
G_{B,T}=\frac{T_1/T_0}{D},\qquad
g_{B,T}=G_{B,T}-1. \tag{T12}
$$

Here, \(G_{B,T}\) is the real growth index, and \(g_{B,T}\) is the corresponding growth rate.

For example, if the deflator rises from 100 to 130, enter \(D=1.30\), not 130.

For comparisons spanning several years, calculate the compound annual growth rate:

$$
g_{B,T}^{annual}=G_{B,T}^{1/n}-1. \tag{T13}
$$

where \(n\) is the number of years.

Use the same periods and inflation adjustment when calculating conventional GDP growth for comparison. Section 5 explains why compound annual growth rates and average annual percentage-point adjustments are not identical measures.

**What value should we use in the starting period?**

If the particular product or bundle did not exist in period 0, its starting value is zero:

$$
M_0=0,\qquad T_0=Y_0.
$$

This does not mean that all free products were absent from the economy. It only applies to the specific products included in the calculation.

If those products already existed in period 0, we must estimate their value in that period as well.

**Assumptions and limitations**

The main advantage of the total-income approach is that it does not require estimating a hypothetical reservation price before a product existed.

However, the results still depend on survey valuations, adoption estimates, annualization, and inflation adjustments.

Under certain assumptions, including that the official GDP deflator overstates the relevant inflation, the framework can support a lower-bound interpretation of welfare growth. But this does not mean every empirical GDP-B estimate is conservative. Survey and modeling errors can make estimates either too high or too low.

**Productivity-B**

The same framework can be extended to productivity.

Productivity-B measures growth in GDP-B output relative to growth in hours worked. To calculate it, divide the GDP-B quantity-growth index by the hours-worked growth index.

Use growth indexes for both quantities, not a growth index divided by the level of hours worked.

## 3. Survey design: Measuring the value of access

### 3.1 Clearly define what respondents would give up

Before asking people how much compensation they would accept, we need to define exactly what they would lose access to and for how long.

| Design choice | What to specify |
|---|---|
| **Product** | A specific product, feature, or category of services. |
| **Access** | Which accounts, devices, household members, and activities are covered. Can respondents use downloaded content or access the product indirectly? |
| **Duration** | When access stops and when it resumes. |
| **Alternatives** | Whether respondents can use competing products or substitutes. |
| **Existing payments** | For paid services, whether subscriptions continue, are paused, or are refunded. |
| **Compensation** | How much respondents receive, when they are paid, and under what conditions. |

These details matter. For example, giving up Facebook while keeping other social networks is different from giving up all social media. Similarly, losing access to a paid service while continuing to pay for it is different from having the subscription canceled.

Keep these definitions consistent across survey waves.

**Measure usage before asking about compensation.** First, ask whether respondents have used the product during a defined period, such as the past month. Then ask eligible users the valuation question.

Estimate adoption using the full survey sample, with appropriate weights, or from an external source that measures the same population and definition of usage.

A "Don't Use" option in the valuation question is useful but should not replace a separate usage question. Nonusers might accept a large payment rather than select "Don't Use." They may also value having the option to use a service in the future.

Assuming that nonusers have zero WTA is therefore a simplifying assumption that should be stated explicitly (see Section 5).

### 3.2 Randomly assign one offer per respondent and product

The main survey method used in this cookbook is **single binary discrete choice (SBDC)**.

Each eligible respondent receives one randomly selected compensation offer for each product and answers whether they would accept it.

A standard question is:

> Would you give up access to {item_name} for one month starting tomorrow morning in exchange for ${payment}?

Explain the access restrictions before asking this question.

Eligible users answer **Yes** or **No**. Missing answers, refusals, and responses from ineligible participants should be recorded separately.

Different respondents receive different payment amounts. By comparing acceptance rates across payments, we can estimate how much compensation people require to give up access.

Respondents may evaluate several products, but under this design they should receive only one offer per product. Randomize the order of products, avoid overly long surveys, and keep respondent IDs so that repeated responses from the same person can be accounted for in the analysis.

**Examples from previous studies:**

**Facebook (2016–2017).** The original GDP-B study surveyed 2,885 respondents using payments of $1, $10, $20, $30, $40, $50, $60, $70, $80, $90, $100, and $1,000. Each payment amount was shown to at least 200 respondents (Brynjolfsson et al., 2019).

**Generative AI (2025–2026).** The survey asked:

> Would you give up access to all AI tools like ChatGPT, Gemini, Claude, or Copilot for one month starting tomorrow morning in exchange for [USD]?

The payment amounts were $1, $10, $20, $50, $100, $200, and $500 (Brynjolfsson et al., 2026).

**GDP-B Waves 1 and 2.** The project description reports 423 products in Wave 1, with Yes/No responses, and 417 products in Wave 2, which added a "Don't Use" option.

The actual questionnaires and product lists should be saved alongside the data and code.

Comparisons across waves require consistent product and user definitions. In particular, if Wave 1 did not separately identify users, its overall responses cannot be directly compared with Wave 2's responses among users.

Where possible, use additional usage information, a sample that answers both versions, or sensitivity checks to make the comparison more reliable.

### 3.3 Choose the sample and payment amounts carefully

Start by defining the population the study is intended to represent. The survey sample and weights should reflect that population, including relevant age groups, geography, and demographics.

Matching the population on observable characteristics can improve representativeness, but it does not eliminate all selection bias. Also, a sample of product users should represent users, not necessarily the demographic composition of all adults.

**Choosing payment amounts.** Payments should cover a reasonable range of possible valuations, with enough observations near the expected median and at higher amounts to estimate the capped mean.

A pilot survey or earlier wave can help determine the range. Larger gaps between higher payment amounts are often practical, but payments do not need to follow an exact mathematical spacing rule.

There is no universal requirement to collect 200 responses at every payment amount.

For example, with 423 products and seven payment amounts, collecting 200 responses for every product-payment combination would require 592,200 product evaluations.

The required sample size depends on the number of products, expected adoption rates, desired precision, subgroup comparisons, and whether information will be combined across products.

Importantly, **product evaluations are not the same as unique respondents**, since one person may evaluate several products.

If an initial survey shows that payments are too high or too low, adjust the range in a later wave. Keep some overlapping payment amounts when possible to support comparisons.

The cap used to report average WTA should remain consistent across waves, after accounting for inflation, even if the experimental payment amounts change (see Section 4.3).

**Data quality.** Decide on exclusion rules before looking at the valuation results. Possible checks include duplicate responses, unusually fast completion, failed attention questions, and responses to a fictitious product.

Report how many observations each rule removes and the payment amounts assigned to those observations.

Do not automatically exclude people who reject high compensation offers. Such responses may reflect genuinely high valuations.

### 3.4 Make compensation offers credible

Where feasible, make some survey choices real rather than hypothetical.

For example, randomly select a subset of respondents who will actually receive compensation if they agree to give up access.

Before they answer, explain how selection works, how much they would receive, what restrictions apply, and how compliance will be checked.

If respondents evaluate several products, explain which choice could become binding and how it will be selected.

Earlier studies used methods such as checking Facebook activity, restricting account access, and placing tamper-evident seals on smartphone cameras. These are examples from earlier research, not necessarily methods that remain practical today (Brynjolfsson et al., 2019).

Any real-world experiment needs informed consent, reliable payment procedures, and a practical way to verify compliance.

If actual restrictions cannot be enforced, clearly describe the survey as **hypothetical**.

This distinction matters when comparing results over time. Changes in responses may reflect changes in valuations, but they may also reflect survey wording, sample composition, or how seriously respondents take hypothetical offers.

Simply telling respondents that choices might have consequences is not enough if there is no credible way to carry them out.

### 3.5 Other ways to measure valuations

SBDC is the main method in this cookbook, but other approaches may be useful for specific research questions.

**Becker–DeGroot–Marschak (BDM).** Respondents state the minimum payment they would accept to give up a product. The researcher then randomly draws a payment amount.

If the drawn payment meets or exceeds the respondent's stated minimum, the respondent gives up access and receives the drawn amount.

Under the standard assumptions, respondents have an incentive to report their true minimum compensation.

The method should be explained clearly, and respondents should demonstrate that they understand how it works.

People often report round numbers, such as $50 or $100. If these responses are smoothed or adjusted, report both the original and adjusted results.

BDM can be useful for valuing specific features or products when real compensation and access restrictions are feasible (Becker, DeGroot, and Marschak, 1964).

**Best–worst scaling (BWS).** Respondents see groups of products and choose which they value most and least.

This approach is useful when comparing many products or establishing their relative importance.

Monetary options can be included to help translate these rankings into dollar values, but doing so requires additional assumptions.

If BWS and SBDC produce similar product rankings, that supports agreement about relative value. It does not necessarily mean they produce the same dollar valuations (Brynjolfsson, Collis, and Eggers, 2019).

**Finally, the duration of access loss matters for every method.** The compensation required to give up a product for one year may not equal twelve times the compensation required for one month.

Section 5 explains the difference between multiplying monthly valuations by 12 and directly measuring annual WTA.

## 4. Estimation: Estimate the distribution of WTA

### 4.1 What we learn from yes/no responses

In the survey, each respondent is offered a payment in exchange for giving up access to a product or service. Their response tells us something about their willingness to accept (WTA), but not its exact value.

Let:

- \(W_i\) be respondent \(i\)'s WTA, assumed to be nonnegative.
- \(p_i>0\) be the payment offered to that respondent.
- \(Y_i=1\) if the respondent accepts the offer, and \(Y_i=0\) if they reject it.

Assuming each person has a stable minimum acceptable payment:

$$
Y_i=1\Rightarrow W_i\leq p_i,
\qquad
Y_i=0\Rightarrow W_i>p_i.
\tag{E1}
$$

In other words, accepting $50 tells us that a person's WTA is at most $50. Rejecting $50 tells us it is greater than $50. Neither response reveals the exact amount.

Statisticians call these **current-status or interval-censored data**. We know whether WTA is above or below the offered amount, but not its exact value.

To estimate the distribution of WTA, we use the probability of accepting each payment. For a proposed WTA distribution \(F_W\), each response contributes:

$$
L_i=F_W(p_i)^{Y_i}\{1-F_W(p_i)\}^{1-Y_i}
\tag{E2}
$$

This simply means that accepted offers contribute their predicted acceptance probability, while rejected offers contribute their predicted rejection probability.

Because payments are randomly assigned, we can use responses at different amounts to estimate the WTA distribution. The analysis should cover the intended population and use survey weights where appropriate.

**Important:** Do not assume that accepting an offer means the respondent's WTA equals that payment. A standard Kaplan–Meier estimator that treats accepted offers as exact WTA values is not appropriate. Use a method designed for interval-censored data instead.

For example, the Python package `lifelines` provides Turnbull estimation through [`fit_interval_censoring()`](https://lifelines.readthedocs.io/en/stable/fitters/univariate/KaplanMeierFitter.html), even though the function is part of a class named `KaplanMeierFitter`.

### 4.2 Estimate the acceptance curve and median WTA

A simple starting point is to model how the probability of accepting an offer changes with the payment amount.

One common approach is **logit regression using the logarithm of the offered payment**, consistent with the discrete-choice valuation approach discussed by Hanemann (1984):

$$
F_W(p)=\Pr(Y=1\mid p)=\Lambda(\alpha+\beta\ln p),
\qquad \beta>0.
\tag{E3}
$$

Here, \(\Lambda\) is the logistic function, and \(\beta>0\) ensures that acceptance becomes more likely as compensation increases.

A probit model works similarly but uses the standard normal distribution instead of the logistic function.

For either model, median WTA is:

$$
\widehat m=\exp(-\widehat\alpha/\widehat\beta).
\tag{E4}
$$

The median is the compensation amount at which the model predicts that 50% of users would accept the offer.

Report the median together with its confidence interval and the range of payments actually offered in the survey.

Before relying on the estimate, check that the model fits properly, that acceptance increases with payment, and that the data contain enough information to identify the median.

If acceptance changes very little across payment amounts, the median can be highly uncertain. If the estimated median falls outside the range of payments offered, clearly label it as an **extrapolated estimate**, rather than a value directly supported by the survey.

A few additional points matter:

- If the survey includes offers of $0, use a model that can handle zero explicitly. Do not take the logarithm of zero or replace it with an arbitrary small number.
- If some users genuinely have zero WTA, consider a model that allows a share of respondents to have exactly zero valuation.
- Compare the model's predicted acceptance rates with the actual acceptance rates at each payment.
- Similar median estimates from logit and probit do not mean that the models give similar estimates for very high valuations.

In particular, logit regression on log payment implies a log-logistic WTA distribution. Its unrestricted mean is finite only when \(\beta>1\). This is one reason to use a clearly defined cap when calculating average WTA.

### 4.3 Calculate average WTA using a cap

For estimating total economic value, we generally need **average WTA**, rather than median WTA.

However, very high valuations can strongly affect the average, especially when the survey contains relatively few large compensation offers.

A common approach is to set a maximum value, or **cap**, for each respondent's WTA.

For example, if we use a $500 cap, anyone with an estimated WTA above $500 contributes $500 to the average.

For nonnegative WTA, the capped mean is:

$$
\mu_c=E[\min(W,c)]
=\int_0^c[1-F_W(p)]\,dp.
\tag{E5}
$$

Here, \(c\) is the cap, and \(F_W(p)\) is the estimated acceptance curve.

The integral calculates average WTA up to the chosen cap. This is different from calculating the average only among people whose WTA is below the cap.

Report the estimate clearly, for example:

**Mean monthly WTA, capped at $500.**

The choice of cap matters:

- **Within a study:** The cap can equal the highest payment offered, but it should be specified separately from the experimental payment grid.
- **Across survey waves:** Use the same cap so results are comparable.
- **Across years:** Account for inflation. A $500 cap in different years does not represent the same purchasing power.
- **Above the observed range:** A cap higher than the largest payment offered requires additional assumptions about high valuations.

The fitted model also estimates WTA below the smallest positive payment offered. These estimates depend on the model's assumptions, which should be explained when they matter for the results.

Increasing the cap can increase estimated average WTA even when the underlying responses have not changed. Always report how sensitive the results are to the cap.

The true capped population mean cannot exceed the true unrestricted mean, assuming nonnegative WTA. However, an estimated capped mean is **not automatically a statistical lower bound** on the true mean or total welfare.

Report confidence intervals and show how results change with different models and caps. Estimating the unrestricted mean requires additional assumptions about high valuations beyond the survey's payment range.

### 4.4 Alternative models when data are limited

The logit model is a useful starting point, but it should not be the only approach considered.

Several alternatives can help assess whether the results depend too heavily on modeling assumptions:

- **Isotonic estimation:** Estimates acceptance rates while requiring them to increase, or at least not decrease, as payment increases. It provides a flexible check on the logit or probit estimates.
- **Turnbull estimation:** Estimates the WTA distribution directly from the ranges revealed by respondents' yes/no answers, without assuming a particular distribution. Sometimes the data identify a range of possible medians rather than one exact value.
- **Other parametric models:** Weibull, log-normal, and log-logistic models offer alternative assumptions about the WTA distribution. They can include respondent characteristics, but must be estimated using methods appropriate for censored responses.
- **Hierarchical models:** Combine information across products or respondent groups. This can improve estimates when some groups have few observations, but results depend on how information is shared and on the model's assumptions. Section 7 discusses their use in SurplusGPT.

With a limited set of payment amounts, the survey often tells us only that median WTA falls between two offers. A statistical model then provides a more precise estimate.

For example, if acceptance is below 50% at $20 but above 50% at $50, the median is likely somewhere between those amounts.

If acceptance already exceeds 50% at the smallest offer, the median may be below the tested range. If acceptance never reaches 50%, it may be above the largest offer.

These conclusions are also subject to sampling uncertainty. Report whether the median is supported by the observed range, requires extrapolation, or cannot be estimated reliably.

### 4.5 How WTA varies across respondents

We may also want to understand whether valuations differ by age, income, education, product usage, or other characteristics.

To do this, extend the logit or probit model to include respondent characteristics:

$$
\Pr(Y=1\mid p,x)=F(\alpha+\beta\ln p+x'\delta).
\tag{E6}
$$

Here, \(x\) represents the respondent characteristics, and \(F\) is either the logistic or standard normal cumulative distribution function.

The estimated median WTA for someone with characteristics \(x\) is:

$$
m(x)=\exp[-(\alpha+x'\delta)/\beta].
\tag{E7}
$$

This allows us to compare predicted valuations across groups.

For example, we might estimate median WTA for frequent users and occasional users, or compare people who pay for a service with those who use its free version.

If we want to report differences in dollars, we should calculate the predicted WTA for each group and compare those values directly. A change in acceptance probability is not the same as a change in WTA measured in dollars.

Also, averaging the median WTA estimates across individuals does not generally give the median of the full population.

These comparisons describe **associations**, not necessarily causal effects. For example, frequent users may have higher WTA, but that does not prove that increasing someone's usage would raise their valuation by the estimated amount.

Randomizing the compensation offers helps identify the acceptance curve. It does not make demographic characteristics or usage patterns randomly assigned.

### 4.6 Report uncertainty and check robustness

All WTA estimates contain statistical uncertainty. Use bootstrapping or another appropriate method to calculate confidence intervals for both median and capped mean WTA.

Bootstrapping means repeatedly drawing samples from the data and re-estimating the model to see how much the results vary.

If respondents evaluate several products, keep all responses from the same person together when resampling. If the survey uses a more complex sampling design, account for that design or use the provided replicate weights.

When adoption rates and valuations come from the same survey, estimate their uncertainty together. When adoption estimates come from another source, include their uncertainty when possible.

For each product, retain the following information:

- **Survey data:** Number of respondents and users, survey weights, payment amounts, and acceptance rates at each amount.
- **Model results:** Estimation method, cap, model fit diagnostics, slope, median WTA, capped mean WTA, and confidence intervals.
- **Reliability of the estimate:** Whether the median falls within the tested payment range, below it, above it, or cannot be estimated reliably.
- **Sensitivity checks:** How results change when using different models, caps, exclusions, or assumptions about combining information across groups.

Use clear, interpretable diagnostics rather than an unexplained `reliability_score`. If a summary reliability score is useful, publish exactly how it is calculated and what its categories mean.

Any summary of estimation quality should account for every product, including those with failed estimates or missing results.

**Handling extreme estimates.** Do not automatically apply winsorization, which limits unusually high or low estimated values.

First check whether extreme results reflect data problems or models that are poorly identified.

If values are capped or adjusted, explain what was changed, the threshold used, and why. Keep the original estimates and report how much the adjustment changes the results.

Even if only a small share of estimates is affected, those estimates may account for a large part of the total economic value.

This type of adjustment to estimates or training data is different from the reporting cap used to calculate average WTA in Section 4.3. The two should be documented separately.

### 4.7 Reservation prices require a separate calculation

A **reservation price** is the price at which demand for a product falls to zero. It is not the same as median WTA.

Estimating a reservation price from a loss-of-access survey requires additional assumptions about consumer demand, the product being valued, and what alternatives are available.

The original GDP-B Facebook application estimated a relationship between compensation and willingness to retain access, then extended that relationship beyond the observed data.

The resulting estimates were sensitive to which observations were included.

For a new application, researchers should:

- Explain the model used to estimate the reservation price.
- Identify where the calculation goes beyond observed survey data.
- Report uncertainty and test how results change with different assumptions and extreme payment amounts.
- Avoid removing valid randomized offers simply because they make the model fit less well.

An additional concern is how products change over time. For example, adjusting today's Facebook valuation into 2004 dollars does not tell us what Facebook was worth in 2004. The product, its features, and its user network were different.

Finally, some statistical models allow WTA to extend indefinitely upward. This does not mean that the data identify a specific finite reservation price.

If the reservation price cannot be estimated reliably, use the appropriate total-income method described in Section 2 and clearly state its assumptions.

The key distinction is that **estimating WTA from survey responses and converting it into a reservation price are two separate steps**. The second requires additional economic assumptions and validation.

## 5. Aggregation: From WTA to population values and GDP-B growth

Aggregation has two stages. First, estimate the compensation value of a specified loss of access across a defined population. Second, decide whether and how that valuation belongs in a GDP-B growth calculation. A large product valuation does not, by itself, establish a large contribution to GDP-B growth.

### 5.1 Estimate aggregate value using the mean

For a product in period $t$, define:

- $N_t$: the relevant population, such as residents aged 18–64.
- $\pi_t$: the share of that population meeting the study's definition of a user.
- $\mu_{t,c}$: mean monthly WTA among users, capped at a fixed amount $c$.

The annualized aggregate valuation is:

$$
M_{t,c}^{\mathrm{annualized}}=12N_t\pi_t\mu_{t,c}.
$$

This formula assumes that nonusers have zero value for the specified access restriction. If nonusers value the option to use the product during the restriction period, their valuation needs separate measurement. Use **mean WTA** for aggregation and **median WTA** to describe the typical user. If the mean is capped, label the aggregate accordingly.

Where population composition matters, aggregate within mutually exclusive demographic groups:

$$
M_{t,c}^{\mathrm{annualized}}
=12\sum_g N_{g,t}\pi_{g,t}\mu_{g,t,c}.
$$

This preserves differences in adoption and user valuations across groups. It requires enough data or a validated pooling model to estimate the group inputs. These groups partition the population; this formula does not justify summing valuations for separate products.

### 5.2 Match the population, usage definition, and units

Use a representative usage estimate whose definition matches the valuation study. For example, a survey of people who used a service during the past month should not silently be combined with an external estimate of people who have ever tried it. Match the age range, geography, reference period, and unit of observation. An account count is not necessarily a count of people, and a household valuation should be multiplied by households rather than adults.

An external adoption source can improve population coverage, but it does not automatically correct a valuation sample that overrepresents intensive users. The distribution of valuations among users also needs to represent the target user population. Record how survey weights or other adjustments address that problem.

For comparisons across waves, retain the same product definition, reporting cap on the chosen price basis, and valuation duration. Express values and the cap in consistent real prices if the objective is to compare purchasing power. When reporting several countries, first calculate each country's aggregate in its own consistent units, then document the exchange-rate or purchasing-power conversion used for comparison. GDP and the valuation added to it must use the same currency and price basis.

### 5.3 Annualization and uncertainty

Multiplying a one-month valuation by 12 produces an **annualized value at the conditions observed in that month**. It does not directly measure compensation for losing access for a continuous year, or the benefits actually received over a calendar year with changing adoption and product quality.

Use the ×12 convention when a common reporting scale is useful, and label it explicitly. Where annual access is the research question, include a separate annual-duration experiment or report sensitivity to alternative duration assumptions. Adaptation and substitution can make long-duration values grow less than proportionally; other circumstances can produce the opposite result. There is no universal direction of annualization bias.

Report uncertainty in the aggregate, as well as uncertainty in median WTA. Resample respondents consistently with the survey design, refit the valuation model, and recalculate the aggregate. If adoption is estimated from the same sample, recalculate adoption in the same resample. If it comes from an independent source, incorporate that source's sampling uncertainty when available. Otherwise show explicit adoption scenarios. Also report sensitivity to the cap, model, weights, and annualization convention.

### 5.4 An example

The following numbers are hypothetical. Suppose a population contains 10 million people, 40% use a free service, and mean monthly WTA among users, capped at $500, is $25. The annualized aggregate is:

$$
12\times10{,}000{,}000\times0.40\times\$25=\$1.2\text{ billion}.
$$

Now suppose the same procedure gives a baseline valuation of $0.9 billion. Nominal GDP rises from $100 billion to $110 billion, and the GDP deflator rises by 5%. Under the total-income construction in Section 2, using this one consistently defined free service:

$$
G_B=\frac{110+1.2}{100+0.9}\frac{1}{1.05}=1.04960.
$$

The resulting real growth rate is 4.96%. Conventional real GDP growth is:

$$
g_{GDP}=\frac{110}{100}\frac{1}{1.05}-1=4.76\%.
$$

The difference is approximately **0.20 percentage points**. This example shows why a $1.2 billion valuation level is a different object from a growth contribution. It also shows why an existing baseline valuation must remain in the denominator. The example illustrates the arithmetic conditional on the stated welfare construction; it is not an estimate for an actual economy.

### 5.5 Choose the appropriate GDP-B calculation

GDP-B treats existing paid products, newly introduced products, free products, and improvements in product quality differently. Surveys can estimate the value of all four, but the calculations are not the same.

**Total-income approach.** For free products, define the product or group of products being valued and use the same definition in both periods. Calculate total income as:

\[
T_t = GDP_t + M_t
\]

where \(GDP_t\) is conventional GDP and \(M_t\) is the estimated additional consumer value.

Set the starting value to zero only if the product or group of products did not exist in that period. Adjust for inflation when comparing periods. Convert the resulting index into a growth rate, and use compound annual growth rates when comparing multiple years.

**Bennet or reservation-price approach.** This method requires information about products and quantities in both periods, how valuations are measured, how inflation is handled, and what prices consumers would be willing to pay.

Be careful when using current valuations to estimate historical benefits. For example, the value people place on Facebook today reflects its current features and network of users. It does not necessarily tell us how much Facebook was worth when it first launched.

Similarly, estimating values beyond the compensation amounts offered in a survey requires additional modeling assumptions. These assumptions should be clearly stated and tested.

**Avoid double counting.** Some changes in spending on paid products are already reflected in conventional GDP. GDP-B adjustments should not count those changes again.

Also be clear about which alternatives respondents can still use. For example, the value of losing access to one messaging app may depend on whether other messaging apps remain available.

When both GDP-B methods can be applied, report them as **alternative estimates**. The difference between them does not automatically measure statistical uncertainty or provide upper and lower bounds on the true value.

For each calculation, save the data sources, paper or code versions, and inputs so that others can reproduce the results.

### 5.6 Examples from previous studies

The studies below show how researchers have estimated the value of digital products. They use different populations, products, and valuation methods, so their results should not be added together without accounting for these differences.

**Generative AI.** Brynjolfsson, Collis, Eggers, Kazinnik, and Nguyen (2026), *What is Generative AI Worth?*, report the following results:

| Measure | July 2025 survey | March 2026 survey |
|---|---:|---:|
| Average monthly WTA, capped at $500 | $98.00 | $124.50 |
| Median monthly WTA | $3.39 | $11.48 |
| Estimated number of users (millions) | 98.78 | 115.33 |
| Annualized total consumer value (billions) | $116.2 | $172.3 |

The study covers adults ages 18–64. To estimate the number of users, the authors combine population figures with adoption rates from Bick, Blandin, and Deming. The adoption data were collected at slightly different times from the valuation surveys.

The reported user counts produce the total estimates, allowing for rounding. Exact replication requires the original, unrounded inputs (see Appendix A).

Importantly, these totals represent **annualized values based on surveys conducted at specific points in time**. They do not measure the benefits actually received over an entire calendar year.

[Source: April 13, 2026 paper, Table 2 and Section 2.1](https://digitaleconomy.stanford.edu/app/uploads/2026/04/WhatsGenAIWorth.pdf)

**Facebook.** The March 2019 GDP-B working paper estimates a median monthly WTA of $42.17 for Facebook, with a 95% confidence interval of $32.53 to $54.47.

Multiplying the median by 12 months and approximately 202 million users gives an annual value of about $102 billion.

However, this calculation uses the **median WTA**, while the approach recommended in this cookbook uses the **average WTA** to estimate total value. The two should not be treated as equivalent.

The paper also estimates a $231 billion difference in economic welfare between 2003 and 2017, measured in 2017 dollars. This compares the two endpoints. It is not the sum of benefits received during the years in between.

For economic growth, the paper reports:

- Average annual GDP-B adjustments of 0.05 to 0.11 percentage points, calculated from cumulative adjustments.
- Conventional GDP compound annual growth of 1.83%.
- GDP-B compound annual growth of 1.87% to 1.91%.

These numbers are calculated differently and should not simply be added together.

All figures come from the March 2019 working-paper version. We exclude a cumulative figure in the paper's text that could not be reconciled with the other reported results.

[Source: March 2019 working paper, pages 26–32](https://www.aeaweb.org/conference/2020/preliminary/paper/EGAs9sad)

**Digital services in a Dutch laboratory.** The same working paper reports the following median monthly WTA estimates:

| Product | Median monthly WTA |
|---|---:|
| WhatsApp | €535.73 |
| Facebook | €96.80 |
| Google Maps | €59.16 |
| Instagram | €6.79 |
| Snapchat | €2.17 |
| LinkedIn | €1.52 |
| Skype | €0.18 |
| Twitter | €0.00 |

These estimates come from a laboratory sample in the Netherlands. They should not be interpreted as representative national estimates.

For some products, the sample also includes people who did not use the service. For example, only 33% of participants used Twitter.

This matters when estimating total economic value. Before applying survey valuations to a national population, we need to make sure the survey participants are representative of the users we are counting.

The results also show why adoption rates and available alternatives matter when comparing products. They do not provide population weights that can be applied directly to national estimates.

[Source: March 2019 working paper, Tables 2–3](https://www.aeaweb.org/conference/2020/preliminary/paper/EGAs9sad)

**Other digital products.** Brynjolfsson, Collis, and Eggers (2019) report the following median annual WTA estimates:

| Product category | Median annual WTA |
|---|---:|
| Search engines | $17,530 |
| Email | $8,414 |

These estimates measure the value of giving up an entire category of services for a year. They should not be compared directly with monthly estimates for individual products or brands.

[Source: PNAS article](https://doi.org/10.1073/pnas.1815663116)

**Digital Welfare of Nations.** Brynjolfsson et al. (2023) estimate more than $2.5 trillion in annual consumer value from ten digital products across thirteen countries.

The study recruited respondents through Facebook. Its results therefore depend on the survey's population coverage and the assumptions used to calculate total value.

[Source: Brynjolfsson et al. (2023)](https://www.nber.org/papers/w31670)

**Smartphone cameras.** The March 2019 GDP-B working paper also examines how much people value smartphone cameras.

In a student sample, the authors report:

- Estimated median monthly WTA: €68.13.
- Median of the actual survey bids: €100.

These numbers differ because they use different estimation methods.

The example shows how WTA surveys can measure the value of a specific product feature, rather than an entire product.

However, using these estimates to adjust economic growth requires defining what consumers had before the improvement, such as an older phone or camera, and checking how much of the improvement is already reflected in official price indexes.

[Source: March 2019 working paper, smartphone-camera application](https://www.aeaweb.org/conference/2020/preliminary/paper/EGAs9sad)

## 6. Interpretation and limitations

### 6.1 What WTA actually measures

Willingness to accept (WTA) measures how much compensation someone would need to give up access to a product or service for a specified period. It is not the same as how much they spend on the product or how much they would be willing to pay for it.

People may ask for more compensation than they would be willing to pay for the same product. This difference between WTA and willingness to pay (WTP) is well documented (Sunstein, 2020). Responses can also depend on income, available alternatives, expectations, and how the question is presented.

In economic theory, WTA can measure the compensation needed to make someone as well off as they were before losing access. However, survey responses do not necessarily measure this value perfectly.

It is therefore important to be clear about what the survey asks: compensation for losing something people already have, willingness to pay for something new, or another scenario. These measures should not be treated as interchangeable.

### 6.2 People's valuations can change with experience

People may value a product differently after spending time without it.

For example, Allcott, Braghieri, Eichmeyer, and Gentzkow (2020) studied what happened when people stopped using Facebook for four weeks. They found changes in participants' well-being and in how much they subsequently valued Facebook.

In the authors' November 2019 manuscript, the experiment included 580 people in the treatment group and 1,081 in the control group. These numbers refer to the group used to evaluate the effects of deactivation, not everyone who received a compensation offer. [Source: authors' manuscript, Tables 1 and 3](https://web.stanford.edu/~gentzkow/research/facebook.pdf).

This matters because an initial valuation may reflect habits or expectations that change once people actually experience life without the product.

When possible, researchers should measure valuations both before and after people lose access and clearly report when the measurements were taken. We should not assume that these effects are absent for other products, including AI tools, without testing them.

### 6.3 Survey responses and sample representativeness

Survey responses do not always reflect what people would do in real life. Making some choices binding, meaning respondents may actually have to give up access in exchange for payment, can make responses more credible. However, evidence that this works for one product does not mean it works equally well for every product or population.

Representativeness is another concern. Even when an online survey matches the population on age, gender, or other observable characteristics, respondents may differ in less visible ways. For example, they may use a product more intensively or be more willing to participate in surveys.

Repeated surveys help track changes over time, but using the same survey design does not guarantee that measurement errors remain constant.

Some errors may cancel out when we compare two periods. For example, if every respondent's WTA is overstated by the same dollar amount in both periods, that error can cancel when comparing average WTA. But this does not generally hold for percentage errors. It also may not hold for changes in total economic value if the number of users or population size changes.

Survey bias can also change as products become more familiar, the types of respondents change, or people become more or less confident that compensation offers are real.

To make comparisons over time more reliable, keep recruitment methods, questions, compensation amounts, and other survey features as consistent as possible. When changes are necessary, consider running the old and new versions alongside each other to measure their effects.

### 6.4 Adding up values across products and time

Valuations for individual products cannot always be added together to estimate the value of a group of products.

For example, two products may be substitutes. Losing access to either one may not matter much if the other remains available, but losing both could be much more costly. In other cases, adding individual valuations could overstate the value of the full bundle.

Avoiding overlapping product categories helps, but it does not solve this problem. If the goal is to estimate the value of a bundle, researchers may need to survey people about losing the entire bundle or use a model that accounts for how products interact. Coyle and Nguyen (2023) discuss these challenges in *Free Digital Products and Aggregate Economic Measurement*.

Similar issues arise when comparing different time periods. Giving up a product for one month, twelve separate times, is not necessarily equivalent to giving it up continuously for a year. Researchers should use consistent time periods and test whether duration affects valuations when it matters.

We also need to be careful when describing estimates as conservative or as lower bounds.

- **Capped valuations:** Limiting very high WTA values reduces or leaves unchanged the population average, assuming WTA is nonnegative. However, the resulting estimate is not automatically a statistical lower bound.
- **Growth estimates:** Applying the same cap in two periods does not guarantee that estimated growth is understated.
- **Adoption estimates:** A lower adoption rate produces a lower total value if WTA is held fixed, but this does not mean the overall estimate necessarily understates the true value.

Any claim that an estimate is conservative or represents a lower bound should explain the assumptions needed to support that interpretation.

### 6.5 What GDP-B does and does not measure

A survey about losing access to a product measures only part of its economic value. It does not capture every effect the product may have on society.

For example, consumer valuations may leave out effects on other people, environmental costs, benefits or costs to producers, and broader consequences of information sharing or network use.

Comparing consumer value with company revenue also requires care. Revenue is not profit, so this comparison does not tell us how total economic benefits are divided between consumers and producers.

GDP-B is intended to complement traditional GDP by measuring consumer benefits that conventional economic statistics may not fully capture. It does not replace official GDP.

Related approaches to measuring economic welfare are discussed by Ahmad and Schreyer (2016), Heys, Martin, and Mkandawire (2019), and Hulten and Nakamura.

Finally, estimates covering a selected group of digital products should not be interpreted as measuring all the benefits missing from GDP. Every reported result should clearly state which products and populations are included, what loss of access is being valued, and the main sources of uncertainty.

---

## 7. Optional extension: SurplusGPT and large-scale predictions

The main approach uses responses from human surveys to estimate how much people value products and services. Large language models (LLMs), such as SurplusGPT, can help predict these values for people or products with limited survey data. However, these predictions must still be tested against actual human responses.

### 7.1 Define what the model predicts

For a given person, product, and compensation amount, the model predicts how likely the person is to accept payment in exchange for losing access to that product.

If the population includes both users and nonusers, the model needs to predict two things separately:

- **Adoption:** Does the person use the product, based on our definition of a user?
- **Valuation among users:** If the person uses the product, how likely are they to accept different payment amounts to give it up?

We can use the predicted acceptance rates across payment amounts to estimate median and average willingness to accept (WTA), following Section 4. We can then combine these estimates with population and adoption data to calculate total economic value, following Section 5.

To make meaningful comparisons with human survey results, we must use the same definitions of users and products, along with the same maximum valuation (cap).

The SurplusGPT approach described in this cookbook first uses a statistical model that combines information across respondents and products to produce estimates, especially when survey data are limited. These estimates are then used to train SurplusGPT.

However, the training targets are estimates, not directly observed human choices. **Matching the statistical model's predictions does not necessarily mean SurplusGPT accurately predicts human behavior.** We still need to test its predictions against real survey responses that were not used in training.

### 7.2 Test whether the model works for its intended purpose

The way we test the model should reflect how we plan to use it. Different tests answer different questions:

- **New respondents:** Test on people the model has not seen before to see how well it predicts responses from new individuals.
- **New products:** Test on products that were not included in training to see whether the model can value unfamiliar products.
- **Future surveys:** Test on data collected at a later date to see whether the model continues to work as products and adoption patterns change.

Good performance on one test does not guarantee good performance on the others. To avoid giving the model an unfair advantage, all training steps, including the teacher model and data preparation, must use only the training data.

Compare the model against simpler alternatives, such as average acceptance rates, standard logit or probit models, and models that account for differences across respondents and products. Make sure every method has access to the same information.

Report the following results:

| What we evaluate | What to check |
|---|---|
| **Acceptance probabilities** | How closely predicted acceptance rates match actual responses, including across compensation amounts, products, and the target population. |
| **Product valuations** | How accurately the model predicts median and capped average WTA, accounting for uncertainty in the survey estimates and using comparable valuation ranges. |
| **Adoption rates** | How closely predicted adoption rates match actual adoption, both overall and across groups. A high AUC (a measure of how well the model separates users from nonusers) does not necessarily mean adoption rates are accurate. |
| **Economic consistency** | Whether respondents are predicted to accept compensation more often as the amount increases, and whether the model correctly handles differences between products and valuation periods. |
| **Total economic value** | How accurately the model estimates total value after combining adoption rates and WTA, and how results change with different survey weights and valuation caps. |

If we adjust model predictions to ensure that acceptance rates increase with compensation, report results both before and after the adjustment. Test the full adjusted model on data it has not seen before. Correcting existing predictions removes violations in those predictions, but training on corrected data does not guarantee that future predictions will follow the same pattern. Be clear about which predictions are being evaluated.

For every reported result, document the model version, prompts, training data, teacher model, test sample, and evaluation measures.

An earlier draft included model accuracy statistics and a threshold for limiting extreme valuations (winsorization). We do not treat these as general recommendations because the underlying analyses have not been independently verified. They should only be reported as reproducible results once the relevant code, data versions, and settings have been documented.

## 8. Implementation: A reproducible example and the `gdpb` project

### 8.1 Package status and scope

The workflow of Sections 3 through 5 is implemented in `gdpb`, an open-source Python package at https://github.com/kazinniksoph/gdpb-cookbook (MIT license). This cookbook lives in the same repository, so the text and the code are versioned together.

As of October 29, 2026 (package version 0.2.0) the package provides:

- the response and item file formats of Section 8.2, with a usage flag measured before the offer and `not_asked` for nonusers;
- cleaning rules applied in a fixed order with an audit of rows removed by each rule and the offers assigned to removed users (Section 3.3);
- logit or probit estimation on log offer, median WTA with a respondent-level bootstrap, and a capped mean whose cap is recorded separately from the offer grid (Sections 4.2–4.3);
- the pooled-adjacent-violators acceptance curve, which is the nonparametric maximum-likelihood estimate for current-status data, as a check on the parametric fit (Section 4.4);
- a median location label (within, below, or above the offers shown) so that extrapolated estimates are marked as such (Section 4.6);
- annualized capped aggregate value with the adoption source recorded, the total-income growth calculation of equations T11–T13, and Productivity-B (Sections 2.4 and 5);
- deposit files: item estimates, acceptance by offer, aggregates, metadata with software versions, cleaning audit, and a readable summary (Section 8.4).

The package's test suite checks that it reproduces the Appendix B results on the Appendix B files and the arithmetic of the Section 5.4 example. It does not yet include Turnbull or other interval-censored parametric estimators, post-stratification weights, a design-based bootstrap for complex samples, or survey-platform exporters; those are listed in the repository's roadmap. The LLM extension of Section 7 is deliberately outside the package.

The standalone example below and in Appendix B needs only NumPy and SciPy. It is the reference the package is checked against, and it can be run without installing the package.

### 8.2 Files and definitions for the worked example

The example uses three files. The same formats are read by the `gdpb` package. All generated observations are synthetic.

| File | Fields and interpretation |
|---|---|
| `responses.csv` | `respondent_id`, `item_id`, `is_user` (0/1, measured before the offer), `offer` (positive for users), `response` (`yes`, `no`, or `not_asked` for nonusers), `weight` (1 in this example). |
| `items.csv` | `item_id`, `scope`, `currency`, `duration_months`, and `price_grid` separated by pipes. |
| `config.json` | Item to estimate, target population, adoption input and source, reporting cap, annualization factor, and random seed. |

For example, the response format is:

```csv
respondent_id,item_id,is_user,offer,response,weight
1,demo_service,1,5,no,1
2,demo_service,1,50,yes,1
3,demo_service,0,,not_asked,1
```

These three rows demonstrate the format; the script generates the full example sample. A real analysis also needs versioned instrument wording, usage-window and population definitions, field dates, product-scope rules, and a cleaning log. Keep those in the study's data dictionary and run manifest. A retained `weight` field is not evidence that an estimator supports the required survey design.

The example's item and configuration are:

```csv
item_id,scope,currency,duration_months,price_grid
demo_service,category,USD,1,5|10|25|50|100|250|500
```

```json
{
  "item_id": "demo_service",
  "population": 1000000,
  "adoption_rate": 0.40,
  "reporting_cap": 500,
  "annualization_factor": 12,
  "seed": 314159,
  "adoption_source": "hypothetical fixed input"
}
```

The target population and adoption rate are hypothetical. They are not estimates for a named country or product.

### 8.3 Run and inspect the example

Save the complete code in Appendix B as `gdpb_example.py` (it is also at `examples/gdpb_example.py` in the repository). It was run for this revision with Python 3.12.14, NumPy 2.3.5, and SciPy 1.17.0, and again with Python 3.13.7, NumPy 2.3.1, and SciPy 1.16.0 with identical rounded results. Install the two numerical dependencies in the chosen Python environment, then run:

```bash
python -m pip install numpy==2.3.5 scipy==1.17.0
python gdpb_example.py --make-example --folder example --bootstrap 200
```

Use a new example folder: `--make-example` writes synthetic input files there. To estimate from those saved inputs without regenerating them, run:

```bash
python gdpb_example.py --folder example --bootstrap 200
```

The script generates 2,100 respondents, including 840 users. User acceptance is simulated from a logit-on-log-payment model whose population median is $50. Each user receives one offer. Nonusers receive no valuation question. It reads the saved files, fits the binary-choice likelihood, integrates the fitted survival curve to $500, bootstraps users, and writes `example/results.json`.

The checked run produced the following rounded results:

| Output | Result |
|---|---:|
| Median monthly WTA | $50.34 |
| Mean monthly WTA capped at $500 | $100.41 |
| Median bootstrap 95% interval | $42.90–$57.56 |
| Capped-mean bootstrap 95% interval | $84.44–$113.26 |
| Annualized capped aggregate at the hypothetical inputs | $481.97 million |
| Aggregate interval conditional on fixed adoption and population | $405.29–$543.66 million |
| Successful bootstrap fits | 200 of 200 |

Small differences in numerical results can occur when running the code in different environments. This example shows how the calculations work. It does not establish that the estimated product values are accurate.

The example covers one product, gives all respondents equal weight, uses positive compensation amounts, and estimates values for one month. It checks for duplicate respondents and rejects invalid model estimates.

The confidence intervals account only for uncertainty in the survey estimates. Population size and adoption rates are treated as fixed. We use 200 bootstrap repetitions to keep the example fast. For actual research, use enough repetitions to produce stable confidence intervals and account for how the survey sample was collected.

The model also estimates values below the smallest compensation amount offered in the survey. When the estimated median falls outside the range of offers, the code flags it as an extrapolation. For an actual study, we recommend additional checks, including comparing observed and predicted acceptance rates at each offer, testing estimates that rely on fewer modeling assumptions, documenting all data cleaning decisions, and accounting for uncertainty in population and adoption estimates.

To run the same files through the package, add the file names and an output folder to the configuration and call `gdpb run`:

```bash
gdpb run example/config.json      # after adding "responses", "items" and "output" keys
```

The package's `items.csv` reports the same median and capped mean to the cent, and its `aggregate.csv` the same annualized value.

### 8.4 Document the evidence behind published results

For every analysis, save the data and code versions, software environment, random assignment and data cleaning rules, estimation method, valuation cap, survey weights, population and adoption data sources, and method used to calculate uncertainty.

Keep actual survey responses separate from model predictions. For each product, clearly state whether the estimate is supported by the compensation amounts tested in the survey, requires extrapolation beyond those amounts, combines information across products, or could not be estimated.

Any claim that results have been replicated should specify which published result was reproduced, the numerical value obtained, and the exact code, data, and settings used. Reproducing a published median WTA does not mean that the average WTA, adoption rate, or total national value has also been reproduced.

If the underlying survey data cannot be shared, explain the access restrictions and publish the code settings and validation results that can be shared without revealing confidential information.

## 9. Methodological checklist

### Before collecting survey data

- [ ] Clearly define the product or service being valued, who is included in the study, the time period, what access respondents would lose, what alternatives they could use, and whether they would still pay any existing subscription fees.
- [ ] Ask about current usage before mentioning compensation. Keep users, nonusers, missing responses, and refusals separate.
- [ ] Randomly assign one compensation amount to each respondent for each product. Save both the assigned amount and the respondent ID.
- [ ] Choose the sample size and compensation amounts to get sufficiently precise estimates. Set a separate maximum valuation for reporting and comparisons.
- [ ] Decide in advance how respondents will be sampled and weighted, which responses will be excluded for quality reasons, and whether any survey choices will involve real payments or consequences.

### Before calculating total value

- [ ] Use a statistical model designed for yes/no responses. Accepting an offer does not mean a respondent's willingness to accept (WTA) equals that exact amount.
- [ ] Check that the model works properly, including whether it produces reasonable estimates across the compensation amounts offered. Clearly identify estimates that go beyond the observed data.
- [ ] Report both the median WTA and the average WTA after applying a clearly stated upper limit (cap). Show how sensitive the results are to the model, the cap, and statistical uncertainty.
- [ ] Use average WTA, rather than median WTA, to calculate total value. Clearly identify any historical calculations that used the median instead.
- [ ] Make sure the survey and population data use consistent definitions of users, age groups, geography, currency, and time periods.
- [ ] State whether nonusers are assumed to have zero value. If monthly values are multiplied by 12 to estimate annual value, make that assumption explicit.
- [ ] Account for uncertainty in both WTA estimates and adoption rates where the data allow. Clearly identify any numbers treated as fixed.

### Before reporting GDP-B or model results

- [ ] Distinguish between the total dollar value of a product and its contribution to economic growth. Use the appropriate GDP-B calculation for each.
- [ ] Compare the same set of products across years. Account for their value in the starting year if they already existed, and avoid counting benefits twice when they are already included in GDP.
- [ ] Adjust for inflation correctly. Keep price indexes, growth rates, compound annual growth rates, and simple averages of annual adjustments separate.
- [ ] Present results from different methods as alternative estimates. Do not automatically treat the range between them as a confidence interval or as guaranteed upper and lower bounds.
- [ ] Explain the main limitations, including hypothetical survey responses, changes in preferences over time, overlapping product values, differences between survey respondents and the population, and effects on others that the survey does not measure.
- [ ] For SurplusGPT, test predictions against real human responses that were not used to build or tune the model. Report both how well predictions match observed behavior and how accurately they reproduce total value.
- [ ] Provide the exact version of the code and sources used, along with the data inputs and settings needed to reproduce the results. Clearly state anything that could not be accessed or independently verified.

---

## 10. References

### Research papers

- Ahmad, N., and P. Schreyer (2016). “Measuring GDP in a Digitalised Economy.” *OECD Statistics Working Papers* 2016/07. [Publisher and DOI](https://doi.org/10.1787/5jlwqd81d09r-en).

- Allcott, H., L. Braghieri, S. Eichmeyer, and M. Gentzkow (2020). “The Welfare Effects of Social Media.” *American Economic Review* 110(3): 629–676. [Published article](https://doi.org/10.1257/aer.20190658). The sample counts used in Section 6 are from the [authors' November 8, 2019 manuscript](https://web.stanford.edu/~gentzkow/research/facebook.pdf), Tables 1 and 3.

- Becker, G. M., M. H. DeGroot, and J. Marschak (1964). “Measuring Utility by a Single-Response Sequential Method.” *Behavioral Science* 9(3): 226–232. [Publisher and DOI](https://doi.org/10.1002/bs.3830090304).

- Bick, A., A. Blandin, and D. J. Deming (2024, subsequently revised). “The Rapid Adoption of Generative AI.” NBER Working Paper 32966. [Working-paper record](https://www.nber.org/papers/w32966). Use a dated survey release for an adoption estimate; the current working-paper record does not, by itself, identify the data vintage used in an earlier valuation study.

- Brynjolfsson, E., A. Collis, and F. Eggers (2019). “Using Massive Online Choice Experiments to Measure Changes in Well-Being.” *Proceedings of the National Academy of Sciences* 116(15): 7250–7255. [Published article](https://doi.org/10.1073/pnas.1815663116).

- Brynjolfsson, E., A. Collis, W. E. Diewert, F. Eggers, and K. J. Fox (2019). “GDP-B: Accounting for the Value of New and Free Goods in the Digital Economy.” NBER Working Paper 25695, March. [Working-paper record](https://www.nber.org/papers/w25695); [March 2019 version used for the historical examples](https://www.aeaweb.org/conference/2020/preliminary/paper/EGAs9sad).

- Brynjolfsson, E., A. Collis, W. E. Diewert, F. Eggers, and K. J. Fox (2025). “GDP-B: Accounting for the Value of New and Free Goods.” *American Economic Journal: Macroeconomics* 17(4): 312–344. [Published article](https://doi.org/10.1257/mac.20210319); [replication archive](https://doi.org/10.3886/E209901V1).

- Brynjolfsson, E., A. Collis, W. E. Diewert, F. Eggers, and K. J. Fox (undated author manuscript). “GDP-B: Accounting for the Value of New and Free Goods.” [Manuscript hosted by the Australian Bureau of Statistics](https://www.abs.gov.au/system/files/documents/9d03e643ba44abb61eefe972765b3c67/Fox%20-%20The%20digital%20economy%2C%20welfare%20and%20productivity%20growth.pdf). Cited here for its distinction between global WTA and marginal shadow prices, not as the final published version.

- Brynjolfsson, E., A. Collis, F. Eggers, S. Kazinnik, and D. Nguyen (2026). “What is Generative AI Worth?” Working paper dated April 13. [Dated paper](https://digitaleconomy.stanford.edu/app/uploads/2026/04/WhatsGenAIWorth.pdf); [SSRN record](https://doi.org/10.2139/ssrn.6569938). Section 5 uses the reported values in Table 2 and the capped-mean definition in Section 2.1.

- Brynjolfsson, E., A. Collis, A. Liaqat, D. Kutzman, H. Garro, D. Deisenroth, N. Wernerfelt, and J. J. Lee (2023). “The Digital Welfare of Nations: New Measures of Welfare Gains and Inequality.” NBER Working Paper 31670. [Working-paper record](https://www.nber.org/papers/w31670).

- Coyle, D., and D. Nguyen (2020). “Free Goods and Economic Welfare.” ESCoE Discussion Paper 2020-18. [Working paper](https://www.escoe.ac.uk/publications/free-goods-and-economic-welfare-escoe-dp-2020-18/). This is the working-paper title; the published version has the title below.

- Coyle, D., and D. Nguyen (2023). “Free Digital Products and Aggregate Economic Measurement.” *Economie et Statistique / Economics and Statistics* 539: 27–50. [Published article](https://doi.org/10.24187/ecostat.2023.539.2096).

- Diewert, W. E., and H. Mizobuchi (2009). “Exact and Superlative Price and Quantity Indicators.” *Macroeconomic Dynamics* 13(S2): 335–380. [Published article](https://doi.org/10.1017/S136510050909018X).

- Hanemann, W. M. (1984). “Welfare Evaluations in Contingent Valuation Experiments with Discrete Responses.” *American Journal of Agricultural Economics* 66(3): 332–341. [Published article](https://doi.org/10.2307/1240800).

- Heys, R., J. Martin, and W. Mkandawire (2019). “GDP and Welfare: A Spectrum of Opportunity.” ESCoE Discussion Paper 2019-16. [Working paper](https://www.escoe.ac.uk/publications/gdp-and-welfare-a-spectrum-of-opportunity/).

- Hulten, C. R., and L. I. Nakamura (2019). “Expanded GDP for Welfare Measurement in the 21st Century.” NBER Working Paper 26578. [Working paper](https://www.nber.org/papers/w26578). Published in *Measuring and Accounting for Innovation in the Twenty-First Century* (2021), edited by C. Corrado, J. Haskel, J. Miranda, and D. Sichel. [Published chapter](https://www.nber.org/books-and-chapters/measuring-and-accounting-innovation-twenty-first-century/expanded-gdp-welfare-measurement-21st-century).

- Sunstein, C. R. (2020). “Valuing Facebook.” *Behavioural Public Policy* 4(3): 370–381. Published online in 2019. [Published article](https://doi.org/10.1017/bpp.2018.34).

### Software documentation

- **lifelines:** [`KaplanMeierFitter` documentation](https://lifelines.readthedocs.io/en/stable/fitters/univariate/KaplanMeierFitter.html), particularly `fit_interval_censoring()`, which implements the Turnbull estimator. Record the installed software version when reproducing an analysis.

- **SciPy:** [`scipy.optimize.minimize`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html) and [`scipy.integrate.quad`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html). These document the optimization and integration routines used in the independent example in Section 8.

## Appendix A. Source and version notes

**Equations.** This cookbook uses its own equation numbers. The 2019 working paper, a later manuscript, and the 2025 published paper are different versions and should not be treated as identical. We checked the publication details for the 2025 paper but could not access its full text. We also found a difference between equation 31 in the 2019 paper and an earlier equation. Because of this inconsistency, we do not use equation 31 as a basis for the code.

**Historical growth results.** The Facebook results come from the March 2019 working paper. The paper reports two different measures: average annual adjustments and compound annual growth rates. We keep these separate. We also leave out a cumulative figure of 29.16% that we could not reconcile with the other results. The $231 billion estimate measures the change between two points in time, not the total benefits accumulated over the years between them.

**Generative AI example.** The table uses results from an April 13, 2026 paper and covers adults ages 18–64. The adoption data and valuation surveys were collected at slightly different times. Some numbers also differ slightly because of rounding. For example, multiplying the reported 2026 population (206.29 million) by the reported adoption rate (56%) gives 115.52 million users, rather than the 115.33 million shown in the paper. This is consistent with rounding and does not necessarily indicate an error. The table is intended as an illustration. Exact replication requires the original, unrounded data and dates.

**Project-specific results.** We could not independently check the private survey results, SurplusGPT accuracy statistics, detailed diagnostics, or earlier decisions about handling extreme values (winsorization). We therefore do not present them as verified results or recommend applying the same settings to every project. Each project release should include the code version, population definitions, and evaluation results needed to check its findings.

**Package status.** An earlier draft of this appendix recorded that the `gdpb` repository returned a 404 error on October 29, 2026; it was private at the time. It was made public the same day at https://github.com/kazinniksoph/gdpb-cookbook, and this cookbook now lives in it. Section 8.1 describes what version 0.2.0 implements and what it does not. The package's own tests check it against the Appendix B script; that is a check of internal consistency on synthetic data, not evidence that any estimated product value is accurate. The package's re-estimation of the generative AI survey medians from private microdata matches the published March 2026 median to within about 1% once the paper's cleaning rules are applied; the July 2025 figure does not yet match and should not be cited as replicated.

## Appendix B. Complete runnable example

Save this block as `gdpb_example.py` and follow Section 8. The script generates synthetic observations and estimates one product. Its numerical results are illustrative.

```python
"""One-item SBDC example. All generated observations are synthetic."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import expit


def make_example(folder):
    folder.mkdir(parents=True, exist_ok=True)
    grid = [5, 10, 25, 50, 100, 250, 500]
    rng = np.random.default_rng(20261029)
    rows = []
    # Known user WTA distribution: median 50, log-logistic shape 1.3.
    # One independent offer/response per user; all survey weights equal one.
    for offer in grid:
        for accepted in rng.binomial(1, expit(1.3 * np.log(offer / 50)), 120):
            rows.append([len(rows) + 1, "demo_service", 1, offer,
                         "yes" if accepted else "no", 1])
    # Usage was screened before any offer. Nonusers receive no WTA question.
    for _ in range(1260):
        rows.append([len(rows) + 1, "demo_service", 0, "", "not_asked", 1])
    with (folder / "responses.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["respondent_id", "item_id", "is_user", "offer",
                         "response", "weight"])
        writer.writerows(rows)
    with (folder / "items.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "scope", "currency", "duration_months",
                         "price_grid"])
        writer.writerow(["demo_service", "category", "USD", 1,
                         "|".join(map(str, grid))])
    config = {"item_id": "demo_service", "population": 1000000,
              "adoption_rate": 0.40, "reporting_cap": 500,
              "annualization_factor": 12, "seed": 314159,
              "adoption_source": "hypothetical fixed input"}
    (folder / "config.json").write_text(json.dumps(config, indent=2) + "\n")


def fit_curve(offers, accepted, cap):
    x = np.column_stack([np.ones(len(offers)), np.log(offers)])

    def objective(theta):
        z = x @ theta
        return np.mean(np.logaddexp(0, z) - accepted * z)

    def gradient(theta):
        return x.T @ (expit(x @ theta) - accepted) / len(offers)

    fit = minimize(objective, [0.0, 1.0], jac=gradient, method="BFGS",
                   options={"gtol": 1e-7, "maxiter": 1000})
    alpha, beta = fit.x
    fitted = expit(x @ fit.x)
    hessian = x.T @ (x * (fitted * (1 - fitted))[:, None]) / len(offers)
    if (not fit.success or beta <= 0 or not np.isfinite(fit.x).all()
            or np.linalg.eigvalsh(hessian).min() < 1e-8):
        raise ValueError("Unstable fit, wrong-sign slope, or separation.")
    median = float(np.exp(-alpha / beta))
    capped_mean = quad(
        lambda p: 1.0 if p == 0 else expit(-(alpha + beta * np.log(p))),
        0, cap, epsabs=1e-7)[0]
    return float(alpha), float(beta), median, float(capped_mean)


def run(folder, bootstrap):
    config = json.loads((folder / "config.json").read_text())
    with (folder / "items.csv").open(newline="") as f:
        items = list(csv.DictReader(f))
    with (folder / "responses.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    item_id = config["item_id"]
    if len(items) != 1 or items[0]["item_id"] != item_id:
        raise ValueError("This example supports one item only.")
    if float(items[0]["duration_months"]) != 1:
        raise ValueError("This example requires one-month valuations.")
    if not rows or any(r["item_id"] != item_id for r in rows):
        raise ValueError("Responses must refer to the configured item.")
    if len({r["respondent_id"] for r in rows}) != len(rows):
        raise ValueError("Expected one row per respondent for this item.")
    if any(float(r["weight"]) != 1 for r in rows):
        raise ValueError("This illustration requires equal weights.")
    if any(r["is_user"] not in {"0", "1"} for r in rows):
        raise ValueError("is_user must be 0 or 1.")
    users = [r for r in rows if r["is_user"] == "1"]
    if not users or any(r["response"] not in {"yes", "no"} for r in users):
        raise ValueError("Eligible users need yes/no responses.")
    offers = np.array([float(r["offer"]) for r in users])
    accepted = np.array([r["response"] == "yes" for r in users], dtype=float)
    cap = float(config["reporting_cap"])
    adoption = float(config["adoption_rate"])
    if not np.isfinite(offers).all() or np.any(offers <= 0):
        raise ValueError("Offers must be finite and positive.")
    if not 0 < cap <= offers.max() or not 0 <= adoption <= 1:
        raise ValueError("Check reporting cap and adoption rate.")
    if len(np.unique(offers)) < 3 or len(np.unique(accepted)) < 2:
        raise ValueError("Insufficient variation for the example model.")
    if config["population"] <= 0 or config["annualization_factor"] != 12:
        raise ValueError("Use a positive population and annualization factor 12.")
    alpha, beta, median, mean_c = fit_curve(offers, accepted, cap)
    rng = np.random.default_rng(config["seed"])
    draws = []
    for _ in range(bootstrap):
        selected = rng.integers(0, len(users), size=len(users))
        try:
            draws.append(fit_curve(offers[selected], accepted[selected], cap)[2:])
        except ValueError:
            pass
    if len(draws) < 0.95 * bootstrap:
        raise ValueError("Too many bootstrap fits failed; inspect identification.")
    bounds = np.quantile(np.asarray(draws), [0.025, 0.975], axis=0)
    scale = 12 * config["population"] * adoption
    location = ("below_grid" if median < offers.min() else
                "above_grid" if median > offers.max() else "within_grid")
    result = {
        "data_status": "synthetic illustration; no empirical claim",
        "item_id": item_id, "currency": items[0]["currency"],
        "respondents": len(rows), "users": len(users),
        "sample_usage_rate": len(users) / len(rows),
        "adoption_rate_used": adoption, "population": config["population"],
        "alpha": alpha, "beta": beta, "reporting_cap": cap,
        "median_monthly_wta": median, "median_location": location,
        "capped_mean_monthly_wta": mean_c,
        "median_ci95": bounds[:, 0].tolist(),
        "capped_mean_ci95": bounds[:, 1].tolist(),
        "annualized_capped_value": scale * mean_c,
        "annualized_value_ci95_conditional": (scale * bounds[:, 1]).tolist(),
        "bootstrap_requested": bootstrap, "bootstrap_successful": len(draws),
        "interval_scope": "WTA sampling only; fixed adoption and population"
    }
    (folder / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=Path("example"))
    parser.add_argument("--make-example", action="store_true")
    parser.add_argument("--bootstrap", type=int, default=200)
    args = parser.parse_args()
    if args.bootstrap < 20:
        parser.error("Use at least 20 replicates for this illustration.")
    if args.make_example:
        make_example(args.folder)
    run(args.folder, args.bootstrap)
```
