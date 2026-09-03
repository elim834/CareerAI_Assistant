using System.Collections.ObjectModel;

namespace frontend.Models
{
    public enum RecommendationSeverity
    {
        Critical,
        Warning,
        Info
    }

    public class RecommendationItem
    {
        public string Text { get; set; } = "";
        public RecommendationSeverity Severity { get; set; }

        public string IconText => Severity switch
        {
            RecommendationSeverity.Critical => "🔴",
            RecommendationSeverity.Warning => "🟡",
            _ => "🔵"
        };
    }

    public class PriorityItem
    {
        public int Id { get; set; }
        public string Title { get; set; } = "";
        public string DaysLeftDisplay { get; set; } = "";
        public string ScoreDisplay { get; set; } = "";
        public string PriorityLabel { get; set; } = "";
        public string PriorityIcon { get; set; } = "";
    }

    public class CalendarDayCell
    {
        public int Day { get; set; }
        public DateTime Date { get; set; }
        public bool IsCurrentMonth { get; set; }
        public bool IsToday { get; set; }
        public int DeadlineCount { get; set; }
        public ObservableCollection<ApplicationDto> DeadlineApps { get; set; } = new();
    }
}