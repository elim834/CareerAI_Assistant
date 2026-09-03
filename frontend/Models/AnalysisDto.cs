namespace frontend.Models
{
    public class AnalysisResponse
    {
        public int ApplicationId { get; set; }
        public AnalysisDto? Analysis { get; set; }
    }

    public class AnalysisDto
    {
        public double? AcceptanceScore { get; set; }
        public string? Reasoning { get; set; }
        public string? VisaSummary { get; set; }
        public string? SuggestedFocus { get; set; }
        public List<string>? Risks { get; set; }
        public List<string>? ActionPlan { get; set; }
        public string? LanguageRequirementStatus { get; set; }
        public string? AnalyzedAt { get; set; }
    }
    
    public class LastAnalysisResponse
    {
        public bool Analyzed { get; set; }
        public AnalysisDto? Analysis { get; set; }
    }
}