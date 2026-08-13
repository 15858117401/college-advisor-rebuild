package com.college_advisor.service.rag.dto;

import java.util.List;

public record ParsedCatalog(String graduationPreamble, List<CourseDraft> courses) {}
