# Full Graph Evaluation Results

- Cases: 36
- Route matches: 35/36 (97.2%)
- Execution errors: 0
- Concurrency: 10

## Case 1 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What are the prerequisites and credit hours for STAT 400?

### Final response

> **STAT 400 – Statistics and Probability I**
>
> - **Credit hours:** 4  
> - **Prerequisite:** MATH 231  
>
> This course is an introduction to mathematical statistics. Topics include probability, random variables, expectation, distribution functions, the central limit theorem, point estimation, confidence intervals, and hypothesis testing. It prepares students for STAT 410 and STAT 425, and it is the same course as MATH 463.

## Case 2 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> Show me all Spring 2026 sections and meeting times for STAT 107.

### Final response

> Here are all Spring 2026 sections for **STAT 107 (Data Science Discovery)**.
>
> ## Lectures
> | Section | CRN | Days | Time | Location | Instructor |
> |---------|-----|------|------|----------|------------|
> | L1 | 70317 | MWF | 10:00–10:50 AM | THEAT Lincoln Hall | Fagen-Ulmschneider, W / Flanagan, K |
> | L2 | 75730 | MWF | 11:00–11:50 AM | THEAT Lincoln Hall | Fagen-Ulmschneider, W / Flanagan, K |
>
> ## Laboratory-Discussions
> | Section | CRN | Days | Time | Location | Instructor |
> |---------|-----|------|------|----------|------------|
> | Y01 | 70318 | R | 11:00 AM–12:20 PM | 2036 Campus Instructional Facility | Chen, E |
> | Y02 | 70322 | R | 12:30–1:50 PM | 2036 Campus Instructional Facility | Hermon, M |
> | Y03 | 70326 | W | 2:00–3:20 PM | 2036 Campus Instructional Facility | Hunnius, J |
> | Y04 | 70327 | W | 3:30–4:50 PM | 1047 Sidney Lu Mech Engr Bldg | Hecht, T |
> | Y05 | 70329 | R | 11:00 AM–12:20 PM | 2018 Campus Instructional Facility | Hermon, M |
> | Y06 | 70330 | R | 12:30–1:50 PM | 3038 Campus Instructional Facility | Tsiamalos, E |
> | Y07 | 70331 | W | 2:00–3:20 PM | 1047 Sidney Lu Mech Engr Bldg | Hecht, T |
> | Y08 | 70332 | W | 3:30–4:50 PM | 3117 Everitt Laboratory | Hunnius, J |
> | Y09 | 70334 | R | 9:30–10:50 AM | 2078 Natural History Building | Khirwadkar, A |
> | Y10 | 70320 | R | 11:00 AM–12:20 PM | 3038 Campus Instructional Facility | Littlefield, S |
> | Y11 | 70321 | R | 12:30–1:50 PM | 4101 Materials Science & Eng Bld | Khirwadkar, A |
> | Y12 | 70333 | R | 2:00–3:20 PM | 2036 Campus Instructional Facility | Korkmaz, M |
> | Y13 | 74092 | R | 11:00 AM–12:20 PM | 1047 Sidney Lu Mech Engr Bldg | Zhang, J |
> | Y14 | 74093 | R | 12:30–1:50 PM | 1047 Sidney Lu Mech Engr Bldg | Zhang, J |
> | Y15 | 74094 | R | 11:00 AM–12:20 PM | 3018 Campus Instructional Facility | Tsiamalos, E |
> | Y16 | 74095 | R | 12:30–1:50 PM | 2018 Campus Instructional Facility | Chen, E |
> | Y17 | 74096 | W | 2:00–3:20 PM | 1043 Sidney Lu Mech Engr Bldg | Jarrold, G |
> | Y18 | 74097 | W | 3:30–4:50 PM | 136 Loomis Laboratory | Jarrold, G |
> | Y19 | 74098 | R | 9:30–10:50 AM | 300 Noyes Laboratory | Bao, Y |
> | Y20 | 74099 | R | 11:00 AM–12:20 PM | 1043 Sidney Lu Mech Engr Bldg | Zhou, X |
> | Y21 | 76949 | W | 2:00–3:20 PM | 156 Henry Administration Bldg | Korkmaz, M |
> | Y23 | 76955 | F | 3:30–4:50 PM | G32 Literatures, Cultures, & Ling | Adeline, M |
> | Y24 | 76958 | R | 8:00–9:20 AM | 136 Armory | Littlefield, S |
> | Y26 | 76964 | F | 2:00–3:20 PM | 106B6 Engineering Hall | Shimgekar, S |
> | Y27 | 76967 | F | 3:30–4:50 PM | G36 Literatures, Cultures, & Ling | Zhou, X |
>
> Both lectures (L1, L2) cover the same content, so you can pair either lecture with any lab-discussion section that fits your schedule. Note that Y22 and Y25 are not offered this term.

## Case 3 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> Which instructors have the highest historical average GPA for STAT 420?

### Final response

> Based on historical instructor GPA data for STAT 420, the following are the instructors ranked by their average GPA:
>
> | Instructor | Average GPA |
> |-----------|-------------|
> | **Unger, D.** | **3.82** |
> | Findley, K. | 3.59 |
> | Li, X. | 3.59 |
> | Yu, A. | 3.54 |
> | Deeke, J. | 3.47 |
> | Icaza, E. | 3.45 |
>
> **Unger, D.** holds the highest historical average GPA for STAT 420 at **3.82**.
>
> Note: These figures are historical averages and are not linked to specific sections or academic terms.

## Case 4 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What are the 2026-2027 graduation requirements for the Statistics BSLAS?

### Final response

> Here are the **2026–2027 graduation requirements** for the **Statistics, BSLAS** at the University of Illinois Urbana-Champaign, as returned from the official catalog:
>
> ---
>
> ## Statistics, BSLAS — Graduation Requirements
>
> - **Catalog year:** 2026–2027
> - **College:** College of Liberal Arts & Sciences
> - **Official source:** [Statistics, BSLAS](https://catalog.illinois.edu/undergraduate/las/statistics-bslas/#degreerequirementstext)
>
> ### Major and Supporting Coursework Overview
> The program overview states that required major and supporting coursework normally totals **70–72 hours**. At least **12 hours of 300- or 400-level coursework in the major** must be completed on the UIUC campus.
>
> The degree-requirement course table separately reports **42–44 total hours** for the Statistics coursework listed below. Both figures are retained because they describe different totals on the official page.
>
> ### Introductory and Preparatory Coursework — 17–19 hours
>
> **Calculus through MATH 241 — 11–12 hours** (sequence:)
> - MATH 220 — Calculus, or MATH 221 — Calculus I
> - MATH 231 — Calculus II
> - MATH 241 — Calculus III
>
> **Introductory Statistics — 3–4 hours** (select one:)
> - STAT 107 — Data Science Discovery
> - STAT 200 — Statistical Analysis
> - STAT 212 — Biostatistics
>
> **Linear Algebra — 3 hours** (select one:)
> - MATH 257 — Linear Algebra with Computational Applications
> - MATH 415 — Applied Linear Algebra
> - MATH 416 — Abstract Linear Algebra
>
> ### Statistical Core Coursework — 13 hours
> | Course | Hours |
> | :-- | --: |
> | STAT 400 — Statistics and Probability I | 4 |
> | STAT 410 — Statistics and Probability II | 3 |
> | STAT 425 — Statistical Modeling I | 3 |
> | STAT 426 — Statistical Modeling II | 3 |
>
> ### Advanced Statistics Electives — 12 hours
> Select four courses from the following list:
> - STAT 385 — Statistics Programming Methods
> - STAT 424 — Design of Experiments
> - STAT 427 — Statistical Consulting
> - STAT 428 — Statistical Computing
> - STAT 429 — Time Series Analysis
> - STAT 430 — Topics in Applied Statistics
> - STAT 431 — Applied Bayesian Analysis
> - STAT 432 — Basics of Statistical Learning
> - STAT 433 — Stochastic Processes
> - STAT 434 — Survival Analysis
> - STAT 440 — Statistical Data Management
> - STAT 443 — Professional Statistics
> - STAT 447 — Data Science Programming Methods
> - STAT 448 — Advanced Data Analysis
> - STAT 480 — Big Data Analytics
> - MATH 444 — Elementary Real Analysis, or MATH 447 — Real Variables
>
> ### Statistics Coursework Total
> The degree-requirement course table totals **42–44 hours**.
>
> ---
>
> Would you like details on any of these courses, section availability for Spring 2026, or historical GPA information for specific instructors?

## Case 5 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> Does the Mathematics BSLAS require an abstract algebra course?

### Final response

> Yes — the Mathematics BSLAS requires an abstract algebra course.
>
> Per the 2026–2027 catalog graduation requirements, the Major Core Requirements include:
>
> > **Abstract algebra** | MATH 417 — Intro to Abstract Algebra, or MATH 427 — Honors Abstract Algebra | 3
>
> So you must complete either MATH 417 or MATH 427 to satisfy the major core.

## Case 6 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> Find 400-level STAT courses worth four credit hours.

### Final response

> Here are the 400-level STAT courses carrying 4 credit hours:
>
> **Fixed 4 credit hours:**
> - STAT 400 — 4 Hours
> - STAT 408 — 4 Hours
> - STAT 448 — 4 Hours
>
> **Variable credit (can be taken for 3 or 4 credit hours):**
> STAT 410, STAT 420, STAT 425, STAT 426, STAT 427, STAT 428, STAT 429, STAT 430, STAT 431, STAT 432, STAT 433, STAT 434, STAT 437, STAT 440, STAT 443, STAT 447, STAT 463 — each listed as "3 or 4 Hours"
>
> Let me know if you'd like catalog details, sections, or instructor GPA stats for any of these.

## Case 7 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I am a junior in Statistics and have completed STAT 107, STAT 400, and STAT 410. What should I take next?

### Final response

> Before I give recommendations, I need to flag a discrepancy between what you told me and the student record I have on file.
>
> **You said:** You’re a junior in Statistics, and you’ve completed STAT 107, STAT 400, and STAT 410.
>
> **Your profile shows:** Your declared major is **Mathematics – Applied Mathematics** (GPA 2.92), and your transcript already lists many additional statistics courses completed, including:
> - STAT 207, STAT 385
> - STAT 425, STAT 426
> - STAT 432, STAT 440, STAT 448
> - Plus MATH 347, CS 225/233, and others
>
> This matters for advising because the “what next” answer looks very different depending on which record is accurate. Could you clarify?
>
> **Scenario A — Your stated record is accurate (only STAT 107, 400, 410 so far):**  
> Typical next steps in the UIUC Statistics sequence would include:
> - **STAT 425 – Applied Regression and Design** (natural follow-up to STAT 400/410; a core methods course)
> - **STAT 385 – Statistical Programming Methods** (if you haven’t had a dedicated programming-for-stats course)
> - **STAT 440 – Statistical Data Management** (useful, practical, and common for majors)
> - **STAT 432 – Basics of Statistical Learning** (if you want the machine-learning track)
>
> **Scenario B — Your on-file profile is accurate (advanced STAT courses already done):**  
> Then you’re well past the core sequence, and we’d be talking about capstone/consulting options (e.g., STAT 427 Statistical Consulting), electives like time series or Bayesian methods, or whether to prioritize the math requirements — not about STAT 425/432.
>
> Could you confirm which scenario reflects your actual situation? Also, if you can pull up your DARS audit or tell me which specific STAT requirements remain for your degree, I can give you a much more precise plan.

## Case 8 — route mismatch

- Expected route: `catalog_lookup`
- Actual route: `advising`

### User query

> I need one easy STAT elective to graduate and would prefer a class with a higher historical GPA.

### Final response

> Here's what I can and can't do to help you find an easy STAT elective:
>
> **What I can do:** Use the professor-research skill to pull student experiences — Rate My Professors reviews and r/UIUC discussions — for specific STAT courses and instructors you're considering, including workload and difficulty signals.
>
> **What I can't do directly:** I don't have access to a historical GPA distribution lookup tool for UIUC, so I can't verify course-level average GPAs myself. I can combine student-reported difficulty/grade sentiment with the official course facts you bring me.
>
> A couple of quick notes from your profile to help target the right courses:
>
> - You've already completed a heavy STAT sequence: **STAT 400, 410, 425, 426, 432, 440, 448, 385** (plus STAT 200 and STAT 207), so most of the standard "easy" 400-level options are already off your list.
> - For an **applied math major** with your GPA profile (2.71 cumulative, 2.92 major), a lower-intensity 300-level or applied STAT elective may fit better than another theory-heavy 400-level course — but that depends on which courses your degree audit still counts as eligible.
>
> **To give you a useful recommendation, I need:**
>
> 1. The list of STAT electives your degree audit still shows as **not yet completed and eligible** (from DARS or your advisor's approved list).
> 2. Any constraints — e.g., must be 300+ level, on-campus, or a specific semester preference.
>
> Once you share those, I'll research the top candidates' instructors and student experiences so you can pick one that's both easy and a good fit.

## Case 9 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> Plan my next semester with no classes before 10 AM, no Friday classes, and a maximum of 15 credits.

### Final response

> I'd love to help plan your next semester, but I don't have access to the live UIUC Schedule of Classes, so I can't look up which sections meet at which times. To build a schedule that works for you — no classes before 10 AM, no Friday classes, and 15 credits or fewer — I'll need a bit more from you.
>
> Here's what I need:
>
> 1. **Courses you're considering** — Do you have a target course list? For reference, your profile shows you've completed the core Math/Stat sequence (MATH 220–347, STAT 200–448, CS 101–340, etc.) as a Math–Applied Math major with a 2.71 cumulative GPA.
>
> 2. **Remaining degree requirements** — If you share your degree audit or tell me what requirements are still unmet (e.g., specific 400-level math courses, gen eds, or a particular elective), that will help me recommend options.
>
> 3. **Course times/days** — Once you know which courses you're eyeing, share the section meeting times from the Course Explorer (e.g., "MATH 412, TR 11:00–12:20"). Or, if you paste the full list of sections, I can filter out any sections that start before 10 AM or meet on Fridays, and check the total credit count.
>
> 4. **Instructor preferences (optional)** — Tell me which professors you're considering, and I can look into their ratings and student experiences via Rate My Professors and r/UIUC to help you choose between sections.
>
> Once you send the course list and section times, I'll put together a plan that meets your constraints and stays within 15 credits.

## Case 10 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I am a sophomore majoring in Mathematics and want to graduate one semester early. Build a course plan for me.

### Final response

> I can help you plan for early graduation, but I want to be upfront: I can’t build an accurate plan from your profile alone. Here’s what I can see and what I’m missing.
>
> ## What I can see from your profile
> - **Major:** Mathematics – Applied Mathematics (major GPA 2.92, cumulative 2.71)
> - **Completed courses** include a strong math/stat/CS foundation: MATH 220, 231, 241, 347; STAT 200, 207, 400, 410, 425, 426, 432, 440, 448, 385; CS 124, 128, 173, 225, 233, 340 — plus gen eds (HIST, ANTH, EALC, THEA, etc.) and writing (BTW 250, ESL 115).
>
> ## What I need to build a real plan
>
> 1. **Your DARS/degree audit** — the most important piece. It shows exactly which requirements remain for the Applied Math concentration, such as which MATH 400/500-level electives are needed, whether STAT courses count toward math requirements, any remaining CS/quantitative requirements, and gen ed or campus-level requirements like Advanced Composition. Note: BTW 250 may or may not satisfy that.
> 2. **Current term and registration status** — Are you in your 4th semester now? Have you already registered for next term?
> 3. **Total credit hours earned** — This determines how close you are to the 120-hour graduation threshold, which drives whether “one semester early” is feasible.
> 4. **Any courses already planned** for upcoming semesters.
> 5. **Constraints** — For example, do you need a manageable course load given your GPA (2.71 cumulative), or are you planning to retake/replace any grades?
>
> ## Preliminary sketch (to be validated against DARS)
>
> Assuming you’re finishing your sophomore year, a typical early-grad path would look like:
>
> - **Junior year:** Finish the remaining core math sequence (e.g., MATH 347 is done; likely MATH 412/413, 414/415, or 424 depending on track) plus applied math electives and any remaining STAT requirements.
> - **Senior year (single semester):** Capstone/advanced electives and any leftover gen eds — with the bulk of requirements already cleared by then.
>
> But this is only a guess until I see the audit.
>
> **Next step:** If you can upload or paste your DARS audit, and confirm your current semester and credit count, I’ll turn that into a semester-by-semester plan with specific course options. If you’d also like, I can research particular professors via Rate My Professors and r/UIUC for any courses in the plan — just let me know which ones.

## Case 11 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I enjoy machine learning but dislike theoretical proofs. Which STAT courses would fit me best?

### Final response

> Based on your transcript, you already have a strong applied and computational statistics foundation—STAT 385, 400, 410, 425, 426, 432, 440, and 448—so this is an easy fit assessment.
>
> **Best fits if you like ML and dislike proofs:**
>
> - **STAT 542 (Statistical Learning)** — The natural next step after STAT 432. It’s UIUC’s flagship ML course: heavy on modeling, prediction, and R-based implementation, with projects and much less proof than a mathematical statistics course. You have the prerequisites (STAT 425/426-level background), but note it’s a graduate-level course, so check enrollment restrictions and GPA requirements.
> - **STAT 525 or STAT 540 (Computational/Computing for Statistics)** — Both are methods-and-implementation oriented (simulation, resampling, computing) rather than theorem-proving. If you like writing code and seeing methods work on data, these are strong options.
> - **STAT 571 (Multivariate Analysis)** — Applied multivariate techniques (PCA, clustering, discriminant analysis) that pair well with your ML interests. Expect some matrix algebra, but the emphasis is on application rather than formal proof.
>
> **Courses to steer away from:**
>
> - **STAT 510/511 (Mathematical Statistics I/II)** — Proof-heavy, theory-first courses, the opposite of what you enjoy. You already took STAT 410, the undergraduate theory course; the graduate sequence doubles down on that.
> - Any further theory seminars or probability-theory electives.
>
> **A few things that would help refine this:**
>
> 1. Are you looking for **undergraduate-level (400-level) or graduate-level (500-level)** courses? Your degree is in Applied Mathematics, so the answer may depend on how many remaining hours you need and whether you want to count graduate courses.
> 2. Are you considering **STAT courses specifically**, or would you also be open to **CS 441 (Applied Machine Learning)**? It’s very aligned with your interests and tends to be less theoretical than CS 446.
> 3. Do you have a specific semester’s schedule in mind? Instructor quality varies a lot for STAT 542, and I can research specific professors if you’d like.
>
> If you can tell me which of those you’re targeting, I can dig into specific sections and instructors for you.

## Case 12 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> 帮我选一下下学期的课。

### Final response

> 好的！我很乐意帮你规划下学期的课程。为了给出有针对性的建议，我需要先了解一些信息：
>
> ## 我需要知道的信息
>
> 1. **你现在是大几？计划哪年毕业？** 这会影响选课节奏和必修课优先级。
>
> 2. **你有最近的学位审核（Degree Audit）吗？** 你是想了解还差哪些毕业要求，还是已经有了具体的候选课程清单？
>
> 3. **下学期的课程有没有已经看中的？** 比如你在考虑某几门课，想比较它们的难度、老师或搭配。
>
> 4. **你选课时的偏好是什么？**
>    - 希望课程量（学分）大概多少？
>    - 这学期想冲高GPA（轻松一点），还是愿意上难度大的课？
>    - 有没有特别感兴趣的领域（统计、CS、纯数、应用方向）？
>
> 5. **下学期是否有实习、找工作、研究等时间安排？** 这会影响推荐的课程负荷。
>
> ## 我目前看到的情况
>
> 从你的成绩单来看，你在 **应用数学** 方向已经修了不少课：
> - **统计类**：STAT 400/410/425/426/432/440/448/385（统计方向已经相当深入）
> - **CS 类**：CS 124/128/173/225/233/340（计算机基础扎实）
> - **数学类**：MATH 220/231/241/347（已完成微积分和入门证明课）
>
> 你的累计GPA是 2.71，专业课GPA是 2.92。如果你这学期希望稳一点、提升GPA，我可以帮你规划一个难度均衡的课表；如果你想冲难度更高的数学课（比如 MATH 285、MATH 415、MATH 441、MATH 461 等），我也可以结合你的情况分析。
>
> 你先把上面的信息告诉我，我就能给你具体的选课建议啦！

## Case 13 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> STAT 420 怎么样？

### Final response

> **STAT 420 — Methods of Applied Statistics（应用统计方法）**
>
> **课程概况**
> - 学分：3 或 4 学分
> - 内容：基于微积分的应用统计方法系统覆盖，包括简单和多元回归、相关、方差分析（ANOVA）与协方差分析、多重比较、拟合优度检验、列联表、非参数方法、检验的功效等；强调各种检验方法在何时、为何适用以及如何使用。
> - 先修要求：STAT 408 或 STAT 400；MATH 231 或同等水平；了解基础矩阵运算；或经授课教师同意。
> - 课程历史数据：累计约 1,519 名学生、20 个教学班，整体平均 GPA 3.58。
>
> **历史授课教师平均 GPA（不区分具体学期/班级）**
>
> | 教师 | 平均 GPA |
> |---|---|
> | Unger, D. | 3.82 |
> | Findley, K. | 3.59 |
> | Li, X. | 3.59 |
> | Yu, A. | 3.54 |
> | Deeke, J. | 3.47 |
> | Icaza, E. | 3.45 |
>
> 如果你是想了解本学期（Spring 2026）的排课、某位具体老师的评价，或者这门课是否适合你的背景，告诉我你的情况（比如已经学过哪些统计课），我可以进一步帮你查询。

## Case 14 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> Can I still graduate on time?

### Final response

> I'd be happy to help you figure that out, but I need a bit more information before I can give you a definitive answer.
>
> Here's what I can already see in your profile:
>
> - Major: Mathematics – Applied Mathematics
> - Cumulative GPA: 2.71; major GPA: 2.92 — both comfortably above the typical 2.0 graduation minimums, though some programs and courses have their own grade floors, so that's not a guarantee by itself.
> - You've completed a substantial list of courses across math, stats (STAT 400/410/425/426/432/440/448/385), CS, and gen eds.
>
> What I still need to determine "on time":
>
> 1. Your catalog year — the year you entered UIUC, since that determines which degree requirements apply.
> 2. Your intended graduation term (e.g., Spring 2026, Fall 2026) — "on time" is relative to this.
> 3. Your total completed credit hours (a count, not just course names) and how many you're registered for this semester.
> 4. Your DARS audit — the only reliable way to see which requirements are unmet. You can pull it from Self-Service under "Degree Audit."
> 5. Whether you have any holds, incomplete grades, or repeated courses that could affect progress.
>
> A couple of things I can already flag:
>
> - With a heavy STAT course load already done (including STAT 425, 432, 440, 448), you may be close to or past the stats/elective requirements for the Applied Math major — but I can't confirm without the audit.
> - Your GPA is fine for graduation, but if you're aiming for grad school or specific post-grad plans, that's a separate conversation.
>
> Suggested next step: Pull your DARS audit, note your total completed credit hours and catalog year, and tell me your target graduation term. With those in hand, I can walk through what's left and whether your planned timeline is realistic. You can also bring the same audit to your Math advisor for a second opinion.
>
> Want to start with the audit, or do you already know your credit count and catalog year off the top of your head?

## Case 15 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> What course should I take next?

### Final response

> I’m happy to help you plan your next step! Before recommending a specific course, I want to be transparent about what I can and can’t tell from your profile.
>
> **What I can see:**
> - You’re a **Mathematics – Applied Mathematics** major with a major GPA of 2.92 and cumulative GPA of 2.71.
> - You’ve completed a strong statistics sequence: STAT 400, 410, 425, 426, 432, 440, 448, 385.
> - You have a solid math core: MATH 220, 231, 241, 347.
> - You also have meaningful computer science exposure: CS 101, 124, 128, 173, 225, 233, 340.
>
> **What I’d need from you to make a useful recommendation:**
>
> 1. **Which term are you planning for?** Fall 2025, Spring 2026, or summer?
> 2. **What’s your goal?** Are you nearing graduation, planning graduate school (e.g., statistics, data science, applied math), or targeting a specific job or internship?
> 3. **What remains on your degree audit?** If you can share which general-education, math, or statistics requirements are still unmet, that would help me pinpoint options. A DARS audit would be ideal.
> 4. **Are you already considering any courses?** If you have a few in mind, I can help you weigh them — including using professor research tools if instructor choice matters to you.
>
> One observation: with your extensive STAT background and applied math focus, natural next options could include higher-level applied math courses (e.g., MATH 441/442 differential equations, MATH 415/416 applied linear algebra) or advanced data science / ML-adjacent courses. But I don’t want to guess without knowing your remaining requirements and goals. Tell me more and I’ll narrow it down!

## Case 16 — route matched

- Expected route: `out_of_scope`
- Actual route: `out_of_scope`

### User query

> What will the weather be like in Chicago this weekend?

### Final response

> I’m not sure what “this” refers to. Could you provide more context or clarify what you’d like to discuss?

## Case 17 — route matched

- Expected route: `out_of_scope`
- Actual route: `out_of_scope`

### User query

> Can you debug this Python function for me?

### Final response

> Sorry, I’m not sure what you’re referring to. Could you clarify what you mean or what you’d like help with?

## Case 18 — route matched

- Expected route: `out_of_scope`
- Actual route: `out_of_scope`

### User query

> Write a five-paragraph essay about the history of Illinois.

### Final response

> It looks like the draft you'd like me to rewrite wasn't included in your message. Please paste the draft, and I'll rewrite it for you.

## Case 19 — route matched

- Expected route: `out_of_scope`
- Actual route: `out_of_scope`

### User query

> I have had a severe headache for three days. What medication should I take?

### Final response

> I don't see a draft in your message. Could you please paste the text you'd like me to rewrite?

## Case 20 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> What are the Statistics major requirements, and based on the courses I have completed, create a semester-by-semester plan for graduation.

### Final response

> Great question — but before laying out a plan, I need to flag a couple of things that affect how accurate it can be.
>
> ## Things to clarify first
>
> 1. **Your declared major is Mathematics – Applied Mathematics**, not Statistics. Are you planning to (a) switch majors to Statistics, (b) add Statistics as a second major, or (c) just exploring? This changes the plan significantly. For example, a second major may share many requirements, so fewer new courses would be needed.
> 2. **I don’t have access to your official degree audit (DARS) or your current catalog year’s requirements.** I can give a draft plan based on the typical UIUC B.S. in Statistics (LAS) curriculum and your transcript, but it must be verified against your DARS before you register. Catalog year matters because requirements have shifted over time.
>
> ## How your completed courses map to a typical Statistics B.S.
>
> Assuming the standard LAS Statistics curriculum, here’s what you appear to have already satisfied:
>
> | Requirement area | Typical courses | Your completed courses |
> |---|---|---|
> | Calculus sequence | MATH 220/221, 231, 241 | ✅ All three |
> | Math foundation | MATH 347 or MATH 415 | ✅ MATH 347 |
> | Intro statistics | STAT 200 or equivalent | ✅ STAT 200, STAT 207 |
> | Statistical theory | STAT 400, 410, 425, 426 | ✅ All four |
> | Statistical computing / data | STAT 385, 432, 440, 448 | ✅ All four |
> | CS requirement | CS 101/124/125 | ✅ CS 101, CS 124 (plus more) |
> | Advanced composition | BTW 250 or equivalent | ✅ BTW 250 |
> | Gen eds (humanities, social science, natural science) | — | ✅ Largely complete (HIST, ANTH, EALC, CHEM, IB, etc.) |
>
> You’ve already completed a very large share of the Statistics major — likely around 80–90% of the major-specific coursework, depending on catalog year.
>
> ## Likely remaining items (to be verified in DARS)
>
> - **STAT 430** (if it’s still a required core course in your catalog year)
> - Possibly **one statistics elective** (e.g., STAT 420, STAT 433, STAT 458, or an approved upper-level option)
> - **LAS foreign language requirement** — LAS usually requires proficiency through the 3rd semester of a language (e.g., through the 103 level). FR 156 appears to be a culture/film course rather than a language sequence, and EALC 230 is a culture course, so this could still be open. Let me know if you have AP/placement credit or transfer credit.
> - Any remaining campus gen ed / credit-hour minimums
>
> ## Draft semester-by-semester plan (3 semesters, assuming fall/spring/fall)
>
> **Semester 1 (Fall)**
> - STAT 430 (core, if required)
> - STAT elective (one of STAT 420/433/458, per DARS)
> - Begin or continue foreign language if needed (e.g., FR 101 or placement-appropriate course)
>
> **Semester 2 (Spring)**
> - Second STAT elective or advanced option (if required)
> - Continue language (if needed)
> - Any remaining gen ed / open elective to maintain full-time load
>
> **Semester 3 (Fall — graduation)**
> - Final required STAT course
> - Finish language sequence (if needed)
> - Any last gen ed or elective credits
>
> If language isn’t an issue and no extra electives are required, you could plausibly finish in **two semesters**, which your transcript history (you’ve taken 40+ courses) suggests is realistic.
>
> ## What I need to finalize this
>
> To turn this draft into a registration-ready plan, please share:
> 1. **Your DARS audit** or the specific catalog year you’re under
> 2. Confirmation of **switch vs. second major**
> 3. Your **intended graduation term** and typical credit load per semester
> 4. Whether you have **foreign language credit** (AP/transfer/placement)
>
> Also worth noting: your cumulative GPA is 2.71 (major GPA 2.92), which is comfortably above LAS’s usual 2.0 graduation threshold, so GPA isn’t a barrier — but if you’re switching majors, make sure you meet the current declaration criteria (usually a minimum GPA in prerequisite courses), which your math/stat grades look strong enough to satisfy.

## Case 21 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I am a Statistics major who has completed STAT 107, STAT 400, and STAT 410. Build my next-semester schedule based on my academic history, with no classes before 10 AM and no Friday classes.

### Final response

> Thanks for reaching out—I’d be happy to help plan next semester, but I need to flag a couple of things first.
>
> ## 1. Mismatch in your academic history
>
> You said you’re a **Statistics major** who has completed **STAT 107, STAT 400, and STAT 410**.  
> The academic history I have on file instead shows:
>
> - **Major:** Mathematics – Applied Mathematics  
> - **Major GPA:** 2.92 | **Cumulative GPA:** 2.71  
> - **STAT courses completed:** STAT 200, STAT 207, STAT 385, STAT 400, STAT 410, STAT 425, STAT 426, STAT 432, STAT 440, STAT 448  
> - **STAT 107 is not listed** in your completed courses
>
> Could you clarify which is accurate—did you change majors, is there transfer credit not reflected here, or is your profile out of date? This matters because it changes which courses are appropriate for you to take next.
>
> ## 2. I don’t have the data needed to guarantee time/day constraints
>
> To build a schedule with **no classes before 10 AM** and **no Friday classes**, I would need the actual course schedule (days/times) for the target semester and a catalog of what’s offered. I don’t have access to a course catalog or registrar schedule data—my available tools only cover professor reputation research (Rate My Professors and r/UIUC discussions).
>
> To move forward, I need:
>
> 1. **Target semester** (e.g., Fall 2025, Spring 2026)  
> 2. **Degree requirements** you still need (or a degree audit, if you have one)  
> 3. **Candidate courses** you’re considering—if you give me a list, I can research instructors and workloads to help you choose
>
> ## 3. What I *can* help with
>
> Once you name the courses you’re considering, I can research UIUC professor ratings and student experiences (e.g., workload, teaching style) using my professor research tools, and weigh them against your GPA trend (2.71 cumulative) to suggest a balanced course load.
>
> Want to start by clarifying your major/history and giving me a list of 3–5 courses you’re considering?

## Case 22 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I have completed STAT 400 and MATH 257, and I want a career in machine learning. Which two statistics courses should I take next semester?

### Final response

> Thanks — and great context. STAT 400 plus linear algebra is exactly the right foundation for ML, so you’re on a strong path. But before I recommend a pair, I need to flag something in your profile:
>
> **Discrepancy:** Your profile lists STAT 400 as completed, but does **not** list MATH 257. It also shows you've *already* completed a long list of STAT courses: STAT 207, 385, 410, 425, 426, 432, 440, and 448. That changes the advice substantially, so can you confirm which of those you’ve actually taken?
>
> Here’s how I’d advise you in each scenario:
>
> **If you really have completed STAT 410/425/426/432/440/448 already:**
> - **STAT 542 (Statistical Learning)** — This is the stats department’s graduate-level ML course (regularization, trees, SVM, boosting, etc.) and the natural next step after STAT 432. It’s the single most career-relevant statistics course for ML. Caveat: it’s a 500-level course, so you’ll likely need instructor approval, and with a 2.71 cumulative GPA you should expect a demanding workload and possibly a GPA requirement to check with the department.
> - **STAT 433 (Stochastic Processes)** — Useful if you’re interested in probabilistic ML, reinforcement learning, or Bayesian methods. Alternatively, if the topic for the semester is ML/data-science related, **STAT 430 (Topics in Applied Statistics)** can be a great flexible choice.
>
> **If you haven’t actually taken the upper-level sequence yet:**
> - **STAT 425 (Statistical Modeling I)** — Regression modeling, the bread-and-butter tool underneath most ML.
> - **STAT 432 (Basics of Statistical Learning)** — The undergrad ML course in the stats department; builds directly on STAT 400 and is the prerequisite mindset for STAT 542 later.
>
> One more note: since your major GPA (2.92) is stronger than your cumulative, a focused semester of stats courses is reasonable — but if you want to pursue STAT 542, talk to the instructor and confirm eligibility first.
>
> Could you confirm your actual completed STAT/MATH list? Once you pick the pair, I can also research the specific instructors for you.

## Case 23 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I work every weekday until 2 PM and can take at most 12 credits. Build a Statistics schedule that fits my availability and keeps me on track to graduate.

### Final response

> Thanks — I can build a real schedule once I have a few more details. Right now I’m missing three key pieces:
>
> 1. **Which Statistics credential are you targeting?**  
>    Your profile lists you as a Mathematics–Applied Mathematics major, and you’ve already completed a large STAT block: STAT 200, 207, 385, 400, 410, 425, 426, 432, 440, 448. Are you aiming for a Statistics minor, a second major, or just elective depth? That changes which courses remain.
>
> 2. **Your degree audit / remaining requirements.**  
>    I don’t have visibility into your DARS or which specific requirements are still unmet. If you can share the remaining STAT (and any other) requirements, I can tell you exactly what’s left.
>
> 3. **Target term.**  
>    I don’t have access to the official course schedule — section times, online/evening offerings — for any specific term. UIUC typically offers some STAT courses in the late afternoon, evening, or online formats, but I can’t confirm times without the schedule for the term you’re planning.
>
> **What I can do once we have that:**
>
> - Cross-check each remaining course against your 2 PM cutoff and 12-credit cap. Typical upper-level STAT courses are 3–4 credits, so 3–4 courses would be realistic.
> - Flag evening, online, or self-paced options if the term schedule supports them.
> - Research professors for the specific courses you’re considering, using UIUC ratings and student discussions (r/UIUC), so you can pick sections that fit your workload tolerance — especially relevant given your cumulative GPA of 2.71, where instructor fit and manageable workloads matter.
>
> **Quick heads-up on your stats background:** you’ve already completed the core STAT sequence (400/410/425/426) plus applied/data courses (432/440/448/385/207), so a Statistics minor likely has very few requirements left — possibly just one or two courses depending on your catalog year.
>
> Could you share:
>
> 1. The credential you’re targeting,
> 2. Your DARS or remaining requirements, and
> 3. The term you’re planning for?
>
> Once I have those, I can draft a concrete, credit-checked schedule.

## Case 24 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I transferred into the Statistics major with 60 credits. Help me create a semester-by-semester plan to graduate within two years.

### Final response

> Thanks for reaching out! I'd love to help you map this out, but I want to flag a few things before laying out a plan — right now I don't have enough reliable information to give you an accurate two-year schedule.
>
> ## A discrepancy to resolve first
>
> Your trusted student profile lists your major as **Mathematics – Applied Mathematics** (major GPA 2.92, cumulative GPA 2.71), not Statistics. If you're switching/transferring into Statistics, that's fine, but I need to know:
>
> - Are you officially admitted to the Statistics major, or in the process of applying/transferring within UIUC?
> - Which catalog year and degree audit are you working from?
>
> ## What I'd need to build an accurate plan
>
> A semester-by-semester plan for the Statistics major depends on things I don't have access to:
>
> 1. **Your official degree audit (DARS) or transfer credit evaluation** — 60 credits transferring is great, but it matters *what* they satisfied (core math/stat courses vs. gen eds vs. electives).
> 2. **Which of your completed courses were accepted toward the Statistics major** — you've already taken STAT 200, 400, 410, 425, 426, 432, 440, 448, and 385, plus MATH 220–347. If all of those count, you may already be close to done with the core. If some were taken outside the major or don't articulate, the plan changes significantly.
> 3. **The current Statistics degree requirements** — I don't have a copy of the department's official curriculum, and I don't want to invent requirements for you.
> 4. **Course-offering constraints** — several STAT courses are only offered in specific semesters, and prerequisites chain tightly.
>
> ## What I *can* do in the meantime
>
> - If you can share your DARS/degree audit (or paste the list of which requirements are unmet), I can help sequence remaining courses semester by semester.
> - If you send which STAT/MATH courses were officially counted toward the major, I can check prerequisite chains and identify bottlenecks.
> - I can also research specific instructors for the STAT courses you still need once we know which ones those are — that's a strength of the professor-research tools I have.
>
> **Bottom line:** send me your degree audit (or tell me your catalog year and which transferred courses were applied to the major), and confirm the Statistics vs. Applied Math situation, and I'll build you a concrete two-year semester-by-semester plan. Without that, any schedule I'd draft would be guesswork — which I won't do with something this important.

## Case 25 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I failed STAT 400 last semester but still want to graduate on time. How should I adjust my course plan for the next three semesters?

### Final response

> That’s a frustrating setback, but it’s very fixable. Retaking STAT 400 and rebalancing your next three semesters can absolutely keep you on track for graduation.
>
> Before laying out a concrete plan, I need to flag a few things and ask for some details, because your situation has some specifics that matter.
>
> **One thing I noticed:** Your record shows STAT 400 in your completed courses, along with several upper-level stats courses (STAT 410, 425, 426, 432, 440, 448). Since you’re telling me you failed it last semester, I want to confirm what your degree audit actually shows — do you need to retake STAT 400 for credit (e.g., the math department requires a C or better in major courses), or was it an elective that could potentially be substituted (e.g., MATH 461)?
>
> **Initial framework for the next three semesters:**
>
> 1. **Retake STAT 400 ASAP** — in the very first of your next three semesters, or during summer if that’s available. It’s a foundation course, and delaying it could bottleneck other courses and add risk to your timeline.
>
> 2. **Keep the retake semester lighter** (~13–15 credits). Pair STAT 400 with only one heavy course and maybe a lighter gen-ed or elective. Given your cumulative GPA (2.71) and major GPA (2.92), this semester is also a chance to protect your GPA while you regain momentum.
>
> 3. **Check the repeat-grade policy for your college.** At UIUC, repeated courses generally leave both grades on your transcript and both count toward your GPA — there’s no grade replacement. A strong retake (A/B) is important for proving competency, but confirm the exact policy with your college advisor.
>
> 4. **Run a fresh DARS audit** to see exactly what remains: math core, concentration electives, and total credits. That determines how much room you have in each of the three semesters.
>
> **To give you a real semester-by-semester plan, I need:**
>
> - Which three semesters are we talking about (e.g., Fall 2025, Spring 2026, Summer 2026)? Is summer enrollment an option?
> - What does your DARS show as remaining requirements and total credits?
> - Are any courses you still need gated on STAT 400 as a prerequisite?
> - How many credits do you typically handle well (given your GPA, I’d lean toward 12–15)?
>
> And one more thing — when you retake STAT 400, choosing the right instructor can make a big difference. Want me to research STAT 400 professors (Rate My Professors + r/UIUC) so you can pick a section that fits how you learn? Just tell me which term you’re targeting.

## Case 26 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> Given that I have finished STAT 400 and prefer applied projects over theory, should I take STAT 420 or STAT 425 next?

### Final response

> Quick heads-up: I tried to pull r/UIUC student discussions on both courses, but the Reddit research tool is currently unavailable due to a configuration error (missing API key), so I can’t give you student-experience evidence right now. I’d normally use that to compare workload and “applied vs. theory” vibes, so feel free to ask again later.
>
> One important flag from your record: **STAT 425 already shows as completed** in your profile, along with STAT 410, 426, 432, 440, 448, and 385. So I want to make sure we’re answering the right question:
>
> **If you’re asking about STAT 420 vs. STAT 425 for a future course:**
> - **STAT 420 (Methods of Applied Statistics)** is the applied, data-analysis-oriented option — the natural fit if you prefer applied projects over theory.
> - **STAT 425 (Statistical Modeling I)** is more modeling/mathematical foundations-focused — and you’ve already taken it.
>
> **If you meant STAT 420 vs. a different course** (e.g., STAT 430, STAT 440, or a CS/data-science elective), let me know which one.
>
> Could you clarify what you’re actually considering next? Also useful to know:
> 1. Is this for your Math-Applied major requirements, or an elective?
> 2. Do you need it to satisfy a specific degree requirement?
> 3. What STAT courses are left on your plan?
>
> With that, I can give a more grounded recommendation — and once the Reddit tool is back up, I can pull real student feedback on the specific course and instructors.

## Case 27 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I plan to study abroad next spring and will not be able to take STAT courses then. Arrange my remaining major courses around that semester.

### Final response

> Here’s a suggested plan for your remaining math major coursework around a spring study-abroad semester.
>
> **One caveat first:** I can see your completed courses, but I don’t have access to your degree audit or official list of remaining requirements. I’m inferring the typical Applied Math (BS) requirements, so confirm everything against your DARS before committing.
>
> **What your profile already tells me**
> - Your STAT coursework looks essentially complete: STAT 400, 410, 425, 426, 432, 440, 448, and 385 are all done, so no STAT requirement should force itself into your schedule.
> - Your CS requirements also look covered: CS 101, 124, 128, 173, 225, 233, and 340.
> - That leaves the MATH-side core as the likely remaining work: **linear algebra (MATH 415/416)**, **differential equations (MATH 286 or 441)**, and a **numerical analysis course (MATH 470/471/472 or CS 450)**, plus possibly advanced MATH electives depending on your concentration.
>
> **Suggested sequencing around your spring abroad**
>
> **Fall (before study abroad) — on campus**
> - Take MATH 415 (Applied Linear Algebra) early — it’s a prerequisite for numerical analysis.
> - Take MATH 441 (Differential Equations) — it only requires MATH 241, which you’ve completed.
> - Keep the rest of your schedule lighter if possible, since both are 4xx math courses.
>
> **Spring (study abroad) — no STAT courses**
> - Take general education, language, or free electives abroad that you’ve confirmed will transfer back.
> - Avoid core UIUC MATH requirements abroad — math sequence courses rarely transfer cleanly, and prerequisite chains are easier to manage on campus.
> - Verify transfer credit with your study-abroad advisor before enrolling.
>
> **Fall (after return) — on campus**
> - Take MATH 471 (Basic Numerical Analysis) or CS 450 — with MATH 415 done, you’ll meet the prerequisite.
> - Add any remaining advanced MATH electives or leftover requirements in this term.
>
> **Questions that would tighten this plan**
> 1. What is your expected graduation term? That determines how many on-campus semesters you have after the abroad term.
> 2. Can you share your DARS or the official remaining-requirements list? I inferred the remaining courses, but your concentration may require specific electives I can’t see (e.g., MATH 447/448/453, additional STAT hours, or a capstone).
> 3. Do you plan to take any more STAT electives at all? If not, the “no STAT abroad” constraint is automatically satisfied and the plan above works as-is.
>
> Also worth noting: your cumulative GPA is 2.71, so I’d lean toward not stacking the pre-abroad fall with more than the two MATH courses above — protecting your major GPA (2.92) is easier with a balanced term before a disruptive semester.

## Case 28 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I want a data science internship next summer and have completed STAT 107 and STAT 207. Recommend courses for next semester that fit that goal.

### Final response

> Great goal to target. Looking at your transcript, you're actually in a strong spot already — you've completed the full STAT data science sequence (STAT 385, 400, 410, 425, 426, 432, 440, 448) plus CS 225/233/340. For a summer data science internship, the typical gaps left are **databases/SQL**, **applied machine learning**, and **big-data tooling** — plus having a portfolio project to point to.
>
> ## Recommended courses for next semester
>
> **1. CS 411 — Database Systems** (highest priority)  
> SQL, relational design, and big-data topics (NoSQL, Spark) are the most commonly tested skills in data science internship interviews. This is probably your single most valuable next course.
>
> **2. One applied ML option:**  
> - **CS 441 — Applied Machine Learning** (project-heavy, great for portfolio/recruiting) or  
> - **CS 412 — Introduction to Data Mining** (more breadth, slightly lighter theory)
>
> Your STAT 432 background gives you the theory; what internships want is demonstrated applied work, so pick whichever has a stronger project component.
>
> **3. A data-engineering/big-data elective if offered:**  
> - **STAT 447 — Data Science Programming Methods** (Python/R tooling for data science) or  
> - **STAT 430** if the topic that semester covers something relevant (e.g., deep learning, text mining). Check the current topic before committing.
>
> **4. Optional, only if you have room:** CS 361 (Stats for CS) would be redundant given your STAT 400/410 — skip it.
>
> ## Things to weigh given your GPA
>
> Your cumulative GPA (2.71) means course selection strategy matters. CS 411 + CS 441 together is a solid but heavy load. If that worries you, pair the technical core with lighter, interest-based courses (you've done well with courses like HORT/KIN/LEAD) to protect your GPA while keeping the technical signal strong.
>
> ## What I'd need to refine this further
>
> - Which term is "next semester" (Spring 2026, or summer/fall)?
> - Target credit load?
> - Are you willing to take on CS-heavy courses, or do you prefer to stay mostly in STAT/MATH?
> - Any course restrictions (CS courses are often capped for non-CS majors)?
>
> Also, if you want, I can research specific professors for CS 411/441 (ratings, workload, teaching style) once you've narrowed it down — just say the word.

## Case 29 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I am double-majoring in Mathematics and Statistics and have completed the calculus sequence. Help me choose courses that make progress toward both majors without exceeding 15 credits.

### Final response

> Based on your record, here’s where you stand and a suggested path. Note that your trusted profile lists your major as **Mathematics – Applied Mathematics** (not yet the Statistics double major), so there are a couple of things to confirm below.
>
> ## What your transcript already shows
>
> - **Calculus sequence complete:** MATH 220, 231, 241  
> - **Proofs/intro math:** MATH 347 done  
> - **Stats core largely done:** STAT 400, 410, 425, 440, 448, plus electives STAT 426, 432, 385 — that’s most of the Statistics major core already  
> - **Supporting CS done:** CS 173, CS 225, CS 233, CS 340  
>
> So you’re in a good position: the limiting factor for progress is now mostly the **math major requirements**, not the stats side.
>
> ## A sample schedule (≈13–15 credits) that serves both majors
>
> Since many statistics courses are already complete, I’d prioritize math courses that also strengthen your stats work:
>
> 1. **MATH 441 – Differential Equations** (3–4 cr) — a standard requirement for the Applied Math concentration and commonly counted as related work for Statistics majors. Prereq: MATH 241, which you’ve completed.  
> 2. **MATH 415 (Applied Linear Algebra) or MATH 416 (Abstract Linear Algebra)** (3–4 cr) — linear algebra is a core math requirement and underpins a lot of statistical methodology (regression, multivariate analysis). Given your applied focus, 415 may fit better; 416 is the proof-based option.  
> 3. **MATH 461 – Probability Theory** (3–4 cr) — the rigorous treatment of probability. It typically satisfies math major requirements and pairs with your STAT background (STAT 400/410 already done). Check whether it double-counts, or whether you should instead take a remaining STAT elective like **STAT 430/431** depending on your statistics concentration.  
> 4. **Optional 4th course** — if you want to reach ~15 credits, add a lighter course (e.g., a general education or a 2–3 cr elective). Given your cumulative GPA is 2.71, I’d keep the technical load at 3 courses and not overload a fourth heavy quant course.
>
> ## What I need from you to finalize this
>
> 1. **Your DARS or degree audit** (or the official requirement lists) — this is the only way to confirm exactly which courses count toward each major and whether STAT/MATH courses can double-count.  
> 2. **Your Statistics concentration** (e.g., Applied Statistics, Data Science, etc.) — it changes which remaining STAT courses you need.  
> 3. **Your preference for rigor/style** — proof-heavy (416, 417, 444) vs. applied/computational (415, 441), and whether you want a course that mostly advances one major at a time.
>
> Once you share those, I can narrow this down to a precise ≤15-credit schedule. If you’d also like, I can research instructor ratings/reviews for the specific sections you’re considering.

## Case 30 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I need three courses next semester, prefer instructors with higher historical GPAs, and want to avoid proof-heavy classes. What should I take based on my completed STAT 400 and STAT 410?

### Final response

> Based on your transcript, you've already completed the standard STAT 400/410 pipeline — STAT 425, STAT 426, STAT 432, STAT 440, STAT 448, and STAT 385 are all done. That narrows things down quite a bit, and it matters for your “no proof-heavy” constraint.
>
> A few observations:
>
> - **STAT 430 (Probability Theory)** is the natural next theory course after STAT 410, but it’s heavily proof-based — I’d steer you away given your preference.
> - **STAT 433 (Stochastic Processes)** is the main remaining upper-level applied STAT course that directly builds on STAT 400/410. It’s typically computation/application-oriented rather than proof-heavy, so it’s a strong candidate.
> - If you’re open to **MATH options** for your Applied Math major, many advanced courses (e.g., MATH 413, MATH 441) are proof-heavy too, so we’d want to filter those out carefully.
>
> To give you a real recommendation, I need a bit more info:
>
> 1. **Which courses are you actually choosing between?** Do you have a shortlist of sections for next semester, or are you working from a degree audit / list of remaining requirements?
> 2. **What are your remaining degree requirements?** If you’re near graduation, the best three courses may be the ones that satisfy leftover requirements rather than just STAT electives.
> 3. **Do you know the instructors for the sections you’re considering?**
>
> One important caveat on the “higher historical GPA” preference: I can’t pull official grade-distribution-by-instructor data directly — that lives in UIUC’s public GPA/grade data tools (e.g., the university’s course grade reporting sites). What I *can* do is research instructor reputation and student experience for specific instructors via Rate My Professors and r/UIUC, and combine that with your stated preferences. The official GPA data and the subjective reviews are two separate things, and I’ll keep them straight.
>
> If you tell me which courses (and ideally which instructors) you’re weighing, I’ll research them for you right away.

## Case 31 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I am a senior Statistics major with two semesters left. Review my completed courses and help me plan how to finish my remaining degree requirements on time.

### Final response

> I’m glad to help you map out your final two semesters. Before I suggest a concrete plan, I need to flag something important and get a few details from you, since I don’t have access to your official degree audit.
>
> ## Important discrepancy
>
> You mentioned that you’re a **Statistics major**, but the student profile I have lists your major as **Mathematics – Applied Mathematics** (major GPA 2.92, cumulative GPA 2.71). Your transcript does include a strong statistics sequence, so a Statistics major is plausible, but I don’t want to plan around the wrong requirements.
>
> **Can you confirm your official declared major(s)?** If you’ve changed majors or are double-majoring, that changes the plan significantly.
>
> ## What I can see from your completed courses
>
> You have 46 completed courses, and a few things stand out:
>
> - **Statistics core looks essentially complete:** STAT 200, 207, 385, 400, 410, 425, 426, 432, 440, 448.
> - **Strong math foundation:** MATH 220, 231, 241, 347, plus CS 173.
> - **Good technical/CS electives:** CS 101, 124, 128, 225, 233, 340.
> - **General education breadth appears well covered**, including composition via BTW 250/ESL 115.
>
> ## What I need to build an accurate plan
>
> Degree completion depends on your specific catalog year, track, and remaining checkpoints. Please share:
>
> 1. **Your official DARS/degree audit** or your department’s major checklist — this is the ground truth for what remains.
> 2. **Your declared major(s)** and any concentration/track.
> 3. **Total credit hours earned so far** and how many you still need for graduation (most UIUC majors require at least 120).
> 4. **Any known missing requirements**, such as advanced composition, foreign language, or a capstone/project course.
> 5. **Your preferred schedule or semester load** — for example, a lighter final semester might help if you’re job hunting.
>
> ## A caution
>
> With a cumulative GPA of 2.71, it’s worth checking whether any remaining requirements or a second major have a **minimum GPA requirement** or grade floor in your catalog year, and whether you’re near any academic probation thresholds. I don’t want to assume the specifics — your DARS and department advisor can confirm.
>
> Once you confirm your major and share your DARS or key missing-requirement details, I can suggest a concrete two-semester sequence, including which STAT/MATH courses would satisfy remaining requirements and which electives make sense given your applied math background.

## Case 32 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What do Rate My Professors and Reddit say about Professor Albert Yu?

### Final response

> I couldn't retrieve professor reviews for Albert Yu right now — both search tools returned configuration errors (the underlying search service isn't available), so I have no Rate My Professors or Reddit data to report.
>
> This is a tooling issue, not evidence that no reviews exist. You could try again later, or if you'd like, I can still look up official course catalog details or historical GPA statistics for a specific STAT course (for example, STAT 400) that Professor Yu teaches. Just let me know which course you're interested in.

## Case 33 — route matched

- Expected route: `advising`
- Actual route: `advising`

### User query

> I prefer well-structured lectures and lower exam difficulty. Should I take STAT 400 with Albert Yu or David Unger?

### Final response

> I wasn't able to pull up reviews for either professor right now. Both the Rate My Professors and Reddit search tools are currently unavailable due to a configuration error (a missing API key), so I have no evidence to compare Albert Yu and David Unger for STAT 400.
>
> Rather than guess, I’d rather not give an uninformed recommendation on something as important as instructor choice. A few options:
>
> 1. **Retry shortly** — the tool issue may be temporary; I can run the searches again whenever you’d like.
> 2. **Ask me again with a nudge** — if you’ve seen anything about either instructor (e.g., a syllabus, a friend’s experience, a Reddit thread), I can help interpret it.
> 3. **Fall back on general STAT 400 knowledge** — both instructors teach the course regularly, but I can’t responsibly compare their lecture structure or exam difficulty without actual review data.
>
> If it helps in the meantime, your profile shows you’ve already completed STAT 400-level work (STAT 410, 425, 426, 432, 440, 448) with a strong math background, so you’re well positioned for the course material regardless. But for the specific “well-structured lectures / easier exams” fit, I’d want the review evidence before advising you.
>
> Want me to retry the search now, or later?

## Case 34 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What do students say about Professor David Douglas at UIUC?

### Final response

> I couldn't find any student opinions about Professor David Douglas right now — both research sources returned errors:
>
> - **Rate My Professors search**: unavailable (configuration error — TAVILY_API_KEY is required).
> - **Reddit (r/UIUC) search**: unavailable (same configuration error).
>
> This means I currently have **no evidence either way** about what students say about him — it's a lack of available data, not evidence that there are no reviews.
>
> A couple of options:
> - **Retry** the search in a bit, in case the tool configuration is fixed.
> - If you can share **the specific course code** (e.g., STAT 400) or confirm the department, that would help me narrow the search once the sources are back up.
>
> Would you like me to try again?

## Case 35 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What is Professor Albert Yu's Rate My Professors rating?

### Final response

> I couldn't retrieve Professor Albert Yu's Rate My Professors rating right now — the Rate My Professors search tool is currently returning a configuration error, rather than an empty result list.
>
> Feel free to try again in a moment, or let me know if you'd be interested in something else, like Reddit discussions about him or historical GPA statistics for one of his STAT courses.

## Case 36 — route matched

- Expected route: `catalog_lookup`
- Actual route: `catalog_lookup`

### User query

> What does Reddit say about Professor Albert Yu for STAT 400?

### Final response

> I wasn't able to retrieve Reddit discussions about Professor Albert Yu for STAT 400. The r/UIUC search tool returned a configuration error (`TAVILY_API_KEY is required`), so that source is currently unavailable rather than having no results. You could try again later, or if you'd like, I can look up official STAT 400 section details and historical instructor GPA statistics instead.
