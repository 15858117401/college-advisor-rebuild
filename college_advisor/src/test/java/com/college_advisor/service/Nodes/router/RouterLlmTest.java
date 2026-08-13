package com.college_advisor.service.Nodes.router;

import com.college_advisor.service.graph.client.RouterClient;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.InputStream;
import java.util.Properties;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class RouterLlmTest {

    private static RouterClient client;

    @BeforeAll
    static void setUp() throws Exception {
        Properties props = new Properties();
        try (InputStream in = RouterLlmTest.class.getClassLoader()
                .getResourceAsStream("application-local.properties")) {
            props.load(in);
        }
        client = new RouterClient(
                props.getProperty("dashscope.api-key"),
                props.getProperty("dashscope.model-name"));
    }

    // ─────────────────────────────────────────────────────────────────
    // simple_task: pure data lookup / filter / search — no personalization
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> simpleTaskInputs() {
        return Stream.of(
                // course attributes
                "What is STAT 432?",
                "How many credits is STAT 107?",
                "Is STAT 400 hard?",
                "What are the prerequisites for STAT 425?",
                "Does STAT 433 require attendance?",
                "How much workload does STAT 432 have per week?",
                "What is the average GPA in STAT 410?",
                "Describe STAT 200",

                // section info
                "When does STAT 432 meet?",
                "Who teaches STAT 400?",
                "What is the CRN for STAT 425?",
                "What time is STAT 107?",

                // prerequisite lookup (forward)
                "What do I need to take before STAT 432?",

                // reverse prerequisite
                "After taking STAT 107 what courses can I take?",
                "Which courses list STAT 400 as a prerequisite?",
                "What becomes available after I finish STAT 200?",

                // filtering
                "Which STAT courses are low difficulty?",
                "Are there STAT courses with a high average GPA?",
                "Which STAT courses don't require attendance?",
                "Which courses are required for the STAT major?",
                "Which STAT courses have light workload?",

                // semantic search
                "Are there STAT courses about machine learning?",
                "Which STAT courses teach Python?",
                "Are there STAT courses on Bayesian statistics?",
                "Are there STAT courses about data visualization?",
                "Are there any STAT courses related to probability theory?",
                "Are there any programming courses in the STAT department?",

                // graduation requirements
                "What are the graduation requirements for the STAT major?",
                "What required courses does the STAT major include?",
                "What are the advanced elective options for the STAT major?",

                // instructor lookup
                "What STAT courses does Professor Wang teach?",
                "Which STAT classes does Professor Smith offer?",
                "Who teaches STAT 432?",

                // Reddit opinion search
                "What do people say about STAT 432 on Reddit?",
                "Are there any Reddit discussions about Professor Smith at UIUC?",
                "What is the Reddit opinion on STAT 400?",

                // Rate My Professor
                "What is Professor Wang's rating on Rate My Professor?",
                "Is Professor Smith well rated?",
                "Look up Professor Johnson's reviews",

                // course comparison
                "Which is harder, STAT 400 or STAT 432?",
                "Compare the average GPA of STAT 107 and STAT 200",
                "Is STAT 410 or STAT 425 more work?",

                // bundled factual questions
                "What is STAT 432 and is it hard and how many credits?",
                "What are the prerequisites for STAT 400 and what is its average GPA?",
                "Who teaches STAT 107 and when does it meet?",
                "Which STAT courses are required and which are low difficulty?"
        );
    }

    @ParameterizedTest(name = "[simple_task] \"{0}\"")
    @MethodSource("simpleTaskInputs")
    void shouldRouteToSimpleTask(String input) {
        assertEquals("simple_task", client.classify(input));
    }

    // ─────────────────────────────────────────────────────────────────
    // build_single_plan: exactly ONE personalized advising goal,
    // WITH sufficient inline context (year + STAT major + completed courses + goal)
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> buildSinglePlanInputs() {
        return Stream.of(
                // recommendation — explicit year + major + completed courses + goal
                "I am a sophomore in the STAT major and I have completed STAT 100 and STAT 200. Recommend me 3 courses for next semester.",
                "I want to study data science. I am a junior in the STAT major and have already taken STAT 107 and STAT 200. Recommend me some courses.",
                "I am a junior in the STAT major and I have finished STAT 400. I am interested in probability theory. What courses do you recommend I take next?",
                "I want an easy elective for next semester. I am a senior in the STAT major and have satisfied all requirements except one free elective.",
                "I am a sophomore in the STAT major and have completed STAT 100. Recommend me courses — I prefer ones that don't require much attendance.",
                "I am a sophomore in the STAT major and have taken STAT 107, STAT 200, and CS 101. What courses do you recommend I take next semester?",
                "I want to go to grad school in statistics. I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. What courses should I prioritize?",
                "I want to keep my workload light this term. I am a senior in the STAT major with only STAT 425 and one elective left to complete.",
                "I am interested in programming. I am a junior in the STAT major and have taken STAT 200 and CS 225. Recommend me courses.",
                "I want to take 4 courses next semester. I am a freshman in the STAT major who has only completed STAT 100. What do you suggest?",
                "I am a sophomore in the STAT major with a 3.4 GPA and have completed STAT 200. Recommend me courses that are manageable so I can make the Dean's List.",

                // scheduling — explicit courses + constraints + build request
                "I am a junior in the STAT major and I want to take STAT 400 and STAT 432 next semester. Help me build a schedule that avoids Friday classes.",
                "I am a sophomore in the STAT major. I want to take 3 courses next semester with no 8am sections — STAT 410, STAT 425, and one elective. Build me a schedule.",
                "I am a senior in the STAT major. Build me a timetable for Fall semester — I need STAT 400 and STAT 200 and I prefer morning sections.",
                "I am a junior in the STAT major. I need to take STAT 432, STAT 400, and STAT 425 next semester. Help me arrange my schedule to avoid back-to-back 3-hour blocks.",

                // degree planning — explicit year + major + completed courses
                "I am a junior in the STAT major and have completed STAT 100, STAT 200, STAT 400, and STAT 410. Help me plan my remaining semesters to graduate on time.",
                "I am a freshman in the STAT major and have just completed STAT 100. I want to finish the major in 3 years. Help me plan.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. Help me make a multi-semester plan for the degree.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. Plan out my remaining semesters so I satisfy all prerequisites in the right order.",
                "I am a sophomore in the STAT major and have done STAT 100 and STAT 107. I want to graduate a semester early. Map out my degree path.",

                // GPA target — explicit current GPA + credit hours + year + major
                "I am a junior in the STAT major with a 3.0 GPA. I have completed STAT 200, STAT 400, and STAT 410. I want to improve my GPA next semester — what courses do you recommend I take?",
                "I am a sophomore in the STAT major with a 2.8 GPA. I have completed STAT 107 and STAT 200. I want easier courses next semester to improve my GPA — what do you recommend?"
        );
    }

    @ParameterizedTest(name = "[build_single_plan] \"{0}\"")
    @MethodSource("buildSinglePlanInputs")
    void shouldRouteToBuildSinglePlan(String input) {
        assertEquals("build_single_plan", client.classify(input));
    }

    // ─────────────────────────────────────────────────────────────────
    // course_planner subset — degree planning inputs from buildSinglePlanInputs
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> coursePlannerInputs() {
        return Stream.of(
                "I am a junior in the STAT major and have completed STAT 100, STAT 200, STAT 400, and STAT 410. Help me plan my remaining semesters to graduate on time.",
                "I am a freshman in the STAT major and have just completed STAT 100. I want to finish the major in 3 years. Help me plan.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. Help me make a multi-semester plan for the degree.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. Plan out my remaining semesters so I satisfy all prerequisites in the right order.",
                "I am a sophomore in the STAT major and have done STAT 100 and STAT 107. I want to graduate a semester early. Map out my degree path."
        );
    }

    // ─────────────────────────────────────────────────────────────────
    // scheduler subset — extracted from buildSinglePlanInputs for scheduler-specific tests
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> schedulerInputs() {
        return Stream.of(
                "I am a junior in the STAT major and I want to take STAT 400 and STAT 432 next semester. Help me build a schedule that avoids Friday classes.",
                "I am a sophomore in the STAT major. I want to take 3 courses next semester with no 8am sections — STAT 410, STAT 425, and one elective. Build me a schedule.",
                "I am a senior in the STAT major. Build me a timetable for Fall semester — I need STAT 400 and STAT 200 and I prefer morning sections.",
                "I am a junior in the STAT major. I need to take STAT 432, STAT 400, and STAT 425 next semester. Help me arrange my schedule to avoid back-to-back 3-hour blocks."
        );
    }

    // ─────────────────────────────────────────────────────────────────
    // planner: two or more separable advising goals, all with sufficient context
    // Note: cases requiring mid-execution clarify redirect are NOT included yet
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> plannerInputs() {
        return Stream.of(
                // ── freshman: empty completed-course list is valid context ─────────
                "I am a freshman in the STAT major and have not taken any college courses yet. I enjoy programming and data analysis — recommend courses that match my interests for this first semester, and also create a full 4-year degree plan to graduation.",

                // ── sophomore: recommend + schedule ──────────────────────────────
                "I am a sophomore in the STAT major and have completed STAT 100 and STAT 107. Recommend me courses for next semester, then build me a schedule around them.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. I want to take 3 courses next semester with no 8am sections — help me pick them and build a timetable.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. I know I need to take STAT 400 — recommend one more course to pair with it and then build me a schedule for next semester.",

                // ── sophomore: recommend + degree plan ───────────────────────────
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. Recommend what I should take next semester and also map out the rest of my degree.",
                "I am a sophomore in the STAT major and have completed STAT 100 and STAT 107. I want to go to grad school in statistics — recommend courses that will strengthen my application and also plan my remaining semesters.",
                "I am a sophomore in the STAT major and have completed STAT 100, STAT 107, and STAT 200. I want to keep my workload manageable — recommend lighter courses for next semester and also help me plan out the years ahead.",

                // ── junior: recommend electives + schedule ────────────────────────
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. I still need 2 electives — recommend them and then build me a schedule for next semester.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, STAT 410, and STAT 425. I need one more elective — help me choose it and also build a schedule for next semester that avoids Friday classes.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. I want to prepare for a career in data science — recommend relevant electives and then build my schedule for next semester.",

                // ── junior: recommend + degree plan ──────────────────────────────
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, and STAT 410. First recommend the 2-3 courses I should take next semester to fill my prerequisite gaps, then separately map out a semester-by-semester degree plan for my remaining 2 years.",
                "I am a junior in the STAT major and have completed STAT 200, STAT 400, STAT 410, and STAT 425. I want to apply to grad school — recommend courses that strengthen my application and also map out my remaining semesters.",

                // ── senior: pick elective + build final schedule ──────────────────
                "I am a senior in the STAT major and have completed all required courses except STAT 432 and one free elective. Help me pick the elective and then build my final semester schedule.",
                "I am a senior in the STAT major and have completed STAT 200, STAT 400, STAT 410, STAT 425, and STAT 432, but still need 2 electives to graduate. Help me choose them and also create a schedule for my last semester.",

                // ── with scheduling constraints ───────────────────────────────────
                "I am a junior in the STAT major and have completed STAT 200 and STAT 400. I have a part-time job on MWF mornings so I can only take afternoon or evening sections. Recommend my next courses and build a schedule around my availability.",
                "I am a sophomore in the STAT major and have completed STAT 107 and STAT 200. I do not want more than 3 courses next semester. Recommend what to take and arrange a timetable with no back-to-back classes."
        );
    }

    @ParameterizedTest(name = "[planner] \"{0}\"")
    @MethodSource("plannerInputs")
    void shouldRouteToPlanner(String input) {
        assertEquals("planner", client.classify(input));
    }

    // ─────────────────────────────────────────────────────────────────
    // clarify: personalized requests missing critical context, or too vague
    // ─────────────────────────────────────────────────────────────────
    public static Stream<String> clarifyInputs() {
        return Stream.of(
                // vague / no subject
                "Help me",
                "I have a question",
                "I need some advice",
                "Anything is fine",

                // personalized advising — no context at all
                "Help me choose courses",
                "Recommend me some courses",
                "What should I take next?",
                "What courses should I take?",
                "Help me plan my degree",
                "Build my schedule",
                "Make me a timetable",
                "Help me graduate on time",
                "What should I take this semester?",
                "I want to plan my next semester",
                "What would you recommend for me?",

                // has year/major but missing completed courses — can't advise without knowing what's done
                "I am a junior in the STAT major. What should I take next?",
                "I am a sophomore in STAT. Recommend me courses for next semester.",

                // GPA target without current GPA or credits
                "I want to raise my GPA, what should I take?",
                "Help me get a better GPA",
                "I want to make the Dean's List, what courses should I take?",

                // off-topic
                "What is 2 + 2?",
                "Tell me a joke",
                "What is the weather today?"
        );
    }

    @ParameterizedTest(name = "[clarify] \"{0}\"")
    @MethodSource("clarifyInputs")
    void shouldRouteToClarify(String input) {
        assertEquals("clarify", client.classify(input));
    }
}
