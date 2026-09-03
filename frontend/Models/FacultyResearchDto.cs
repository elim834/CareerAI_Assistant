namespace frontend.Models
{
    public class FacultyResearchDto
    {
        public string? ResearcherName { get; set; }
        public List<string>? RecentTopics { get; set; }
        public string? Summary { get; set; }
        public List<string>? Sources { get; set; }
    }
}