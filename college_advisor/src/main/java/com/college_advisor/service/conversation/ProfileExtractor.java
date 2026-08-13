package com.college_advisor.service.conversation;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.chat.ChatModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class ProfileExtractor {

    private static final Logger log = LoggerFactory.getLogger(ProfileExtractor.class);
    private static final ObjectMapper mapper = new ObjectMapper();

    private static final String EXTRACT_PROMPT =
            "Extract user profile information from the following conversation history.\n" +
            "Return ONLY a valid JSON object with these exact keys (use JSON null for anything not mentioned):\n\n" +
            "{\n" +
            "  \"year\": \"freshman\" | \"sophomore\" | \"junior\" | \"senior\" | null,\n" +
            "  \"completedCourses\": [\"COURSE_CODE\", ...] | null,\n" +
            "  \"preferences\": {\n" +
            "    \"noEarlierThan\": \"HH:MM\" | null,\n" +
            "    \"noLaterThan\": \"HH:MM\" | null,\n" +
            "    \"avoidDays\": [\"Monday\", ...] | null,\n" +
            "    \"noMandatoryAttendance\": true | false | null,\n" +
            "    \"workload\": \"light\" | \"medium\" | \"heavy\" | null,\n" +
            "    \"difficulty\": \"easy\" | \"medium\" | \"hard\" | null,\n" +
            "    \"minGpa\": <number> | null,\n" +
            "    \"goals\": \"<string>\" | null\n" +
            "  } | null,\n" +
            "  \"schedule\": {\"<COURSE_CODE>\": \"<CRN>\" | null, ...} | null\n" +
            "}\n\n" +
            "Rules: Only extract what was explicitly stated or shown in the assistant's response. " +
            "Do not infer. Output ONLY the JSON object, no explanation, no markdown fences.\n\n" +
            "CONVERSATION:\n";

    private final UserProfileStore profileStore;
    private final ChatModel model;

    public ProfileExtractor(UserProfileStore profileStore, ChatModel model) {
        this.profileStore = profileStore;
        this.model        = model;
    }

    /**
     * Extracts user profile from summary if it exceeds DISTILL_THRESHOLD. No-op otherwise.
     * All failures are caught and logged — never propagated to caller.
     */
    public void extractIfNeeded(String userId, String summary) {
        if (summary.length() <= DistillationService.DISTILL_THRESHOLD) return;
        try {
            String raw = model.chat(EXTRACT_PROMPT + summary);
            UserProfile profile = parseJson(raw);
            if (profile.isEmpty()) return;
            profileStore.mergeProfile(userId, profile);
            log.info("[profile-extractor] userId={} profile updated", userId);
        } catch (Exception e) {
            log.warn("[profile-extractor] userId={} failed, skipping: {}", userId, e.getMessage(), e);
        }
    }

    static UserProfile parseJson(String raw) throws Exception {
        String json = raw.strip();
        if (json.startsWith("```")) {
            int start = json.indexOf('\n') + 1;
            int end   = json.lastIndexOf("```");
            json = json.substring(start, end > start ? end : json.length()).strip();
        }

        JsonNode node = mapper.readTree(json);

        String year = textOrNull(node, "year");

        List<String> courses = null;
        if (node.has("completedCourses") && !node.get("completedCourses").isNull()) {
            courses = new ArrayList<>();
            for (JsonNode c : node.get("completedCourses")) courses.add(c.asText());
        }

        Map<String, Object> preferences = null;
        if (node.has("preferences") && !node.get("preferences").isNull()) {
            preferences = mapper.convertValue(node.get("preferences"), new TypeReference<>() {});
        }

        Map<String, Object> schedule = null;
        if (node.has("schedule") && !node.get("schedule").isNull()) {
            schedule = mapper.convertValue(node.get("schedule"), new TypeReference<>() {});
        }

        return new UserProfile(year, courses, preferences, schedule);
    }

    private static String textOrNull(JsonNode node, String field) {
        return (node.has(field) && !node.get(field).isNull()) ? node.get(field).asText() : null;
    }
}
