package com.college_advisor.service.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import jakarta.annotation.Nullable;

/**
 * RateMyProfessor search tool.
 * Used by: SimpleTaskNode, RecommenderNode.
 */
public class ProfessorRatingTools {

    private final TavilyClient tavilyClient;

    public ProfessorRatingTools(TavilyClient tavilyClient) {
        this.tavilyClient = tavilyClient;
    }

    @Tool("在 Rate My Professor 上查询教授评分和评价。用于：用户想了解某教授的评分" +
         "（如'Wang 教授评分怎样'、'Is Professor Smith rated highly'）。返回评分页面摘要。")
    public String searchRateMyProfessor(
            @P("教授姓名，如 'Wang' 或 'John Smith'") String professorName,
            @P("学校名称，默认 'UIUC'（可选）") @Nullable String university) throws Exception {
        String uni = (university == null) ? "UIUC" : university;
        String query = professorName + " " + uni + " professor rating";
        return tavilyClient.search(query, "ratemyprofessors.com");
    }

    @Tool("在 Reddit 上搜索课程或教授的真实评价和讨论。用于：用户想了解某门课/某教授的口碑" +
         "（如'大家怎么评价 STAT 432'、'Professor Wang 好不好'）。返回相关帖子摘要。")
    public String searchReddit(
            @P("搜索词，如 'STAT 432 UIUC review' 或 'Professor Wang UIUC statistics'") String query) throws Exception {
        return tavilyClient.search(query, "reddit.com");
    }
}
