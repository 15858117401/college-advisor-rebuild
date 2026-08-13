package com.college_advisor.service.tools;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

public class TavilyClient {

    private static final String ENDPOINT = "https://api.tavily.com/search";

    private final String apiKey;
    private final HttpClient httpClient;
    private final ObjectMapper mapper;

    public TavilyClient(String apiKey) {
        this.apiKey = apiKey;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.mapper = new ObjectMapper();
    }

    /**
     * Searches Tavily and returns a JSON string of results.
     * @param query          search query
     * @param includeDomains optional domain restrictions (e.g. "reddit.com")
     */
    public String search(String query, String... includeDomains) throws Exception {
        ObjectNode body = mapper.createObjectNode();
        body.put("api_key", apiKey);
        body.put("query", query);
        body.put("search_depth", "basic");
        body.put("max_results", 5);

        if (includeDomains.length > 0) {
            ArrayNode domains = mapper.createArrayNode();
            for (String d : includeDomains) domains.add(d);
            body.set("include_domains", domains);
        }

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(ENDPOINT))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                .timeout(Duration.ofSeconds(30))
                .build();

        HttpResponse<String> response =
                httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            return mapper.writeValueAsString(
                    Map.of("error", "Tavily HTTP " + response.statusCode()));
        }

        JsonNode root = mapper.readTree(response.body());
        JsonNode results = root.path("results");
        if (results.isMissingNode()) {
            return mapper.writeValueAsString(Map.of("results", List.of()));
        }

        // Return only title, url, content per result
        ArrayNode slim = mapper.createArrayNode();
        for (JsonNode r : results) {
            ObjectNode item = mapper.createObjectNode();
            item.put("title",   r.path("title").asText(""));
            item.put("url",     r.path("url").asText(""));
            item.put("content", r.path("content").asText(""));
            slim.add(item);
        }
        return mapper.writeValueAsString(Map.of("results", slim));
    }
}
