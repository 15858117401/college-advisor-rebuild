package com.college_advisor.service.rag.client;

import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.model.openai.OpenAiEmbeddingModel;

/**
 * Wraps langchain4j {@code OpenAiEmbeddingModel} (DashScope-compatible) to expose a simple {@code float[]} API.
 */
public class EmbeddingClient {

    private final OpenAiEmbeddingModel embeddingModel;

    public EmbeddingClient(String apiKey, String embeddingModelName, int outputDimensionality) {
        this.embeddingModel = OpenAiEmbeddingModel.builder()
                .baseUrl("https://dashscope.aliyuncs.com/compatible-mode/v1")
                .apiKey(apiKey)
                .modelName(embeddingModelName)
                .dimensions(outputDimensionality)
                .build();
    }

    /**
     * @return embedding values, length {@code outputDimensionality}
     */
    public float[] embedText(String text) {
        if (text == null || text.isBlank()) {
            throw new IllegalArgumentException("text must not be blank");
        }
        try {
            Embedding embedding = embeddingModel.embed(text).content();
            return embedding.vector();
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Embed failed: " + e.getMessage(), e);
        }
    }
}
