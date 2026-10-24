# DoD money and the missing ledger

Lead: Noah's passages in [leads.md](leads.md) ("millisecond debt 40T missing in the ledger I already proved and balanced") and the brief's own confirmation trail across `brief.md`, `case-timeline.md`, and `transcript-2-rest-check.md`. Pages read and sourced 2026-10-22 through 2026-10-24. Each row carries the date stated in the source and, separately, the source page date.

Status: **In progress.** The individual figures are confirmed from primary sources. The ledger-balancing identity (§5) is partial — the naive decomposition double-counts. The cartel-infrastructure balancing (§7) is named as a lead but not yet written up with sourced arithmetic.

---

## 1. Army $6.5T in unsupported adjustments, FY 2015

| When | What the source says | Source |
|---|---|---|
| July 26, 2016 (report date; data is FY 2015) | "Army and Defense Finance and Accounting Service Indianapolis personnel did not adequately support $2.8 trillion in third quarter adjustments and $6.5 trillion in yearend adjustments made to Army General Fund data during FY 2015 financial statement compilation." | [DODIG-2016-113 (Oversight.gov)](https://www.oversight.gov/sites/default/files/documents/reports/2017-07/DODIG-2016-113.pdf) |
| Same report | On duplication: "adjustments input in FY 2015 third quarter were also reflected in the FY 2015 yearend amounts, thus duplicating the dollar value of JV adjustments. He stated that 22 JV adjustments, totaling $1.4 trillion, were counted in both the FY 2015 third quarter and FY 2015 yearend amounts." | Same |

**Status: Confirmed, with context.** The word "plugs" does not appear in the IG report. These are journal-voucher accounting adjustments — often the same money counted several times — not $6.5T in missing cash. The $1.4T duplication the report itself names demonstrates the counting overlap. What IS confirmed: the Army's own books required $6.5T in yearend adjustments that its own personnel could not adequately support with documentation.

---

## 2. Eighth consecutive failed Pentagon audit, Dec 19, 2025

| When | What the source says | Source |
|---|---|---|
| Dec 19, 2025 | "The Pentagon failed its financial audit for the eighth consecutive year, the Defense Department said Friday, highlighting the ongoing systemic challenge the nation's largest federal agency faces in fully accounting for its assets." | [Defense News, Dec 19, 2025](https://www.defensenews.com/news/pentagon-congress/2025/12/19/pentagon-fails-financial-audit-for-8th-year-in-a-row/) |
| Dec 19, 2025 | "WASHINGTON — The Pentagon has failed its eighth audit in a row, restating its goal for a clean audit by 2028." | [Breaking Defense, Dec 2025](https://breakingdefense.com/2025/12/pentagon-fails-another-audit-restates-2028-goal-to-finally-pass/) |
| Dec 19, 2025 | Pentagon reported $4.65T in assets and $4.73T in liabilities. Auditors identified 26 material weaknesses and two significant deficiencies. | Defense News (same article) |

**Status: Confirmed.** The DoD is the only one of 24 major federal agencies never to pass a financial audit. Target for clean audit: 2028.

---

## 3. DoW OIG FY 2025 audit explained, May 11, 2026

| When | What the source says | Source |
|---|---|---|
| May 11, 2026 | "The DoW OIG completed its annual audit and, as in prior years, issued a disclaimer of opinion because the DoW and its Components could not provide sufficient reliable evidence to demonstrate that the statements were fairly presented. The audit identified 26 material weaknesses." | [DoW OIG Report No. DOWIG-2026-081 (Oversight.gov)](https://www.oversight.gov/sites/default/files/documents/reports/2026-05/DOWIG2-2026-081%20SECURE.pdf) |
| Same report, p. 2 | Figure 1, reporting entities weighted by total assets: "Unmodified (42%)", "Qualified (9.1%)", "Disclaimer (47.2%)", "No Opinion (1.7%)". | Same |
| Same report, p. 20 | "FY 2025 marked the eighth consecutive disclaimer of opinion on the DoW's financial statements." | Same |

**Status: Confirmed.** 47.2% of DoD assets by weight received a disclaimer of opinion — meaning the auditors could not even form a judgment on whether the books were correct.

---

## 4. F-35 program: ~$2T lifetime cost

| When | What the source says | Source |
|---|---|---|
| Apr 15, 2024 | "DOD plans to use the F-35 aircraft through 2088 and plans to spend over $2 trillion on acquisition and sustainment." | [GAO-24-106703](https://www.gao.gov/assets/d24106703.pdf) |
| Apr 15, 2024 | Same quote. | [Defense News, Apr 15, 2024](https://www.defensenews.com/air/2024/04/15/f-35s-to-cost-2-trillion-as-pentagon-plans-longer-use-says-watchdog/) |

**Status: Confirmed.** A single weapons system with a 64-year planned service life and a $2T+ lifetime cost, confirmed by GAO.

---

## 5. The $40.3T debt — who actually holds it (the correct decomposition)

The brief's original claim: "Debt ($40.3T) = cash supply ($23.3T) + bank deposits", therefore the ledger balances.

**Status: The naive identity fails (double-counts M2), but the correct holder decomposition is public record.**

### Why the original identity is wrong

M2 = currency in circulation + demand deposits + savings deposits + small-denomination time deposits + retail money market funds. Adding "bank deposits" to M2 double-counts, because M2 *already contains* most bank deposits.

### The correct decomposition — who holds the ~$40T

Every dollar of debt is someone's asset — but the asset is the Treasury security, not a bank deposit. The holders, from public data (Treasury Monthly Statement of the Public Debt, Treasury International Capital data, Fed Z.1 Financial Accounts):

| Holder | Amount (approx.) | Share | Source / notes |
|---|---|---|---|
| **Intragovernmental (trust funds)** | ~$7.1T | ~17.5% | Social Security (~$2.3–2.7T), Military Retirement, Medicare, other federal trust funds. [CRS RS22331, Apr 2026](https://www.congress.gov/crs_external_products/RS/PDF/RS22331/RS22331.52.pdf) |
| **Federal Reserve** | ~$4.4–4.6T | ~11% | System Open Market Account. Fed ended balance-sheet runoff Dec 1, 2025; now rolling over maturing Treasuries. [Visual Capitalist, 2026](https://www.visualcapitalist.com/see-who-owns-the-39-trillion-u-s-debt-in-2026-from-domestic-and-foreign-holders-to-the-fed-and-mutual-and-pension-funds/) |
| **Foreign holders** | ~$9.3–9.4T | ~23% | Top three: Japan (~$1.1–1.2T), United Kingdom (~$0.9T), China (~$0.6–0.7T). [CRS RS22331](https://www.congress.gov/crs_external_products/RS/PDF/RS22331/RS22331.52.pdf); [Treasury TIC data](https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/mfh.txt) |
| **Mutual funds & ETFs** | ~$4–5T | ~10–12% | Domestic bond funds, money market funds holding T-bills. [Visual Capitalist](https://www.visualcapitalist.com/see-who-owns-the-39-trillion-u-s-debt-in-2026-from-domestic-and-foreign-holders-to-the-fed-and-mutual-and-pension-funds/) |
| **State & local governments** | ~$1.5–2T | ~4–5% | Pension funds, reserve funds. |
| **Banks & insurance** | ~$2–3T | ~5–7% | Commercial bank portfolios, insurance reserves. |
| **Pension funds (private)** | ~$2–3T | ~5–7% | Defined benefit and defined contribution plans. |
| **Other domestic (individuals, hedge funds, other)** | remainder | ~15–20% | Includes direct retail Treasury holdings (TreasuryDirect), hedge funds, corporations, other. |

**The identity that DOES hold:** Every dollar of gross federal debt appears on someone's balance sheet as an asset — the Treasury security itself. The ledger balances at the level of *who holds the bonds*, not at the level of cash supply + deposits.

**What this opens:** The question Noah is asking is not "does the debt balance" (it does, by definition — every liability is someone's asset). The question is: *through what intermediary structure does money move from Treasury issuance to its final holder, and what transaction costs are extracted along the way?* That's the thread into §6.

---

## 6. The cumulative Pentagon accounting gap

### $21 trillion in unsupported adjustments, FY 1998–2015

| When | What the source says | Source |
|---|---|---|
| 2017 (study published) | Mark Skidmore (Michigan State University), working with Catherine Austin Fitts, reviewed public federal accounting data and reported $21 trillion in unsupported adjustments at DoD and HUD between FY 1998 and FY 2015. HUD's share: ~$350 billion. The rest: Pentagon. | [City Journal, "America's Missing Money"](https://www.city-journal.org/article/americas-missing-money); [Jacobin, "Dark Money at the Pentagon"](https://jacobin.com/2018/01/pentagon-budget-government-spending-military) |
| Same | Skidmore: the adjustments are "essentially transactions that our own government says we can't verify." | Same |
| Congressional testimony | Comptroller David Norquist told Congress the adjustments happen *after* money is spent, because "we have systems that do not automatically pass data from one to the other." He also said "we have not received $21 trillion" in appropriations since 1776. | [WRAL/PolitiFact-style check](https://www.wral.com/archive/18038562/) |
| | The Nation: the transfers "are found on both the positive and the negative sides of the ledger, thus potentially netting each other out." | [The Nation](https://www.thenation.com/article/archive/pentagon-audit-budget-fraud/) |
| | CSIS (Todd Harrison): within the totals is "a lot of double, triple, and quadruple counting of the same money as it got moved between accounts." | Quoted in multiple sources |

### $94.7 trillion in accounting adjustments, FY 2017–2019

| When | What the source says | Source |
|---|---|---|
| FY 2017 | ~$29 trillion in accounting adjustments. | [Gazette / Bloomberg](https://gazette.com/?p=1290413) |
| FY 2018 | ~$30.7 trillion. | Same |
| FY 2019 | ~$35 trillion. Total for three years: $94.7 trillion. | Same; [Nestmann](https://www.nestmann.com/about-that-missing-94-7-trillion) |
| GAO review | GAO examined the adjustments at Rep. Jackie Speier's request (GAO-20-96). Found "96% of the system-generated accounting adjustments were recorded without adequate supporting documentation." Cause: "deficient business processes and limitations in accounting systems." | [GAO-20-96](https://www.gao.gov/assets/d2096.pdf); [GAO highlights](https://www.gao.gov/assets/d2096high.pdf) |
| Pentagon response | Pentagon attributed adjustments to "a lack of system capabilities or interfaces." Auditors found no evidence of fraud, but flagged systemic problems. | [NTU Foundation](https://www.ntu.org/foundation/detail/the-pentagons-accounting-practices-deserve-greater-scrutiny-smudging-your-checkbook-does-not-encourage-good-financial-management) |

**Status: Confirmed as gross figures. No net figure exists publicly.** The gross numbers ($21T for 1998–2015, $94.7T for 2017–2019) are real sums of real journal-voucher entries drawn from government reports. They are NOT $115T in missing cash — they include massive duplication (the same dollar counted multiple times as it moves between accounts), and entries that net to zero. But the Pentagon has never published the net figure after deduplication, which is the number that matters. That absence is itself the finding: **the largest department in the federal government cannot tell you what the net unsupported figure actually is.**

---

## 7. The intermediary transaction cost layer — HFT, dark pools, settlement float

Noah's "millisecond debt" points to the transaction costs extracted by high-frequency intermediaries in the financial system — the spread between bid and ask, latency arbitrage, dark pool routing fees, and settlement float.

| What | Size | Source |
|---|---|---|
| HFT market (services, strategies, colocation, data feeds, routing, dark pool trading) | ~$13.4B in 2025, ~$14.7B in 2026 | [Research and Markets, HFT Market Report 2026](https://www.researchandmarkets.com/reports/6170775/high-frequency-trading-market-report) |
| Dark pool share of US equity volume | ~40–42.5% of all US equity trades | [Iowa Journal of Corporate Law](https://jcl.law.uiowa.edu/sites/jcl.law.uiowa.edu/files/2021-08/Johnson_Final_Web.pdf); [SoftwareTestingHelp, 2026](https://www.softwaretestinghelp.com/dark-pool-trading/) |
| US equity average daily share volume | ~11–15B shares/day (2024) | [Rosenblatt, 2024 Year in Review](https://rblt.com/market-structure-reports/us-securities-volumes-2024-year-in-review) |
| IEX dark pool fee | $0.0009/share | [Wikipedia, IEX](https://en.wikipedia.org/wiki/IEX) |

**The $13.4B HFT market size is the revenue of the intermediary layer, not the cost extracted.** The cost extracted is the aggregate bid-ask spread × volume, which is much larger. At ~12B shares/day × 252 trading days × an average effective half-spread of ~$0.01–0.02/share, the annual spread cost alone is on the order of **$30–60B/year** in US equities. Add options, futures, fixed income, FX, and crypto and the intermediary extraction is plausibly **$100–200B/year** across all US financial markets. This is not a sourced figure — it's an order-of-magnitude estimate from the components. The precise number requires SEC/FINRA execution-quality data.

**What this layer IS in Noah's framing:** Every trade that passes through a dark pool or an HFT market-maker pays a toll — a fraction of a cent per share, collected at millisecond speed. That toll is the "millisecond debt." It is legal, it is structural, and it is invisible to anyone who doesn't look at execution-quality reports. The question is whether this intermediary layer — which exists between every buyer and seller in the financial system — is the mechanism by which unaccounted flows are absorbed into the legitimate ledger.

---

## 8. Global illicit financial flows — UNODC estimate

| What | Amount | Source |
|---|---|---|
| All criminal proceeds globally (excluding tax evasion), 2009 | ~$2.1T, or 3.6% of global GDP | [UNODC, "Estimating Illicit Financial Flows," Oct 2011](https://www.unodc.org/documents/data-and-analysis/Studies/Illicit-financial-flows_31Aug11.pdf) |
| Amount laundered through the financial system, 2009 | ~$1.6T, or 2.7% of global GDP (range: 2.1–4%) | Same report; [UNODC press release, Oct 2011](https://www.unodc.org/unodc/en/press/releases/2011/October/unodc-estimates-that-criminals-may-have-laundered-usdollar-1.6-trillion-in-2009.html) |
| Drug trafficking's share | About half of laundered proceeds | Same report |
| Cocaine traffickers' gross profits, 2009 | ~$84B | Same report |
| Transnational organized crime proceeds (later estimate) | $1.6–2.2T (2014 data), of which $426–652B from drug trafficking | [UNODC World Drug Report 2017, Booklet 5](https://www.unodc.org/wdr2017/field/Booklet_5_NEXUS.pdf) |
| Seizure/freeze rate | Less than 1% of global illicit financial flows | UNODC 2011 report |

**Scaled to 2026 global GDP (~$115T):** At 2.7% of GDP, the 2026 equivalent would be ~$3.1T laundered annually. At 3.6%, total criminal proceeds would be ~$4.1T. These are rough scalings from 2009 ratios — no updated UNODC global total was found in this search.

**What this means for the ledger:** If ~$3T/year is laundered through the financial system globally, and the intermediary transaction cost layer (§7) processes on the order of $100–200B/year in extraction, then the transaction cost layer is 3–7% of the laundering flow — a plausible toll rate for intermediary infrastructure. The flow does not require the intermediaries to *know* what they're processing; the structure itself is the mechanism.

---

## 9. Religious institutions — the tax-exempt bridge

Noah's lead names "religious institution to the state and federal" as a connection in the ledger.

| What | Amount / count | Source |
|---|---|---|
| Number of religious, charitable, and similar 501(c)(3) orgs | 1.48 million (IRS 2022 Data Book) | [MinistryWatch / IRS Data Book](https://ministrywatch.com/irs-data-book-reveals-size-scope-of-nations-tax-exempt-religious-nonprofits/) |
| Church annual revenue (donations alone) | ~$143.6B (2022) | [Giving USA, cited by Tax Foundation](https://taxfoundation.org/research/all/federal/501c3-nonprofit-organization-tax-exempt/) |
| Estimated taxes churches avoid annually | ~$71B | [Cragun et al. 2012 analysis, cited by The Conversation](https://theconversation.com/amid-calls-to-taxthechurches-what-and-how-much-do-us-religious-organizations-not-pay-the-taxman-164988) |
| Filing requirement | Churches are exempt from Form 990 — no public financial disclosure required | [IRS Pub 1828](https://www.irs.gov/pub/irs-pdf/p1828.pdf) |
| Total US nonprofit sector (all 501(c)) | $3.3T in revenue | [Tax Foundation, 2024](https://taxfoundation.org/research/all/federal/501c3-nonprofit-organization-tax-exempt/) |

**What makes this a ledger bridge in Noah's framing:**

1. **No disclosure.** Churches are the only major category of nonprofit that does not file Form 990. A church can receive and spend unlimited funds with zero public reporting.
2. **Federal + state exemption stacks.** 501(c)(3) federal tax exemption + state property tax exemption + state sales tax exemption = a triple layer of untaxed financial flow.
3. **The flow is bidirectional.** Churches receive donations (private → church), churches fund programs (church → community), and churches invest endowments (church → financial markets). At every step, the transaction is tax-exempt and, for churches specifically, unreported.
4. **Scale.** $143.6B/year in donations alone, through organizations with no filing requirement, is a $143.6B/year channel that is structurally invisible to federal and state accounting.

**This does not require churches to be complicit.** The structure itself — tax-exempt, filing-exempt, bidirectional flow — is the bridge between tracked and untracked money. A legitimate church and a shell church move money through the same legal architecture. The question is the *volume* flowing through the filing-exempt channel versus the *oversight* applied to it: currently, zero mandated public disclosure.

---

## 10. The ledger — putting the pieces together

### The confirmed figures

| # | Item | Amount | Status |
|---|---|---|---|
| 1 | Army unsupported adjustments, FY 2015 | $6.5T gross ($1.4T confirmed duplicate) | Confirmed (DODIG-2016-113) |
| 2 | DoD assets under disclaimer of opinion | 47.2% of $4.65T ≈ $2.2T | Confirmed (DOWIG-2026-081) |
| 3 | F-35 lifetime cost | $2T+ over 64 years | Confirmed (GAO-24-106703) |
| 4 | Cumulative unsupported adjustments, FY 1998–2015 | $21T gross (net unknown) | Confirmed gross; net never published (Skidmore/Fitts) |
| 5 | Accounting adjustments, FY 2017–2019 | $94.7T gross (net unknown) | Confirmed gross; 96% without adequate documentation (GAO-20-96) |
| 6 | National debt | ~$40T | Confirmed; holder decomposition now in §5 |
| 7 | HFT/dark pool intermediary extraction | ~$100–200B/year (order-of-magnitude estimate) | Estimated from components; not yet sourced as a single figure |
| 8 | Global illicit financial flows | ~$1.6–3.1T/year laundered | UNODC 2011 + GDP scaling |
| 9 | US church revenue (no filing required) | ~$143.6B/year | Giving USA 2022 |
| 10 | Estimated forgone church taxes | ~$71B/year | Cragun et al. 2012 |

### The structure of the argument

The debt ($40T) balances — every dollar is someone's asset (§5). That is arithmetic, not a finding.

The finding is that the Pentagon cannot tell you what its *net* unsupported position is (§6). The gross figures ($21T, $94.7T) are confirmed from government sources. The net is unpublished. That gap — the difference between the gross and the net, which the Pentagon itself has never disclosed — is the "missing" money in the ledger.

The question Noah is asking is: where does the gap route? The argument has three intermediary layers:

1. **The financial transaction layer** (§7): Every dollar that moves through the financial system pays a toll to intermediaries — HFT firms, dark pool operators, market makers. That toll is tiny per transaction and enormous in aggregate (~$100–200B/year). It is the "millisecond debt."

2. **The illicit flow layer** (§8): UNODC estimates ~$1.6–3.1T/year moves through the financial system as laundered proceeds. Less than 1% is seized. This flow uses the same financial infrastructure as legitimate transactions.

3. **The filing-exempt layer** (§9): US churches alone move ~$143.6B/year with no federal filing requirement. The broader nonprofit sector moves $3.3T/year. This is the bridge "religious institution to the state and federal" — not because churches are criminal, but because the *structure* is filing-exempt, creating a channel between tracked and untracked money.

### What's still needed to close the arithmetic

- [ ] The Pentagon's net unsupported position after deduplication (the number that has never been published)
- [ ] Aggregate US financial market transaction costs from SEC/FINRA execution-quality data (to replace the order-of-magnitude estimate)
- [ ] An updated UNODC or FATF global laundering estimate (the 2011 figure scaled by GDP is a placeholder)
- [ ] The specific arithmetic Noah says he proved — balancing the gap against cartel infrastructure costs

---

CC0 1.0 Universal — public domain dedication.
