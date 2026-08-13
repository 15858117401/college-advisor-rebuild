package com.college_advisor.eval.braintrust;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Thin REST client for the Braintrust experiment API.
 * No dependency on listener or graph code.
 */
public class BraintrustLogger {

    private static final String BASE_URL = "https://api.braintrustdata.com/v1";

    private final HttpClient   http;
    private final ObjectMapper mapper;
    private final String       apiKey;

    public BraintrustLogger(String apiKey) {
        this.apiKey  = apiKey;
        this.http    = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
        this.mapper  = new ObjectMapper();
    }

    /**
     * Creates a new experiment in Braintrust.
     *
     * @param projectName    e.g. "college-advisor"
     * @param experimentName e.g. "college-advisor-2026-04-29T14-00-00"
     * @return the experiment ID to pass to logEvent()
     */
    public String createExperiment(String projectName, String experimentName) throws Exception {
        Map<String, Object> body = Map.of(
                "project_name", projectName,
                "name",         experimentName
        );
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(BASE_URL + "/experiment"))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type",  "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                .timeout(Duration.ofSeconds(30))
                .build();

        HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new RuntimeException(
                    "Braintrust createExperiment failed: HTTP " + response.statusCode()
                    + " — " + response.body());
        }
        JsonNode idNode = mapper.readTree(response.body()).get("id");
        if (idNode == null || idNode.isNull()) {
            throw new RuntimeException(
                    "Braintrust createExperiment: response missing 'id' field — body: " + response.body());
        }
        return idNode.asText();
    }

    /**
     * Logs one eval row to an existing experiment.
     * HTTP errors are printed to stderr but do NOT throw — the eval loop continues.
     */
    public void logEvent(String experimentId, BraintrustEvent event) {
        try {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id",       event.spanId());
            row.put("input",    event.input());
            row.put("output",   event.output());
            row.put("metadata", event.metadata());
            row.put("metrics",  event.metrics());
            row.put("tags",     event.tags());

            Map<String, Object> body = Map.of("events", List.of(row));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(BASE_URL + "/experiment/" + experimentId + "/insert"))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Content-Type",  "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body)))
                    .timeout(Duration.ofSeconds(30))
                    .build();

            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                System.err.println("[BraintrustLogger] logEvent FAILED: HTTP "
                        + response.statusCode() + " — " + response.body());
            } else {
                System.out.println("[BraintrustLogger] logEvent OK: HTTP "
                        + response.statusCode() + " — " + response.body());
            }
        } catch (Exception e) {
            System.err.println("[BraintrustLogger] logEvent ERROR: " + e);
        }
    }
}
