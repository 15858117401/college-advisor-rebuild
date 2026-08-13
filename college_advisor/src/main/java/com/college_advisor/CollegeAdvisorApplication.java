package com.college_advisor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CollegeAdvisorApplication {

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(CollegeAdvisorApplication.class);
        app.setAdditionalProfiles("local");
        app.run(args);
    }

}
