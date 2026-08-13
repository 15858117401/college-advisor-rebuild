package com.college_advisor.ingest;

import com.college_advisor.service.rag.CatalogIngestionService;
import com.college_advisor.service.rag.client.EmbeddingClient;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.jdbc.core.JdbcTemplate;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Properties;

public class IngestApplication {

    public static void main(String[] args) throws Exception {
        Properties props = new Properties();
        try (InputStream in = IngestApplication.class.getResourceAsStream("/application-ingest.properties")) {
            props.load(in);
        }

        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl(props.getProperty("spring.datasource.url"));
        hikari.setUsername(props.getProperty("spring.datasource.username").strip());
        hikari.setPassword(props.getProperty("spring.datasource.password").strip());

        try (HikariDataSource ds = new HikariDataSource(hikari)) {
            JdbcTemplate jdbc = new JdbcTemplate(ds);

            EmbeddingClient embeddingClient = new EmbeddingClient(
                    props.getProperty("dashscope.api-key"),
                    props.getProperty("dashscope.embedding-model-name"),
                    Integer.parseInt(props.getProperty("ingest.output-dimensionality", "768"))
            );

            CatalogIngestionService service = new CatalogIngestionService(
                    jdbc, embeddingClient,
                    props.getProperty("ingest.major-code", "STAT")
            );

            String markdown;
            try (InputStream md = IngestApplication.class.getResourceAsStream("/stat.md")) {
                markdown = new String(md.readAllBytes(), StandardCharsets.UTF_8);
            }
            service.ingest(markdown);
            System.out.println("Ingest complete.");
        }
    }
}
